"""
Dashboard & Transactions Routes
--------------------------------
GET /dashboard/stats            — platform statistics
GET /transactions               — all transactions (newest first)
GET /transactions/{property_id} — transactions for a specific property
"""

from fastapi import APIRouter
from config.database import (
    properties_collection,
    transactions_collection,
    blockchain_collection,
    fractional_collection,
)

router = APIRouter(tags=["Dashboard"])


def _serialize(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@router.get(
    "/dashboard/stats",
    summary="Get real-time PropChain platform statistics",
)
async def dashboard_stats():
    # Properties — DB-level aggregation avoids loading all docs into memory
    total_props = await properties_collection.count_documents({})
    verified_count = await properties_collection.count_documents({"status": "Verified"})
    fractional_count = await properties_collection.count_documents({"fractional_enabled": True})

    value_agg = await properties_collection.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$market_value"}}}
    ]).to_list(1)
    total_value = value_agg[0]["total"] if value_agg else 0

    cities_list = await properties_collection.distinct("city")
    cities = set(c for c in cities_list if c)

    # Transactions & blocks
    total_txns = await transactions_collection.count_documents({})
    total_blocks = await blockchain_collection.count_documents({})

    # Fractional holdings — aggregate for invested total and distinct investor emails
    holdings_agg = await fractional_collection.aggregate([
        {"$group": {"_id": None, "total_invested": {"$sum": "$invested"}, "emails": {"$addToSet": "$email"}}}
    ]).to_list(1)
    total_invested = holdings_agg[0]["total_invested"] if holdings_agg else 0
    investors = set(e for e in (holdings_agg[0]["emails"] if holdings_agg else []) if e)

    # AI verifications
    verifications = await blockchain_collection.count_documents(
        {"transaction_type": "DOCUMENT_VERIFICATION"}
    )
    fraud_prevented = await blockchain_collection.count_documents(
        {"transaction_type": "DOCUMENT_VERIFICATION", "data.verdict": {"$in": ["SUSPICIOUS", "FLAGGED"]}}
    )

    return {
        "total_properties": total_props,
        "verified_properties": verified_count,
        "pending_properties": total_props - verified_count,
        "total_market_value": total_value,
        "blockchain_blocks": total_blocks,
        "total_transactions": total_txns,
        "fractional_properties": fractional_count,
        "total_fractional_invested": total_invested,
        "verifications_performed": verifications,
        "fraud_prevented": fraud_prevented,
        "active_investors": len(investors),
        "cities_covered": len(cities),
    }


@router.get(
    "/transactions",
    summary="Get all platform transactions",
)
async def get_transactions():
    cursor = transactions_collection.find().sort("timestamp", -1)
    txns = [_serialize(t) async for t in cursor]
    return {"transactions": txns, "total": len(txns)}


@router.get(
    "/transactions/{property_id}",
    summary="Get all transactions for a specific property",
)
async def get_property_transactions(property_id: str):
    cursor = transactions_collection.find({"property_id": property_id}).sort("timestamp", -1)
    txns = [_serialize(t) async for t in cursor]
    return {"transactions": txns, "total": len(txns)}
