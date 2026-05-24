# app/services/political_service.py
"""Phase 3 — Political Intelligence (MongoDB version)."""

import json
import logging
from datetime import datetime
from typing import Optional

import httpx
from bson import ObjectId
from fastapi import HTTPException

from app.core.cache import cache_get, cache_set, SOURCE_TTL
from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

KNESSET_BASE = "https://knesset.gov.il/Odata/ParliamentInfo.svc"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


async def _knesset_get(path: str, params: dict = None) -> dict:
    url = f"{KNESSET_BASE}/{path}"
    if params is None:
        params = {}
    params["$format"] = "json"
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(url, params=params, headers=HEADERS)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning("Knesset API error %s: %s", path, e)
            return {"value": []}


# ── Sync ──────────────────────────────────────────────────────────────────────

async def sync_mps(limit: int = 120) -> int:
    db = get_db()
    data = await _knesset_get("KNS_PersonToPosition", {
        "$top": str(limit),
        "$filter": "KnessetNum eq 25",
        "$expand": "KNS_Person",
        "$orderby": "PersonID",
    })
    synced = 0
    for row in data.get("value", []):
        person = row.get("KNS_Person") or {}
        knesset_id = row.get("PersonID")
        if not knesset_id:
            continue
        name = f"{person.get('FirstName','')} {person.get('LastName','')}".strip() or f"MP-{knesset_id}"
        name_heb = f"{person.get('FirstNameHeb','')} {person.get('LastNameHeb','')}".strip()
        doc = {
            "knesset_id": knesset_id,
            "name": name,
            "name_hebrew": name_heb or None,
            "role": row.get("PositionName"),
            "is_active": True,
            "updated_at": datetime.utcnow(),
        }
        await db.mps.update_one({"knesset_id": knesset_id}, {"$set": doc}, upsert=True)
        synced += 1
    return synced


async def sync_parties() -> int:
    db = get_db()
    data = await _knesset_get("KNS_Faction", {"$filter": "KnessetNum eq 25", "$top": "30"})
    WING_MAP = {
        "likud": "right", "shas": "right", "utj": "right",
        "religious zionism": "right", "otzma": "right",
        "national unity": "center", "yesh atid": "center",
        "israel beiteinu": "center", "labor": "left",
        "meretz": "left", "hadash": "left",
    }
    synced = 0
    for row in data.get("value", []):
        name = row.get("Name", "")
        if not name:
            continue
        wing = next((v for k, v in WING_MAP.items() if k in name.lower()), "unknown")
        doc = {
            "name": name,
            "name_hebrew": row.get("NameHeb"),
            "seats": row.get("NumberOfSeats", 0),
            "wing": wing,
            "updated_at": datetime.utcnow(),
        }
        await db.parties.update_one({"name": name}, {"$set": doc}, upsert=True)
        synced += 1
    return synced


async def sync_committees(limit: int = 30) -> int:
    db = get_db()
    data = await _knesset_get("KNS_Committee", {"$filter": "KnessetNum eq 25", "$top": str(limit)})
    synced = 0
    for row in data.get("value", []):
        cid = row.get("CommitteeID")
        if not cid:
            continue
        doc = {
            "committee_id": cid,
            "name": row.get("Name", f"Committee-{cid}"),
            "name_hebrew": row.get("NameHeb"),
            "description": row.get("Description"),
            "updated_at": datetime.utcnow(),
        }
        await db.knesset_committees.update_one({"committee_id": cid}, {"$set": doc}, upsert=True)
        synced += 1
    return synced


# ── Queries ───────────────────────────────────────────────────────────────────

async def get_all_mps(party_name: Optional[str] = None) -> list[dict]:
    db = get_db()
    query = {"is_active": True}
    if party_name:
        query["party_name"] = party_name
    cursor = db.mps.find(query, {"_id": 0})
    return await cursor.to_list(length=200)


async def get_mp(mp_id: str) -> Optional[dict]:
    db = get_db()
    try:
        oid = ObjectId(mp_id)
    except Exception:
        return None
    mp = await db.mps.find_one({"_id": oid}, {"_id": 0})
    if mp:
        mp["id"] = mp_id
        mp["quotes"] = await (db.mp_quotes.find({"mp_id": mp_id}, {"_id": 0})).to_list(50)
        mp["actions"] = await (db.mp_actions.find({"mp_id": mp_id}, {"_id": 0})).to_list(50)
    return mp


async def get_all_parties() -> list[dict]:
    db = get_db()
    cursor = db.parties.find({}, {"_id": 0}).sort("seats", -1)
    return await cursor.to_list(length=50)


async def get_party(party_id: str) -> Optional[dict]:
    db = get_db()
    try:
        oid = ObjectId(party_id)
    except Exception:
        return None
    party = await db.parties.find_one({"_id": oid}, {"_id": 0})
    if party:
        party["id"] = party_id
        party["members"] = await (db.mps.find({"party_id": party_id}, {"_id": 0})).to_list(150)
    return party


async def get_committees() -> list[dict]:
    db = get_db()
    cursor = db.knesset_committees.find({}, {"_id": 0}).sort("name", 1)
    return await cursor.to_list(length=50)


# ── Quotes & Actions ──────────────────────────────────────────────────────────

async def add_quote(mp_id: str, data: dict) -> dict:
    db = get_db()
    doc = {"mp_id": mp_id, "created_at": datetime.utcnow(), **data}
    result = await db.mp_quotes.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    return doc


async def add_action(mp_id: str, data: dict) -> dict:
    db = get_db()
    doc = {"mp_id": mp_id, "created_at": datetime.utcnow(), **data}
    result = await db.mp_actions.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    return doc


async def get_mp_quotes(mp_id: str) -> list[dict]:
    db = get_db()
    cursor = db.mp_quotes.find({"mp_id": mp_id}, {"_id": 0}).sort("created_at", -1)
    return await cursor.to_list(100)


async def get_mp_actions(mp_id: str) -> list[dict]:
    db = get_db()
    cursor = db.mp_actions.find({"mp_id": mp_id}, {"_id": 0}).sort("created_at", -1)
    return await cursor.to_list(100)


# ── Contradiction Detection ───────────────────────────────────────────────────

_CONTRADICTION_PROMPT = """
You are a political fact-checker. Given an MP's quote and a later action, determine if there is a contradiction.
Quote: "{quote}"
Action: "{action}"
Topic: {topic}
Respond with JSON: {{"is_contradiction": true/false, "severity": "low"|"medium"|"high", "explanation": "...", "topic": "..."}}
Only respond with valid JSON.
"""


async def detect_contradiction(quote: dict, action: dict, use_ai: bool = False) -> Optional[dict]:
    if use_ai and settings.openai_api_key:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            prompt = _CONTRADICTION_PROMPT.format(
                quote=quote.get("quote", "")[:300],
                action=action.get("action", "")[:300],
                topic=quote.get("topic") or action.get("topic") or "general",
            )
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1, max_tokens=200,
                response_format={"type": "json_object"},
            )
            result = json.loads(resp.choices[0].message.content)
            if result.get("is_contradiction"):
                return result
        except Exception as e:
            logger.warning("Contradiction AI failed: %s", e)

    # Rule-based fallback
    OPPOSING = [
        ({"support","approve","yes","agree"}, {"oppose","reject","no","against"}),
        ({"increase","raise","expand"}, {"decrease","cut","reduce"}),
        ({"peace","negotiate"}, {"war","attack","military"}),
    ]
    q_text = quote.get("quote", "").lower()
    a_text = action.get("action", "").lower()
    for pos, neg in OPPOSING:
        if (any(w in q_text for w in pos) and any(w in a_text for w in neg)) or \
           (any(w in q_text for w in neg) and any(w in a_text for w in pos)):
            return {
                "is_contradiction": True, "severity": "medium",
                "explanation": "Quote and action appear to contradict each other.",
                "topic": quote.get("topic") or "general",
            }
    return None


async def run_contradiction_scan(mp_id: str, use_ai: bool = False) -> list[dict]:
    db = get_db()
    quotes = await get_mp_quotes(mp_id)
    actions = await get_mp_actions(mp_id)
    new_contradictions = []

    for quote in quotes:
        for action in actions:
            if quote.get("topic") and action.get("topic") and quote["topic"] != action["topic"]:
                continue
            result = await detect_contradiction(quote, action, use_ai=use_ai)
            if result:
                existing = await db.contradictions.find_one({
                    "mp_id": mp_id,
                    "quote_id": str(quote.get("id", "")),
                    "action_id": str(action.get("id", "")),
                })
                if not existing:
                    doc = {
                        "mp_id": mp_id,
                        "quote_id": str(quote.get("id", "")),
                        "action_id": str(action.get("id", "")),
                        "explanation": result["explanation"],
                        "severity": result.get("severity", "medium"),
                        "topic": result.get("topic"),
                        "detected_at": datetime.utcnow(),
                    }
                    await db.contradictions.insert_one(doc)
                    doc.pop("_id", None)
                    new_contradictions.append(doc)

    # Update consistency score
    total = len(quotes) * len(actions)
    if total > 0:
        score = max(0.0, 1.0 - len(new_contradictions) / total)
        await db.mps.update_one({"_id": ObjectId(mp_id)}, {"$set": {"consistency_score": round(score, 2)}})

    return new_contradictions


async def get_contradictions(mp_id: str) -> list[dict]:
    db = get_db()
    cursor = db.contradictions.find({"mp_id": mp_id}, {"_id": 0}).sort("detected_at", -1)
    return await cursor.to_list(100)


# ── Bill Voting ───────────────────────────────────────────────────────────────

async def vote_on_bill(bill_id: str, user_id: str, support: bool) -> dict:
    db = get_db()
    bill = await db.knesset_bills.find_one({"_id": ObjectId(bill_id)})
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    await db.bill_votes.update_one(
        {"bill_id": bill_id, "user_id": user_id},
        {"$set": {"support": support, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    return await get_bill_tally(bill_id)


async def get_bill_tally(bill_id: str) -> dict:
    db = get_db()
    total = await db.bill_votes.count_documents({"bill_id": bill_id})
    support = await db.bill_votes.count_documents({"bill_id": bill_id, "support": True})
    return {
        "bill_id": bill_id,
        "total_votes": total,
        "support": support,
        "oppose": total - support,
        "support_pct": round((support / total * 100) if total else 0, 1),
    }
