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
    # Properties
    all_props = [_serialize(p) async for p in properties_collection.find()]
    verified = [p for p in all_props if p.get("status") == "Verified"]
    fractional_props = [p for p in all_props if p.get("fractional_enabled")]
    total_value = sum(p.get("market_value", 0) for p in all_props)

    # Transactions
    total_txns = await transactions_collection.count_documents({})

    # Blockchain blocks
    total_blocks = await blockchain_collection.count_documents({})

    # Fractional invested
    all_holdings = [_serialize(h) async for h in fractional_collection.find()]
    total_invested = sum(h.get("invested", 0) for h in all_holdings)

    # Unique investors
    investors = set(h.get("email") for h in all_holdings if h.get("email"))

    # Cities
    cities = set(p.get("city") for p in all_props if p.get("city"))

    # AI verifications (doc_verification blocks)
    verifications = await blockchain_collection.count_documents(
        {"transaction_type": "DOCUMENT_VERIFICATION"}
    )
    fraud_prevented = await blockchain_collection.count_documents(
        {"transaction_type": "DOCUMENT_VERIFICATION", "data.verdict": {"$in": ["SUSPICIOUS", "FLAGGED"]}}
    )

    return {
        "total_properties": len(all_props),
        "verified_properties": len(verified),
        "pending_properties": len(all_props) - len(verified),
        "total_market_value": total_value,
        "blockchain_blocks": total_blocks,
        "total_transactions": total_txns,
        "fractional_properties": len(fractional_props),
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
