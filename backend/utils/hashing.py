import hashlib
import json
from datetime import datetime, timezone


def compute_hash(block_index: int, property_id: str, data: dict, previous_hash: str, timestamp: str) -> str:
    """
    Compute SHA-256 hash of a block.
    Keys are sorted to ensure consistent hashing regardless of dict insertion order.
    """
    block_string = json.dumps(
        {
            "block_index": block_index,
            "property_id": property_id,
            "data": data,
            "previous_hash": previous_hash,
            "timestamp": timestamp,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(block_string.encode()).hexdigest()


def get_utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


GENESIS_HASH = "0" * 64  # Standard genesis previous hash placeholder
