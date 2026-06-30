# app/routes/blocs.py
"""
Bloc & Party Full-Profile Routes.
Covers Screen 1 (Coalition vs. Opposition), Screen 2 (Agenda Comparison),
Screen 3 (Individual Party Detail Page), and the Trusted Source Verification endpoints.
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
from app.services.political_service import backfill_party_verification
from app.services.political_verification_service import (
    build_full_party_verification_report,
    cross_check_party_via_wikipedia,
    TRUSTED_SOURCES,
)
from app.core.database import get_db

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


# ── Backfill / Migration ──────────────────────────────────────────────────────

@router.post(
    "/parties/backfill-verification",
    summary="Backfill verification fields on existing party docs",
    description=(
        "Patches all existing party documents in MongoDB with verified_by[], "
        "verification_score, verification_label, verification_badge, seats, "
        "seats_source, and a live Wikipedia cross-check result. "
        "Run this once after deploying the verification code — no CSV download needed. "
        "Takes ~20–30 seconds (one Wikipedia API call per party)."
    ),
    tags=["Admin Sync", "Trusted Sources"],
)
async def backfill_verification():
    """Fast in-place patch for stale party documents. No CSV sync needed."""
    result = await backfill_party_verification()
    return result


# ── Trusted Source Verification Routes ───────────────────────────────────────

@router.get(
    "/sources/trusted",
    summary="Trusted sources registry",
    description=(
        "Returns the full registry of 7 trusted sources used for Politics & Bills data. "
        "Each source includes: reliability rating, bias note, type, and usage notes. "
        "Use this to show users which sources back each data point."
    ),
    tags=["Trusted Sources"],
)
async def trusted_sources_registry():
    """Return the canonical list of trusted data sources."""
    return {
        "total": len(TRUSTED_SOURCES),
        "sources": list(TRUSTED_SOURCES.values()),
        "data_integrity_note": (
            "All political facts are sourced from the listed verified databases. "
            "AI is used ONLY for translation and biography text — never for political facts "
            "like seat counts, coalition status, or bill status."
        ),
    }


@router.get(
    "/parties/verification-summary",
    summary="Verification badges for all parties",
    description=(
        "Returns a compact list of all parties with their verification_badge, "
        "verification_score, and cross_check summary. "
        "Use this to display source-trust indicators on the main party list screen."
    ),
    tags=["Trusted Sources"],
)
async def parties_verification_summary():
    """Get verification badges for all parties — one row per party."""
    db = get_db()
    parties = await db.parties.find(
        {},
        {
            "_id": 1,
            "name": 1,
            "verification_score": 1,
            "verification_label": 1,
            "verification_badge": 1,
            "cross_check_result": 1,
            "verified_by": 1,
            "seats_source": 1,
        },
    ).sort("name", 1).to_list(50)

    result = []
    for p in parties:
        p["id"] = str(p.pop("_id"))
        cross = p.get("cross_check_result") or {}
        result.append({
            "id": p["id"],
            "name": p.get("name"),
            "verification_score": p.get("verification_score", 0),
            "verification_label": p.get("verification_label", "unverified"),
            "badge": p.get("verification_badge", {}),
            "sources_count": len(p.get("verified_by", [])),
            "sources": [v.get("source_name") for v in p.get("verified_by", [])],
            "wikipedia_cross_check": cross.get("agreement_label") if cross.get("checked") else "not_run",
            "seats_source": p.get("seats_source"),
        })

    return {
        "total": len(result),
        "parties": result,
        "note": (
            "Run POST /political/sync/oknesset to refresh verification data. "
            "Wikipedia cross-checks run automatically during sync."
        ),
    }


@router.get(
    "/parties/{party_id}/verification",
    summary="Full verification report for a party",
    description=(
        "Returns the complete trusted-source verification report for one party. "
        "Includes: verified_by[] list (which source verified which field), "
        "live Wikipedia cross-check result (leader + seat count comparison), "
        "verification badge for UI display, and the full trusted sources registry. "
        "Use this for the party detail page 'Data Sources' panel."
    ),
    tags=["Trusted Sources"],
)
async def party_verification_report(party_id: str):
    """Get full trusted-source verification report for a single party."""
    db = get_db()
    from bson import ObjectId
    try:
        oid = ObjectId(party_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid party_id format")

    party = await db.parties.find_one({"_id": oid})
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    name_eng = party.get("name", "")
    verified_by = party.get("verified_by", [])
    verification_score = party.get("verification_score", 0)
    verification_label = party.get("verification_label", "unverified")
    cross_check_result = party.get("cross_check_result")

    return build_full_party_verification_report(
        name_eng=name_eng,
        verified_by=verified_by,
        verification_score=verification_score,
        verification_label=verification_label,
        cross_check_result=cross_check_result,
    )


@router.post(
    "/verify",
    summary="Trigger live cross-check for all parties",
    description=(
        "Runs a live Wikipedia cross-check for every party in the database. "
        "Compares stored leader name and seat count against Wikipedia summary text. "
        "Detects and stores agreements and divergences. "
        "Results are stored in MongoDB and returned immediately. "
        "Typically takes 15–30 seconds for all parties."
    ),
    tags=["Trusted Sources", "Admin Sync"],
)
async def run_party_cross_checks():
    """Live cross-check all parties against Wikipedia. Stores divergences."""
    db = get_db()
    parties = await db.parties.find(
        {},
        {"_id": 1, "name": 1, "leader": 1, "seats": 1, "wikipedia_url": 1},
    ).to_list(50)

    results = []
    for party in parties:
        pid = party["_id"]
        name_eng = party.get("name", "")
        result = await cross_check_party_via_wikipedia(
            name_eng=name_eng,
            stored_leader=party.get("leader"),
            stored_seats=party.get("seats", 0),
            wikipedia_url=party.get("wikipedia_url"),
        )
        # Persist updated cross_check_result
        await db.parties.update_one(
            {"_id": pid},
            {"$set": {"cross_check_result": result}},
        )
        results.append({
            "party": name_eng,
            "checked": result.get("checked"),
            "agreement_label": result.get("agreement_label"),
            "agreements": result.get("agreements", []),
            "divergences": result.get("divergences", []),
        })

    verified_count = sum(1 for r in results if r.get("checked"))
    divergence_count = sum(1 for r in results if r.get("divergences"))

    return {
        "status": "complete",
        "total_parties": len(results),
        "wikipedia_checked": verified_count,
        "parties_with_divergences": divergence_count,
        "results": results,
        "note": "Divergences indicate mismatches between stored data and Wikipedia text. Always verify at the source URL.",
    }
