from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


class DocumentType(str, Enum):
    TITLE_DEED = "Title Deed"
    SALE_AGREEMENT = "Sale Agreement"
    AADHAAR = "Aadhaar Card"
    PAN = "PAN Card"
    ENCUMBRANCE_CERT = "Encumbrance Certificate"
    PROPERTY_TAX = "Property Tax Receipt"
    NOC = "No Objection Certificate"
    MUTATION_CERT = "Mutation Certificate"


class Verdict(str, Enum):
    AUTHENTIC = "AUTHENTIC"
    SUSPICIOUS = "SUSPICIOUS"
    FLAGGED = "FLAGGED"


class ExtractionMode(str, Enum):
    AWS = "aws"      # Real Bedrock (Claude vision)
    MOCK = "mock"    # Simulated (no AWS needed)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class ExtractedField(BaseModel):
    key: str
    value: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class RuleCheckResult(BaseModel):
    rule: str
    passed: bool
    detail: str


class DocumentVerifyResponse(BaseModel):
    # Document identity
    document_hash: str = Field(..., description="SHA-256 hash of the uploaded file")
    document_type: str
    file_name: str
    file_size_kb: float

    # Extraction results
    extracted_fields: list[ExtractedField]
    raw_text_preview: str = Field(..., description="First 500 chars of extracted text")
    extraction_confidence: float = Field(..., ge=0.0, le=1.0)

    # Fraud analysis
    fraud_score: float = Field(..., ge=0.0, le=1.0, description="0 = clean, 1 = highly suspicious")
    verdict: Verdict
    is_authentic: bool
    flags: list[str] = Field(default_factory=list)
    rule_checks: list[RuleCheckResult]
    ai_explanation: str

    # Meta
    verified_by: str
    mode: ExtractionMode
    processing_time_ms: int

    # On-chain logging (if auto_log=True)
    blockchain_block: Optional[dict] = None
    logged_on_chain: bool = False


# ---------------------------------------------------------------------------
# Cross-document consistency check models
# ---------------------------------------------------------------------------

class Inconsistency(BaseModel):
    field: str = Field(..., description="The field that is inconsistent across documents")
    documents_involved: list[str] = Field(..., description="Document types where the conflict was found")
    values: dict = Field(default_factory=dict, description="The conflicting values per document")
    description: str = Field(..., description="Human-readable explanation of the inconsistency")
    severity: Literal["HIGH", "MEDIUM", "LOW"]


class PerDocResult(BaseModel):
    document_type: str
    file_name: str
    extracted: list[ExtractedField]


class CrossVerifyResponse(BaseModel):
    overall_verdict: Literal["CONSISTENT", "INCONSISTENT", "SUSPICIOUS"]
    consistency_score: int = Field(..., ge=0, le=100, description="0 = fully inconsistent, 100 = fully consistent")
    documents_analyzed: int
    per_doc_results: list[PerDocResult]
    inconsistencies: list[Inconsistency]
    ai_summary: str
    verified_by: str
    mode: ExtractionMode
    processing_time_ms: int
    logged_on_chain: bool = False
    block_hash: Optional[str] = None
