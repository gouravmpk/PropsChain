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


async def init_db():
    """
    Create indexes on startup.
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
            IndexModel([("property_id", ASCENDING)], unique=True, name="unique_property_id"),
        ]
    )
