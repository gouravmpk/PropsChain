"""
Marketplace Route
-----------------
GET /marketplace  — list all fractional investment opportunities
"""

from fastapi import APIRouter
from config.database import properties_collection

router = APIRouter(tags=["Marketplace"])


def _serialize(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@router.get(
    "/marketplace",
    summary="Browse fractional investment opportunities",
    description="Returns all properties with fractional ownership enabled and available tokens.",
)
async def get_marketplace():
    query = {"fractional_enabled": True, "available_tokens": {"$gt": 0}}
    cursor = properties_collection.find(query).sort("market_value", -1)
    listings = [_serialize(p) async for p in cursor]
    return {"listings": listings, "total": len(listings)}
