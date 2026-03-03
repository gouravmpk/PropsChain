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
import logging
import os
import time

from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-east-1")
BEDROCK_MODEL = os.getenv("BEDROCK_MODEL", "us.amazon.nova-lite-v1:0")
BEDROCK_FALLBACK_MODEL = os.getenv("BEDROCK_FALLBACK_MODEL", "us.amazon.nova-pro-v1:0")  # tier-2: used when nova-lite is throttled
BEDROCK_CACHE_TABLE = os.getenv("BEDROCK_CACHE_TABLE", "propchain-ai-cache")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
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
    from botocore.exceptions import ClientError as _ClientError
    _bedrock = boto3.client(
        "bedrock-runtime",
        region_name=BEDROCK_REGION,
        aws_access_key_id=AWS_KEY,
        aws_secret_access_key=AWS_SECRET,
        # read_timeout=60: Nova Pro on large PDFs can take ~30 s; tenacity handles retries
        config=_BotoConfig(connect_timeout=5, read_timeout=60, retries={"max_attempts": 1}),
    )
    # DynamoDB response cache — hash(file_bytes) → Bedrock result, 7-day TTL
    # Zero model cost on repeated document uploads (seen & praised by hackathon judges)
    _ddb = boto3.resource(
        "dynamodb",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_KEY,
        aws_secret_access_key=AWS_SECRET,
    )
    _cache_table = _ddb.Table(BEDROCK_CACHE_TABLE)
else:
    class _ClientError(Exception):  # type: ignore[no-redef]
        pass
    _cache_table = None


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
# DynamoDB cache helpers
# ---------------------------------------------------------------------------

def _cache_get(file_hash: str) -> dict | None:
    """Return cached Bedrock result for file_hash, or None on miss."""
    if _cache_table is None:
        return None
    try:
        resp = _cache_table.get_item(Key={"file_hash": file_hash})
        item = resp.get("Item")
        if item:
            logging.info(f"[cache] HIT for {file_hash[:12]}...")
            return json.loads(item["result"])
    except Exception as e:
        logging.warning(f"[cache] get failed: {e}")
    return None


def _cache_put(file_hash: str, result: dict) -> None:
    """Store Bedrock result in DynamoDB with 7-day TTL."""
    if _cache_table is None:
        return
    try:
        _cache_table.put_item(Item={
            "file_hash": file_hash,
            "result": json.dumps(result),
            "ttl": int(time.time()) + 86400 * 7,
        })
        logging.info(f"[cache] PUT {file_hash[:12]}...")
    except Exception as e:
        logging.warning(f"[cache] put failed: {e}")


# ---------------------------------------------------------------------------
# Bedrock — single-call extract + analyze via Claude vision
# ---------------------------------------------------------------------------

def _is_nova_model(model_id: str) -> bool:
    return "amazon.nova" in model_id or "nova" in model_id.lower()


@retry(
    retry=retry_if_exception_type(_ClientError),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
def _bedrock_analyze(file_bytes: bytes, file_name: str, document_type: str, model_id: str | None = None) -> dict:
    """Send document to Bedrock (Nova or Claude) with exponential-backoff retry.
    Retries up to 4× on ThrottlingException with 2–30 s wait between attempts.
    Accepts an optional model_id override; defaults to BEDROCK_MODEL.
    """
    _model = model_id or BEDROCK_MODEL
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

    if _is_nova_model(_model):
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
            modelId=_model,
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
        response = _bedrock.invoke_model(modelId=_model, body=json.dumps(body_payload))
        body = json.loads(response["body"].read())
        content = body["content"][0]["text"]

    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON object found in Bedrock response. Raw: {content[:200]}")
    return json.loads(content[start:end + 1])


# ---------------------------------------------------------------------------
# OpenAI fallback — activates when Bedrock is throttled / unavailable
# ---------------------------------------------------------------------------

def _openai_fallback_analyze(file_bytes: bytes, file_name: str, document_type: str) -> dict:
    """Use OpenAI GPT-4o-mini vision when Bedrock is unavailable.
    Returns the same JSON schema as _bedrock_analyze so callers are transparent.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set — OpenAI fallback unavailable")

    import io as _io
    import openai
    from PIL import Image as _PIL

    # Convert first page / image to JPEG for the OpenAI vision API
    media = _media_type(file_name).split("/")[-1]
    if media == "pdf":
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pix = doc[0].get_pixmap(dpi=150)
        img = _PIL.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
    else:
        img = _PIL.open(_io.BytesIO(file_bytes)).convert("RGB")

    buf = _io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    b64_img = base64.standard_b64encode(buf.getvalue()).decode()

    prompt = f"""You are an expert in Indian property document fraud detection.
You are given a {document_type}. Extract all key fields and analyze for fraud.
Respond ONLY with valid JSON:
{{
  "extracted_fields": [{{"key": "...", "value": "...", "confidence": 0.95}}],
  "fraud_indicators": [],
  "suspicious_fields": {{}},
  "overall_assessment": "AUTHENTIC",
  "fraud_score": 0.05,
  "confidence": 0.90,
  "explanation": "One sentence summary"
}}
overall_assessment must be: AUTHENTIC | SUSPICIOUS | FLAGGED"""

    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
            {"type": "text", "text": prompt},
        ]}],
        max_tokens=2048,
    )
    content = response.choices[0].message.content
    s = content.find("{")
    e = content.rfind("}")
    if s == -1 or e == -1:
        raise ValueError(f"No JSON in OpenAI response: {content[:200]}")
    return json.loads(content[s:e + 1])


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

    # ── Extract + Analyze  (cache → Bedrock → OpenAI fallback → mock) ────────
    if USE_AWS:
        cached = _cache_get(doc_hash)
        if cached:
            ai_result = cached
            extracted_fields = ai_result.get("extracted_fields", [])
            mode = "aws-cached"
        else:
            try:
                ai_result = _bedrock_analyze(file_bytes, file_name, document_type)
                _cache_put(doc_hash, ai_result)
                extracted_fields = ai_result.get("extracted_fields", [])
                mode = "aws"
            except Exception as lite_err:
                logging.warning(f"Nova Lite failed (after retries): {lite_err}. Trying Nova Pro fallback.")
                try:
                    ai_result = _bedrock_analyze(file_bytes, file_name, document_type, model_id=BEDROCK_FALLBACK_MODEL)
                    _cache_put(doc_hash, ai_result)
                    extracted_fields = ai_result.get("extracted_fields", [])
                    mode = "aws-pro-fallback"
                except Exception as pro_err:
                    logging.error(f"Nova Pro also failed: {pro_err}. Trying OpenAI fallback.")
                    try:
                        ai_result = _openai_fallback_analyze(file_bytes, file_name, document_type)
                        extracted_fields = ai_result.get("extracted_fields", [])
                        mode = "openai-fallback"
                    except Exception as oai_err:
                        logging.error(f"OpenAI fallback also failed: {oai_err}. Falling back to mock.")
                        extracted_fields = _mock_extract(document_type, is_suspicious_mock)
                        ai_result = _mock_bedrock_result(is_suspicious_mock, document_type, extracted_fields)
                        mode = "mock-fallback"
    else:
        extracted_fields = _mock_extract(document_type, is_suspicious_mock)
        ai_result = _mock_bedrock_result(is_suspicious_mock, document_type, extracted_fields)

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
        "verified_by": (
            f"Amazon Nova Lite ({BEDROCK_MODEL}) · AWS Bedrock · {BEDROCK_REGION} [cached]" if mode == "aws-cached"
            else f"Amazon Nova Lite ({BEDROCK_MODEL}) · AWS Bedrock · {BEDROCK_REGION}" if mode == "aws"
            else f"Amazon Nova Pro ({BEDROCK_FALLBACK_MODEL}) · AWS Bedrock · {BEDROCK_REGION} [lite-fallback]" if mode == "aws-pro-fallback"
            else f"OpenAI GPT-4o-mini (Bedrock fallback)" if mode == "openai-fallback"
            else "PropChain-AI-Mock (degraded fallback)" if mode == "mock-fallback"
            else "PropChain-AI-Mock (no AWS credentials)"
        ),
        "mode": mode,
        "processing_time_ms": elapsed_ms,
    }


# ---------------------------------------------------------------------------
# Cross-document consistency check
# ---------------------------------------------------------------------------

def _cross_doc_analyze(docs: list[dict]) -> dict:
    """
    Send multiple documents to Bedrock (Nova) in a single converse() call.
    Each doc dict: {"file_bytes": bytes, "file_name": str, "document_type": str}
    Returns structured cross-check JSON.
    """
    import fitz  # PyMuPDF
    import io as _io
    from PIL import Image as _Image

    NOVA_MAX_IMAGES = 20

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

    def _file_to_images(file_bytes: bytes, file_name: str) -> list[bytes]:
        media = _media_type(file_name)
        fmt = media.split("/")[-1]
        if fmt == "pdf":
            return _pdf_to_images(file_bytes)
        else:
            img = _Image.open(_io.BytesIO(file_bytes))
            return [_pil_to_jpeg(img)]

    def _stitch(pages: list[bytes]) -> list[bytes]:
        while len(pages) > NOVA_MAX_IMAGES:
            stitched = []
            for i in range(0, len(pages), 2):
                if i + 1 < len(pages):
                    a = _Image.open(_io.BytesIO(pages[i]))
                    b = _Image.open(_io.BytesIO(pages[i + 1]))
                    w = max(a.width, b.width)
                    combined = _Image.new("RGB", (w, a.height + b.height), (255, 255, 255))
                    combined.paste(a, (0, 0))
                    combined.paste(b, (0, a.height))
                    stitched.append(_pil_to_jpeg(combined))
                else:
                    stitched.append(pages[i])
            pages = stitched
        return pages

    # Build doc list header for the prompt
    doc_labels = "\n".join(
        f"- Document {i+1}: {d['document_type']} (file: {d['file_name']})"
        for i, d in enumerate(docs)
    )

    prompt = f"""You are an expert Indian property document fraud analyst.

You have been given {len(docs)} property documents:
{doc_labels}

The documents are provided as images in order above — each group of images belongs to one document in sequence.

Your task:
1. For EACH document, extract all key fields visible (owner name, survey/plot number, registration date, consideration amount, address, Aadhaar/PAN number, parties involved).
2. Cross-check the following fields ACROSS all documents:
   - Owner / party names (must be consistent across all docs)
   - Survey / plot / property numbers (must match)
   - Property address / locality
   - Dates (registration before transfer, possession dates logical)
   - Financial amounts (sale consideration must match between sale deed and agreement)
3. List EVERY inconsistency found with severity: HIGH (clear fraud signal), MEDIUM (suspicious), LOW (minor variation).
4. Give an overall verdict: CONSISTENT (no issues), INCONSISTENT (clear mismatches), or SUSPICIOUS (possible issues).
5. Give a consistency_score from 0 (totally inconsistent) to 100 (fully consistent).

Respond ONLY with valid JSON in this exact format:
{{
  "per_doc": [
    {{
      "document": "Title Deed",
      "extracted": [
        {{"key": "Owner Name", "value": "Ravi Kumar", "confidence": 0.97}}
      ]
    }}
  ],
  "inconsistencies": [
    {{
      "field": "Owner Name",
      "documents": ["Title Deed", "Aadhaar Card"],
      "values": {{"Title Deed": "Ravi Kumar", "Aadhaar Card": "R. Kumar"}},
      "description": "Owner name abbreviated differently — possible mismatch",
      "severity": "MEDIUM"
    }}
  ],
  "overall_verdict": "INCONSISTENT",
  "consistency_score": 62,
  "summary": "One sentence assessment of the document set."
}}"""

    # Assemble content: all doc images interleaved with labels, then prompt
    # Budget: NOVA_MAX_IMAGES total images across ALL docs
    all_images: list[bytes] = []
    per_doc_counts: list[int] = []
    for d in docs:
        pages = _stitch(_file_to_images(d["file_bytes"], d["file_name"]))
        all_images.extend(pages)
        per_doc_counts.append(len(pages))

    # If total images still exceeds limit, stitch across all
    all_images = _stitch(all_images)

    content: list[dict] = []
    img_idx = 0
    for i, d in enumerate(docs):
        content.append({"text": f"=== Document {i+1}: {d['document_type']} ==="})
        count = per_doc_counts[i] if img_idx + per_doc_counts[i] <= len(all_images) else len(all_images) - img_idx
        for _ in range(count):
            if img_idx < len(all_images):
                content.append({"image": {"format": "jpeg", "source": {"bytes": all_images[img_idx]}}})
                img_idx += 1
    content.append({"text": prompt})

    response = _bedrock.converse(
        modelId=BEDROCK_MODEL,
        messages=[{"role": "user", "content": content}],
        inferenceConfig={"maxTokens": 4096},
    )
    raw = response["output"]["message"]["content"][0]["text"]
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON object found in cross-verify response. Raw: {raw[:200]}")
    return json.loads(raw[start:end + 1])


def _mock_cross_verify(docs: list[dict]) -> dict:
    """Deterministic mock result for cross-document verification."""
    n = len(docs)
    # Mix of consistent and inconsistent based on doc count parity
    if n >= 3:
        return {
            "per_doc": [
                {
                    "document": d["document_type"],
                    "extracted": [
                        {"key": "Owner Name", "value": "Ravi Kumar" if i == 0 else "R. Kumar", "confidence": 0.96},
                        {"key": "Survey Number", "value": "123/4A", "confidence": 0.94},
                        {"key": "Registration Date", "value": "15/01/2024" if i < 2 else "20/03/2024", "confidence": 0.97},
                    ],
                }
                for i, d in enumerate(docs)
            ],
            "inconsistencies": [
                {
                    "field": "Owner Name",
                    "documents": [docs[0]["document_type"], docs[1]["document_type"]],
                    "values": {docs[0]["document_type"]: "Ravi Kumar", docs[1]["document_type"]: "R. Kumar"},
                    "description": "Owner name is abbreviated in the second document — possible mismatch or clerical error",
                    "severity": "MEDIUM",
                },
            ],
            "overall_verdict": "SUSPICIOUS",
            "consistency_score": 71,
            "summary": f"Cross-check of {n} documents shows a name inconsistency that warrants manual review.",
        }
    else:
        return {
            "per_doc": [
                {
                    "document": d["document_type"],
                    "extracted": [
                        {"key": "Owner Name", "value": "Ravi Kumar", "confidence": 0.97},
                        {"key": "Survey Number", "value": "123/4A", "confidence": 0.95},
                        {"key": "Registration Date", "value": "15/01/2024", "confidence": 0.98},
                    ],
                }
                for d in docs
            ],
            "inconsistencies": [],
            "overall_verdict": "CONSISTENT",
            "consistency_score": 94,
            "summary": f"Both documents are consistent — owner name, survey number, and dates all match.",
        }


async def cross_verify_documents(docs: list[dict]) -> dict:
    """
    Cross-document consistency check.
    docs: list of {"file_bytes": bytes, "file_name": str, "document_type": str}
    Returns structured result matching CrossVerifyResponse fields.
    """
    start = time.time()
    mode = "aws" if USE_AWS else "mock"

    if USE_AWS:
        try:
            ai_result = _cross_doc_analyze(docs)
        except Exception as err:
            logging.error(f"Bedrock cross-verify failed (after retries): {err}. Using mock fallback.")
            ai_result = _mock_cross_verify(docs)
            mode = "mock-fallback"
    else:
        ai_result = _mock_cross_verify(docs)

    # Normalise per_doc to our schema
    per_doc_results = []
    for item in ai_result.get("per_doc", []):
        per_doc_results.append({
            "document_type": item.get("document", ""),
            "file_name": next(
                (d["file_name"] for d in docs if d["document_type"] == item.get("document")),
                "",
            ),
            "extracted": item.get("extracted", []),
        })

    # Normalise inconsistencies
    inconsistencies = []
    for inc in ai_result.get("inconsistencies", []):
        inconsistencies.append({
            "field": inc.get("field", ""),
            "documents_involved": inc.get("documents", []),
            "values": inc.get("values", {}),
            "description": inc.get("description", ""),
            "severity": inc.get("severity", "LOW"),
        })

    elapsed_ms = int((time.time() - start) * 1000)

    return {
        "overall_verdict": ai_result.get("overall_verdict", "SUSPICIOUS"),
        "consistency_score": int(ai_result.get("consistency_score", 50)),
        "documents_analyzed": len(docs),
        "per_doc_results": per_doc_results,
        "inconsistencies": inconsistencies,
        "ai_summary": ai_result.get("summary", ""),
        "verified_by": (
            f"Amazon Nova Lite ({BEDROCK_MODEL}) · AWS Bedrock · {BEDROCK_REGION}" if mode == "aws"
            else f"Amazon Nova Pro ({BEDROCK_FALLBACK_MODEL}) · AWS Bedrock · {BEDROCK_REGION} [lite-fallback]" if mode == "aws-pro-fallback"
            else f"OpenAI GPT-4o-mini (Bedrock fallback)" if mode == "openai-fallback"
            else "PropChain-AI-Mock (degraded fallback)" if mode == "mock-fallback"
            else "PropChain-AI-Mock (no AWS credentials)"
        ),
        "mode": mode,
        "processing_time_ms": elapsed_ms,
    }
