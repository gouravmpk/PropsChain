import uuid

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
users_collection      = db["users"]
transactions_collection = db["transactions"]
fractional_collection = db["fractional_holdings"]
deals_collection      = db["deals"]


async def init_db():
    """
    Create indexes on startup and ensure demo accounts exist (idempotent).
    Unique index on (property_id, block_index) enforces append-only behaviour
    at the database level — no two blocks can share the same index for a property.
    """
    await blockchain_collection.create_indexes(
        [
            IndexModel(
                [("property_id", ASCENDING), ("block_index", ASCENDING)],
                unique=True,
                name="unique_property_block",
            ),
            IndexModel([("hash", ASCENDING)], unique=True, name="unique_hash"),
        ]
    )

    await properties_collection.create_indexes(
        [
            IndexModel([("id", ASCENDING)], unique=True, name="idx_property_id"),
        ]
    )

    await users_collection.create_indexes(
        [
            IndexModel([("email", ASCENDING)], unique=True, name="unique_email"),
        ]
    )

    await deals_collection.create_indexes(
        [
            IndexModel([("id", ASCENDING)], unique=True, name="unique_deal_id"),
            IndexModel([("property_id", ASCENDING)], name="idx_deal_property"),
            IndexModel([("buyer_email", ASCENDING)], name="idx_deal_buyer"),
            IndexModel([("seller_email", ASCENDING)], name="idx_deal_seller"),
        ]
    )

    await _seed_demo_data()


# ── Seed data ─────────────────────────────────────────────────────────────────

async def _seed_demo_data():
    """
    Safety-net: insert the 4 demo user accounts if they don't already exist.
    Full property/blockchain data is managed by seed.py — run that for a clean demo.
    This is a no-op after seed.py has been executed.
    """
    from passlib.context import CryptContext

    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    DEMO_USERS = [
        {
            "id": str(uuid.uuid4()), "name": "Arjun Sharma",
            "email": "demo@propchain.in",
            "password": pwd_ctx.hash("Demo@1234"), "phone": "+91-9876543210",
            "aadhaar": "XXXX-XXXX-4567", "created_at": "2026-01-01T09:00:00",
            "kyc_verified": True, "wallet_balance": 50_000_000,
        },
        {
            "id": str(uuid.uuid4()), "name": "Priya Nair",
            "email": "seller@propchain.in",
            "password": pwd_ctx.hash("Demo@1234"), "phone": "+91-9876543211",
            "aadhaar": "XXXX-XXXX-8901", "created_at": "2026-01-01T09:00:00",
            "kyc_verified": True, "wallet_balance": 10_000_000,
        },
        {
            "id": str(uuid.uuid4()), "name": "Vikram Mehta",
            "email": "investor@propchain.in",
            "password": pwd_ctx.hash("Demo@1234"), "phone": "+91-9876543212",
            "aadhaar": "XXXX-XXXX-2345", "created_at": "2026-01-01T09:00:00",
            "kyc_verified": True, "wallet_balance": 25_000_000,
        },
        {
            "id": str(uuid.uuid4()), "name": "Ravi Kumar",
            "email": "ravi@propchain.in",
            "password": pwd_ctx.hash("Demo@1234"), "phone": "+91-9876543213",
            "aadhaar": "XXXX-XXXX-6789", "created_at": "2026-01-01T09:00:00",
            "kyc_verified": False, "wallet_balance": 1_000_000,
        },
    ]

    for u in DEMO_USERS:
        if not await users_collection.find_one({"email": u["email"]}):
            await users_collection.insert_one(u)

    print("Demo accounts ready (run seed.py for full property/blockchain data)")
