#!/usr/bin/env python3
"""
PropChain Demo Seed Script
==========================
Drops ALL existing collections and seeds fresh demo data for a clean walk-through.

Usage:
    cd backend
    python seed.py                    # backend must be running on localhost:8000
    python seed.py --url http://...   # custom backend URL
    python seed.py --db-only          # skip API calls (only direct DB inserts)

Accounts seeded (password: Demo@1234 for all):
    demo@propchain.in     -- Arjun Sharma   (buyer / primary demo user)
    seller@propchain.in   -- Priya Nair     (property seller)
    investor@propchain.in -- Vikram Mehta   (fractional investor)
    ravi@propchain.in     -- Ravi Kumar     (suspicious property owner)
"""

import sys
import os
import hashlib
import json
import uuid
import time
import argparse
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME     = os.getenv("DB_NAME", "propchain_db")

ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://localhost:8000/api", help="Backend API base URL")
ap.add_argument("--db-only", action="store_true", help="Skip API calls (DB inserts only)")
args = ap.parse_args()

if not args.url.startswith(("http://", "https://")):
    args.url = "http://" + args.url
BASE = args.url.rstrip("/")

OK, ERR, SKP = "OK ", "ERR", "-- "


# ─────────────────────────────────────────────────────────────────────────────
# HASH HELPER  (mirrors utils/hashing.py exactly — do NOT change)
# ─────────────────────────────────────────────────────────────────────────────

GENESIS_HASH = "0" * 64


def compute_hash(block_index, property_id, data, previous_hash, timestamp):
    s = json.dumps(
        {
            "block_index":   block_index,
            "property_id":   property_id,
            "data":          data,
            "previous_hash": previous_hash,
            "timestamp":     timestamp,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(s.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# HTTP HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def post(path, data=None, params=None, token=None):
    url = f"{BASE}{path}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    body = json.dumps(data or {}).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read()).get("detail", "")
        except Exception:
            pass
        print(f"  [{ERR}] {path} -> HTTP {e.code}: {detail}")
        return None
    except URLError as e:
        print(f"  [{ERR}] Cannot reach backend ({BASE}): {e.reason}")
        return None


def get_token(email, password="Demo@1234"):
    res = post("/auth/login", {"email": email, "password": password})
    return (res or {}).get("token")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 0: CONNECT + DROP ALL COLLECTIONS
# ─────────────────────────────────────────────────────────────────────────────

print("\n[STEP 0] Connecting to MongoDB and dropping collections...")
try:
    from pymongo import MongoClient, ASCENDING
    from passlib.context import CryptContext
except ImportError as e:
    print(f"  [{ERR}] Missing dependency: {e}")
    print("         Run: pip install pymongo passlib[bcrypt]")
    sys.exit(1)

try:
    sync_client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
    sync_client.admin.command("ping")
except Exception as e:
    print(f"  [{ERR}] Cannot connect to MongoDB at {MONGODB_URL}")
    print(f"         {e}")
    sys.exit(1)

sync_db = sync_client[DB_NAME]

COLLECTIONS = [
    "blockchain_ledger",
    "properties",
    "users",
    "transactions",
    "fractional_holdings",
    "deals",
]
for name in COLLECTIONS:
    sync_db[name].drop()
    print(f"  [{OK}] Dropped: {name}")

# Recreate all indexes upfront (mirrors database.py init_db)
sync_db["users"].create_index([("email", ASCENDING)], unique=True, name="unique_email")
sync_db["blockchain_ledger"].create_index(
    [("property_id", ASCENDING), ("block_index", ASCENDING)],
    unique=True, name="unique_property_block",
)
sync_db["blockchain_ledger"].create_index(
    [("hash", ASCENDING)], unique=True, name="unique_hash"
)
sync_db["properties"].create_index(
    [("id", ASCENDING)], unique=True, name="idx_property_id"
)
sync_db["deals"].create_index([("id", ASCENDING)], unique=True, name="unique_deal_id")
sync_db["deals"].create_index([("property_id", ASCENDING)], name="idx_deal_property")
sync_db["deals"].create_index([("buyer_email", ASCENDING)],  name="idx_deal_buyer")
sync_db["deals"].create_index([("seller_email", ASCENDING)], name="idx_deal_seller")
print(f"  [{OK}] Indexes created")

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: USERS (direct pymongo insert — bypasses startup seed conflict)
# ─────────────────────────────────────────────────────────────────────────────

print("\n[STEP 1] Seeding users...")

START_TS = "2026-01-01T09:00:00"

USERS = [
    {
        "id":             str(uuid.uuid4()),
        "name":           "Arjun Sharma",
        "email":          "demo@propchain.in",
        "password":       pwd_ctx.hash("Demo@1234"),
        "phone":          "+91-9876543210",
        "aadhaar":        "XXXX-XXXX-4567",
        "created_at":     START_TS,
        "kyc_verified":   True,
        "wallet_balance": 50_000_000,   # Rs 5 Cr
    },
    {
        "id":             str(uuid.uuid4()),
        "name":           "Priya Nair",
        "email":          "seller@propchain.in",
        "password":       pwd_ctx.hash("Demo@1234"),
        "phone":          "+91-9876543211",
        "aadhaar":        "XXXX-XXXX-8901",
        "created_at":     START_TS,
        "kyc_verified":   True,
        "wallet_balance": 10_000_000,   # Rs 1 Cr
    },
    {
        "id":             str(uuid.uuid4()),
        "name":           "Vikram Mehta",
        "email":          "investor@propchain.in",
        "password":       pwd_ctx.hash("Demo@1234"),
        "phone":          "+91-9876543212",
        "aadhaar":        "XXXX-XXXX-2345",
        "created_at":     START_TS,
        "kyc_verified":   True,
        "wallet_balance": 25_000_000,   # Rs 2.5 Cr
    },
    {
        "id":             str(uuid.uuid4()),
        "name":           "Ravi Kumar",
        "email":          "ravi@propchain.in",
        "password":       pwd_ctx.hash("Demo@1234"),
        "phone":          "+91-9876543213",
        "aadhaar":        "XXXX-XXXX-6789",
        "created_at":     START_TS,
        "kyc_verified":   False,
        "wallet_balance": 1_000_000,    # Rs 10 L
    },
]

sync_db["users"].insert_many(USERS)
for u in USERS:
    print(f"  [{OK}] {u['name']:<18} {u['email']}")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: PROP-HIST01 — Full blockchain showcase (all 10 tx types, 12 blocks)
#
# Timeline: Priya Nair registers a Juhu bungalow, gets it verified, tokenizes
# it, then sells to Arjun Sharma via 3-installment deal. Vikram Mehta holds
# 100 fractional tokens.  All blocks inserted directly so chain is always INTACT.
# ─────────────────────────────────────────────────────────────────────────────

print("\n[STEP 2] Building PROP-HIST01 blockchain (12 blocks, all tx types)...")

PID        = "PROP-HIST01"
DEAL_ID    = "DEAL-HIST0001"
MKT_VAL    = 42_000_000.0   # asking price
NEGOTIATED = 40_000_000.0   # agreed price
ADVANCE    = 4_000_000.0
N_EMI      = 3
EMI_AMT    = round((NEGOTIATED - ADVANCE) / N_EMI, 2)  # 12_000_000.0


def ts(year, month, day, hour=9, minute=0):
    return datetime(year, month, day, hour, minute, 0, tzinfo=timezone.utc).isoformat()


_hist_blocks = []
_prev_hash   = GENESIS_HASH


def _blk(idx, tx_type, data, timestamp):
    global _prev_hash
    h = compute_hash(idx, PID, data, _prev_hash, timestamp)
    block = {
        "block_index":      idx,
        "property_id":      PID,
        "transaction_type": tx_type,
        "data":             data,
        "previous_hash":    _prev_hash,
        "timestamp":        timestamp,
        "minted_by":        "PropChain-Mock",
        "hash":             h,
    }
    _hist_blocks.append(block)
    _prev_hash = h
    return block


# Block 0 — GENESIS
b0 = _blk(0, "GENESIS", {
    "owner_name":           "Priya Nair",
    "owner_aadhaar_last4":  "8901",
    "property_address":     "14, Juhu Tara Road, Mumbai, Maharashtra - 400049",
    "area_sqft":            6500.0,
    "property_type":        "Residential",
    "market_value":         MKT_VAL,
    "registration_number":  "SRV/MH/JHU/2025/0099",
    "registration_status":  "REGISTERED",
}, ts(2025, 11, 1))

# Block 1 — DOCUMENT_VERIFICATION (AI result: AUTHENTIC)
b1 = _blk(1, "DOCUMENT_VERIFICATION", {
    "document_type":  "Title Deed + Encumbrance Certificate",
    "document_hash":  hashlib.sha256(b"juhu-bungalow-title-deed-2025").hexdigest(),
    "fraud_score":    0.04,
    "is_authentic":   True,
    "flags":          [],
    "verdict":        "AUTHENTIC",
    "verified_by":    "PropChain-AI (Amazon Nova Lite)",
    "registry_checks": {
        "owner_match":      True,
        "encumbrance_free": True,
        "area_match":       True,
    },
}, ts(2025, 11, 5, 11))

# Block 2 — STATUS_UPDATE (Sub-Registrar approves)
b2 = _blk(2, "STATUS_UPDATE", {
    "new_status":      "VERIFIED",
    "previous_status": "REGISTERED",
    "reason":          "All documents verified. No encumbrances found.",
    "updated_by":      "Sub-Registrar Office, Juhu, Mumbai",
}, ts(2025, 11, 6, 10))

# Block 3 — FRACTIONAL_MINT (Priya tokenizes the bungalow)
b3 = _blk(3, "FRACTIONAL_MINT", {
    "total_tokens":  1000,
    "token_price":   42_000,
    "token_symbol":  f"{PID}-TKN",
    "owner_name":    "Priya Nair",
    "yield_percent": 8.5,
}, ts(2025, 11, 10, 14))

# Block 4 — FRACTIONAL_TRANSFER (Vikram Mehta buys 100 tokens)
b4 = _blk(4, "FRACTIONAL_TRANSFER", {
    "from_holder":      "Priya Nair",
    "to_holder":        "Vikram Mehta",
    "investor_email":   "investor@propchain.in",
    "tokens_purchased": 100,
    "amount_paid":      4_200_000,
}, ts(2025, 11, 15, 16))

# Block 5 — DEAL_INITIATED (Arjun makes an offer)
b5 = _blk(5, "DEAL_INITIATED", {
    "deal_id":           DEAL_ID,
    "buyer_name":        "Arjun Sharma",
    "buyer_email":       "demo@propchain.in",
    "negotiated_price":  NEGOTIATED,
    "advance_amount":    ADVANCE,
    "installments_total": N_EMI,
    "monthly_emi":       EMI_AMT,
    "message":           "Interested in immediate possession. Happy to pay in 3 installments.",
}, ts(2025, 12, 1, 9))

# Block 6 — DEAL_ACCEPTED (Priya accepts)
b6 = _blk(6, "DEAL_ACCEPTED", {
    "deal_id":           DEAL_ID,
    "seller_name":       "Priya Nair",
    "seller_email":      "seller@propchain.in",
    "buyer_name":        "Arjun Sharma",
    "negotiated_price":  NEGOTIATED,
    "advance_amount":    ADVANCE,
    "installments_total": N_EMI,
}, ts(2025, 12, 2, 10))

# Block 7 — INSTALLMENT_PAYMENT: Advance
_paid_so_far = ADVANCE
b7 = _blk(7, "INSTALLMENT_PAYMENT", {
    "deal_id":      DEAL_ID,
    "payment_id":   "PAY-HIST0001",
    "payment_type": "ADVANCE",
    "amount":       ADVANCE,
    "total_paid":   _paid_so_far,
    "remaining":    NEGOTIATED - _paid_so_far,
    "buyer":        "Arjun Sharma",
    "seller":       "Priya Nair",
    "month":        0,
}, ts(2025, 12, 3, 11))

# Block 8 — INSTALLMENT_PAYMENT: EMI #1
_paid_so_far += EMI_AMT
b8 = _blk(8, "INSTALLMENT_PAYMENT", {
    "deal_id":      DEAL_ID,
    "payment_id":   "PAY-HIST0002",
    "payment_type": "EMI",
    "amount":       EMI_AMT,
    "total_paid":   _paid_so_far,
    "remaining":    NEGOTIATED - _paid_so_far,
    "buyer":        "Arjun Sharma",
    "seller":       "Priya Nair",
    "month":        1,
}, ts(2026, 1, 5))

# Block 9 — INSTALLMENT_PAYMENT: EMI #2
_paid_so_far += EMI_AMT
b9 = _blk(9, "INSTALLMENT_PAYMENT", {
    "deal_id":      DEAL_ID,
    "payment_id":   "PAY-HIST0003",
    "payment_type": "EMI",
    "amount":       EMI_AMT,
    "total_paid":   _paid_so_far,
    "remaining":    NEGOTIATED - _paid_so_far,
    "buyer":        "Arjun Sharma",
    "seller":       "Priya Nair",
    "month":        2,
}, ts(2026, 2, 5))

# Block 10 — INSTALLMENT_PAYMENT: EMI #3 (final)
_paid_so_far += EMI_AMT
b10 = _blk(10, "INSTALLMENT_PAYMENT", {
    "deal_id":      DEAL_ID,
    "payment_id":   "PAY-HIST0004",
    "payment_type": "EMI",
    "amount":       EMI_AMT,
    "total_paid":   _paid_so_far,
    "remaining":    0.0,
    "buyer":        "Arjun Sharma",
    "seller":       "Priya Nair",
    "month":        3,
}, ts(2026, 3, 1, 9))

# Block 11 — OWNERSHIP_TRANSFER (auto-triggered by full payment)
b11 = _blk(11, "OWNERSHIP_TRANSFER", {
    "deal_id":                        DEAL_ID,
    "from_owner":                     "Priya Nair",
    "to_owner":                       "Arjun Sharma",
    "sale_price":                     NEGOTIATED,
    "transaction_ref":                DEAL_ID,
    "stamp_duty_paid":                True,
    "auto_transferred_on_full_payment": True,
}, ts(2026, 3, 1, 9, 1))

sync_db["blockchain_ledger"].insert_many(_hist_blocks)
print(f"  [{OK}] Inserted {len(_hist_blocks)} blocks for PROP-HIST01:")
for blk in _hist_blocks:
    print(f"         Block {blk['block_index']:2d}: {blk['transaction_type']}")

# Property document — current owner is Arjun Sharma (post-deal)
sync_db["properties"].insert_one({
    "id":                PID,
    "title":             "Heritage Bungalow -- Juhu Beach",
    "address":           "14, Juhu Tara Road",
    "city":              "Mumbai",
    "state":             "Maharashtra",
    "pincode":           "400049",
    "area_sqft":         6500.0,
    "property_type":     "Residential",
    "market_value":      NEGOTIATED,
    "owner_name":        "Arjun Sharma",
    "owner_email":       "demo@propchain.in",
    "owner_aadhaar":     "XXXX-XXXX-4567",
    "survey_number":     "SRV/MH/JHU/2025/0099",
    "description":       (
        "5BHK heritage bungalow 100m from Juhu Beach. Fully renovated 2024. "
        "Clear title, no encumbrances. Previously owned by Priya Nair."
    ),
    "status":            "Verified",
    "registered_at":     ts(2025, 11, 1),
    "blockchain_hash":   _hist_blocks[-1]["hash"],
    "fractional_enabled": True,
    "total_tokens":      1000,
    "available_tokens":  900,   # 100 tokens held by Vikram Mehta
    "token_price":       42_000,
    "images":            [],
    "documents_verified": True,
    "fraud_score":       3,
})

# Completed deal
sync_db["deals"].insert_one({
    "id":                DEAL_ID,
    "property_id":       PID,
    "property_title":    "Heritage Bungalow -- Juhu Beach",
    "property_address":  "14, Juhu Tara Road, Mumbai, Maharashtra",
    "asking_price":      MKT_VAL,
    "negotiated_price":  NEGOTIATED,
    "advance_amount":    ADVANCE,
    "installments_total": N_EMI,
    "monthly_emi":       EMI_AMT,
    "payment_deadline":  "2026-04-01",
    "seller_name":       "Priya Nair",
    "seller_email":      "seller@propchain.in",
    "seller_aadhaar":    "XXXX-XXXX-8901",
    "buyer_name":        "Arjun Sharma",
    "buyer_email":       "demo@propchain.in",
    "buyer_aadhaar":     "XXXX-XXXX-4567",
    "message":           "Interested in immediate possession. Happy to pay in 3 installments.",
    "status":            "COMPLETED",
    "total_paid":        NEGOTIATED,
    "payments": [
        {"id": "PAY-HIST0001", "amount": ADVANCE,  "type": "ADVANCE", "month": 0,
         "paid_at": ts(2025, 12, 3, 11), "note": "Advance payment",  "block_hash": b7["hash"]},
        {"id": "PAY-HIST0002", "amount": EMI_AMT,  "type": "EMI",    "month": 1,
         "paid_at": ts(2026, 1, 5),      "note": "Installment #1",   "block_hash": b8["hash"]},
        {"id": "PAY-HIST0003", "amount": EMI_AMT,  "type": "EMI",    "month": 2,
         "paid_at": ts(2026, 2, 5),      "note": "Installment #2",   "block_hash": b9["hash"]},
        {"id": "PAY-HIST0004", "amount": EMI_AMT,  "type": "EMI",    "month": 3,
         "paid_at": ts(2026, 3, 1),      "note": "Installment #3",   "block_hash": b10["hash"]},
    ],
    "created_at":                 ts(2025, 12, 1, 9),
    "accepted_at":                ts(2025, 12, 2, 10),
    "completed_at":               ts(2026, 3, 1, 9, 1),
    "cancelled_at":               None,
    "blockchain_initiated_hash":  b5["hash"],
    "blockchain_accepted_hash":   b6["hash"],
    "blockchain_completed_hash":  b11["hash"],
})

# Fractional holding for Vikram Mehta
sync_db["fractional_holdings"].insert_one({
    "property_id": PID,
    "investor":    "Vikram Mehta",
    "email":       "investor@propchain.in",
    "tokens":      100,
    "invested":    4_200_000,
    "date":        "2025-11-15",
})

print(f"  [{OK}] PROP-HIST01 property, completed deal, and fractional holding seeded")


# ─────────────────────────────────────────────────────────────────────────────
# STEPS 3-5: API-based property registration + tokenization + investments
# ─────────────────────────────────────────────────────────────────────────────

if args.db_only:
    print(f"\n[{SKP}] --db-only: skipping API calls")
    print("\nAccounts (password: Demo@1234):")
    for u in USERS:
        print(f"  {u['email']:<28} {u['name']}")
    sys.exit(0)

print(f"\n[STEP 3] Registering 6 properties via API ({BASE})...")

# Internal keys prefixed with _ are not sent to the API
API_FIELDS = {
    "title", "address", "city", "state", "pincode",
    "area_sqft", "property_type", "market_value",
    "owner_name", "owner_aadhaar", "survey_number", "description",
}

PROP_DEFS = [
    # ── [0] DEAL-DEMO: Priya Nair's verified apartment (ready for live deal) ──
    {
        "title":         "3BHK Premium Apartment -- Indiranagar",
        "address":       "12/A, 5th Cross, Indiranagar",
        "city":          "Bengaluru", "state": "Karnataka", "pincode": "560038",
        "area_sqft":     1800.0, "property_type": "Residential",
        "market_value":  15_000_000.0,
        "owner_name":    "Priya Nair", "owner_aadhaar": "XXXX-XXXX-8901",
        "survey_number": "SRV/KA/IND/2025/1234",
        "description":   "Stunning 3BHK with Italian marble, modular kitchen, clubhouse. Ready to move.",
        "_force_status": "Verified",
        "_owner_email":  "seller@propchain.in",
        "_fraud_score":  4,
    },
    # ── [1] FRAUD-DEMO: Ravi Kumar's suspicious property ─────────────────────
    {
        "title":         "Commercial Plot -- Outer Ring Road",
        "address":       "Survey No. 123/4A, Outer Ring Road",
        "city":          "Bengaluru", "state": "Karnataka", "pincode": "560068",
        "area_sqft":     10_000.0, "property_type": "Commercial",
        "market_value":  20_000_000.0,
        "owner_name":    "Ravi Kumar", "owner_aadhaar": "XXXX-XXXX-6789",
        "survey_number": "BLR2024FAKE",   # invalid number -- triggers registry flag
        "description":   "Commercial plot near ORR. Documents pending verification.",
        "_force_status": "Under Review",
        "_owner_email":  "ravi@propchain.in",
        "_fraud_score":  72,
    },
    # ── [2] Tech Park: Vikram Mehta owns, tokenized 2000 tokens ──────────────
    {
        "title":         "Tech Park Tower A -- Whitefield",
        "address":       "EPIP Zone, Whitefield",
        "city":          "Bengaluru", "state": "Karnataka", "pincode": "560066",
        "area_sqft":     45_000.0, "property_type": "Commercial",
        "market_value":  280_000_000.0,
        "owner_name":    "Vikram Mehta", "owner_aadhaar": "XXXX-XXXX-2345",
        "survey_number": "SRV/KA/WF/2025/0045",
        "description":   "Grade-A office tower. 95% occupancy, Fortune 500 tenants. 9.4% annual yield.",
        "_force_status": "Verified",
        "_owner_email":  "investor@propchain.in",
        "_fraud_score":  2,
        "_tokenize":     2000,
        # Investments: demo@ 5% (100 tokens), seller@ 3% (60 tokens)
        "_invest": [
            (5, "demo@propchain.in"),
            (3, "seller@propchain.in"),
        ],
    },
    # ── [3] Apollo: Vikram Mehta owns, tokenized 1000 tokens ─────────────────
    {
        "title":         "Apollo Diagnostics Wing -- Block C",
        "address":       "21, Greams Road, Thousand Lights",
        "city":          "Chennai", "state": "Tamil Nadu", "pincode": "600006",
        "area_sqft":     32_000.0, "property_type": "Healthcare",
        "market_value":  195_000_000.0,
        "owner_name":    "Vikram Mehta", "owner_aadhaar": "XXXX-XXXX-2345",
        "survey_number": "SRV/TN/CHN/2025/0210",
        "description":   "Premium diagnostics & OPD wing. 15-year Apollo lease. 8.8% annual yield.",
        "_force_status": "Verified",
        "_owner_email":  "investor@propchain.in",
        "_fraud_score":  1,
        "_tokenize":     1000,
        # Investments: demo@ 10% (100 tokens), seller@ 5% (50 tokens)
        "_invest": [
            (10, "demo@propchain.in"),
            (5,  "seller@propchain.in"),
        ],
    },
    # ── [4] Connaught Place: Priya Nair owns, tokenized 2000 tokens ──────────
    {
        "title":         "Prime Retail Space -- Connaught Place",
        "address":       "Block A, Inner Circle, Connaught Place",
        "city":          "New Delhi", "state": "Delhi", "pincode": "110001",
        "area_sqft":     18_500.0, "property_type": "Commercial",
        "market_value":  320_000_000.0,
        "owner_name":    "Priya Nair", "owner_aadhaar": "XXXX-XXXX-8901",
        "survey_number": "SRV/DL/CPL/2025/0033",
        "description":   "Iconic retail hub, 100% occupied. 9.2% rental yield. Heritage building.",
        "_force_status": "Verified",
        "_owner_email":  "seller@propchain.in",
        "_fraud_score":  2,
        "_tokenize":     2000,
        # Investments: demo@ 8% (160 tokens), investor@ 4% (80 tokens)
        "_invest": [
            (8, "demo@propchain.in"),
            (4, "investor@propchain.in"),
        ],
    },
    # ── [5] Lonavala farm: Arjun Sharma, Under Review ────────────────────────
    {
        "title":         "Organic Farmland -- Lonavala",
        "address":       "Survey No. 88, Khandala Road",
        "city":          "Lonavala", "state": "Maharashtra", "pincode": "410401",
        "area_sqft":     43_560.0, "property_type": "Agricultural",
        "market_value":  8_500_000.0,
        "owner_name":    "Arjun Sharma", "owner_aadhaar": "XXXX-XXXX-4567",
        "survey_number": "SRV/MH/LON/2025/0789",
        "description":   "1-acre certified organic farm. Mutation pending Sub-Registrar review.",
        "_force_status": "Under Review",
        "_owner_email":  "demo@propchain.in",
        "_fraud_score":  18,
    },
]

registered_props = []   # list of (prop_id | None, pdef)

for pdef in PROP_DEFS:
    payload = {k: v for k, v in pdef.items() if k in API_FIELDS}
    res = post("/properties/register", payload)
    if res:
        pid = res["property"]["id"]
        # Force correct status / email / fraud_score via pymongo
        sync_db["properties"].update_one({"id": pid}, {"$set": {
            "status":             pdef["_force_status"],
            "owner_email":        pdef["_owner_email"],
            "fraud_score":        pdef["_fraud_score"],
            "documents_verified": pdef["_fraud_score"] < 20,
        }})
        registered_props.append((pid, pdef))
        icon = "V" if pdef["_force_status"] == "Verified" else "R"
        print(f"  [{OK}] [{icon}] [{pdef['property_type']:12s}] {pdef['title'][:45]} -> {pid}")
    else:
        registered_props.append((None, pdef))
    time.sleep(0.3)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: TOKENIZE PROPERTIES
# ─────────────────────────────────────────────────────────────────────────────

print("\n[STEP 4] Tokenizing properties...")

tokenized = {}  # index in registered_props -> pid

for i, (pid, pdef) in enumerate(registered_props):
    if not pid or "_tokenize" not in pdef:
        continue
    tokens = pdef["_tokenize"]
    res = post(f"/properties/{pid}/enable-fractional", params={"total_tokens": tokens})
    if res:
        tokenized[i] = pid
        print(f"  [{OK}] {pdef['title'][:45]} -> {tokens} tokens @ Rs {res['token_price']:,}/token")
    time.sleep(0.3)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: FRACTIONAL INVESTMENTS
# ─────────────────────────────────────────────────────────────────────────────

print("\n[STEP 5] Creating fractional investments...")

for i, (pid, pdef) in enumerate(registered_props):
    if i not in tokenized or not pdef.get("_invest"):
        continue
    for pct, email in pdef["_invest"]:
        res = post("/fractional/invest", {
            "property_id":      pid,
            "fraction_percent": pct,
            "investor_email":   email,
        })
        if res:
            investor = email.split("@")[0]
            print(
                f"  [{OK}] {investor:<14} -> {pct}% "
                f"({res['tokens']} tokens, Rs {res['amount']:,.0f})"
                f"  [{pdef['title'][:30]}]"
            )
        time.sleep(0.25)


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

ok_count    = sum(1 for pid, _ in registered_props if pid)
tok_count   = len(tokenized)

print(f"""
{'=' * 62}
  SEED COMPLETE -- PropChain demo data is ready
{'=' * 62}

  Accounts (password: Demo@1234)
  -----------------------------------------------
  demo@propchain.in     -- Arjun Sharma   (buyer)
  seller@propchain.in   -- Priya Nair     (seller)
  investor@propchain.in -- Vikram Mehta   (investor)
  ravi@propchain.in     -- Ravi Kumar     (fraud demo)

  Properties
  -----------------------------------------------
  PROP-HIST01      Heritage Bungalow Juhu (12 blocks, all tx types)
                   Completed deal: Priya Nair -> Arjun Sharma Rs 4 Cr
                   Vikram Mehta holds 100 fractional tokens

  API properties   {ok_count}/6 registered, {tok_count}/3 tokenized
    [0] Indiranagar 3BHK -- VERIFIED, owned by seller@  (live deal demo)
    [1] ORR Plot         -- UNDER REVIEW, fraud score 72 (AI verify demo)
    [2] Tech Park        -- tokenized, 2000 tokens
    [3] Apollo Diag      -- tokenized, 1000 tokens
    [4] Connaught Place  -- tokenized, 2000 tokens
    [5] Lonavala Farm    -- UNDER REVIEW (pending verification)

  Demo Script (judges walk-through)
  -----------------------------------------------
  1. Login as demo@propchain.in
  2. AI Verify -> upload a property PDF -> see fraud score
  3. Browse properties -> click "Make Offer" on Indiranagar apt
     (seller@propchain.in must accept from a separate session)
  4. Blockchain Explorer -> open PROP-HIST01 -> see all 12 blocks
  5. Fractional -> browse Tech Park / Apollo / Connaught Place tokens

  NOTE: Restart the backend after seeding so DB indexes are rebuilt.
{'=' * 62}
""")
