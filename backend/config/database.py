import hashlib
import uuid
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, IndexModel
from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "propchain_db")

client = AsyncIOMotorClient(MONGODB_URL)
db = client[DB_NAME]

# Collections
blockchain_collection = db["blockchain_ledger"]
properties_collection = db["properties"]
users_collection = db["users"]
transactions_collection = db["transactions"]
fractional_collection = db["fractional_holdings"]


async def init_db():
    """
    Create indexes on startup and seed demo data if DB is empty.
    Unique index on (property_id, block_index) enforces append-only behaviour
    at the database level — no two blocks can share the same index for a property.
    """
    await blockchain_collection.create_indexes(
        [
            # Enforce uniqueness: each (property, block_index) pair is one-of-a-kind
            IndexModel(
                [("property_id", ASCENDING), ("block_index", ASCENDING)],
                unique=True,
                name="unique_property_block",
            ),
            # Fast lookup of the latest block for a property
            IndexModel(
                [("property_id", ASCENDING), ("block_index", ASCENDING)],
                name="property_block_lookup",
            ),
            # Fast lookup by hash (for block explorer)
            IndexModel([("hash", ASCENDING)], unique=True, name="unique_hash"),
        ]
    )

    await properties_collection.create_indexes(
        [
            IndexModel([("id", ASCENDING)], unique=True, name="unique_property_id"),
        ]
    )

    await users_collection.create_indexes(
        [
            IndexModel([("email", ASCENDING)], unique=True, name="unique_email"),
        ]
    )

    await _seed_demo_data()


# ── Seed data ─────────────────────────────────────────────────────────────────

async def _seed_demo_data():
    """Insert demo data if the collections are empty (idempotent)."""
    from passlib.context import CryptContext
    from utils.hashing import compute_hash, GENESIS_HASH, get_utc_timestamp

    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # ── Demo user ─────────────────────────────────────────────────────────────
    if not await users_collection.find_one({"email": "demo@propchain.in"}):
        await users_collection.insert_one({
            "id": str(uuid.uuid4()),
            "name": "Arjun Sharma",
            "email": "demo@propchain.in",
            "password": pwd_ctx.hash("Demo@1234"),
            "phone": "+91-9876543210",
            "aadhaar": "XXXX-XXXX-4567",
            "created_at": "2026-01-15T10:00:00",
            "kyc_verified": True,
            "wallet_balance": 5000000,
        })

    # ── Demo properties ───────────────────────────────────────────────────────
    sample_props = [
        {
            "id": "PROP-ALPHA001",
            "title": "Premium Commercial Complex",
            "address": "15, Nariman Point",
            "city": "Mumbai", "state": "Maharashtra", "pincode": "400021",
            "area_sqft": 12000,
            "property_type": "Commercial",
            "market_value": 85000000,
            "owner_name": "Arjun Sharma",
            "owner_email": "demo@propchain.in",
            "owner_aadhaar": "XXXX-XXXX-4567",
            "survey_number": "SRV/MH/2024/0012",
            "description": "Modern commercial complex in the heart of Mumbai's financial district",
            "status": "Verified",
            "registered_at": "2026-01-20T14:30:00",
            "blockchain_hash": hashlib.sha256(b"PROP-ALPHA001").hexdigest(),
            "fractional_enabled": True,
            "total_tokens": 1000,
            "available_tokens": 650,
            "token_price": 85000,
            "images": [],
            "documents_verified": True,
            "fraud_score": 2,
        },
        {
            "id": "PROP-BETA002",
            "title": "Apollo Healthcare Hub",
            "address": "72, Anna Salai",
            "city": "Chennai", "state": "Tamil Nadu", "pincode": "600002",
            "area_sqft": 25000,
            "property_type": "Healthcare",
            "market_value": 250000000,
            "owner_name": "Dr. Priya Nair",
            "owner_email": "priya@propchain.in",
            "owner_aadhaar": "XXXX-XXXX-8901",
            "survey_number": "SRV/TN/2024/0340",
            "description": "Multi-specialty hospital complex with state-of-the-art facilities",
            "status": "Verified",
            "registered_at": "2026-01-25T09:00:00",
            "blockchain_hash": hashlib.sha256(b"PROP-BETA002").hexdigest(),
            "fractional_enabled": True,
            "total_tokens": 2500,
            "available_tokens": 1800,
            "token_price": 100000,
            "images": [],
            "documents_verified": True,
            "fraud_score": 1,
        },
        {
            "id": "PROP-GAMMA003",
            "title": "Tech Park Tower B",
            "address": "Outer Ring Road, Marathahalli",
            "city": "Bengaluru", "state": "Karnataka", "pincode": "560037",
            "area_sqft": 18500,
            "property_type": "Commercial",
            "market_value": 120000000,
            "owner_name": "Vikram Reddy",
            "owner_email": "vikram@propchain.in",
            "owner_aadhaar": "XXXX-XXXX-2345",
            "survey_number": "SRV/KA/2024/0891",
            "description": "Grade-A IT park in Bengaluru's silicon corridor with 98% occupancy",
            "status": "Under Review",
            "registered_at": "2026-02-01T11:00:00",
            "blockchain_hash": hashlib.sha256(b"PROP-GAMMA003").hexdigest(),
            "fractional_enabled": False,
            "total_tokens": 0,
            "available_tokens": 0,
            "token_price": 0,
            "images": [],
            "documents_verified": False,
            "fraud_score": 15,
        },
        {
            "id": "PROP-DELTA004",
            "title": "Luxury Residential Tower",
            "address": "DLF Cyber City, Sector 24",
            "city": "Gurugram", "state": "Haryana", "pincode": "122002",
            "area_sqft": 8500,
            "property_type": "Residential",
            "market_value": 45000000,
            "owner_name": "Arjun Sharma",
            "owner_email": "demo@propchain.in",
            "owner_aadhaar": "XXXX-XXXX-4567",
            "survey_number": "SRV/HR/2025/0045",
            "description": "Premium 4BHK luxury apartment with panoramic city views",
            "status": "Verified",
            "registered_at": "2026-02-10T16:00:00",
            "blockchain_hash": hashlib.sha256(b"PROP-DELTA004").hexdigest(),
            "fractional_enabled": True,
            "total_tokens": 450,
            "available_tokens": 300,
            "token_price": 100000,
            "images": [],
            "documents_verified": True,
            "fraud_score": 3,
        },
    ]

    for p in sample_props:
        if not await properties_collection.find_one({"id": p["id"]}):
            await properties_collection.insert_one(dict(p))

            # Create blockchain genesis block for this property
            if not await blockchain_collection.find_one({"property_id": p["id"]}):
                ts = get_utc_timestamp()
                block_data = {
                    "owner_name": p["owner_name"],
                    "property_address": f"{p['address']}, {p['city']}, {p['state']}",
                    "area_sqft": p["area_sqft"],
                    "property_type": p["property_type"],
                    "market_value": p["market_value"],
                    "registration_number": p["survey_number"],
                    "registration_status": "REGISTERED",
                }
                blk_hash = compute_hash(
                    block_index=0,
                    property_id=p["id"],
                    data=block_data,
                    previous_hash=GENESIS_HASH,
                    timestamp=ts,
                )
                await blockchain_collection.insert_one({
                    "block_index": 0,
                    "property_id": p["id"],
                    "transaction_type": "GENESIS",
                    "data": block_data,
                    "previous_hash": GENESIS_HASH,
                    "timestamp": ts,
                    "minted_by": "PropChain-Seed",
                    "hash": blk_hash,
                })

    # ── Fractional holdings ───────────────────────────────────────────────────
    seed_holdings = [
        {"property_id": "PROP-ALPHA001", "investor": "Rohit Gupta", "email": "rohit@gmail.com", "tokens": 150, "invested": 12750000, "date": "2026-01-22"},
        {"property_id": "PROP-ALPHA001", "investor": "Sneha Patel", "email": "sneha@gmail.com", "tokens": 100, "invested": 8500000, "date": "2026-01-28"},
        {"property_id": "PROP-ALPHA001", "investor": "Arjun Sharma", "email": "demo@propchain.in", "tokens": 100, "invested": 8500000, "date": "2026-01-30"},
        {"property_id": "PROP-BETA002", "investor": "Ravi Kumar", "email": "ravi@gmail.com", "tokens": 400, "invested": 40000000, "date": "2026-01-27"},
        {"property_id": "PROP-BETA002", "investor": "Meena Iyer", "email": "meena@gmail.com", "tokens": 300, "invested": 30000000, "date": "2026-02-01"},
        {"property_id": "PROP-DELTA004", "investor": "Arjun Sharma", "email": "demo@propchain.in", "tokens": 150, "invested": 15000000, "date": "2026-02-12"},
    ]
    for h in seed_holdings:
        if not await fractional_collection.find_one({"property_id": h["property_id"], "email": h["email"]}):
            await fractional_collection.insert_one(dict(h))

    # ── Sample transactions ───────────────────────────────────────────────────
    if not await transactions_collection.find_one({"property_id": "PROP-ALPHA001"}):
        seed_txns = [
            {"id": str(uuid.uuid4()), "type": "REGISTRATION", "property_id": "PROP-ALPHA001", "from": "Government", "to": "Arjun Sharma", "amount": 85000000, "timestamp": "2026-01-20T14:30:00", "block_hash": hashlib.sha256(b"PROP-ALPHA001").hexdigest(), "status": "Confirmed"},
            {"id": str(uuid.uuid4()), "type": "FRACTIONAL_PURCHASE", "property_id": "PROP-ALPHA001", "from": "Arjun Sharma", "to": "Rohit Gupta", "amount": 12750000, "timestamp": "2026-01-22T09:15:00", "block_hash": hashlib.sha256(b"txn2").hexdigest(), "status": "Confirmed"},
            {"id": str(uuid.uuid4()), "type": "REGISTRATION", "property_id": "PROP-BETA002", "from": "Government", "to": "Dr. Priya Nair", "amount": 250000000, "timestamp": "2026-01-25T09:00:00", "block_hash": hashlib.sha256(b"PROP-BETA002").hexdigest(), "status": "Confirmed"},
            {"id": str(uuid.uuid4()), "type": "REGISTRATION", "property_id": "PROP-DELTA004", "from": "Government", "to": "Arjun Sharma", "amount": 45000000, "timestamp": "2026-02-10T16:00:00", "block_hash": hashlib.sha256(b"PROP-DELTA004").hexdigest(), "status": "Confirmed"},
        ]
        for t in seed_txns:
            await transactions_collection.insert_one(t)

    print("✅ Demo seed data ready")
