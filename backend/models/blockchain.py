from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any
from enum import Enum


# ---------------------------------------------------------------------------
# Transaction types — every block must declare what kind of event it records
# ---------------------------------------------------------------------------
class TransactionType(str, Enum):
    GENESIS = "GENESIS"                          # First registration of a property
    OWNERSHIP_TRANSFER = "OWNERSHIP_TRANSFER"    # Buyer ↔ Seller transfer
    DOCUMENT_VERIFICATION = "DOCUMENT_VERIFICATION"  # AI fraud-check result logged
    STATUS_UPDATE = "STATUS_UPDATE"              # e.g. "DISPUTED", "ENCUMBERED"
    FRACTIONAL_MINT = "FRACTIONAL_MINT"          # Fractional tokens created
    FRACTIONAL_TRANSFER = "FRACTIONAL_TRANSFER"  # Token sold to investor
    FRACTIONAL_REDEEM = "FRACTIONAL_REDEEM"      # Token holder exits / sells back
    # Deal / Negotiation / Installment Payment lifecycle
    DEAL_INITIATED = "DEAL_INITIATED"            # Buyer makes an offer at negotiated price
    DEAL_ACCEPTED = "DEAL_ACCEPTED"              # Seller accepts the offer
    INSTALLMENT_PAYMENT = "INSTALLMENT_PAYMENT"  # Advance or monthly EMI recorded on-chain


# ---------------------------------------------------------------------------
# Request models (what the API accepts)
# ---------------------------------------------------------------------------

class MintPropertyRequest(BaseModel):
    """Register a brand-new property on the blockchain (genesis block)."""
    property_id: str = Field(..., example="PROP-KA-2024-001")
    owner_name: str = Field(..., example="Ravi Kumar")
    owner_aadhaar_last4: str = Field(..., min_length=4, max_length=4, example="7890")
    property_address: str = Field(..., example="123 MG Road, Bengaluru, KA 560001")
    area_sqft: float = Field(..., gt=0, example=1200.0)
    property_type: str = Field(..., example="Residential")  # Residential / Commercial / Agricultural
    market_value: float = Field(..., gt=0, example=5000000.0)
    registration_number: Optional[str] = Field(None, example="REG-BLR-2024-9876")

    @field_validator("owner_aadhaar_last4")
    @classmethod
    def must_be_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("owner_aadhaar_last4 must contain only digits")
        return v


class TransferOwnershipRequest(BaseModel):
    """Record an ownership transfer between parties."""
    property_id: str = Field(..., example="PROP-KA-2024-001")
    from_owner: str = Field(..., example="Ravi Kumar")
    to_owner: str = Field(..., example="Priya Sharma")
    sale_price: float = Field(..., gt=0, example=5500000.0)
    transaction_ref: str = Field(..., example="TXN-20240228-001")
    stamp_duty_paid: bool = Field(default=False)
    registration_fee_paid: bool = Field(default=False)


class DocumentVerificationRequest(BaseModel):
    """Log an AI document verification result on-chain."""
    property_id: str = Field(..., example="PROP-KA-2024-001")
    document_type: str = Field(..., example="Title Deed")
    document_hash: str = Field(..., description="SHA-256 hash of the uploaded document file")
    fraud_score: float = Field(..., ge=0.0, le=1.0, description="0 = clean, 1 = highly suspicious")
    is_authentic: bool
    flags: list[str] = Field(default_factory=list, example=["font_inconsistency", "metadata_mismatch"])
    verified_by: str = Field(default="PropChain-AI")


class StatusUpdateRequest(BaseModel):
    """Update the legal/registration status of a property."""
    property_id: str = Field(..., example="PROP-KA-2024-001")
    new_status: str = Field(..., example="ENCUMBERED")  # REGISTERED, DISPUTED, ENCUMBERED, CLEARED
    reason: str = Field(..., example="Bank loan mortgage registered")
    updated_by: str = Field(..., example="Sub-Registrar Office, Bengaluru")


class FractionalMintRequest(BaseModel):
    """Tokenize a property into fractional shares."""
    property_id: str = Field(..., example="PROP-KA-2024-001")
    total_tokens: int = Field(..., gt=0, example=1000)
    token_symbol: str = Field(..., example="PROP-KA-001-TKN")
    price_per_token: float = Field(..., gt=0, example=5000.0)
    owner_name: str = Field(..., example="Ravi Kumar")


class FractionalTransferRequest(BaseModel):
    """Record sale of fractional tokens."""
    property_id: str = Field(..., example="PROP-KA-2024-001")
    from_holder: str = Field(..., example="Ravi Kumar")
    to_holder: str = Field(..., example="Amit Patel")
    tokens_transferred: int = Field(..., gt=0, example=50)
    price_per_token: float = Field(..., gt=0, example=5200.0)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class BlockResponse(BaseModel):
    """A single block as returned by the API."""
    block_index: int
    property_id: str
    transaction_type: TransactionType
    data: dict
    previous_hash: str
    timestamp: str
    hash: str

    class Config:
        from_attributes = True


class PropertyPassportResponse(BaseModel):
    """Full blockchain history for a property."""
    property_id: str
    current_owner: str
    current_status: str
    total_blocks: int
    latest_hash: str
    is_chain_valid: bool
    transaction_history: list[BlockResponse]


class ChainVerificationResponse(BaseModel):
    """Result of chain integrity check."""
    property_id: str
    total_blocks: int
    is_valid: bool
    status: str   # "INTACT" or "COMPROMISED"
    errors: list[str]
