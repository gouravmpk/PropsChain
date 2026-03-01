"""
Properties Routes
-----------------
GET    /properties                    — list all properties (with filters)
GET    /properties/{property_id}      — property detail
POST   /properties/register           — register new property (also mints blockchain genesis block)
POST   /properties/{id}/transfer      — transfer ownership
POST   /properties/{id}/enable-fractional  — tokenise property
POST   /fractional/invest             — buy fractional tokens
"""

import uuid
import random
import string
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config.database import properties_collection, transactions_collection, fractional_collection
from services.blockchain_service import mint_genesis, add_transaction
from models.blockchain import TransactionType

router = APIRouter(tags=["Properties"])


# ── Pydantic models ───────────────────────────────────────────────────────────
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


class TransferProperty(BaseModel):
    property_id: str
    new_owner_name: str
    new_owner_email: str
    new_owner_aadhaar: str
    transfer_amount: float


class FractionalInvestment(BaseModel):
    property_id: str
    fraction_percent: float
    investor_email: str


# ── Helpers ───────────────────────────────────────────────────────────────────
def _gen_property_id() -> str:
    return "PROP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def _serialize(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


# ── Routes ────────────────────────────────────────────────────────────────────
@router.get(
    "/properties",
    summary="List all registered properties",
)
async def list_properties(
    city: Optional[str] = None,
    status: Optional[str] = None,
    prop_type: Optional[str] = None,
):
    query: dict = {}
    if city:
        query["city"] = {"$regex": city, "$options": "i"}
    if status:
        query["status"] = {"$regex": status, "$options": "i"}
    if prop_type:
        query["property_type"] = {"$regex": prop_type, "$options": "i"}

    cursor = properties_collection.find(query).sort("registered_at", -1)
    props = [_serialize(p) async for p in cursor]
    return {"properties": props, "total": len(props)}


@router.get(
    "/properties/{property_id}",
    summary="Get property passport detail",
)
async def get_property(property_id: str):
    prop = await properties_collection.find_one({"id": property_id})
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    prop = _serialize(prop)

    # Attach fractional holders
    holders_cursor = fractional_collection.find({"property_id": property_id})
    prop["holders"] = [_serialize(h) async for h in holders_cursor]
    return prop


@router.post(
    "/properties/register",
    summary="Register a new property on PropChain blockchain",
)
async def register_property(prop: PropertyCreate):
    prop_id = _gen_property_id()
    fraud_score = random.randint(1, 20)
    status = "Verified" if fraud_score < 10 else "Under Review"
    registered_at = datetime.utcnow().isoformat()

    # ── Mint genesis block on blockchain ──────────────────────────────────────
    block_data = {
        "owner_name": prop.owner_name,
        "owner_aadhaar_last4": prop.owner_aadhaar[-4:] if len(prop.owner_aadhaar) >= 4 else prop.owner_aadhaar,
        "property_address": f"{prop.address}, {prop.city}, {prop.state} - {prop.pincode}",
        "area_sqft": prop.area_sqft,
        "property_type": prop.property_type,
        "market_value": prop.market_value,
        "registration_number": prop.survey_number,
        "registration_status": "REGISTERED",
    }
    block = await mint_genesis(prop_id, block_data)

    new_prop = {
        "id": prop_id,
        **prop.dict(),
        "owner_email": "",
        "status": status,
        "registered_at": registered_at,
        "blockchain_hash": block["hash"],
        "fractional_enabled": False,
        "total_tokens": 0,
        "available_tokens": 0,
        "token_price": 0,
        "images": [],
        "documents_verified": status == "Verified",
        "fraud_score": fraud_score,
    }
    await properties_collection.insert_one(new_prop)

    # ── Log transaction ───────────────────────────────────────────────────────
    txn = {
        "id": str(uuid.uuid4()),
        "type": "REGISTRATION",
        "property_id": prop_id,
        "from": "Applicant",
        "to": prop.owner_name,
        "amount": prop.market_value,
        "timestamp": registered_at,
        "block_hash": block["hash"],
        "status": "Confirmed",
    }
    await transactions_collection.insert_one(txn)

    return {
        "message": "Property registered successfully",
        "property": _serialize(new_prop),
        "block": {
            "hash": block["hash"],
            "index": block["block_index"],
            "timestamp": block["timestamp"],
        },
    }


@router.post(
    "/properties/{property_id}/transfer",
    summary="Transfer property ownership",
)
async def transfer_property(property_id: str, transfer: TransferProperty):
    prop = await properties_collection.find_one({"id": property_id})
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    old_owner = prop["owner_name"]

    # ── Append transfer block ─────────────────────────────────────────────────
    block = await add_transaction(
        property_id=property_id,
        transaction_type=TransactionType.OWNERSHIP_TRANSFER,
        data={
            "from_owner": old_owner,
            "to_owner": transfer.new_owner_name,
            "sale_price": transfer.transfer_amount,
            "transaction_ref": f"TXN-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            "stamp_duty_paid": True,
            "registration_fee_paid": True,
        },
    )

    # ── Update property record ─────────────────────────────────────────────────
    update = {
        "$set": {
            "owner_name": transfer.new_owner_name,
            "owner_email": transfer.new_owner_email,
            "owner_aadhaar": transfer.new_owner_aadhaar,
            "status": "Verified",
            "blockchain_hash": block["hash"],
        }
    }
    await properties_collection.update_one({"id": property_id}, update)

    txn = {
        "id": str(uuid.uuid4()),
        "type": "TRANSFER",
        "property_id": property_id,
        "from": old_owner,
        "to": transfer.new_owner_name,
        "amount": transfer.transfer_amount,
        "timestamp": datetime.utcnow().isoformat(),
        "block_hash": block["hash"],
        "status": "Confirmed",
    }
    await transactions_collection.insert_one(txn)

    updated_prop = _serialize(await properties_collection.find_one({"id": property_id}))
    return {
        "message": "Property transferred successfully",
        "block": {"hash": block["hash"], "index": block["block_index"]},
        "property": updated_prop,
    }


@router.post(
    "/properties/{property_id}/enable-fractional",
    summary="Enable fractional ownership for a property",
)
async def enable_fractional(property_id: str, total_tokens: int = 1000):
    prop = await properties_collection.find_one({"id": property_id})
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    token_price = int(prop["market_value"] / total_tokens)

    block = await add_transaction(
        property_id=property_id,
        transaction_type=TransactionType.FRACTIONAL_MINT,
        data={
            "total_tokens": total_tokens,
            "token_price": token_price,
            "token_symbol": f"{property_id}-TKN",
            "owner_name": prop["owner_name"],
        },
    )

    await properties_collection.update_one(
        {"id": property_id},
        {
            "$set": {
                "fractional_enabled": True,
                "total_tokens": total_tokens,
                "available_tokens": total_tokens,
                "token_price": token_price,
                "blockchain_hash": block["hash"],
            }
        },
    )

    return {
        "message": "Fractional ownership enabled",
        "token_price": token_price,
        "total_tokens": total_tokens,
        "block": {"hash": block["hash"], "index": block["block_index"]},
    }


@router.post(
    "/fractional/invest",
    summary="Purchase fractional tokens in a property",
)
async def invest_fractional(inv: FractionalInvestment):
    prop = await properties_collection.find_one({"id": inv.property_id})
    if not prop or not prop.get("fractional_enabled"):
        raise HTTPException(status_code=400, detail="Property not available for fractional investment")

    tokens_to_buy = int((inv.fraction_percent / 100) * prop["total_tokens"])
    if tokens_to_buy < 1:
        raise HTTPException(status_code=400, detail="Fraction too small — minimum 1 token")
    if tokens_to_buy > prop["available_tokens"]:
        raise HTTPException(status_code=400, detail=f"Only {prop['available_tokens']} tokens available")

    amount = tokens_to_buy * prop["token_price"]

    block = await add_transaction(
        property_id=inv.property_id,
        transaction_type=TransactionType.FRACTIONAL_TRANSFER,
        data={
            "investor_email": inv.investor_email,
            "tokens_purchased": tokens_to_buy,
            "amount_paid": amount,
            "from_holder": prop["owner_name"],
            "to_holder": inv.investor_email.split("@")[0].title(),
        },
    )

    await properties_collection.update_one(
        {"id": inv.property_id},
        {"$inc": {"available_tokens": -tokens_to_buy}},
    )

    holder = {
        "property_id": inv.property_id,
        "investor": inv.investor_email.split("@")[0].title(),
        "email": inv.investor_email,
        "tokens": tokens_to_buy,
        "invested": amount,
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
    }
    await fractional_collection.insert_one(holder)

    txn = {
        "id": str(uuid.uuid4()),
        "type": "FRACTIONAL_PURCHASE",
        "property_id": inv.property_id,
        "from": prop["owner_name"],
        "to": inv.investor_email,
        "amount": amount,
        "timestamp": datetime.utcnow().isoformat(),
        "block_hash": block["hash"],
        "status": "Confirmed",
    }
    await transactions_collection.insert_one(txn)

    return {
        "message": "Investment successful",
        "tokens": tokens_to_buy,
        "amount": amount,
        "block": {"hash": block["hash"], "index": block["block_index"]},
    }
