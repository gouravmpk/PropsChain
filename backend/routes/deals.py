"""
Property Deal / Negotiation / Installment Routes
-------------------------------------------------
Real-world deal flow:
  Buyer finds Verified property → makes an offer at a negotiated price
  → seller accepts → buyer pays advance → pays monthly installments
  → on full payment PropChain auto-transfers ownership on-chain.

Routes:
  POST   /deals                          — buyer initiates a deal offer
  GET    /deals/my                       — all deals for logged-in user
  GET    /deals/{deal_id}                — deal detail
  POST   /deals/{deal_id}/accept         — seller accepts
  POST   /deals/{deal_id}/pay            — record advance / EMI payment
  POST   /deals/{deal_id}/cancel         — buyer or seller cancels
"""

import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from config.database import (
    blockchain_collection,
    deals_collection,
    properties_collection,
    transactions_collection,
    users_collection,
)
from models.blockchain import TransactionType
from routes.auth import get_current_user_from_token

router = APIRouter(prefix="/deals", tags=["Deals"])


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic request models
# ─────────────────────────────────────────────────────────────────────────────

class CreateDealRequest(BaseModel):
    property_id: str
    buyer_aadhaar: str
    negotiated_price: float = Field(..., gt=0, description="Agreed price after negotiation")
    advance_amount: float = Field(..., gt=0, description="Advance / token money amount")
    installments_total: int = Field(..., ge=1, le=120, description="Number of monthly EMIs (1–120)")
    message: Optional[str] = Field(None, description="Optional message for the seller")
    payment_deadline: Optional[str] = Field(
        None,
        description="ISO date (YYYY-MM-DD) by which all payments must be completed. "
                    "For reference only — does not auto-cancel the deal.",
    )


class PayInstallmentRequest(BaseModel):
    note: Optional[str] = None
    pay_full: bool = Field(
        False,
        description="Set True to pay the entire remaining balance at once "
                    "instead of a single EMI.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Internal helper — append a block to a property's blockchain chain
# ─────────────────────────────────────────────────────────────────────────────

async def _add_block(property_id: str, tx_type: TransactionType, data: dict) -> str:
    """Write one append-only SHA-256 block and also log to transactions."""
    count = await blockchain_collection.count_documents({"property_id": property_id})
    last = await blockchain_collection.find_one(
        {"property_id": property_id}, sort=[("block_index", -1)]
    )
    prev_hash = last["hash"] if last else "0" * 64

    payload = {
        "block_index": count,
        "property_id": property_id,
        "transaction_type": tx_type.value,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data,
        "previous_hash": prev_hash,
    }
    raw = json.dumps(payload, sort_keys=True, default=str)
    block_hash = hashlib.sha256(raw.encode()).hexdigest()
    payload["hash"] = block_hash
    await blockchain_collection.insert_one(payload)

    # Mirror to transactions collection (for dashboard / history views)
    await transactions_collection.insert_one({
        "property_id": property_id,
        "type": tx_type.value,
        "hash": block_hash,
        "created_at": datetime.utcnow().isoformat(),
        **data,
    })
    return block_hash


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.post("", summary="Buyer initiates a deal offer")
async def create_deal(req: CreateDealRequest, authorization: str = Header(None)):
    """
    Buyer makes a negotiated offer on a Verified property.
    Records a DEAL_INITIATED block on-chain.
    """
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    prop = await properties_collection.find_one({"id": req.property_id})
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if prop.get("status") != "Verified":
        raise HTTPException(status_code=400, detail="Only Verified properties can be negotiated")

    # Prevent self-dealing (compare by name since owner_email may be empty)
    if (prop.get("owner_email") and prop["owner_email"] == user["email"]) or \
       prop.get("owner_name", "").lower() == user.get("name", "").lower():
        raise HTTPException(status_code=400, detail="You cannot make an offer on your own property")

    # Validate amounts
    if req.advance_amount >= req.negotiated_price:
        raise HTTPException(status_code=400, detail="Advance amount must be less than negotiated price")

    # Block duplicate active deals
    existing = await deals_collection.find_one({
        "property_id": req.property_id,
        "status": {"$in": ["PENDING_SELLER", "ACCEPTED", "IN_PROGRESS"]},
    })
    if existing:
        raise HTTPException(
            status_code=409,
            detail="An active deal already exists for this property. Cancel it first.",
        )

    # Resolve seller identity — fall back to DB lookup if owner_email is blank
    seller_email = prop.get("owner_email") or ""
    seller_name = prop.get("owner_name", "Unknown")
    if not seller_email:
        seller_user = await users_collection.find_one({
            "name": {"$regex": f"^{seller_name}$", "$options": "i"}
        })
        seller_email = seller_user["email"] if seller_user else ""

    emi = round((req.negotiated_price - req.advance_amount) / req.installments_total, 2)
    deal_id = f"DEAL-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.utcnow().isoformat()

    deal = {
        "id": deal_id,
        "property_id": req.property_id,
        "property_title": prop.get("title", ""),
        "property_address": f"{prop.get('address', '')}, {prop.get('city', '')}, {prop.get('state', '')}",
        "asking_price": prop.get("market_value", 0),
        "negotiated_price": req.negotiated_price,
        "advance_amount": req.advance_amount,
        "installments_total": req.installments_total,
        "monthly_emi": emi,
        "payment_deadline": req.payment_deadline,  # optional YYYY-MM-DD target date
        "seller_name": seller_name,
        "seller_email": seller_email,
        "seller_aadhaar": prop.get("owner_aadhaar", ""),
        "buyer_name": user["name"],
        "buyer_email": user["email"],
        "buyer_aadhaar": req.buyer_aadhaar,
        "message": req.message,
        "status": "PENDING_SELLER",
        "total_paid": 0,
        "payments": [],
        "created_at": now,
        "accepted_at": None,
        "completed_at": None,
        "blockchain_initiated_hash": None,
        "blockchain_accepted_hash": None,
        "blockchain_completed_hash": None,
    }

    await deals_collection.insert_one(deal)

    block_hash = await _add_block(req.property_id, TransactionType.DEAL_INITIATED, {
        "deal_id": deal_id,
        "buyer_name": user["name"],
        "buyer_email": user["email"],
        "negotiated_price": req.negotiated_price,
        "advance_amount": req.advance_amount,
        "installments_total": req.installments_total,
        "monthly_emi": emi,
        "payment_deadline": req.payment_deadline,
    })
    await deals_collection.update_one(
        {"id": deal_id},
        {"$set": {"blockchain_initiated_hash": block_hash}}
    )

    return {
        "success": True,
        "deal_id": deal_id,
        "monthly_emi": emi,
        "blockchain_hash": block_hash,
        "message": "Offer submitted. Waiting for seller to accept.",
    }


@router.get("/my", summary="Get all deals for the logged-in user")
async def get_my_deals(authorization: str = Header(None)):
    """Returns deals where the user is buyer or seller, newest first."""
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    cursor = deals_collection.find(
        {"$or": [
            {"buyer_email": user["email"]},
            {"seller_email": user["email"]},
            # Also match by name for compatibility with empty seller_email
            {"seller_name": {"$regex": f"^{user['name']}$", "$options": "i"}},
        ]},
        {"_id": 0},
    ).sort("created_at", -1)
    deals = await cursor.to_list(100)
    return deals


@router.get("/{deal_id}", summary="Get deal details")
async def get_deal(deal_id: str, authorization: str = Header(None)):
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    deal = await deals_collection.find_one({"id": deal_id}, {"_id": 0})
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.post("/{deal_id}/accept", summary="Seller accepts the deal offer")
async def accept_deal(deal_id: str, authorization: str = Header(None)):
    """Seller confirms the deal. Buyer can now start paying."""
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    deal = await deals_collection.find_one({"id": deal_id})
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Allow match by email OR by name (for properties registered without email)
    is_seller = (
        deal.get("seller_email") == user["email"]
        or deal.get("seller_name", "").lower() == user.get("name", "").lower()
    )
    if not is_seller:
        raise HTTPException(status_code=403, detail="Only the seller can accept this deal")
    if deal["status"] != "PENDING_SELLER":
        raise HTTPException(status_code=400, detail=f"Deal is already {deal['status']}")

    now = datetime.utcnow().isoformat()
    await deals_collection.update_one(
        {"id": deal_id},
        {"$set": {"status": "ACCEPTED", "accepted_at": now, "seller_email": user["email"]}},
    )

    block_hash = await _add_block(deal["property_id"], TransactionType.DEAL_ACCEPTED, {
        "deal_id": deal_id,
        "seller_name": deal["seller_name"],
        "buyer_name": deal["buyer_name"],
        "negotiated_price": deal["negotiated_price"],
        "advance_amount": deal["advance_amount"],
        "installments_total": deal["installments_total"],
    })
    await deals_collection.update_one(
        {"id": deal_id}, {"$set": {"blockchain_accepted_hash": block_hash}}
    )

    return {"success": True, "blockchain_hash": block_hash}


@router.post("/{deal_id}/pay", summary="Buyer records advance or monthly installment")
async def pay_installment(
    deal_id: str,
    req: PayInstallmentRequest = PayInstallmentRequest(),
    authorization: str = Header(None),
):
    """
    First call → records the advance payment.
    Subsequent calls → records each monthly EMI.
    When total_paid >= negotiated_price the deal completes and ownership is
    automatically transferred on-chain (OWNERSHIP_TRANSFER block minted).
    """
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    deal = await deals_collection.find_one({"id": deal_id})
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal["buyer_email"] != user["email"]:
        raise HTTPException(status_code=403, detail="Only the buyer can make payments")
    if deal["status"] not in ("ACCEPTED", "IN_PROGRESS"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pay on a deal with status '{deal['status']}'. Seller must accept first.",
        )

    payments = deal["payments"]
    is_advance = len(payments) == 0

    # ── Determine amount based on pay_full flag ────────────────────────────
    current_remaining = round(deal["negotiated_price"] - deal["total_paid"], 2)
    if req.pay_full and not is_advance:
        # Buyer is clearing the entire remaining balance in one shot
        amount = max(current_remaining, 0)
        pay_type = "FULL_PAYMENT"
        month_num = len(payments)   # label it from current position
    elif is_advance:
        amount = deal["advance_amount"]
        pay_type = "ADVANCE"
        month_num = 0
    else:
        amount = deal["monthly_emi"]
        pay_type = "EMI"
        month_num = len(payments)   # 1..N = EMI months

    if amount <= 0:
        raise HTTPException(status_code=400, detail="No remaining balance to pay.")

    new_total_paid = round(deal["total_paid"] + amount, 2)
    remaining = round(deal["negotiated_price"] - new_total_paid, 2)
    if remaining < 0:
        remaining = 0

    payment_id = f"PAY-{uuid.uuid4().hex[:8].upper()}"
    default_note = (
        "Advance payment" if is_advance
        else "Full remaining balance cleared" if pay_type == "FULL_PAYMENT"
        else f"Installment #{month_num}"
    )
    payment_record = {
        "id": payment_id,
        "amount": amount,
        "type": pay_type,
        "month": month_num,
        "paid_at": datetime.utcnow().isoformat(),
        "note": req.note or default_note,
    }

    auto_transfer = new_total_paid >= deal["negotiated_price"]
    new_status = "COMPLETED" if auto_transfer else "IN_PROGRESS"

    block_hash = await _add_block(deal["property_id"], TransactionType.INSTALLMENT_PAYMENT, {
        "deal_id": deal_id,
        "payment_id": payment_id,
        "payment_type": pay_type,
        "amount": amount,
        "total_paid": new_total_paid,
        "remaining": remaining,
        "buyer": deal["buyer_name"],
        "seller": deal["seller_name"],
        "month": month_num,
    })
    payment_record["block_hash"] = block_hash

    update_data: dict = {
        "total_paid": new_total_paid,
        "status": new_status,
    }
    if new_status == "COMPLETED":
        update_data["completed_at"] = datetime.utcnow().isoformat()

    await deals_collection.update_one(
        {"id": deal_id},
        {"$push": {"payments": payment_record}, "$set": update_data},
    )

    # ── Auto-transfer ownership when fully paid ────────────────────────────
    if auto_transfer:
        await properties_collection.update_one(
            {"id": deal["property_id"]},
            {"$set": {
                "owner_name": deal["buyer_name"],
                "owner_email": deal["buyer_email"],
                "owner_aadhaar": deal["buyer_aadhaar"],
                "market_value": deal["negotiated_price"],
            }},
        )
        transfer_hash = await _add_block(
            deal["property_id"], TransactionType.OWNERSHIP_TRANSFER, {
                "deal_id": deal_id,
                "from_owner": deal["seller_name"],
                "to_owner": deal["buyer_name"],
                "sale_price": deal["negotiated_price"],
                "transaction_ref": deal_id,
                "stamp_duty_paid": True,
                "auto_transferred_on_full_payment": True,
            }
        )
        await deals_collection.update_one(
            {"id": deal_id}, {"$set": {"blockchain_completed_hash": transfer_hash}}
        )

    return {
        "success": True,
        "payment": payment_record,
        "total_paid": new_total_paid,
        "remaining": remaining,
        "deal_status": new_status,
        "ownership_transferred": auto_transfer,
    }


@router.post("/{deal_id}/cancel", summary="Buyer or seller cancels the deal")
async def cancel_deal(deal_id: str, authorization: str = Header(None)):
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    deal = await deals_collection.find_one({"id": deal_id})
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    is_party = (
        user["email"] in (deal.get("buyer_email"), deal.get("seller_email"))
        or user.get("name", "").lower() == deal.get("seller_name", "").lower()
    )
    if not is_party:
        raise HTTPException(status_code=403, detail="Not authorised to cancel this deal")
    if deal["status"] in ("COMPLETED", "CANCELLED"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel a {deal['status']} deal")

    await deals_collection.update_one(
        {"id": deal_id},
        {"$set": {"status": "CANCELLED", "cancelled_at": datetime.utcnow().isoformat()}},
    )
    return {"success": True, "message": "Deal cancelled"}
