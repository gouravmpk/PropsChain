"""
AI Document Verification Service
---------------------------------
Mode 1 (AWS):  Claude via Bedrock directly reads the document (vision) + extracts + analyzes
Mode 2 (Mock): Deterministic simulation — no credentials needed

Credential resolution order:
  1. .env / environment variables (AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY)
  2. AWS Secrets Manager — secret name: "keys", region: ap-south-1
     Secret format: {"AWS_ACCESS_KEY_ID": "...", "AWS_SECRET_ACCESS_KEY": "..."}
  3. Mock mode — no credentials
"""

import base64
import hashlib
import json
import os
import time

from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "ap-south-1")
BEDROCK_MODEL = os.getenv("BEDROCK_MODEL", "apac.anthropic.claude-sonnet-4-20250514-v1:0")
SECRETS_MANAGER_REGION = "ap-south-1"
SECRET_NAME = "keys"


def _load_credentials_from_secrets_manager() -> tuple[str, str] | tuple[None, None]:
    """Fetch AWS credentials from Secrets Manager. Returns (key, secret) or (None, None)."""
    try:
        import boto3
        client = boto3.session.Session().client(
            service_name="secretsmanager",
            region_name=SECRETS_MANAGER_REGION,
        )
        response = client.get_secret_value(SecretId=SECRET_NAME)
        secret = json.loads(response["SecretString"])
        key = secret.get("AWS_ACCESS_KEY_ID") or secret.get("access_key") or secret.get("AccessKeyId")
        sec = secret.get("AWS_SECRET_ACCESS_KEY") or secret.get("secret_key") or secret.get("SecretAccessKey")
        if key and sec:
            return key, sec
    except Exception:
        pass
    return None, None


# Resolve credentials: env vars → Secrets Manager → mock
AWS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET = os.getenv("AWS_SECRET_ACCESS_KEY")

if not (AWS_KEY and AWS_SECRET):
    AWS_KEY, AWS_SECRET = _load_credentials_from_secrets_manager()

USE_AWS = bool(AWS_KEY and AWS_SECRET)

if USE_AWS:
    import boto3
    from botocore.config import Config as _BotoConfig
    _bedrock = boto3.client(
        "bedrock-runtime",
        region_name=BEDROCK_REGION,
        aws_access_key_id=AWS_KEY,
        aws_secret_access_key=AWS_SECRET,
        config=_BotoConfig(connect_timeout=5, read_timeout=30, retries={"max_attempts": 1}),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def _hash_nibble(file_hash: str) -> int:
    """Returns 0-15 from the first hex nibble — used to seed mock randomness."""
    return int(file_hash[0], 16)


def _media_type(file_name: str) -> str:
    ext = file_name.lower().rsplit(".", 1)[-1]
    return {
        "pdf":  "application/pdf",
        "png":  "image/png",
        "jpg":  "image/jpeg",
        "jpeg": "image/jpeg",
        "tiff": "image/tiff",
        "tif":  "image/tiff",
    }.get(ext, "image/jpeg")


# ---------------------------------------------------------------------------
# Bedrock — single-call extract + analyze via Claude vision
# ---------------------------------------------------------------------------

def _is_nova_model(model_id: str) -> bool:
    return "amazon.nova" in model_id or "nova" in model_id.lower()


def _bedrock_analyze(file_bytes: bytes, file_name: str, document_type: str) -> dict:
    """Send document to Bedrock (Nova or Claude). Extracts fields and analyzes fraud."""
    media = _media_type(file_name)
    b64 = base64.standard_b64encode(file_bytes).decode("utf-8")  # used by Claude path

    prompt = f"""You are an expert in Indian property document fraud detection.

You are given a {document_type}. Your job is to:
1. Extract all key-value fields visible in the document
2. Analyze the document for fraud indicators

Check for:
- Inconsistent or future dates
- Name mismatches between different parts of the document
- Suspicious or incorrectly formatted registration numbers
- Signs of digital editing or tampering
- Missing critical fields for a {document_type}
- Amounts that seem inconsistent with property values
- Any other anomalies specific to Indian property documents

Respond ONLY with valid JSON in this exact format:
{{
  "extracted_fields": [
    {{"key": "field name", "value": "field value", "confidence": 0.95}}
  ],
  "fraud_indicators": ["list of specific red flags found, empty if none"],
  "suspicious_fields": {{"field_name": "reason for suspicion"}},
  "overall_assessment": "AUTHENTIC",
  "fraud_score": 0.05,
  "confidence": 0.92,
  "explanation": "One sentence summary of your assessment"
}}

overall_assessment must be one of: AUTHENTIC, SUSPICIOUS, FLAGGED
fraud_score must be 0.0 (clean) to 1.0 (highly suspicious)
confidence is your confidence in the assessment (0.0 to 1.0)"""

    if _is_nova_model(BEDROCK_MODEL):
        import fitz  # PyMuPDF
        import io as _io
        from PIL import Image as _Image

        NOVA_MAX_IMAGES = 20  # Nova converse API limit

        def _jpeg_content(img_bytes: bytes) -> dict:
            return {"image": {"format": "jpeg", "source": {"bytes": img_bytes}}}

        def _pil_to_jpeg(img: "_Image.Image") -> bytes:
            buf = _io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=85)
            return buf.getvalue()

        def _pdf_to_images(raw: bytes) -> list[bytes]:
            doc = fitz.open(stream=raw, filetype="pdf")
            pages = []
            for page in doc:
                pix = page.get_pixmap(dpi=150)
                img = _Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                pages.append(_pil_to_jpeg(img))
            doc.close()
            return pages

        def _tiff_to_images(raw: bytes) -> list[bytes]:
            img = _Image.open(_io.BytesIO(raw))
            frames = []
            try:
                while True:
                    frames.append(_pil_to_jpeg(img.copy()))
                    img.seek(img.tell() + 1)
            except EOFError:
                pass
            return frames if frames else [_pil_to_jpeg(img)]

        def _stitch_pages(page_jpegs: list[bytes]) -> list[bytes]:
            """If pages exceed Nova limit, stitch pairs vertically to reduce image count."""
            while len(page_jpegs) > NOVA_MAX_IMAGES:
                stitched = []
                for i in range(0, len(page_jpegs), 2):
                    if i + 1 < len(page_jpegs):
                        a = _Image.open(_io.BytesIO(page_jpegs[i]))
                        b = _Image.open(_io.BytesIO(page_jpegs[i + 1]))
                        w = max(a.width, b.width)
                        combined = _Image.new("RGB", (w, a.height + b.height), (255, 255, 255))
                        combined.paste(a, (0, 0))
                        combined.paste(b, (0, a.height))
                        stitched.append(_pil_to_jpeg(combined))
                    else:
                        stitched.append(page_jpegs[i])
                page_jpegs = stitched
            return page_jpegs

        img_format = media.split("/")[-1]

        if img_format == "pdf":
            page_jpegs = _pdf_to_images(file_bytes)
        elif img_format in ("tiff", "tif"):
            page_jpegs = _tiff_to_images(file_bytes)
        else:
            # Single image (jpeg/png) — just re-encode as JPEG for consistency
            page_jpegs = [_pil_to_jpeg(_Image.open(_io.BytesIO(file_bytes)))]

        page_jpegs = _stitch_pages(page_jpegs)
        images_content = [_jpeg_content(j) for j in page_jpegs]

        response = _bedrock.converse(
            modelId=BEDROCK_MODEL,
            messages=[{
                "role": "user",
                "content": images_content + [{"text": prompt}],
            }],
            inferenceConfig={"maxTokens": 2048},
        )
        content = response["output"]["message"]["content"][0]["text"]
    else:
        # Anthropic Claude message format
        body_payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media, "data": b64},
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        }
        response = _bedrock.invoke_model(modelId=BEDROCK_MODEL, body=json.dumps(body_payload))
        body = json.loads(response["body"].read())
        content = body["content"][0]["text"]

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
        {"key": "Owner Name",             "value": "R. Kumar",                       "confidence": 0.61},
        {"key": "Survey Number",          "value": "123/4A",                         "confidence": 0.55},
        {"key": "Property Address",       "value": "123 MG Road, Bengaluru",         "confidence": 0.58},
        {"key": "Area (sq ft)",           "value": "1200",                           "confidence": 0.72},
        {"key": "Registration Number",    "value": "BLR2024FAKE",                   "confidence": 0.63},
        {"key": "Registration Date",      "value": "15/01/2027",                     "confidence": 0.69},
        {"key": "Consideration Amount",   "value": "50 Lakhs approx",               "confidence": 0.54},
        {"key": "Vendor Name",            "value": "Rajeev Singh",                   "confidence": 0.62},
        {"key": "Stamp Duty Paid",        "value": "Not Applicable",                 "confidence": 0.51},
    ],
    "Aadhaar Card": [
        {"key": "Full Name",              "value": "Ravi Kumar",                     "confidence": 0.58},
        {"key": "Date of Birth",          "value": "15/08/2030",                     "confidence": 0.61},
        {"key": "Gender",                 "value": "Male",                           "confidence": 0.99},
        {"key": "Address",                "value": "Unknown",                        "confidence": 0.42},
        {"key": "Aadhaar Number",         "value": "1234 5678",                      "confidence": 0.55},
    ],
}


def _mock_extract(document_type: str, is_suspicious: bool) -> list[dict]:
    base = _MOCK_FIELDS_SUSPICIOUS if is_suspicious else _MOCK_FIELDS
    default = _MOCK_FIELDS["Title Deed"]
    fields = base.get(document_type, _MOCK_FIELDS.get(document_type, default))
    return [dict(f) for f in fields]


def _mock_bedrock_result(is_suspicious: bool, document_type: str, fields: list[dict]) -> dict:
    if is_suspicious:
        return {
            "extracted_fields": fields,
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
            "extracted_fields": fields,
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

    # Resolve mock outcome (only used in mock mode)
    if mock_scenario == "authentic":
        is_suspicious_mock = False
    elif mock_scenario in ("suspicious", "flagged"):
        is_suspicious_mock = True
    else:
        is_suspicious_mock = _hash_nibble(doc_hash) >= 8

    mode = "aws" if USE_AWS else "mock"

    # ── Extract + Analyze ─────────────────────────────────────────────────────
    if USE_AWS:
        try:
            ai_result = _bedrock_analyze(file_bytes, file_name, document_type)
            extracted_fields = ai_result.get("extracted_fields", [])
            mode = "aws"
        except Exception as bedrock_err:
            import logging
            logging.error(f"Bedrock call failed: {bedrock_err}")
            raise
    # else:
    #     extracted_fields = _mock_extract(document_type, is_suspicious_mock)
    #     ai_result = _mock_bedrock_result(is_suspicious_mock, document_type, extracted_fields)

    raw_text = "\n".join(f"{f['key']}: {f['value']}" for f in extracted_fields)

    # ── Rule-based checks ─────────────────────────────────────────────────────
    from services.fraud_rules import run_all_rules
    rule_results, rule_flags = run_all_rules(extracted_fields, document_type)

    # ── Score aggregation ─────────────────────────────────────────────────────
    ai_score: float = ai_result.get("fraud_score", 0.0)
    rule_penalty = len(rule_flags) * 0.08
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
    all_flags = list(dict.fromkeys(rule_flags + ai_flags))

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
        "verified_by": "PropChain-Claude-Bedrock" if mode == "aws" else "PropChain-AI-Mock",
        "mode": mode,
        "processing_time_ms": elapsed_ms,
    }
