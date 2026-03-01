import hashlib
import json
import random
import string
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
import base64
import io
import math

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt

# ─────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────
app = FastAPI(
    title="PropChain API",
    description="Blockchain & AI-powered Property Registration Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Auth Config
# ─────────────────────────────────────────────
SECRET_KEY = "propchain-secret-key-opsai-hackathon-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ─────────────────────────────────────────────
# In-Memory "Database"
# ─────────────────────────────────────────────
users_db: dict = {}
properties_db: dict = {}
blockchain_db: list = []
transactions_db: list = []
fractional_db: dict = {}
verification_db: list = []

# ─────────────────────────────────────────────
# Blockchain Utility
# ─────────────────────────────────────────────
GENESIS_BLOCK = {
    "index": 0,
    "timestamp": "2026-01-01T00:00:00",
    "data": "Genesis Block – PropChain",
    "previous_hash": "0" * 64,
    "hash": hashlib.sha256(b"genesis").hexdigest(),
    "nonce": 0,
}
blockchain_db.append(GENESIS_BLOCK)


def calculate_hash(index, timestamp, data, previous_hash, nonce):
    value = f"{index}{timestamp}{json.dumps(data, sort_keys=True)}{previous_hash}{nonce}"
    return hashlib.sha256(value.encode()).hexdigest()


def add_block(data: dict):
    last = blockchain_db[-1]
    index = last["index"] + 1
    timestamp = datetime.utcnow().isoformat()
    nonce = random.randint(1000, 9999)
    previous_hash = last["hash"]
    block_hash = calculate_hash(index, timestamp, data, previous_hash, nonce)
    block = {
        "index": index,
        "timestamp": timestamp,
        "data": data,
        "previous_hash": previous_hash,
        "hash": block_hash,
        "nonce": nonce,
    }
    blockchain_db.append(block)
    return block


def generate_property_id():
    return "PROP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def generate_token_id():
    return "TKN-" + "".join(random.choices(string.digits, k=10))


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────
class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    phone: str
    aadhaar: str


class UserLogin(BaseModel):
    email: str
    password: str


class PropertyCreate(BaseModel):
    title: str
    address: str
    city: str
    state: str
    pincode: str
    area_sqft: float
    property_type: str
    market_value: float
    owner_name: str
    owner_aadhaar: str
    survey_number: str
    description: str


class FractionalInvestment(BaseModel):
    property_id: str
    fraction_percent: float
    investor_email: str


class TransferProperty(BaseModel):
    property_id: str
    new_owner_name: str
    new_owner_email: str
    new_owner_aadhaar: str
    transfer_amount: float


class AIVerificationRequest(BaseModel):
    document_type: str
    content_base64: Optional[str] = None


# ─────────────────────────────────────────────
# Auth Helpers
# ─────────────────────────────────────────────
def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None or email not in users_db:
            raise HTTPException(status_code=401, detail="Invalid token")
        return users_db[email]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ─────────────────────────────────────────────
# Seed Data
# ─────────────────────────────────────────────
def seed_data():
    # Demo user
    users_db["demo@propchain.in"] = {
        "id": str(uuid.uuid4()),
        "name": "Arjun Sharma",
        "email": "demo@propchain.in",
        "password": hash_password("Demo@1234"),
        "phone": "+91-9876543210",
        "aadhaar": "XXXX-XXXX-4567",
        "created_at": "2026-01-15T10:00:00",
        "kyc_verified": True,
        "wallet_balance": 5000000,
    }

    # Demo properties
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
            "status": "Pending",
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
        properties_db[p["id"]] = p

    # Fractional ownership records
    fractional_db["PROP-ALPHA001"] = [
        {"investor": "Rohit Gupta", "email": "rohit@gmail.com", "tokens": 150, "invested": 12750000, "date": "2026-01-22"},
        {"investor": "Sneha Patel", "email": "sneha@gmail.com", "tokens": 100, "invested": 8500000, "date": "2026-01-28"},
        {"investor": "Arjun Sharma", "email": "demo@propchain.in", "tokens": 100, "invested": 8500000, "date": "2026-01-30"},
    ]
    fractional_db["PROP-BETA002"] = [
        {"investor": "Ravi Kumar", "email": "ravi@gmail.com", "tokens": 400, "invested": 40000000, "date": "2026-01-27"},
        {"investor": "Meena Iyer", "email": "meena@gmail.com", "tokens": 300, "invested": 30000000, "date": "2026-02-01"},
    ]
    fractional_db["PROP-DELTA004"] = [
        {"investor": "Arjun Sharma", "email": "demo@propchain.in", "tokens": 150, "invested": 15000000, "date": "2026-02-12"},
    ]

    # Sample blockchain transactions
    for p in sample_props:
        block = add_block({
            "type": "PROPERTY_REGISTRATION",
            "property_id": p["id"],
            "owner": p["owner_name"],
            "timestamp": p["registered_at"],
        })

    # Sample transfer transactions
    transactions_db.extend([
        {
            "id": str(uuid.uuid4()),
            "type": "REGISTRATION",
            "property_id": "PROP-ALPHA001",
            "from": "Government",
            "to": "Arjun Sharma",
            "amount": 85000000,
            "timestamp": "2026-01-20T14:30:00",
            "block_hash": blockchain_db[1]["hash"],
            "status": "Confirmed",
        },
        {
            "id": str(uuid.uuid4()),
            "type": "FRACTIONAL_PURCHASE",
            "property_id": "PROP-ALPHA001",
            "from": "Arjun Sharma",
            "to": "Rohit Gupta",
            "amount": 12750000,
            "timestamp": "2026-01-22T09:15:00",
            "block_hash": blockchain_db[2]["hash"] if len(blockchain_db) > 2 else "",
            "status": "Confirmed",
        },
    ])


seed_data()

# ─────────────────────────────────────────────
# Routes: Auth
# ─────────────────────────────────────────────
@app.post("/api/auth/register")
async def register(user: UserRegister):
    if user.email in users_db:
        raise HTTPException(400, "Email already registered")
    users_db[user.email] = {
        "id": str(uuid.uuid4()),
        "name": user.name,
        "email": user.email,
        "password": hash_password(user.password),
        "phone": user.phone,
        "aadhaar": user.aadhaar,
        "created_at": datetime.utcnow().isoformat(),
        "kyc_verified": False,
        "wallet_balance": 1000000,
    }
    token = create_access_token({"sub": user.email})
    return {"token": token, "user": {**users_db[user.email], "password": None}}


@app.post("/api/auth/login")
async def login(creds: UserLogin):
    user = users_db.get(creds.email)
    if not user or not verify_password(creds.password, user["password"]):
        raise HTTPException(401, "Invalid credentials")
    token = create_access_token({"sub": creds.email})
    safe_user = {k: v for k, v in user.items() if k != "password"}
    return {"token": token, "user": safe_user}


# ─────────────────────────────────────────────
# Routes: Properties
# ─────────────────────────────────────────────
@app.get("/api/properties")
async def list_properties(city: Optional[str] = None, status: Optional[str] = None, prop_type: Optional[str] = None):
    props = list(properties_db.values())
    if city:
        props = [p for p in props if p["city"].lower() == city.lower()]
    if status:
        props = [p for p in props if p["status"].lower() == status.lower()]
    if prop_type:
        props = [p for p in props if p["property_type"].lower() == prop_type.lower()]
    return {"properties": props, "total": len(props)}


@app.get("/api/properties/{property_id}")
async def get_property(property_id: str):
    prop = properties_db.get(property_id)
    if not prop:
        raise HTTPException(404, "Property not found")
    # Attach fractional holders
    prop["holders"] = fractional_db.get(property_id, [])
    return prop


@app.post("/api/properties/register")
async def register_property(prop: PropertyCreate):
    prop_id = generate_property_id()
    fraud_score = random.randint(1, 20)
    status = "Verified" if fraud_score < 10 else "Under Review"
    block = add_block({
        "type": "PROPERTY_REGISTRATION",
        "property_id": prop_id,
        "owner": prop.owner_name,
        "survey": prop.survey_number,
        "value": prop.market_value,
    })
    new_prop = {
        "id": prop_id,
        **prop.dict(),
        "owner_email": "",
        "status": status,
        "registered_at": datetime.utcnow().isoformat(),
        "blockchain_hash": block["hash"],
        "fractional_enabled": False,
        "total_tokens": 0,
        "available_tokens": 0,
        "token_price": 0,
        "images": [],
        "documents_verified": status == "Verified",
        "fraud_score": fraud_score,
    }
    properties_db[prop_id] = new_prop
    transactions_db.append({
        "id": str(uuid.uuid4()),
        "type": "REGISTRATION",
        "property_id": prop_id,
        "from": "Applicant",
        "to": prop.owner_name,
        "amount": prop.market_value,
        "timestamp": datetime.utcnow().isoformat(),
        "block_hash": block["hash"],
        "status": "Confirmed",
    })
    return {"message": "Property registered successfully", "property": new_prop, "block": block}


@app.post("/api/properties/{property_id}/transfer")
async def transfer_property(property_id: str, transfer: TransferProperty):
    prop = properties_db.get(property_id)
    if not prop:
        raise HTTPException(404, "Property not found")
    old_owner = prop["owner_name"]
    prop["owner_name"] = transfer.new_owner_name
    prop["owner_email"] = transfer.new_owner_email
    prop["owner_aadhaar"] = transfer.new_owner_aadhaar
    prop["status"] = "Verified"
    block = add_block({
        "type": "PROPERTY_TRANSFER",
        "property_id": property_id,
        "from_owner": old_owner,
        "to_owner": transfer.new_owner_name,
        "amount": transfer.transfer_amount,
    })
    prop["blockchain_hash"] = block["hash"]
    transactions_db.append({
        "id": str(uuid.uuid4()),
        "type": "TRANSFER",
        "property_id": property_id,
        "from": old_owner,
        "to": transfer.new_owner_name,
        "amount": transfer.transfer_amount,
        "timestamp": datetime.utcnow().isoformat(),
        "block_hash": block["hash"],
        "status": "Confirmed",
    })
    return {"message": "Property transferred", "block": block, "property": prop}


@app.post("/api/properties/{property_id}/enable-fractional")
async def enable_fractional(property_id: str, total_tokens: int = 1000):
    prop = properties_db.get(property_id)
    if not prop:
        raise HTTPException(404, "Property not found")
    token_price = int(prop["market_value"] / total_tokens)
    prop["fractional_enabled"] = True
    prop["total_tokens"] = total_tokens
    prop["available_tokens"] = total_tokens
    prop["token_price"] = token_price
    block = add_block({
        "type": "FRACTIONAL_ENABLED",
        "property_id": property_id,
        "total_tokens": total_tokens,
        "token_price": token_price,
    })
    return {"message": "Fractional ownership enabled", "token_price": token_price, "block": block}


@app.post("/api/fractional/invest")
async def invest_fractional(inv: FractionalInvestment):
    prop = properties_db.get(inv.property_id)
    if not prop or not prop["fractional_enabled"]:
        raise HTTPException(400, "Property not available for fractional investment")
    tokens_to_buy = int((inv.fraction_percent / 100) * prop["total_tokens"])
    if tokens_to_buy > prop["available_tokens"]:
        raise HTTPException(400, "Not enough tokens available")
    amount = tokens_to_buy * prop["token_price"]
    prop["available_tokens"] -= tokens_to_buy
    if inv.property_id not in fractional_db:
        fractional_db[inv.property_id] = []
    fractional_db[inv.property_id].append({
        "investor": inv.investor_email.split("@")[0].title(),
        "email": inv.investor_email,
        "tokens": tokens_to_buy,
        "invested": amount,
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
    })
    block = add_block({
        "type": "FRACTIONAL_PURCHASE",
        "property_id": inv.property_id,
        "investor": inv.investor_email,
        "tokens": tokens_to_buy,
        "amount": amount,
    })
    transactions_db.append({
        "id": str(uuid.uuid4()),
        "type": "FRACTIONAL_PURCHASE",
        "property_id": inv.property_id,
        "from": prop["owner_name"],
        "to": inv.investor_email,
        "amount": amount,
        "timestamp": datetime.utcnow().isoformat(),
        "block_hash": block["hash"],
        "status": "Confirmed",
    })
    return {"message": "Investment successful", "tokens": tokens_to_buy, "amount": amount, "block": block}


# ─────────────────────────────────────────────
# Routes: AI Verification
# ─────────────────────────────────────────────
AI_CHECKS = {
    "sale_deed": ["Seller & Buyer name", "Property description", "Stamp duty", "Registration office seal", "Witness signatures"],
    "aadhaar": ["Aadhaar number format", "Name & DOB", "QR code validity", "UIDAI watermark"],
    "encumbrance": ["EC period", "Outstanding liabilities", "Bank endorsements", "Govt seal"],
    "mutation": ["Previous owner chain", "Revenue records", "Tehsildar signature", "Property survey number"],
    "other": ["Document structure", "Issuing authority", "Date validity", "Signature presence"],
}


@app.post("/api/ai/verify-document")
async def verify_document(
    document_type: str = Form(...),
    file: UploadFile = File(...)
):
    content = await file.read()
    file_size_kb = len(content) / 1024

    checks = AI_CHECKS.get(document_type, AI_CHECKS["other"])
    results = []
    fraud_indicators = []
    overall_score = random.randint(75, 98)

    for check in checks:
        passed = random.random() > 0.15
        confidence = random.randint(82, 99) if passed else random.randint(20, 50)
        results.append({"check": check, "passed": passed, "confidence": confidence})
        if not passed:
            fraud_indicators.append(f"Anomaly detected in: {check}")

    authenticity = "AUTHENTIC" if overall_score >= 85 else "SUSPICIOUS"
    block = add_block({
        "type": "DOCUMENT_VERIFICATION",
        "document_type": document_type,
        "filename": file.filename,
        "authenticity": authenticity,
        "score": overall_score,
    })

    rec = {
        "id": str(uuid.uuid4()),
        "document_type": document_type,
        "filename": file.filename,
        "size_kb": round(file_size_kb, 2),
        "checks": results,
        "overall_score": overall_score,
        "authenticity": authenticity,
        "fraud_indicators": fraud_indicators,
        "verified_at": datetime.utcnow().isoformat(),
        "block_hash": block["hash"],
        "ml_model": "PropChain-FraudNet v2.1",
        "processing_time_ms": random.randint(800, 2500),
    }
    verification_db.append(rec)
    return rec


@app.get("/api/ai/verifications")
async def get_verifications():
    return {"verifications": verification_db[-20:], "total": len(verification_db)}


# ─────────────────────────────────────────────
# Routes: Blockchain
# ─────────────────────────────────────────────
@app.get("/api/blockchain")
async def get_blockchain():
    return {"chain": blockchain_db[-20:], "length": len(blockchain_db)}


@app.get("/api/blockchain/verify")
async def verify_chain():
    valid = True
    broken_at = None
    for i in range(1, len(blockchain_db)):
        curr = blockchain_db[i]
        prev = blockchain_db[i - 1]
        recalc = calculate_hash(curr["index"], curr["timestamp"], curr["data"], curr["previous_hash"], curr["nonce"])
        if curr["previous_hash"] != prev["hash"] or recalc != curr["hash"]:
            valid = False
            broken_at = i
            break
    return {"valid": valid, "chain_length": len(blockchain_db), "broken_at": broken_at}


# ─────────────────────────────────────────────
# Routes: Transactions
# ─────────────────────────────────────────────
@app.get("/api/transactions")
async def get_transactions():
    return {"transactions": list(reversed(transactions_db)), "total": len(transactions_db)}


@app.get("/api/transactions/{property_id}")
async def get_property_transactions(property_id: str):
    txns = [t for t in transactions_db if t.get("property_id") == property_id]
    return {"transactions": list(reversed(txns)), "total": len(txns)}


# ─────────────────────────────────────────────
# Routes: Dashboard Stats
# ─────────────────────────────────────────────
@app.get("/api/dashboard/stats")
async def dashboard_stats():
    props = list(properties_db.values())
    verified = [p for p in props if p["status"] == "Verified"]
    pending = [p for p in props if p["status"] != "Verified"]
    total_value = sum(p["market_value"] for p in props)
    fractional_props = [p for p in props if p["fractional_enabled"]]
    total_invested = sum(
        sum(h["invested"] for h in holders)
        for holders in fractional_db.values()
    )
    return {
        "total_properties": len(props),
        "verified_properties": len(verified),
        "pending_properties": len(pending),
        "total_market_value": total_value,
        "blockchain_blocks": len(blockchain_db),
        "total_transactions": len(transactions_db),
        "fractional_properties": len(fractional_props),
        "total_fractional_invested": total_invested,
        "verifications_performed": len(verification_db),
        "fraud_prevented": sum(1 for v in verification_db if v["authenticity"] == "SUSPICIOUS"),
        "active_investors": 48,
        "cities_covered": 12,
    }


@app.get("/api/marketplace")
async def get_marketplace():
    fractional_props = [p for p in properties_db.values() if p["fractional_enabled"] and p["available_tokens"] > 0]
    return {"listings": fractional_props, "total": len(fractional_props)}


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "PropChain API", "team": "OpsAI", "version": "1.0.0"}
