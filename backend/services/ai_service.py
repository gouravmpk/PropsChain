"""
AI Document Verification Service
---------------------------------
Mode 1 (AWS):  AWS Textract (extract) → AWS Bedrock/Claude (analyze)
Mode 2 (Mock): Deterministic simulation — no AWS credentials needed

The mode is selected automatically:
  - If AWS_ACCESS_KEY_ID is set in .env → AWS mode
  - Otherwise → Mock mode
"""

import hashlib
import json
import os
import time
import random
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

AWS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL = "anthropic.claude-haiku-4-5-20251001"

USE_AWS = bool(AWS_KEY and AWS_SECRET)

if USE_AWS:
    import boto3
    _textract = boto3.client(
        "textract",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_KEY,
        aws_secret_access_key=AWS_SECRET,
    )
    _bedrock = boto3.client(
        "bedrock-runtime",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_KEY,
        aws_secret_access_key=AWS_SECRET,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def _hash_nibble(file_hash: str) -> int:
    """Returns 0-15 from the first hex nibble — used to seed mock randomness."""
    return int(file_hash[0], 16)


# ---------------------------------------------------------------------------
# AWS Textract — real extraction
# ---------------------------------------------------------------------------

def _textract_extract(file_bytes: bytes) -> list[dict]:
    """Call AWS Textract AnalyzeDocument and return key-value pairs."""
    response = _textract.analyze_document(
        Document={"Bytes": file_bytes},
        FeatureTypes=["FORMS"],
    )

    fields = []
    blocks = {b["Id"]: b for b in response["Blocks"]}

    for block in response["Blocks"]:
        if block["BlockType"] == "KEY_VALUE_SET" and "KEY" in block.get("EntityTypes", []):
            key_text = ""
            value_text = ""
            key_conf = block.get("Confidence", 100) / 100

            # Extract key text
            for rel in block.get("Relationships", []):
                if rel["Type"] == "CHILD":
                    for child_id in rel["Ids"]:
                        child = blocks.get(child_id, {})
                        if child.get("BlockType") == "WORD":
                            key_text += child.get("Text", "") + " "

            # Find value block
            for rel in block.get("Relationships", []):
                if rel["Type"] == "VALUE":
                    for val_id in rel["Ids"]:
                        val_block = blocks.get(val_id, {})
                        val_conf = val_block.get("Confidence", 100) / 100
                        for vrel in val_block.get("Relationships", []):
                            if vrel["Type"] == "CHILD":
                                for word_id in vrel["Ids"]:
                                    word = blocks.get(word_id, {})
                                    if word.get("BlockType") == "WORD":
                                        value_text += word.get("Text", "") + " "

            key_text = key_text.strip()
            value_text = value_text.strip()
            if key_text:
                fields.append({
                    "key": key_text,
                    "value": value_text,
                    "confidence": round(key_conf, 3),
                })

    return fields


def _textract_raw_text(file_bytes: bytes) -> str:
    """Get plain text from document for Bedrock analysis."""
    response = _textract.detect_document_text(Document={"Bytes": file_bytes})
    words = [b["Text"] for b in response["Blocks"] if b["BlockType"] == "LINE"]
    return "\n".join(words)


# ---------------------------------------------------------------------------
# AWS Bedrock — real AI fraud analysis
# ---------------------------------------------------------------------------

def _bedrock_analyze(extracted_fields: list[dict], raw_text: str, document_type: str) -> dict:
    """Send extracted content to Claude via Bedrock for fraud analysis."""
    fields_summary = "\n".join(f"  - {f['key']}: {f['value']} (confidence: {f['confidence']*100:.0f}%)" for f in extracted_fields)

    prompt = f"""You are an expert in Indian property document fraud detection.

Analyze the following document and identify any fraud indicators.

Document Type: {document_type}

Extracted Key-Value Fields:
{fields_summary}

Raw Document Text (first 1000 chars):
{raw_text[:1000]}

Check for:
1. Inconsistent dates (future dates, impossible dates, mismatched dates)
2. Name mismatches between different parts of the document
3. Suspicious or incorrectly formatted registration numbers
4. Signs of digital editing or tampering in field values
5. Missing critical fields for a {document_type}
6. Amounts that seem inconsistent with property values
7. Any other anomalies specific to Indian property documents

Respond ONLY with valid JSON in this exact format:
{{
  "fraud_indicators": ["list of specific red flags found, empty if none"],
  "suspicious_fields": {{"field_name": "reason for suspicion"}},
  "overall_assessment": "AUTHENTIC",
  "fraud_score": 0.05,
  "confidence": 0.92,
  "explanation": "One sentence summary of your assessment"
}}

overall_assessment must be one of: AUTHENTIC, SUSPICIOUS, FLAGGED
fraud_score must be 0.0 (clean) to 1.0 (highly suspicious)"""

    response = _bedrock.invoke_model(
        modelId=BEDROCK_MODEL,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }),
    )
    body = json.loads(response["body"].read())
    content = body["content"][0]["text"]

    # Parse JSON from Claude's response
    json_match = content[content.find("{"):content.rfind("}") + 1]
    return json.loads(json_match)


# ---------------------------------------------------------------------------
# Mock extraction — realistic simulation per document type
# ---------------------------------------------------------------------------

_MOCK_FIELDS: dict[str, list[dict]] = {
    "Title Deed": [
        {"key": "Document Title",         "value": "Sale Deed",                      "confidence": 0.99},
        {"key": "Owner Name",             "value": "Ravi Kumar",                     "confidence": 0.97},
        {"key": "Survey Number",          "value": "123/4A",                         "confidence": 0.95},
        {"key": "Property Address",       "value": "123 MG Road, Bengaluru 560001",  "confidence": 0.96},
        {"key": "Area (sq ft)",           "value": "1200",                           "confidence": 0.98},
        {"key": "Registration Number",    "value": "REG-BLR-2024-9876",             "confidence": 0.94},
        {"key": "Registration Date",      "value": "15/01/2024",                     "confidence": 0.97},
        {"key": "Consideration Amount",   "value": "₹50,00,000",                    "confidence": 0.96},
        {"key": "Sub-Registrar Office",   "value": "SRO Bengaluru South",            "confidence": 0.93},
        {"key": "Stamp Duty Paid",        "value": "₹3,50,000",                     "confidence": 0.95},
    ],
    "Sale Agreement": [
        {"key": "Agreement Date",         "value": "10/02/2024",                     "confidence": 0.97},
        {"key": "Vendor Name",            "value": "Ravi Kumar",                     "confidence": 0.98},
        {"key": "Vendee Name",            "value": "Priya Sharma",                   "confidence": 0.96},
        {"key": "Property Description",   "value": "Residential flat, 2BHK",         "confidence": 0.92},
        {"key": "Sale Consideration",     "value": "₹55,00,000",                    "confidence": 0.95},
        {"key": "Advance Amount",         "value": "₹5,00,000",                     "confidence": 0.94},
        {"key": "Possession Date",        "value": "01/04/2024",                     "confidence": 0.91},
        {"key": "Witness 1",              "value": "Suresh Patil",                   "confidence": 0.89},
    ],
    "Aadhaar Card": [
        {"key": "Full Name",              "value": "Ravi Kumar",                     "confidence": 0.99},
        {"key": "Date of Birth",          "value": "15/08/1985",                     "confidence": 0.98},
        {"key": "Gender",                 "value": "Male",                           "confidence": 0.99},
        {"key": "Address",                "value": "123 MG Road, Bengaluru 560001",  "confidence": 0.95},
        {"key": "Aadhaar Number",         "value": "XXXX XXXX 7890",                "confidence": 0.99},
        {"key": "Issue Date",             "value": "20/03/2015",                     "confidence": 0.96},
    ],
    "Encumbrance Certificate": [
        {"key": "Owner Name",             "value": "Ravi Kumar",                     "confidence": 0.97},
        {"key": "Survey Number",          "value": "123/4A",                         "confidence": 0.95},
        {"key": "Period From",            "value": "01/01/2000",                     "confidence": 0.94},
        {"key": "Period To",              "value": "28/02/2024",                     "confidence": 0.96},
        {"key": "Encumbrances",           "value": "NIL",                            "confidence": 0.98},
        {"key": "Issued By",              "value": "Sub-Registrar Office, Bengaluru","confidence": 0.93},
        {"key": "Certificate Number",     "value": "EC-BLR-2024-001234",            "confidence": 0.92},
    ],
    "Property Tax Receipt": [
        {"key": "Property ID",            "value": "BBMP-BLR-2024-56789",           "confidence": 0.97},
        {"key": "Owner Name",             "value": "Ravi Kumar",                     "confidence": 0.96},
        {"key": "Tax Year",               "value": "2023-24",                        "confidence": 0.99},
        {"key": "Amount Paid",            "value": "₹12,500",                       "confidence": 0.98},
        {"key": "Payment Date",           "value": "10/04/2023",                     "confidence": 0.97},
        {"key": "Receipt Number",         "value": "BBMP-RCP-2023-78901",           "confidence": 0.95},
    ],
}

_MOCK_FIELDS_SUSPICIOUS: dict[str, list[dict]] = {
    "Title Deed": [
        {"key": "Document Title",         "value": "Sale Deed",                      "confidence": 0.71},
        {"key": "Owner Name",             "value": "R. Kumar",                       "confidence": 0.61},  # different format
        {"key": "Survey Number",          "value": "123/4A",                         "confidence": 0.55},
        {"key": "Property Address",       "value": "123 MG Road, Bengaluru",         "confidence": 0.58},
        {"key": "Area (sq ft)",           "value": "1200",                           "confidence": 0.72},
        {"key": "Registration Number",    "value": "BLR2024FAKE",                   "confidence": 0.63},  # bad format
        {"key": "Registration Date",      "value": "15/01/2027",                     "confidence": 0.69},  # future date!
        {"key": "Consideration Amount",   "value": "50 Lakhs approx",               "confidence": 0.54},  # non-numeric
        {"key": "Vendor Name",            "value": "Rajeev Singh",                   "confidence": 0.62},  # name mismatch!
        {"key": "Stamp Duty Paid",        "value": "Not Applicable",                 "confidence": 0.51},
    ],
    "Aadhaar Card": [
        {"key": "Full Name",              "value": "Ravi Kumar",                     "confidence": 0.58},
        {"key": "Date of Birth",          "value": "15/08/2030",                     "confidence": 0.61},  # future DOB!
        {"key": "Gender",                 "value": "Male",                           "confidence": 0.99},
        {"key": "Address",               "value": "Unknown",                         "confidence": 0.42},
        {"key": "Aadhaar Number",         "value": "1234 5678",                      "confidence": 0.55},  # only 8 digits!
    ],
}


def _mock_extract(document_type: str, is_suspicious: bool) -> list[dict]:
    base = _MOCK_FIELDS_SUSPICIOUS if is_suspicious else _MOCK_FIELDS
    default = _MOCK_FIELDS["Title Deed"]
    fields = base.get(document_type, _MOCK_FIELDS.get(document_type, default))
    return [dict(f) for f in fields]


def _mock_raw_text(fields: list[dict]) -> str:
    lines = [f"{f['key']}: {f['value']}" for f in fields]
    return "\n".join(lines)


def _mock_bedrock_result(is_suspicious: bool, document_type: str) -> dict:
    if is_suspicious:
        return {
            "fraud_indicators": [
                "Registration date is in the future (2027)",
                "Name mismatch: Owner 'R. Kumar' vs Vendor 'Rajeev Singh'",
                "Registration number 'BLR2024FAKE' does not match expected format",
                "Consideration amount 'approx' is not a valid numeric value",
                "Multiple low-confidence extractions suggest possible image manipulation",
            ],
            "suspicious_fields": {
                "Registration Date": "Date 15/01/2027 is in the future",
                "Vendor Name": "Does not match Owner Name",
                "Registration Number": "Invalid format for Indian property registration",
                "Consideration Amount": "Non-numeric value",
            },
            "overall_assessment": "FLAGGED",
            "fraud_score": 0.87,
            "confidence": 0.91,
            "explanation": f"This {document_type} shows multiple high-risk fraud indicators including future dates, name mismatches, and invalid registration number format.",
        }
    else:
        return {
            "fraud_indicators": [],
            "suspicious_fields": {},
            "overall_assessment": "AUTHENTIC",
            "fraud_score": 0.04,
            "confidence": 0.96,
            "explanation": f"This {document_type} appears authentic with all fields consistent, dates valid, and registration number in correct format.",
        }


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

async def verify_document(
    file_bytes: bytes,
    file_name: str,
    document_type: str,
    mock_scenario: str = "auto",   # auto | authentic | suspicious | flagged
) -> dict:
    """
    Full document verification pipeline.
    Returns a dict matching DocumentVerifyResponse fields.
    """
    start = time.time()

    doc_hash = compute_file_hash(file_bytes)
    file_size_kb = round(len(file_bytes) / 1024, 2)

    # Resolve mock outcome
    # explicit scenario overrides hash-based auto detection
    if mock_scenario == "authentic":
        is_suspicious_mock = False
    elif mock_scenario in ("suspicious", "flagged"):
        is_suspicious_mock = True
    else:
        # auto: deterministic from file hash (first nibble 0-7 = clean, 8-f = suspicious)
        is_suspicious_mock = _hash_nibble(doc_hash) >= 8

    mode = "aws" if USE_AWS else "mock"

    # ── Extraction ────────────────────────────────────────────────────────────
    if USE_AWS:
        extracted_fields = _textract_extract(file_bytes)
        raw_text = _textract_raw_text(file_bytes)
    else:
        extracted_fields = _mock_extract(document_type, is_suspicious_mock)
        raw_text = _mock_raw_text(extracted_fields)

    # ── Rule-based checks ─────────────────────────────────────────────────────
    from services.fraud_rules import run_all_rules
    rule_results, rule_flags = run_all_rules(extracted_fields, document_type)

    # ── AI analysis ───────────────────────────────────────────────────────────
    if USE_AWS:
        ai_result = _bedrock_analyze(extracted_fields, raw_text, document_type)
    else:
        ai_result = _mock_bedrock_result(is_suspicious_mock, document_type)

    # ── Score aggregation ─────────────────────────────────────────────────────
    ai_score: float = ai_result.get("fraud_score", 0.0)
    rule_penalty = len(rule_flags) * 0.08          # each failed rule adds 8%
    final_score = min(round(ai_score + rule_penalty, 3), 1.0)

    # ── Verdict ───────────────────────────────────────────────────────────────
    if final_score < 0.35:
        verdict = "AUTHENTIC"
        is_authentic = True
    elif final_score < 0.65:
        verdict = "SUSPICIOUS"
        is_authentic = False
    else:
        verdict = "FLAGGED"
        is_authentic = False

    # ── Combine flags ─────────────────────────────────────────────────────────
    ai_flags = ai_result.get("fraud_indicators", [])
    all_flags = list(dict.fromkeys(rule_flags + ai_flags))  # deduplicate, preserve order

    # ── Extraction confidence ─────────────────────────────────────────────────
    confidences = [f["confidence"] for f in extracted_fields]
    avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 1.0

    elapsed_ms = int((time.time() - start) * 1000)

    return {
        "document_hash": doc_hash,
        "document_type": document_type,
        "file_name": file_name,
        "file_size_kb": file_size_kb,
        "extracted_fields": extracted_fields,
        "raw_text_preview": raw_text[:500],
        "extraction_confidence": avg_confidence,
        "fraud_score": final_score,
        "verdict": verdict,
        "is_authentic": is_authentic,
        "flags": all_flags,
        "rule_checks": [r.model_dump() for r in rule_results],
        "ai_explanation": ai_result.get("explanation", ""),
        "verified_by": "PropChain-AWS-Textract+Bedrock" if USE_AWS else "PropChain-AI-Mock",
        "mode": mode,
        "processing_time_ms": elapsed_ms,
    }
