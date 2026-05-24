# app/routes/political.py

import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import require_auth, require_admin, get_current_user
from app.models.schemas import MPQuoteCreate, MPActionCreate, BillVoteRequest
from app.services.political_service import (
    sync_mps, sync_parties, sync_committees,
    get_all_mps, get_mp, get_all_parties, get_party, get_committees,
    add_quote, add_action, get_mp_quotes, get_mp_actions,
    run_contradiction_scan, get_contradictions,
    vote_on_bill, get_bill_tally,
)

router = APIRouter(prefix="/political", tags=["Political Intelligence"])


@router.post("/sync")
async def sync_all(_: dict = Depends(require_admin)):
    mps = await sync_mps()
    parties = await sync_parties()
    committees = await sync_committees()
    return {"synced": {"mps": mps, "parties": parties, "committees": committees}}


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
async def add_mp_quote(mp_id: str, body: MPQuoteCreate, _: dict = Depends(require_auth)):
    return await add_quote(mp_id, body.model_dump(exclude_none=True))


@router.post("/mps/{mp_id}/actions")
async def add_mp_action(mp_id: str, body: MPActionCreate, _: dict = Depends(require_auth)):
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
async def scan_contradictions(mp_id: str, current_user: Optional[dict] = Depends(get_current_user)):
    use_ai = current_user is not None and current_user.get("tier") in ("paid", "admin")
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


@router.post("/bills/{bill_id}/vote")
async def vote_bill(bill_id: str, body: BillVoteRequest, user: dict = Depends(require_auth)):
    return await vote_on_bill(bill_id, str(user["_id"]), body.support)


@router.get("/bills/{bill_id}/tally")
async def bill_tally(bill_id: str):
    return await get_bill_tally(bill_id)
