# app/routes/political.py

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    MPQuoteCreate, MPActionCreate, BillVoteRequest,
    BillSummaryOut, BillVoteRecordOut,
)
from app.services.political_service import (
    sync_mps, sync_parties, sync_committees,
    sync_from_oknesset, sync_bills_oknesset,
    get_all_mps, get_mp, get_all_parties, get_party, get_committees,
    add_quote, add_action, get_mp_quotes, get_mp_actions,
    run_contradiction_scan, get_contradictions,
    vote_on_bill, get_bill_tally,
    sync_bills, sync_bill_votes, get_all_bills,
    get_bill, get_bill_vote_records, get_mp_vote_records,
)
from app.services.election_service import (
    get_election_overview,
    get_parties_for_2026,
    get_election_issues,
    get_election_blocs,
    get_election_sources,
)
from app.services.news_service import knesset_api_status

router = APIRouter(prefix="/political", tags=["Political Intelligence"])



@router.post("/sync")
async def sync_all():
    """Full sync using Open Knesset CSV pipeline (geo-block safe). Syncs parties, MKs, and bills."""
    result = await sync_from_oknesset()
    committees = await sync_committees()
    result["committees"] = committees
    return {"synced": result, "source": "Open Knesset CSV Pipeline (oknesset.org)"}


@router.post("/sync/oknesset")
async def sync_oknesset():
    """Explicit Open Knesset sync endpoint — pulls fresh data from oknesset.org CSV pipelines."""
    result = await sync_from_oknesset()
    return {
        "status": "success",
        "source": "Open Knesset (oknesset.org) CSV Pipeline",
        "synced": result,
        "note": "Data sourced from verified Open Knesset datasets, not the geo-blocked official OData API."
    }


@router.get("/mps")
async def list_mps(party_name: Optional[str] = Query(None)):
    mps = await get_all_mps(party_name=party_name)
    return {"total": len(mps), "mps": mps}


@router.get("/mps/{mp_id}")
async def mp_profile(mp_id: str):
    mp = await get_mp(mp_id)
    if not mp:
        raise HTTPException(status_code=404, detail="MP not found")
    return mp


@router.post("/mps/{mp_id}/quotes")
async def add_mp_quote(mp_id: str, body: MPQuoteCreate):
    return await add_quote(mp_id, body.model_dump(exclude_none=True))


@router.post("/mps/{mp_id}/actions")
async def add_mp_action(mp_id: str, body: MPActionCreate):
    return await add_action(mp_id, body.model_dump(exclude_none=True))


@router.get("/mps/{mp_id}/quotes")
async def mp_quotes(mp_id: str):
    quotes = await get_mp_quotes(mp_id)
    return {"mp_id": mp_id, "total": len(quotes), "quotes": quotes}


@router.get("/mps/{mp_id}/actions")
async def mp_actions(mp_id: str):
    actions = await get_mp_actions(mp_id)
    return {"mp_id": mp_id, "total": len(actions), "actions": actions}


@router.post("/mps/{mp_id}/contradictions/scan")
async def scan_contradictions(mp_id: str):
    use_ai = True
    found = await run_contradiction_scan(mp_id, use_ai=use_ai)
    return {"mp_id": mp_id, "new_contradictions_found": len(found), "contradictions": found}


@router.get("/mps/{mp_id}/contradictions")
async def mp_contradictions(mp_id: str):
    contradictions = await get_contradictions(mp_id)
    return {"mp_id": mp_id, "total": len(contradictions), "contradictions": contradictions}


@router.get("/parties")
async def list_parties():
    parties = await get_all_parties()
    return {"total": len(parties), "parties": parties}


@router.get("/parties/{party_id}")
async def party_detail(party_id: str):
    party = await get_party(party_id)
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    return party


@router.get("/committees")
async def list_committees():
    committees = await get_committees()
    return {"total": len(committees), "committees": committees}


@router.post("/bills/sync")
async def sync_bills_route(limit: int = Query(50, ge=1, le=200)):
    synced = await sync_bills(limit)
    return {"synced": synced}


@router.get("/bills/health")
async def bills_health():
    """Return quick health status for Knesset API reachability."""
    status = await knesset_api_status()
    return {"official_api_reachable": status.get("reachable", False), "notice": status.get("message")}


@router.post("/bills/{bill_id}/sync-votes")
async def sync_bill_votes_route(bill_id: str):
    synced = await sync_bill_votes(bill_id)
    return {"bill_id": bill_id, "mp_votes_synced": synced}


@router.get("/bills")
async def list_bills(limit: int = Query(50, ge=1, le=200)):
    bills = await get_all_bills(limit)
    status = await knesset_api_status()
    return {"total": len(bills), "bills": bills, "official_api_reachable": status.get("reachable", False), "official_api_notice": status.get("message")}


@router.get("/bills/{bill_id}", response_model=BillSummaryOut)
async def bill_detail(bill_id: str):
    bill = await get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    status = await knesset_api_status()
    bill["official_api_reachable"] = status.get("reachable", False)
    bill["official_api_notice"] = status.get("message")
    return bill


@router.get("/bills/{bill_id}/votes", response_model=list[BillVoteRecordOut])
async def bill_votes(bill_id: str):
    return await get_bill_vote_records(bill_id)


@router.get("/mps/{mp_id}/votes", response_model=list[BillVoteRecordOut])
async def mp_vote_history(mp_id: str):
    return await get_mp_vote_records(mp_id)


@router.post("/bills/{bill_id}/vote")
async def vote_bill(bill_id: str, body: BillVoteRequest):
    return await vote_on_bill(bill_id, "000000000000000000000000", body.support)


@router.get("/bills/{bill_id}/tally")
async def bill_tally(bill_id: str):
    return await get_bill_tally(bill_id)


# ── Elections 2026 ─────────────────────────────────────────────────────────────
# All data sourced from: Wikipedia, bechirot.gov.il, Times of Israel,
# Israel Policy Forum, official party websites — NOT AI-generated.

@router.get(
    "/elections/2026",
    tags=["Elections 2026"],
    summary="26th Knesset election overview",
    description=(
        "Overview of the 2026 Israeli legislative election (26th Knesset): "
        "expected date, electoral system, key blocs, and verified context. "
        "Data sourced from bechirot.gov.il, Wikipedia, and Times of Israel."
    ),
)
async def election_2026_overview():
    return get_election_overview()


@router.get(
    "/elections/2026/parties",
    tags=["Elections 2026"],
    summary="Parties expected to contest the 2026 election",
    description=(
        "List of all parties expected to run in the 2026 election with "
        "leader, platform, poll ranges, and links to official party websites and Wikipedia. "
        "Filter by bloc: 'coalition', 'opposition', or 'arab_parties'."
    ),
)
async def election_2026_parties(bloc: Optional[str] = Query(None, description="Filter by bloc: coalition | opposition | arab_parties")):
    parties = get_parties_for_2026(bloc=bloc)
    return {
        "total": len(parties),
        "bloc_filter": bloc,
        "parties": parties,
        "data_source_note": "Data sourced from official party websites, Wikipedia, Times of Israel — not AI-generated.",
        "data_freshness": "2026-06-15",
        "official_election_authority": "https://www.bechirot.gov.il/",
    }


@router.get(
    "/elections/2026/issues",
    tags=["Elections 2026"],
    summary="Key campaign issues for the 2026 election",
    description="The major political issues shaping the 2026 Israeli election campaign.",
)
async def election_2026_issues():
    issues = get_election_issues()
    return {
        "total": len(issues),
        "issues": issues,
        "data_freshness": "2026-06-15",
    }


@router.get(
    "/elections/2026/blocs",
    tags=["Elections 2026"],
    summary="Current bloc seat projections (polling)",
    description=(
        "Approximate seat projections for the coalition and opposition blocs, "
        "based on June 2026 polling averages. Note: polls change frequently."
    ),
)
async def election_2026_blocs():
    return get_election_blocs()


@router.get(
    "/elections/2026/sources",
    tags=["Elections 2026"],
    summary="Authoritative sources for Israeli election information",
    description=(
        "A curated list of reliable, official sources for learning about Israeli parties, "
        "politicians, and the 2026 election — to avoid AI misinformation. "
        "Includes bechirot.gov.il, Knesset.gov.il, Wikipedia, and quality news outlets."
    ),
)
async def election_2026_sources():
    return get_election_sources()
