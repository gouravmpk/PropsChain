"""
Property Registry API Routes
-----------------------------
Exposes the national property registry as REST endpoints.
These mirror what real portals like DILRMP, state land records, and EC portals provide.
"""

from fastapi import APIRouter, Query
from services.registry_service import (
    lookup_by_survey,
    lookup_by_registration,
    verify_owner,
    check_encumbrances,
    get_ownership_history,
    search_by_owner,
    get_registry_stats,
)

router = APIRouter(prefix="/registry", tags=["Property Registry"])


@router.get(
    "/lookup",
    summary="Look up a property by survey number or registration number",
    description=(
        "Search the national property registry. Provide either `survey_number` "
        "(e.g. `123/4A`, `Plot-7A`) or `registration_number` (e.g. `REG-BLR-2024-9876`). "
        "Optionally filter by `state`."
    ),
)
async def registry_lookup(
    survey_number: str = Query(None, description="Survey / plot number from the document"),
    registration_number: str = Query(None, description="Registration number from the document"),
    state: str = Query(None, description="State name to narrow results (e.g. Karnataka)"),
):
    if not survey_number and not registration_number:
        return {"error": "Provide at least one of: survey_number, registration_number"}
    if registration_number:
        return lookup_by_registration(registration_number)
    return lookup_by_survey(survey_number, state)


@router.get(
    "/verify-owner",
    summary="Verify if a claimed owner matches the registry",
    description=(
        "Cross-check the name on a document against the officially registered owner. "
        "Detects ownership fraud, impersonation, and benami transactions."
    ),
)
async def registry_verify_owner(
    owner_name: str = Query(..., description="Owner name as it appears on the document"),
    survey_number: str = Query(None),
    registration_number: str = Query(None),
    state: str = Query(None),
):
    return verify_owner(owner_name, survey_number, registration_number, state)


@router.get(
    "/encumbrances",
    summary="Check encumbrances (mortgages, liens, court orders) on a property",
    description=(
        "Returns active encumbrances from the national registry. "
        "An active mortgage or court order means the property cannot be freely sold."
    ),
)
async def registry_encumbrances(
    survey_number: str = Query(None),
    registration_number: str = Query(None),
    state: str = Query(None),
):
    if not survey_number and not registration_number:
        return {"error": "Provide at least one of: survey_number, registration_number"}
    return check_encumbrances(survey_number, registration_number, state)


@router.get(
    "/ownership-history",
    summary="Get the full chain of title / ownership history",
    description=(
        "Returns all past and present owners of a property with transfer dates and sale values. "
        "Useful for detecting rapid flipping, suspicious transfers, or inflated valuations."
    ),
)
async def registry_ownership_history(
    survey_number: str = Query(None),
    registration_number: str = Query(None),
    state: str = Query(None),
):
    if not survey_number and not registration_number:
        return {"error": "Provide at least one of: survey_number, registration_number"}
    return get_ownership_history(survey_number, registration_number, state)


@router.get(
    "/search",
    summary="Search properties by owner name",
    description=(
        "Find all properties — current or historical — associated with an owner's name. "
        "Optionally filter by state. Useful for detecting undisclosed holdings."
    ),
)
async def registry_search(
    owner_name: str = Query(..., description="Full or partial owner name"),
    state: str = Query(None),
):
    return search_by_owner(owner_name, state)


@router.get(
    "/stats",
    summary="Registry statistics",
    description="Returns coverage stats: total properties, states, breakdown by status.",
)
async def registry_stats():
    return get_registry_stats()
