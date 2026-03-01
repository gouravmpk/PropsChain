from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from enum import Enum

from models.ai_verify import DocumentType
from services.ai_service import verify_document, USE_AWS
from services.blockchain_service import add_transaction
from models.blockchain import TransactionType

router = APIRouter(prefix="/ai", tags=["AI Document Verification"])

ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/jpg", "image/tiff"}
MAX_SIZE_MB = 10


class MockScenario(str, Enum):
    AUTO        = "auto"        # deterministic from file hash (default)
    AUTHENTIC   = "authentic"   # always return clean result
    SUSPICIOUS  = "suspicious"  # always return suspicious result
    FLAGGED     = "flagged"     # always return flagged (high fraud) result


@router.post(
    "/verify-document",
    summary="Upload and verify a property document",
    description="""
Upload a property document (PDF or image) for AI-powered fraud detection.

**Pipeline:**
1. SHA-256 hash computed from file bytes
2. AWS Textract extracts key-value fields from the document
3. Rule-based checks (date validation, format checks, name consistency)
4. AWS Bedrock (Claude) performs holistic fraud analysis
5. Final fraud score computed (0.0 = clean, 1.0 = highly suspicious)
6. Result optionally logged on-chain as a `DOCUMENT_VERIFICATION` block

**Verdict thresholds:**
- `AUTHENTIC`  — fraud_score < 0.35
- `SUSPICIOUS` — fraud_score 0.35–0.65
- `FLAGGED`    — fraud_score > 0.65

**Mode:** Automatically uses AWS if `AWS_ACCESS_KEY_ID` is set in `.env`, otherwise falls back to mock simulation.

**mock_scenario** *(ignored in AWS mode)*
- `auto`       — outcome determined by file hash (default)
- `authentic`  — always returns a clean, authentic result
- `suspicious` — always returns a suspicious result
- `flagged`    — always returns a high-fraud flagged result
""",
    responses={
        200: {
            "description": "Verification result",
            "content": {
                "application/json": {
                    "examples": {
                        "authentic": {
                            "summary": "Clean document",
                            "value": {
                                "verdict": "AUTHENTIC",
                                "fraud_score": 0.04,
                                "is_authentic": True,
                                "flags": [],
                                "logged_on_chain": True,
                            },
                        },
                        "flagged": {
                            "summary": "Tampered document",
                            "value": {
                                "verdict": "FLAGGED",
                                "fraud_score": 0.87,
                                "is_authentic": False,
                                "flags": [
                                    "Registration date is in the future (2027)",
                                    "Name mismatch: Owner vs Vendor",
                                ],
                                "logged_on_chain": True,
                            },
                        },
                    }
                }
            },
        },
        400: {"description": "Unsupported file type or file too large"},
        404: {"description": "Property not found on chain (when auto_log_on_chain=true)"},
    },
)
async def verify_property_document(
    file: UploadFile = File(..., description="PDF or image of the property document"),
    property_id: str = Form(..., description="Property ID to associate this document with", example="PROP-KA-2024-001"),
    document_type: DocumentType = Form(..., description="Type of document being uploaded"),
    auto_log_on_chain: bool = Form(
        default=True,
        description="If true, automatically logs the verification result as a blockchain block",
    ),
    mock_scenario: MockScenario = Form(
        default=MockScenario.AUTO,
        description="(Mock mode only) Force a specific outcome for demos. Ignored when using real AWS.",
    ),
):
    # ── Validate file ──────────────────────────────────────────────────────────
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: PDF, JPEG, PNG, TIFF",
        )

    file_bytes = await file.read()

    if len(file_bytes) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({len(file_bytes) / 1024 / 1024:.1f} MB). Max allowed: {MAX_SIZE_MB} MB",
        )

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # ── Run AI verification pipeline ──────────────────────────────────────────
    result = await verify_document(
        file_bytes=file_bytes,
        file_name=file.filename or "unknown",
        document_type=document_type.value,
        mock_scenario=mock_scenario.value,
    )

    # ── Optionally log result on blockchain ───────────────────────────────────
    if auto_log_on_chain:
        on_chain_data = {
            "document_type": result["document_type"],
            "document_hash": result["document_hash"],
            "fraud_score": result["fraud_score"],
            "is_authentic": result["is_authentic"],
            "verdict": result["verdict"],
            "flags": result["flags"],
            "verified_by": result["verified_by"],
        }
        block = await add_transaction(
            property_id=property_id,
            transaction_type=TransactionType.DOCUMENT_VERIFICATION,
            data=on_chain_data,
        )
        result["blockchain_block"] = block
        result["logged_on_chain"] = True
    else:
        result["logged_on_chain"] = False

    return result


@router.get(
    "/mode",
    summary="Check AI verification mode",
    description="Returns whether the service is using real AWS (Textract + Bedrock) or mock simulation.",
    tags=["AI Document Verification"],
)
async def get_ai_mode():
    return {
        "mode": "aws" if USE_AWS else "mock",
        "textract": USE_AWS,
        "bedrock": USE_AWS,
        "model": "anthropic.claude-haiku-4-5-20251001" if USE_AWS else "mock",
        "message": (
            "Using AWS Textract + Bedrock for real document analysis"
            if USE_AWS
            else "Running in mock mode — set AWS_ACCESS_KEY_ID in .env to enable real AI"
        ),
    }
