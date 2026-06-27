# app/routes/politics101.py
"""
Israeli Politics 101 Routes.
Provides: Knesset Sessions, Bills Passed, Committee Actions.
This is the general educational section — not tied to any specific party.
Maps to the "Israeli Politics 101" section on Screen 5.
"""

from typing import Optional

from fastapi import APIRouter, Query

from app.services.politics101_service import (
    get_knesset_sessions,
    get_bills_passed,
    get_committee_actions,
)

router = APIRouter(prefix="/politics-101", tags=["Israeli Politics 101"])


@router.get(
    "/sessions",
    summary="Important Knesset sessions",
    description=(
        "Returns a curated list of the most important Knesset plenary and committee sessions. "
        "Includes major debates, emergency sessions, budget speeches, and landmark votes. "
        "Data sourced from Knesset.gov.il records and verified Israeli news sources. "
        "Set use_ai_refresh=true to fetch additional recent sessions via AI."
    ),
)
async def knesset_sessions(
    limit: int = Query(20, ge=1, le=50, description="Number of sessions to return"),
    use_ai_refresh: bool = Query(
        False,
        description="Fetch additional recent sessions via AI (requires OpenAI key)",
    ),
):
    """Get important Knesset sessions for the Israeli Politics 101 section."""
    return await get_knesset_sessions(
        limit=limit,
        use_ai_refresh=use_ai_refresh,
    )


@router.get(
    "/bills-passed",
    summary="Key bills that passed in the Knesset",
    description=(
        "Returns a curated list of the most significant bills that have passed in the Knesset. "
        "Includes vote counts, initiating party, and AI-generated summaries. "
        "Data sourced from Open Knesset CSV pipeline and verified Knesset records."
    ),
)
async def bills_passed(
    limit: int = Query(10, ge=1, le=50, description="Number of bills to return"),
):
    """Get key bills that passed in the Knesset."""
    return await get_bills_passed(limit=limit)


@router.get(
    "/committee-actions",
    summary="Notable committee actions and decisions",
    description=(
        "Returns a curated list of notable actions and decisions taken by Knesset committees. "
        "Includes Finance Committee, Security Committee, and Constitutional Law Committee. "
        "Data verified from Knesset committee records and Israeli news."
    ),
)
async def committee_actions(
    limit: int = Query(10, ge=1, le=50, description="Number of actions to return"),
):
    """Get notable committee actions for the Israeli Politics 101 section."""
    return await get_committee_actions(limit=limit)
