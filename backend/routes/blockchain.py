from fastapi import APIRouter
from fastapi.responses import JSONResponse

from models.blockchain import (
    MintPropertyRequest,
    TransferOwnershipRequest,
    DocumentVerificationRequest,
    StatusUpdateRequest,
    FractionalMintRequest,
    FractionalTransferRequest,
    TransactionType,
)
from services.blockchain_service import (
    mint_genesis,
    add_transaction,
    get_property_passport,
    verify_chain,
    get_block_by_hash,
    get_all_properties,
)

router = APIRouter(prefix="/blockchain", tags=["Blockchain"])

# ---------------------------------------------------------------------------
# Shared response spec helpers
# ---------------------------------------------------------------------------
_400 = {400: {"description": "Property already registered on chain"}}
_404 = {404: {"description": "Property / Block not found on chain"}}
_409 = {409: {"description": "Block insertion conflict (duplicate)"}}


# ---------------------------------------------------------------------------
# 1. Register a new property — genesis block
# ---------------------------------------------------------------------------
@router.post(
    "/mint",
    summary="Register a property on the blockchain",
    description=(
        "Creates the **genesis block** (block_index = 0) for a property. "
        "The previous_hash of the genesis block is always `000...0` (64 zeros). "
        "Every subsequent transaction appends a new block linked by hash. "
        "\n\n**Error cases:**\n"
        "- `400` — property already registered\n"
    ),
    responses={
        200: {
            "description": "Genesis block created",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Property successfully registered on PropChain blockchain",
                        "property_id": "PROP-KA-2024-001",
                        "block_index": 0,
                        "hash": "b3f629ac19b7398f3c2a80d00df7b622b220d9c4a8f7ec8b5cdf8d47b44280af",
                        "timestamp": "2026-02-28T17:59:49.751390+00:00",
                    }
                }
            },
        },
        **_400,
    },
)
async def mint_property(req: MintPropertyRequest):
    data = {
        "owner_name": req.owner_name,
        "owner_aadhaar_last4": req.owner_aadhaar_last4,
        "property_address": req.property_address,
        "area_sqft": req.area_sqft,
        "property_type": req.property_type,
        "market_value": req.market_value,
        "registration_number": req.registration_number,
        "registration_status": "REGISTERED",
    }
    block = await mint_genesis(req.property_id, data)
    return {
        "message": "Property successfully registered on PropChain blockchain",
        "property_id": req.property_id,
        "block_index": block["block_index"],
        "hash": block["hash"],
        "timestamp": block["timestamp"],
        "block": block,
    }


# ---------------------------------------------------------------------------
# 2. Transfer ownership
# ---------------------------------------------------------------------------
@router.post(
    "/transfer",
    summary="Record an ownership transfer",
    description=(
        "Appends an **OWNERSHIP_TRANSFER** block to the property chain. "
        "The new owner becomes the `current_owner` visible in the Property Passport. "
        "\n\n**Error cases:**\n"
        "- `404` — property not registered yet\n"
    ),
    responses={
        200: {
            "description": "Ownership transfer recorded",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Ownership transferred from 'Ravi Kumar' to 'Priya Sharma'",
                        "property_id": "PROP-KA-2024-001",
                        "block_index": 2,
                        "hash": "57dd647364cfa801d55bb33902fe467fc0e07eec7dc4d975a67188701fc9bc0e",
                        "timestamp": "2026-02-28T18:00:44+00:00",
                    }
                }
            },
        },
        **_404,
    },
)
async def transfer_ownership(req: TransferOwnershipRequest):
    data = {
        "from_owner": req.from_owner,
        "to_owner": req.to_owner,
        "sale_price": req.sale_price,
        "transaction_ref": req.transaction_ref,
        "stamp_duty_paid": req.stamp_duty_paid,
        "registration_fee_paid": req.registration_fee_paid,
    }
    block = await add_transaction(req.property_id, TransactionType.OWNERSHIP_TRANSFER, data)
    return {
        "message": f"Ownership transferred from '{req.from_owner}' to '{req.to_owner}'",
        "property_id": req.property_id,
        "block_index": block["block_index"],
        "hash": block["hash"],
        "timestamp": block["timestamp"],
        "block": block,
    }


# ---------------------------------------------------------------------------
# 3. Log AI document verification
# ---------------------------------------------------------------------------
@router.post(
    "/verify-document",
    summary="Log AI document verification result on-chain",
    description=(
        "Records the result of an AI fraud-check for a property document. "
        "The **document itself is NOT stored** — only its SHA-256 hash and the AI verdict are written on-chain. "
        "This creates an immutable audit trail of every verification attempt. "
        "\n\n`fraud_score`: 0.0 = completely clean, 1.0 = highly suspicious"
        "\n\n**Error cases:**\n"
        "- `404` — property not registered yet\n"
    ),
    responses={
        200: {
            "description": "Verification result recorded on-chain",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Document verification result recorded on-chain",
                        "property_id": "PROP-KA-2024-001",
                        "verdict": "AUTHENTIC",
                        "fraud_score": 0.05,
                        "block_index": 1,
                        "hash": "a168dd2002966673ed655b31fe26b2d15ceaa4760a8a4037b3c81f69016e1c97",
                        "timestamp": "2026-02-28T17:59:58+00:00",
                    }
                }
            },
        },
        **_404,
    },
)
async def log_document_verification(req: DocumentVerificationRequest):
    data = {
        "document_type": req.document_type,
        "document_hash": req.document_hash,
        "fraud_score": req.fraud_score,
        "is_authentic": req.is_authentic,
        "flags": req.flags,
        "verified_by": req.verified_by,
        "verdict": "AUTHENTIC" if req.is_authentic else "SUSPICIOUS",
    }
    block = await add_transaction(req.property_id, TransactionType.DOCUMENT_VERIFICATION, data)
    return {
        "message": "Document verification result recorded on-chain",
        "property_id": req.property_id,
        "verdict": data["verdict"],
        "fraud_score": req.fraud_score,
        "block_index": block["block_index"],
        "hash": block["hash"],
        "timestamp": block["timestamp"],
        "block": block,
    }


# ---------------------------------------------------------------------------
# 4. Update property status
# ---------------------------------------------------------------------------
@router.post(
    "/status",
    summary="Update property legal status",
    description=(
        "Records a status change on-chain. Common values: "
        "`REGISTERED` | `DISPUTED` | `ENCUMBERED` | `CLEARED` | `UNDER_LITIGATION`"
        "\n\n**Error cases:**\n"
        "- `404` — property not registered yet\n"
    ),
    responses={
        200: {
            "description": "Status updated on-chain",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Property status updated to 'ENCUMBERED'",
                        "property_id": "PROP-KA-2024-001",
                        "new_status": "ENCUMBERED",
                        "block_index": 3,
                    }
                }
            },
        },
        **_404,
    },
)
async def update_status(req: StatusUpdateRequest):
    data = {
        "new_status": req.new_status,
        "reason": req.reason,
        "updated_by": req.updated_by,
    }
    block = await add_transaction(req.property_id, TransactionType.STATUS_UPDATE, data)
    return {
        "message": f"Property status updated to '{req.new_status}'",
        "property_id": req.property_id,
        "new_status": req.new_status,
        "block_index": block["block_index"],
        "hash": block["hash"],
        "timestamp": block["timestamp"],
        "block": block,
    }


# ---------------------------------------------------------------------------
# 5. Fractional ownership — mint tokens
# ---------------------------------------------------------------------------
@router.post(
    "/fractional/mint",
    summary="Tokenize a property into fractional shares",
    description=(
        "Records **fractional tokenization** of a property on-chain. "
        "For example, a ₹5.5 crore commercial building can be split into 1000 tokens at ₹5,500 each, "
        "allowing small investors to buy a portion. "
        "\n\n**Error cases:**\n"
        "- `404` — property not registered yet\n"
    ),
    responses={
        200: {
            "description": "Property tokenized",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Property tokenized into 1000 shares at ₹5500.0/token",
                        "token_symbol": "PROP-KA-001-TKN",
                        "total_value": 5500000.0,
                        "block_index": 4,
                    }
                }
            },
        },
        **_404,
    },
)
async def mint_fractional_tokens(req: FractionalMintRequest):
    data = {
        "total_tokens": req.total_tokens,
        "token_symbol": req.token_symbol,
        "price_per_token": req.price_per_token,
        "total_value": req.total_tokens * req.price_per_token,
        "owner_name": req.owner_name,
        "tokens_available": req.total_tokens,
    }
    block = await add_transaction(req.property_id, TransactionType.FRACTIONAL_MINT, data)
    return {
        "message": f"Property tokenized into {req.total_tokens} shares at ₹{req.price_per_token}/token",
        "property_id": req.property_id,
        "token_symbol": req.token_symbol,
        "total_value": data["total_value"],
        "block_index": block["block_index"],
        "hash": block["hash"],
        "timestamp": block["timestamp"],
        "block": block,
    }


# ---------------------------------------------------------------------------
# 6. Fractional ownership — transfer tokens
# ---------------------------------------------------------------------------
@router.post(
    "/fractional/transfer",
    summary="Record a fractional token sale",
    description=(
        "Records the sale of fractional tokens from one holder to another. "
        "Both parties and the number of tokens are logged immutably on-chain."
        "\n\n**Error cases:**\n"
        "- `404` — property not registered yet\n"
    ),
    responses={
        200: {
            "description": "Token transfer recorded",
            "content": {
                "application/json": {
                    "example": {
                        "message": "50 tokens transferred from 'Priya Sharma' to 'Amit Patel'",
                        "total_transaction_value": 260000.0,
                        "block_index": 5,
                    }
                }
            },
        },
        **_404,
    },
)
async def transfer_fractional_tokens(req: FractionalTransferRequest):
    data = {
        "from_holder": req.from_holder,
        "to_holder": req.to_holder,
        "tokens_transferred": req.tokens_transferred,
        "price_per_token": req.price_per_token,
        "total_transaction_value": req.tokens_transferred * req.price_per_token,
    }
    block = await add_transaction(req.property_id, TransactionType.FRACTIONAL_TRANSFER, data)
    return {
        "message": f"{req.tokens_transferred} tokens transferred from '{req.from_holder}' to '{req.to_holder}'",
        "property_id": req.property_id,
        "total_transaction_value": data["total_transaction_value"],
        "block_index": block["block_index"],
        "hash": block["hash"],
        "timestamp": block["timestamp"],
        "block": block,
    }


# ---------------------------------------------------------------------------
# 7. Property Passport — full chain history
# ---------------------------------------------------------------------------
@router.get(
    "/passport/{property_id}",
    summary="Get the full Property Passport",
    description=(
        "Returns the complete **Property Passport** — the full blockchain history for a property. "
        "The response includes:\n"
        "- `current_owner` — derived by replaying all OWNERSHIP_TRANSFER blocks\n"
        "- `current_status` — derived by replaying all STATUS_UPDATE blocks\n"
        "- `is_chain_valid` — live chain integrity check result\n"
        "- `transaction_history` — every block from genesis to latest\n"
        "\n\n**Error cases:**\n"
        "- `404` — property not registered yet\n"
    ),
    responses={**_404},
)
async def get_passport(property_id: str):
    return await get_property_passport(property_id)


# ---------------------------------------------------------------------------
# 8. Chain integrity verification
# ---------------------------------------------------------------------------
@router.get(
    "/verify/{property_id}",
    summary="Verify chain integrity",
    description=(
        "Replays every block in the chain and performs two checks:\n"
        "1. **Hash integrity** — recomputes each block's hash and compares with stored value\n"
        "2. **Chain linkage** — verifies each block's `previous_hash` matches the prior block's `hash`\n\n"
        "If any block was tampered with directly in the database, this endpoint will catch it "
        "and return `status: COMPROMISED` with the exact error location."
        "\n\n**Error cases:**\n"
        "- `404` — property not registered yet\n"
    ),
    responses={
        200: {
            "description": "Verification result",
            "content": {
                "application/json": {
                    "examples": {
                        "intact": {
                            "summary": "Chain is intact",
                            "value": {
                                "property_id": "PROP-KA-2024-001",
                                "total_blocks": 4,
                                "is_valid": True,
                                "status": "INTACT",
                                "errors": [],
                            },
                        },
                        "compromised": {
                            "summary": "Chain tampered",
                            "value": {
                                "property_id": "PROP-KA-2024-001",
                                "total_blocks": 4,
                                "is_valid": False,
                                "status": "COMPROMISED",
                                "errors": [
                                    "Block 1 (index 1): stored hash does not match — TAMPERED"
                                ],
                            },
                        },
                    }
                }
            },
        },
        **_404,
    },
)
async def verify_property_chain(property_id: str):
    return await verify_chain(property_id)


# ---------------------------------------------------------------------------
# 9. Block explorer — lookup by hash
# ---------------------------------------------------------------------------
@router.get(
    "/block/{block_hash}",
    summary="Block explorer — look up a block by its hash",
    description=(
        "Fetch a single block by its SHA-256 hash. "
        "Useful for building a block explorer UI or audit trail feature. "
        "Copy a `hash` value from any write response and paste it here."
        "\n\n**Error cases:**\n"
        "- `404` — no block found with this hash\n"
    ),
    responses={**_404},
)
async def get_block(block_hash: str):
    return await get_block_by_hash(block_hash)


# ---------------------------------------------------------------------------
# 10. List all registered properties
# ---------------------------------------------------------------------------
@router.get(
    "/properties",
    summary="List all properties on the chain",
    description=(
        "Returns a summary of every property currently registered on PropChain. "
        "Includes the latest block index and registration timestamp for each."
    ),
    responses={
        200: {
            "description": "List of all properties",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "property_id": "PROP-KA-2024-001",
                            "total_blocks": 4,
                            "latest_hash": "7d711a27f732e7715ad506d872956677f73a18c74705b1e291accfb70b34590a",
                            "registered_at": "2026-02-28T17:59:49.751390+00:00",
                        }
                    ]
                }
            },
        }
    },
)
async def list_properties():
    return await get_all_properties()
