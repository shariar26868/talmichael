# app/services/political_service.py
"""Phase 3 — Political Intelligence (MongoDB version)."""

import json
import logging
import re
from datetime import datetime
from typing import Optional
from urllib.parse import quote

import httpx
from bson import ObjectId
from fastapi import HTTPException

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


async def _normalize_bill_row(row: dict) -> dict:
    if not row:
        return {}

    bill_id = row.get("BillID") or row.get("Id") or row.get("ID")
    if bill_id is None:
        return {}
    bill_id = str(bill_id)

    initiator_person = row.get("KNS_BillInitiatorMK") or {}
    if isinstance(initiator_person, dict):
        initiator_name = " ".join(
            p for p in [initiator_person.get("FirstName"), initiator_person.get("LastName")]
            if p
        ).strip() or initiator_person.get("FullName")
    else:
        initiator_name = None

    committee = row.get("CommitteeName")
    if not committee and isinstance(row.get("KNS_BillCommittee"), dict):
        committee = row["KNS_BillCommittee"].get("Name")

    return {
        "bill_id": bill_id,
        "name": row.get("Name") or row.get("Title") or "",
        "name_hebrew": row.get("NameHeb") or row.get("TitleHeb"),
        "status": row.get("StatusDesc") or (row.get("KNS_BillStatus") or {}).get("StatusDesc"),
        "type": row.get("TypeDesc") or (row.get("KNS_BillType") or {}).get("TypeDesc"),
        "sub_type": row.get("SubTypeDesc") or (row.get("KNS_BillSubType") or {}).get("SubTypeDesc"),
        "initiator": row.get("InitiatorMKName") or initiator_name or row.get("InitiatorName"),
        "initiator_party": row.get("InitiatorPartyName"),
        "committee": committee,
        "summary": row.get("BillSummary") or row.get("Purpose") or row.get("Summary") or row.get("Proposal") or "",
        "last_updated": row.get("LastUpdatedDate") or row.get("UpdatedDate") or row.get("ModifiedDate"),
        "source": "Knesset OData",
        "api_status": "official",
        "raw": row,
    }


async def _wikipedia_search_titles(query: str) -> list[str]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "format": "json",
                    "utf8": 1,
                    "srlimit": 3,
                },
                headers=HEADERS,
            )
            resp.raise_for_status()
            payload = resp.json()
        return [item.get("title") for item in payload.get("query", {}).get("search", []) if item.get("title")]
    except Exception as e:
        logger.warning("Wikipedia search failed for %s: %s", query, e)
        return []


async def _wikipedia_page_summary(title: str) -> Optional[dict]:
    try:
        encoded_title = quote(title, safe="")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=HEADERS)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("Wikipedia summary fetch failed for %s: %s", title, e)
        return None


def _clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


async def _fallback_bill_from_wikipedia(bill_id: str) -> Optional[dict]:
    if not bill_id:
        return None

    candidate_queries = [
        f"Knesset bill {bill_id}",
        f"Bill {bill_id} Knesset",
        f"Knesset law {bill_id}",
        f"Israeli bill {bill_id}",
    ]

    for query in candidate_queries:
        titles = await _wikipedia_search_titles(query)
        for title in titles:
            summary = await _wikipedia_page_summary(title)
            if summary and summary.get("extract"):
                return {
                    "bill_id": bill_id,
                    "name": summary.get("title") or f"Knesset Bill {bill_id}",
                    "name_hebrew": None,
                    "status": "fallback",
                    "type": "bill",
                    "sub_type": None,
                    "initiator": None,
                    "initiator_party": None,
                    "committee": None,
                    "summary": _clean_text(summary.get("extract")),
                    "last_updated": datetime.utcnow().isoformat(),
                    "source": "Wikipedia fallback",
                    "api_status": "fallback",
                    "raw": summary,
                }
    return None


async def _fallback_bill_from_news(bill_id: str) -> Optional[dict]:
    try:
        from app.services.news_service import fetch_news

        news = await fetch_news("knesset", 50, israeli_only=True, use_cache=False, with_analysis=False)
        match_text = bill_id.lower()
        for article in news.articles:
            text = f"{article.title or ''} {article.description or ''}".lower()
            if match_text in text or "knesset" in text and bill_id in article.link:
                return {
                    "bill_id": bill_id,
                    "name": article.title or f"Knesset bill {bill_id}",
                    "name_hebrew": None,
                    "status": "fallback",
                    "type": "bill",
                    "sub_type": None,
                    "initiator": None,
                    "initiator_party": None,
                    "committee": None,
                    "summary": _clean_text(article.description),
                    "last_updated": datetime.utcnow().isoformat(),
                    "source": "Google News RSS fallback",
                    "api_status": "fallback",
                    "raw": article.model_dump() if hasattr(article, "model_dump") else {},
                }
    except Exception as e:
        logger.warning("News fallback failed for bill %s: %s", bill_id, e)
    return None


async def _fallback_bill_from_web(bill_id: str) -> Optional[dict]:
    if not bill_id:
        return None

    fallback = await _fallback_bill_from_wikipedia(bill_id)
    if fallback:
        return fallback

    return await _fallback_bill_from_news(bill_id)


async def _resolve_bill_identifier(bill_id: str) -> Optional[dict]:
    db = get_db()
    if not bill_id:
        return None

    bill = None
    try:
        bill = await db.knesset_bills.find_one({"_id": ObjectId(bill_id)})
    except Exception:
        bill = None

    if not bill:
        bill = await db.knesset_bills.find_one({"bill_id": str(bill_id)})

    if bill:
        bill["id"] = str(bill["_id"])
    return bill


async def _fetch_bill_from_api(bill_id: str) -> Optional[dict]:
    if not bill_id:
        return None

    filter_value = bill_id if bill_id.isdigit() else f"'{bill_id}'"
    data = await _knesset_get(
        "KNS_Bill",
        {
            "$filter": f"BillID eq {filter_value}",
            "$expand": "KNS_BillStatus,KNS_BillType,KNS_BillSubType,KNS_BillInitiatorMK,KNS_BillCommittee",
            "$top": "1",
            "$orderby": "LastUpdatedDate desc",
        },
    )
    rows = data.get("value", [])
    if not rows:
        return await _fallback_bill_from_web(bill_id)

    return await _normalize_bill_row(rows[0])


def _normalize_vote_record(row: dict, bill_id: str) -> dict:
    person = row.get("KNS_Person") or {}
    if isinstance(person, dict):
        mp_name = " ".join(
            p for p in [person.get("FirstName"), person.get("LastName")] if p
        ).strip() or person.get("FullName")
        knesset_person_id = person.get("PersonID") or person.get("ID")
    else:
        mp_name = None
        knesset_person_id = None

    vote_value = (
        row.get("VoteResultDesc") or row.get("VoteDesc") or row.get("VoteTypeDesc") or
        row.get("Vote") or row.get("VoteName") or row.get("Result")
    )
    vote_date = row.get("VoteDate") or row.get("Date") or row.get("VotingDate")

    return {
        "bill_id": str(bill_id),
        "mp_id": None,
        "knesset_person_id": str(knesset_person_id) if knesset_person_id is not None else None,
        "mp_name": mp_name or row.get("MPName") or row.get("Name") or "Unknown",
        "party": (person or {}).get("PartyName") or row.get("PartyName") or row.get("FactionName"),
        "vote": str(vote_value).strip() if vote_value is not None else "unknown",
        "vote_date": vote_date,
        "source": "Knesset OData",
        "raw": row,
    }


def _normalize_vote_label(value: str) -> str:
    if not value:
        return "unknown"
    value = value.lower().strip()
    if "yes" in value or value in {"a", "for", "approve", "support", "aye"}:
        return "yes"
    if "no" in value or value in {"oppose", "against", "nay", "reject"}:
        return "no"
    if "abstain" in value or value in {"abstention", "abs"}:
        return "abstain"
    if "absent" in value or value in {"not present", "absent"}:
        return "absent"
    return value


async def sync_bills(limit: int = 50) -> int:
    db = get_db()
    data = await _knesset_get(
        "KNS_Bill",
        {
            "$filter": "KnessetNum eq 25",
            "$top": str(limit),
            "$orderby": "LastUpdatedDate desc",
            "$expand": "KNS_BillStatus,KNS_BillType,KNS_BillSubType,KNS_BillInitiatorMK,KNS_BillCommittee",
        },
    )
    bills = data.get("value", [])
    synced = 0
    for row in bills:
        bill = await _normalize_bill_row(row)
        if not bill:
            continue
        bill["updated_at"] = datetime.utcnow()
        await db.knesset_bills.update_one(
            {"bill_id": bill["bill_id"]},
            {"$set": bill},
            upsert=True,
        )
        synced += 1
    return synced


async def sync_bill_votes(bill_id: str) -> int:
    db = get_db()
    bill = await _resolve_bill_identifier(bill_id)
    if not bill:
        bill = await _fetch_bill_from_api(bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")
        await db.knesset_bills.update_one(
            {"bill_id": bill["bill_id"]},
            {"$set": bill},
            upsert=True,
        )
        bill = await _resolve_bill_identifier(bill["bill_id"])

    data = await _knesset_get(
        "KNS_BillVote",
        {
            "$filter": f"BillID eq {bill['bill_id']}",
            "$expand": "KNS_Person",
            "$top": "500",
        },
    )
    votes = data.get("value", [])
    if not votes:
        data = await _knesset_get(
            "KNS_Vote",
            {
                "$filter": f"BillID eq {bill['bill_id']}",
                "$expand": "KNS_Person",
                "$top": "500",
            },
        )
        votes = data.get("value", [])

    synced = 0
    for row in votes:
        record = _normalize_vote_record(row, bill["bill_id"])
        if record["knesset_person_id"]:
            mp = await db.mps.find_one({"knesset_id": int(record["knesset_person_id"])} if record["knesset_person_id"].isdigit() else {"knesset_id": record["knesset_person_id"]})
            if mp:
                record["mp_id"] = str(mp["_id"])
                record["mp_object_id"] = str(mp["_id"])
        if record["vote"]:
            record["vote"] = _normalize_vote_label(record["vote"])
        await db.bill_vote_records.update_one(
            {"bill_id": record["bill_id"], "knesset_person_id": record["knesset_person_id"], "mp_name": record["mp_name"]},
            {"$set": record},
            upsert=True,
        )
        synced += 1
    return synced


async def get_all_bills(limit: int = 50) -> list[dict]:
    db = get_db()
    cursor = db.knesset_bills.find({}, {"raw": 0}).sort("last_updated", -1).limit(limit)
    bills = await cursor.to_list(length=limit)
    for bill in bills:
        bill["id"] = str(bill["_id"])
        bill.pop("_id", None)
    return bills


async def get_bill_vote_summary(bill_id: str) -> dict:
    db = get_db()
    records = await db.bill_vote_records.find({"bill_id": str(bill_id)}, {"vote": 1}).to_list(length=1000)
    summary = {"total": len(records), "yes": 0, "no": 0, "abstain": 0, "absent": 0, "other": 0}
    for rec in records:
        label = _normalize_vote_label(rec.get("vote", ""))
        if label in summary:
            summary[label] += 1
        else:
            summary["other"] += 1
    return summary


async def get_bill(bill_id: str) -> Optional[dict]:
    db = get_db()
    bill = await _resolve_bill_identifier(bill_id)
    if not bill and bill_id.isdigit():
        bill = await _fetch_bill_from_api(bill_id)
        if bill:
            bill["updated_at"] = datetime.utcnow()
            result = await db.knesset_bills.update_one(
                {"bill_id": bill["bill_id"]},
                {"$set": bill},
                upsert=True,
            )
            if result.upserted_id:
                bill["id"] = str(result.upserted_id)
            else:
                stored = await db.knesset_bills.find_one({"bill_id": bill["bill_id"]})
                bill["id"] = str(stored["_id"])

    if not bill:
        return None

    analyze = False
    if bill.get("summary") and not bill.get("ai_summary"):
        analyze = True

    if analyze:
        from app.services.ai_service import analyze_article
        analysis = await analyze_article(
            guid=f"bill-{bill['bill_id']}",
            title=bill.get("name", ""),
            description=bill.get("summary", ""),
            source="Knesset Bill",
            user_tier="pro",
        )
        bill["ai_summary"] = analysis.summary_hebrew
        await db.knesset_bills.update_one({"_id": ObjectId(bill["id"])}, {"$set": {"ai_summary": bill["ai_summary"]}})

    bill["community_tally"] = await get_bill_tally(bill["id"])
    bill["official_vote_summary"] = await get_bill_vote_summary(bill["bill_id"])
    bill.pop("raw", None)
    bill.pop("_id", None)
    return bill


async def get_bill_vote_records(bill_id: str) -> list[dict]:
    bill = await _resolve_bill_identifier(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    db = get_db()
    cursor = db.bill_vote_records.find({"bill_id": bill["bill_id"]}, {"_id": 0, "raw": 0}).sort("vote_date", -1)
    records = await cursor.to_list(length=1000)
    for record in records:
        record["bill_name"] = bill.get("name")
    return records


async def get_mp_vote_records(mp_id: str) -> list[dict]:
    db = get_db()
    query = {"$or": [{"mp_id": mp_id}, {"knesset_person_id": mp_id}, {"mp_object_id": mp_id}]}
    if ObjectId.is_valid(mp_id):
        mp = await db.mps.find_one({"_id": ObjectId(mp_id)})
        if mp and mp.get("knesset_id"):
            query["$or"].append({"knesset_person_id": str(mp["knesset_id"])})
    cursor = db.bill_vote_records.find(query, {"_id": 0, "raw": 0}).sort("vote_date", -1)
    return await cursor.to_list(1000)
