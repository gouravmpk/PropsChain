"""
Rule-based fraud checks applied to extracted document fields.
These run regardless of AWS availability — no external calls needed.
"""

import re
from datetime import datetime, date
from models.ai_verify import RuleCheckResult


# ---------------------------------------------------------------------------
# Individual rule functions
# Each returns a RuleCheckResult
# ---------------------------------------------------------------------------

def check_future_dates(fields: dict) -> RuleCheckResult:
    """Registration/execution dates must not be in the future."""
    today = date.today()
    date_keys = [k for k in fields if any(w in k.lower() for w in ["date", "dated", "executed"])]
    suspicious = []
    for key in date_keys:
        val = fields[key]
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%B %d, %Y", "%d %B %Y"):
            try:
                parsed = datetime.strptime(val.strip(), fmt).date()
                if parsed > today:
                    suspicious.append(f"{key}: '{val}' is in the future")
                break
            except ValueError:
                continue
    passed = len(suspicious) == 0
    return RuleCheckResult(
        rule="Future Date Check",
        passed=passed,
        detail="All dates are valid" if passed else f"Future dates detected: {'; '.join(suspicious)}",
    )


def check_registration_number_format(fields: dict) -> RuleCheckResult:
    """Indian property registration numbers follow state-specific patterns."""
    reg_keys = [k for k in fields if any(w in k.lower() for w in ["registration", "reg no", "doc no", "document number"])]
    if not reg_keys:
        return RuleCheckResult(rule="Registration Number Format", passed=True, detail="No registration number field found — skipped")

    pattern = re.compile(r"^[A-Z]{2,4}[-/]?\d{2,4}[-/]?\d{2,6}$", re.IGNORECASE)
    invalid = []
    for key in reg_keys:
        val = fields.get(key, "").strip()
        if val and not pattern.match(val):
            invalid.append(f"{key}: '{val}'")

    passed = len(invalid) == 0
    return RuleCheckResult(
        rule="Registration Number Format",
        passed=passed,
        detail="Format valid" if passed else f"Unexpected format: {'; '.join(invalid)}",
    )


def check_name_consistency(fields: dict) -> RuleCheckResult:
    """Owner name in header vs signature block should match."""
    name_keys = [k for k in fields if any(w in k.lower() for w in ["owner", "vendor", "vendee", "buyer", "seller", "grantor", "grantee", "party"])]
    names = [fields[k].strip().lower() for k in name_keys if fields.get(k)]
    if len(names) < 2:
        return RuleCheckResult(rule="Name Consistency", passed=True, detail="Single name reference — no conflict possible")

    # Check if names are completely different (simple heuristic)
    first_words = [n.split()[0] if n.split() else "" for n in names]
    unique_first = set(first_words)
    passed = len(unique_first) <= len(names) // 2 + 1  # allow some variation

    return RuleCheckResult(
        rule="Name Consistency",
        passed=passed,
        detail="Names appear consistent" if passed else f"Name mismatch across fields: {names}",
    )


def check_aadhaar_format(fields: dict) -> RuleCheckResult:
    """Aadhaar numbers must be 12 digits."""
    aadhaar_keys = [k for k in fields if "aadhaar" in k.lower() or "aadhar" in k.lower() or "uid" in k.lower()]
    if not aadhaar_keys:
        return RuleCheckResult(rule="Aadhaar Format", passed=True, detail="No Aadhaar field — skipped")

    invalid = []
    for key in aadhaar_keys:
        val = re.sub(r"[\s-]", "", fields.get(key, ""))
        if val and (not val.isdigit() or len(val) != 12):
            invalid.append(f"{key}: '{fields[key]}'")

    passed = len(invalid) == 0
    return RuleCheckResult(
        rule="Aadhaar Format",
        passed=passed,
        detail="Aadhaar format valid" if passed else f"Invalid Aadhaar: {'; '.join(invalid)}",
    )


def check_amount_format(fields: dict) -> RuleCheckResult:
    """Consideration/sale amounts must be numeric and reasonable."""
    amount_keys = [k for k in fields if any(w in k.lower() for w in ["amount", "consideration", "price", "value", "rupee"])]
    suspicious = []
    for key in amount_keys:
        val = fields.get(key, "")
        # Strip currency symbols and commas
        cleaned = re.sub(r"[₹,\s]", "", val).replace("Rs.", "").replace("Rs", "")
        if cleaned and not re.match(r"^\d+(\.\d{1,2})?$", cleaned):
            suspicious.append(f"{key}: '{val}'")

    passed = len(suspicious) == 0
    return RuleCheckResult(
        rule="Amount Format",
        passed=passed,
        detail="Amount fields are valid" if passed else f"Unreadable amounts: {'; '.join(suspicious)}",
    )


def check_missing_mandatory_fields(fields: dict, document_type: str) -> RuleCheckResult:
    """Check that expected fields for this document type are present."""
    mandatory = {
        "Title Deed": ["owner", "area", "date", "registration"],
        "Sale Agreement": ["buyer", "seller", "amount", "date"],
        "Aadhaar Card": ["name", "date", "address"],
        "PAN Card": ["name", "pan"],
        "Encumbrance Certificate": ["owner", "date", "period"],
        "Property Tax Receipt": ["owner", "amount", "date"],
        "No Objection Certificate": ["owner", "date", "authority"],
        "Mutation Certificate": ["owner", "date", "survey"],
    }
    required = mandatory.get(document_type, [])
    fields_lower = {k.lower(): v for k, v in fields.items()}
    missing = []
    for req in required:
        if not any(req in k for k in fields_lower):
            missing.append(req)

    passed = len(missing) == 0
    return RuleCheckResult(
        rule="Mandatory Fields",
        passed=passed,
        detail="All mandatory fields present" if passed else f"Missing fields for {document_type}: {missing}",
    )


def check_low_confidence_fields(extracted_fields: list) -> RuleCheckResult:
    """Flag fields where AI extraction confidence < 70%."""
    low = [f"{f['key']} ({f['confidence']*100:.0f}%)" for f in extracted_fields if f.get("confidence", 1.0) < 0.70]
    passed = len(low) == 0
    return RuleCheckResult(
        rule="Extraction Confidence",
        passed=passed,
        detail="All fields extracted with high confidence" if passed else f"Low-confidence fields: {', '.join(low)}",
    )


# ---------------------------------------------------------------------------
# Run all rules together
# ---------------------------------------------------------------------------

def run_all_rules(extracted_fields: list[dict], document_type: str) -> tuple[list[RuleCheckResult], list[str]]:
    """
    Run all rule-based checks.
    Returns (rule_results, flags_list).
    """
    fields_dict = {f["key"]: f["value"] for f in extracted_fields}

    results = [
        check_future_dates(fields_dict),
        check_registration_number_format(fields_dict),
        check_name_consistency(fields_dict),
        check_aadhaar_format(fields_dict),
        check_amount_format(fields_dict),
        check_missing_mandatory_fields(fields_dict, document_type),
        check_low_confidence_fields(extracted_fields),
    ]

    # Collect human-readable flags from failed rules
    flags = [r.detail for r in results if not r.passed]
    return results, flags
