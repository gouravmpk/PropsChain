"""
Property Registry Service
-------------------------
Queries the generic Indian property registry mock database.
Used by API routes and integrated into the AI verification pipeline.
"""

from data.property_registry import (
    get_by_survey_number,
    get_by_registration_number,
    get_by_owner_name,
    PROPERTY_REGISTRY,
)


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _clean(p: dict) -> dict:
    """Return a registry record safe to send to the client."""
    return {k: v for k, v in p.items()}


def _names_match(name1: str, name2: str) -> bool:
    """
    Fuzzy name match that handles:
      - Exact match          "Ravi Kumar" == "Ravi Kumar"
      - Case differences     "ravi kumar" == "Ravi Kumar"
      - Initial abbreviation "R. Kumar"   ~= "Ravi Kumar"
    """
    n1 = name1.lower().strip().rstrip(".")
    n2 = name2.lower().strip().rstrip(".")

    if n1 == n2:
        return True

    parts1 = n1.split()
    parts2 = n2.split()

    if not parts1 or not parts2:
        return False

    # Last names must match
    if parts1[-1] != parts2[-1]:
        return False

    # First name: accept if either is an initial of the other
    first1 = parts1[0].rstrip(".")
    first2 = parts2[0].rstrip(".")
    if first1 == first2:
        return True
    if len(first1) == 1 and first2.startswith(first1):
        return True
    if len(first2) == 1 and first1.startswith(first2):
        return True

    return False


def _resolve_property(
    survey_number: str | None,
    registration_number: str | None,
    state: str | None,
) -> dict | None:
    """Find a single best-match property from available identifiers."""
    if registration_number:
        return get_by_registration_number(registration_number)
    if survey_number:
        candidates = get_by_survey_number(survey_number, state)
        return candidates[0] if candidates else None
    return None


# ─── Public API ───────────────────────────────────────────────────────────────

def lookup_by_survey(survey_number: str, state: str | None = None) -> dict:
    results = get_by_survey_number(survey_number, state)
    if not results:
        return {
            "found": False,
            "survey_number": survey_number,
            "message": f"Survey/plot number '{survey_number}' not found in national registry.",
        }
    return {
        "found": True,
        "count": len(results),
        "properties": [_clean(p) for p in results],
    }


def lookup_by_registration(registration_number: str) -> dict:
    p = get_by_registration_number(registration_number)
    if not p:
        return {
            "found": False,
            "registration_number": registration_number,
            "message": f"Registration number '{registration_number}' not found in national registry.",
        }
    return {"found": True, "property": _clean(p)}


def verify_owner(
    owner_name: str,
    survey_number: str | None = None,
    registration_number: str | None = None,
    state: str | None = None,
) -> dict:
    """
    Verify whether owner_name matches the currently registered owner.
    Returns match status, discrepancy details, and a fraud_flag.
    """
    prop = _resolve_property(survey_number, registration_number, state)

    if prop is None:
        # Try owner-name lookup as last resort
        candidates = get_by_owner_name(owner_name, state)
        if candidates:
            prop = candidates[0]

    if prop is None:
        return {
            "verified": False,
            "owner_match": False,
            "message": "Property not found in national registry — cannot verify ownership.",
            "fraud_flag": True,
            "severity": "HIGH",
        }

    registered_owner = prop["current_owner"]["name"]
    match = _names_match(owner_name, registered_owner)

    return {
        "verified": True,
        "property_id": prop["property_id"],
        "owner_match": match,
        "claimed_owner": owner_name,
        "registered_owner": registered_owner,
        "property_status": prop["property_status"],
        "encumbrance_status": prop["encumbrance_status"],
        "fraud_flag": not match,
        "severity": "HIGH" if not match else "NONE",
        "message": (
            f"Owner verified — registry confirms '{registered_owner}'"
            if match
            else f"MISMATCH — Registry shows '{registered_owner}', document claims '{owner_name}'"
        ),
    }


def check_encumbrances(
    survey_number: str | None = None,
    registration_number: str | None = None,
    state: str | None = None,
) -> dict:
    prop = _resolve_property(survey_number, registration_number, state)

    if prop is None:
        return {
            "found": False,
            "message": "Property not found — encumbrance status unknown.",
            "fraud_flag": True,
            "severity": "MEDIUM",
        }

    enc_list = prop.get("encumbrances", [])
    status = prop["encumbrance_status"]
    p_status = prop["property_status"]

    if p_status == "Disputed":
        severity = "HIGH"
    elif status == "ACTIVE":
        severity = "MEDIUM"
    else:
        severity = "NONE"

    return {
        "found": True,
        "property_id": prop["property_id"],
        "encumbrance_status": status,
        "property_status": p_status,
        "encumbrances": enc_list,
        "fraud_flag": status == "ACTIVE" or p_status == "Disputed",
        "severity": severity,
    }


def get_ownership_history(
    survey_number: str | None = None,
    registration_number: str | None = None,
    state: str | None = None,
) -> dict:
    prop = _resolve_property(survey_number, registration_number, state)

    if prop is None:
        return {"found": False, "message": "Property not found in national registry."}

    history = prop.get("ownership_history", [])
    return {
        "found": True,
        "property_id": prop["property_id"],
        "state": prop["state"],
        "address": prop.get("address"),
        "current_owner": prop["current_owner"],
        "ownership_history": history,
        "total_transfers": len(history),
    }


def search_by_owner(owner_name: str, state: str | None = None) -> dict:
    props = get_by_owner_name(owner_name, state)
    return {
        "found": bool(props),
        "count": len(props),
        "properties": [_clean(p) for p in props],
    }


def get_registry_stats() -> dict:
    states = sorted({p["state"] for p in PROPERTY_REGISTRY})
    by_state = {s: sum(1 for p in PROPERTY_REGISTRY if p["state"] == s) for s in states}
    statuses = {}
    for p in PROPERTY_REGISTRY:
        statuses[p["property_status"]] = statuses.get(p["property_status"], 0) + 1
    return {
        "total_properties": len(PROPERTY_REGISTRY),
        "states_covered": len(states),
        "states": states,
        "by_state": by_state,
        "by_status": statuses,
    }


# ─── Registry cross-check (called from ai_service pipeline) ──────────────────

def registry_cross_check(extracted_fields: list[dict], document_type: str) -> dict:
    """
    Run registry checks against AI-extracted fields from a document.
    Returns additional fraud flags and a score penalty to merge into
    the main verification result.
    """
    flags: list[str] = []
    checks: list[dict] = []

    # Build a flat field map from extracted_fields
    field_map: dict[str, str] = {}
    for f in extracted_fields:
        field_map[f["key"].lower().strip()] = str(f.get("value", "")).strip()

    def _get(*keys: str) -> str | None:
        for k in keys:
            v = field_map.get(k.lower())
            if v:
                return v
        return None

    survey_num = _get(
        "survey number", "survey no", "survey/plot number",
        "plot number", "khasra number", "gata number",
    )
    reg_num = _get(
        "registration number", "reg. number", "doc no",
        "document number", "deed number",
    )
    owner = _get(
        "owner name", "full name", "vendor name",
        "applicant name", "buyer name",
    )
    state = _get("state")

    # ── 1. Property existence check ───────────────────────────────────────────
    prop = _resolve_property(survey_num, reg_num, state)

    if survey_num or reg_num:
        if prop is None:
            checks.append({
                "check": "Property Existence",
                "found": False,
                "identifier": reg_num or survey_num,
            })
            flags.append(
                f"REGISTRY: Property with {'registration number' if reg_num else 'survey number'} "
                f"'{reg_num or survey_num}' not found in national registry — "
                "number may be fabricated or incorrect"
            )
        else:
            checks.append({
                "check": "Property Existence",
                "found": True,
                "property_id": prop["property_id"],
                "state": prop["state"],
                "address": prop.get("address"),
            })

    # ── 2. Owner verification ─────────────────────────────────────────────────
    if owner and prop is not None:
        registered_owner = prop["current_owner"]["name"]
        match = _names_match(owner, registered_owner)
        checks.append({
            "check": "Owner Verification",
            "owner_match": match,
            "claimed_owner": owner,
            "registered_owner": registered_owner,
            "severity": "NONE" if match else "HIGH",
        })
        if not match:
            flags.append(
                f"REGISTRY: Owner mismatch — document claims '{owner}' "
                f"but registry shows '{registered_owner}'"
            )

    # ── 3. Encumbrance check ──────────────────────────────────────────────────
    if prop is not None:
        enc = prop.get("encumbrances", [])
        p_status = prop["property_status"]
        e_status = prop["encumbrance_status"]

        checks.append({
            "check": "Encumbrance Check",
            "encumbrance_status": e_status,
            "property_status": p_status,
            "encumbrances": enc,
        })

        if p_status == "Disputed":
            flags.append(
                "REGISTRY: Property is under active court dispute — "
                "any transfer is legally restricted"
            )
        elif e_status == "ACTIVE":
            holder = enc[0].get("holder", "unknown lender") if enc else "unknown lender"
            enc_type = enc[0].get("type", "encumbrance") if enc else "encumbrance"
            flags.append(
                f"REGISTRY: Active {enc_type} found — property is pledged to {holder}. "
                "Seller must clear this before transfer."
            )

    # ── Score: each registry flag adds 0.10 to fraud score ───────────────────
    return {
        "registry_checks": checks,
        "registry_flags": flags,
        "registry_penalty": round(len(flags) * 0.10, 2),
    }
