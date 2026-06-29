# app/routes/blocs.py
"""
Bloc & Party Full-Profile Routes.
Covers Screen 1 (Coalition vs. Opposition), Screen 2 (Agenda Comparison),
and Screen 3 (Individual Party Detail Page).
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from app.services.blocs_service import (
    get_blocs,
    get_party_full_profile,
    get_mp_full_profile,
    get_agenda_comparison,
    sync_party_agendas,
)

router = APIRouter(prefix="/political", tags=["Blocs & Party Profiles"])


# ── Coalition vs. Opposition ─────────────────────────────────────────────────

@router.get(
    "/blocs",
    summary="Coalition vs. Opposition bloc grouping",
    description=(
        "Returns ALL political parties grouped by bloc: coalition, opposition, and arab_parties. "
        "Includes correct seat counts per bloc. Use this to power the main Coalition vs. Opposition screen. "
        "Data sourced from Open Knesset + Wikipedia — not AI-generated."
    ),
)
async def get_political_blocs():
    """Get all parties organized by coalition / opposition / arab bloc."""
    return await get_blocs()


# ── Party Full Profile (Screen 3) ────────────────────────────────────────────

@router.get(
    "/agenda-comparison",
    summary="Agenda comparison",
    description="Returns a horizontal agenda comparison across parties for the Politics screen.",
)
async def agenda_comparison(bloc: Optional[str] = Query(None)):
    """Return the horizontal-scroll agenda comparison table."""
    return await get_agenda_comparison(bloc=bloc)


@router.get(
    "/parties/{party_id}/full-profile",
    summary="Full party profile — Screen 3",
    description=(
        "Full detail page for a single political party. "
        "Returns: party info, all MPs with photos, key bills initiated, "
        "key parliamentary actions, and detailed topic-based agenda. "
        "This is what opens when a user taps on a party in the Coalition/Opposition screen."
    ),
)
async def party_full_profile(party_id: str):
    """Get full party profile including members, bills, actions, and agenda."""
    profile = await get_party_full_profile(party_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Party not found")
    return profile


# ── MP Full Profile (Screen 4 — enhanced) ────────────────────────────────────

@router.get(
    "/mps/{mp_id}/full-profile",
    summary="Full MP profile — Screen 4",
    description=(
        "Full detail page for a single Member of Parliament. "
        "Returns: bio, service years, bills passed count, attendance %, "
        "political career history, committee memberships, "
        "Actions vs. Claims comparison table, and notable recent activity. "
        "This is what opens when a user taps on an MP in the party detail page."
    ),
)
async def mp_full_profile(mp_id: str):
    """Get full MP profile with career history, actions vs. claims, and notable activity."""
    profile = await get_mp_full_profile(mp_id)
    if not profile:
        raise HTTPException(status_code=404, detail="MP not found")
    return profile





# ── Agenda Sync (Admin / Background) ─────────────────────────────────────────

@router.post(
    "/parties/sync-agendas",
    summary="Sync party agendas from official websites via AI",
    description=(
        "Triggers an AI-assisted re-sync of all party agendas from their official websites. "
        "Uses GPT-4o-mini to extract structured platform data per topic. "
        "Run this periodically to keep agenda data up-to-date. "
        "Requires OpenAI API key in configuration."
    ),
    tags=["Admin Sync"],
)
async def sync_agendas(background_tasks: BackgroundTasks):
    """Trigger background sync of all party agendas from their official websites."""
    background_tasks.add_task(sync_party_agendas)
    return {
        "status": "sync_started",
        "message": "Party agenda sync is running in the background. Check /political/parties/agenda-comparison after a few minutes.",
        "note": "Uses GPT-4o-mini to summarize official party website content.",
    }


@router.post(
    "/parties/sync-agendas/now",
    summary="Sync party agendas — wait for result",
    description=(
        "Same as /parties/sync-agendas but waits synchronously for the result. "
        "Use for testing or small datasets. For production, use the background version."
    ),
    tags=["Admin Sync"],
)
async def sync_agendas_now():
    """Run agenda sync synchronously and return the result."""
    result = await sync_party_agendas()
    return result
