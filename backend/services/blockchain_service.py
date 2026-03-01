from bson import ObjectId
from fastapi import HTTPException

from config.database import blockchain_collection, properties_collection
from models.blockchain import TransactionType
from utils.hashing import compute_hash, get_utc_timestamp, GENESIS_HASH


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _serialize(doc: dict) -> dict:
    """Convert MongoDB document to JSON-safe dict (ObjectId → str)."""
    doc["_id"] = str(doc["_id"])
    return doc


async def _get_latest_block(property_id: str) -> dict | None:
    """Return the highest-index block for a property, or None if not found."""
    return await blockchain_collection.find_one(
        {"property_id": property_id},
        sort=[("block_index", -1)],
    )


async def _get_full_chain(property_id: str) -> list[dict]:
    """Return all blocks for a property ordered from genesis to latest."""
    cursor = blockchain_collection.find(
        {"property_id": property_id},
        sort=[("block_index", 1)],
    )
    return await cursor.to_list(length=None)


def _build_block(
    block_index: int,
    property_id: str,
    transaction_type: TransactionType,
    data: dict,
    previous_hash: str,
) -> dict:
    """Assemble a block dict and compute its hash."""
    timestamp = get_utc_timestamp()
    block = {
        "block_index": block_index,
        "property_id": property_id,
        "transaction_type": transaction_type,
        "data": data,
        "previous_hash": previous_hash,
        "timestamp": timestamp,
        "minted_by": "PropChain-Mock",
    }
    block["hash"] = compute_hash(
        block_index=block_index,
        property_id=property_id,
        data=data,
        previous_hash=previous_hash,
        timestamp=timestamp,
    )
    return block


async def _insert_block(block: dict) -> dict:
    """Persist a block to MongoDB and return the serialized document."""
    try:
        result = await blockchain_collection.insert_one(block)
        block["_id"] = str(result.inserted_id)
        return block
    except Exception as e:
        # Unique index violation means a block with this index already exists
        raise HTTPException(
            status_code=409,
            detail=f"Block insertion failed (possible duplicate): {str(e)}",
        )


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

async def mint_genesis(property_id: str, data: dict) -> dict:
    """
    Create the genesis (first) block for a property.
    Raises 400 if the property is already registered.
    """
    existing = await _get_latest_block(property_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Property '{property_id}' is already registered on the chain.",
        )

    block = _build_block(
        block_index=0,
        property_id=property_id,
        transaction_type=TransactionType.GENESIS,
        data=data,
        previous_hash=GENESIS_HASH,
    )
    return await _insert_block(block)


async def add_transaction(
    property_id: str,
    transaction_type: TransactionType,
    data: dict,
) -> dict:
    """
    Append a new block to an existing property chain.
    Raises 404 if the property has not been registered yet.
    """
    latest = await _get_latest_block(property_id)
    if not latest:
        raise HTTPException(
            status_code=404,
            detail=f"Property '{property_id}' not found on chain. Register it first via /blockchain/mint.",
        )

    block = _build_block(
        block_index=latest["block_index"] + 1,
        property_id=property_id,
        transaction_type=transaction_type,
        data=data,
        previous_hash=latest["hash"],
    )
    return await _insert_block(block)


async def get_property_passport(property_id: str) -> dict:
    """
    Build a full Property Passport from the chain.
    Derives current owner and status by replaying all transactions.
    Also runs chain verification inline.
    """
    chain = await _get_full_chain(property_id)
    if not chain:
        raise HTTPException(
            status_code=404,
            detail=f"No blockchain record found for property '{property_id}'.",
        )

    # Replay the chain to derive current state
    current_owner = "Unknown"
    current_status = "UNREGISTERED"

    for block in chain:
        t = block["transaction_type"]
        d = block["data"]

        if t == TransactionType.GENESIS:
            current_owner = d.get("owner_name", "Unknown")
            current_status = d.get("registration_status", "REGISTERED")

        elif t == TransactionType.OWNERSHIP_TRANSFER:
            current_owner = d.get("to_owner", current_owner)

        elif t == TransactionType.STATUS_UPDATE:
            current_status = d.get("new_status", current_status)

    # Verify integrity
    verification = await verify_chain(property_id)

    return {
        "property_id": property_id,
        "current_owner": current_owner,
        "current_status": current_status,
        "total_blocks": len(chain),
        "latest_hash": chain[-1]["hash"],
        "is_chain_valid": verification["is_valid"],
        "transaction_history": [_serialize(b) for b in chain],
    }


async def verify_chain(property_id: str) -> dict:
    """
    Verify the integrity of every block in the chain:
    1. Each block's stored hash must match a freshly computed hash.
    2. Each block's previous_hash must match the prior block's hash.
    """
    chain = await _get_full_chain(property_id)
    if not chain:
        raise HTTPException(
            status_code=404,
            detail=f"No chain found for property '{property_id}'.",
        )

    errors: list[str] = []

    for i, block in enumerate(chain):
        # --- Hash integrity check ---
        expected_hash = compute_hash(
            block_index=block["block_index"],
            property_id=block["property_id"],
            data=block["data"],
            previous_hash=block["previous_hash"],
            timestamp=block["timestamp"],
        )
        if expected_hash != block["hash"]:
            errors.append(
                f"Block {i} (index {block['block_index']}): stored hash does not match — TAMPERED"
            )

        # --- Chain linkage check ---
        if i > 0:
            if block["previous_hash"] != chain[i - 1]["hash"]:
                errors.append(
                    f"Block {i} (index {block['block_index']}): previous_hash mismatch with block {i - 1} — CHAIN BROKEN"
                )

        # --- Genesis previous_hash check ---
        if i == 0 and block["previous_hash"] != GENESIS_HASH:
            errors.append(
                f"Block 0: previous_hash is not the expected genesis hash — TAMPERED"
            )

    return {
        "property_id": property_id,
        "total_blocks": len(chain),
        "is_valid": len(errors) == 0,
        "status": "INTACT" if not errors else "COMPROMISED",
        "errors": errors,
    }


async def get_block_by_hash(block_hash: str) -> dict:
    """Fetch a single block by its hash (block explorer use case)."""
    block = await blockchain_collection.find_one({"hash": block_hash})
    if not block:
        raise HTTPException(
            status_code=404,
            detail=f"No block found with hash '{block_hash}'.",
        )
    return _serialize(block)


async def get_all_properties() -> list[dict]:
    """Return a summary of all registered property IDs and their latest block."""
    pipeline = [
        {"$sort": {"block_index": -1}},
        {
            "$group": {
                "_id": "$property_id",
                "latest_block_index": {"$first": "$block_index"},
                "latest_hash": {"$first": "$hash"},
                "transaction_type": {"$first": "$transaction_type"},
                "registered_at": {"$last": "$timestamp"},
            }
        },
        {"$sort": {"registered_at": -1}},
    ]
    cursor = blockchain_collection.aggregate(pipeline)
    results = await cursor.to_list(length=None)
    return [
        {
            "property_id": r["_id"],
            "total_blocks": r["latest_block_index"] + 1,
            "latest_hash": r["latest_hash"],
            "registered_at": r["registered_at"],
        }
        for r in results
    ]
