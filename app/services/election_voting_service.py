# app/services/election_voting_service.py
"""
Election Community Voting Service.
Handles user votes for favorite party and favorite candidate in the 2026 election.
Also provides election news feed and timeline.
"""

import logging
import re
from datetime import datetime
from typing import Optional

from app.core.database import get_db
from app.services.election_service import ELECTION_2026_PARTIES, ELECTION_2026_OVERVIEW
from app.services.news_service import fetch_news

logger = logging.getLogger(__name__)

# ── Election Timeline (verified from bechirot.gov.il) ────────────────────────
ELECTION_2026_TIMELINE = [
    {
        "date": "2026-08-15",
        "event": "Party Registration Deadline",
        "description": "Final day for political parties to submit their registration and party lists to the Central Elections Committee.",
        "authority": "Central Elections Committee (ועדת הבחירות המרכזית)",
        "official_link": "https://www.bechirot.gov.il/",
        "status": "upcoming",
    },
    {
        "date": "2026-09-01",
        "event": "Official Campaign Launch",
        "description": "Televised election broadcasts begin across all major networks. Campaign spending officially begins.",
        "authority": "Central Elections Committee",
        "official_link": "https://www.bechirot.gov.il/",
        "status": "upcoming",
    },
    {
        "date": "2026-10-25",
        "event": "Campaign Silence Period Begins",
        "description": "48 hours before the election, all campaign advertising and public polling are prohibited.",
        "authority": "Central Elections Committee",
        "official_link": "https://www.bechirot.gov.il/",
        "status": "upcoming",
    },
    {
        "date": "2026-10-27",
        "event": "Election Day",
        "description": "National holiday. Polling stations open from 7:00 AM to 10:00 PM. All Israeli citizens 18+ may vote.",
        "authority": "Central Elections Committee",
        "official_link": "https://www.bechirot.gov.il/",
        "status": "upcoming",
    },
    {
        "date": "2026-10-28",
        "event": "Official Results",
        "description": "Preliminary results announced overnight. Official certified results within 3–5 days.",
        "authority": "Central Elections Committee",
        "official_link": "https://www.bechirot.gov.il/",
        "status": "upcoming",
    },
]


async def vote_for_party(party_name: str, user_id: str) -> dict:
    """Record a user's community vote for their favorite party in the 2026 election."""
    db = get_db()

    # Validate party exists in 2026 election list
    valid_parties = {p["name"] for p in ELECTION_2026_PARTIES}
    if party_name not in valid_parties:
        return {"error": f"Party '{party_name}' not found in 2026 election list.", "valid_parties": list(valid_parties)}

    # Upsert: one vote per user per election
    await db.election_party_votes.update_one(
        {"user_id": user_id, "election_year": 2026},
        {"$set": {
            "party_name": party_name,
            "election_year": 2026,
            "updated_at": datetime.utcnow(),
        }},
        upsert=True,
    )

    tally = await get_party_poll()
    return {
        "status": "recorded",
        "party": party_name,
        "user_id": user_id,
        "recorded_at": datetime.utcnow().isoformat() + "Z",
        "current_tally": tally,
    }


async def vote_for_candidate(candidate_name: str, party_name: str, user_id: str) -> dict:
    """Record a user's community vote for their favorite candidate in the 2026 election."""
    db = get_db()

    # Validate candidate name is non-empty
    if not candidate_name or not candidate_name.strip():
        return {"error": "Candidate name is required."}

    # Upsert: one candidate vote per user per election
    await db.election_candidate_votes.update_one(
        {"user_id": user_id, "election_year": 2026},
        {"$set": {
            "candidate_name": candidate_name.strip(),
            "party_name": party_name,
            "election_year": 2026,
            "updated_at": datetime.utcnow(),
        }},
        upsert=True,
    )

    tally = await get_candidate_poll()
    return {
        "status": "recorded",
        "candidate": candidate_name,
        "party": party_name,
        "user_id": user_id,
        "recorded_at": datetime.utcnow().isoformat() + "Z",
        "current_tally": tally,
    }


async def get_party_poll() -> dict:
    """Return real-time community poll results for parties (2026 election)."""
    db = get_db()

    total = await db.election_party_votes.count_documents({"election_year": 2026})

    pipeline = [
        {"$match": {"election_year": 2026}},
        {"$group": {"_id": "$party_name", "votes": {"$sum": 1}}},
        {"$sort": {"votes": -1}},
    ]
    results = await db.election_party_votes.aggregate(pipeline).to_list(50)

    party_results = []
    for r in results:
        party_name = r["_id"]
        votes = r["votes"]
        pct = round((votes / total * 100) if total > 0 else 0, 1)

        # Find party info from election data
        party_info = next((p for p in ELECTION_2026_PARTIES if p["name"] == party_name), {})
        party_results.append({
            "party": party_name,
            "name_hebrew": party_info.get("name_hebrew"),
            "leader": party_info.get("leader"),
            "bloc": party_info.get("bloc"),
            "wing": party_info.get("wing"),
            "votes": votes,
            "pct": pct,
            "poll_seats_range": party_info.get("poll_seats_range"),
        })

    return {
        "election_year": 2026,
        "total_votes": total,
        "results": party_results,
        "note": "This is a community preference poll — not an official election poll.",
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


async def get_candidate_poll() -> dict:
    """Return real-time community poll results for candidates (2026 election)."""
    db = get_db()

    total = await db.election_candidate_votes.count_documents({"election_year": 2026})

    pipeline = [
        {"$match": {"election_year": 2026}},
        {"$group": {
            "_id": {"candidate": "$candidate_name", "party": "$party_name"},
            "votes": {"$sum": 1},
        }},
        {"$sort": {"votes": -1}},
    ]
    results = await db.election_candidate_votes.aggregate(pipeline).to_list(100)

    candidate_results = []
    for r in results:
        candidate_name = r["_id"]["candidate"]
        party_name = r["_id"].get("party", "")
        votes = r["votes"]
        pct = round((votes / total * 100) if total > 0 else 0, 1)
        candidate_results.append({
            "candidate": candidate_name,
            "party": party_name,
            "votes": votes,
            "pct": pct,
        })

    return {
        "election_year": 2026,
        "total_votes": total,
        "results": candidate_results,
        "note": "This is a community preference poll — not an official election poll.",
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


async def get_election_timeline() -> dict:
    """Return the 2026 election timeline with key milestones."""
    now = datetime.utcnow().date()
    timeline = []
    for event in ELECTION_2026_TIMELINE:
        event_date_str = event.get("date", "")
        try:
            event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
            status = "past" if event_date < now else "upcoming"
        except ValueError:
            status = "upcoming"
        timeline.append({**event, "status": status})

    return {
        "election_year": 2026,
        "scheduled_date": ELECTION_2026_OVERVIEW.get("scheduled_date"),
        "official_authority": ELECTION_2026_OVERVIEW.get("official_authority"),
        "official_source": ELECTION_2026_OVERVIEW.get("official_source"),
        "timeline": timeline,
        "data_freshness": "2026-06-15",
        "source": "bechirot.gov.il + Wikipedia — not AI-generated",
    }


async def get_election_news(category: Optional[str] = None, limit: int = 20) -> dict:
    """
    Return real election-related news articles.
    Prefers live news feeds and falls back to cached articles if no live results are available.
    """
    db = get_db()

    election_keywords = [
        "election", "vote", "poll", "ballot", "campaign", "candidate",
        "Knesset 2026", "coalition", "opposition", "legislation",
        "בחירות", "בחירות 2026", "סקר", "מפלגה", "כנסת",
        "Bennett", "Netanyahu", "Lapid", "Gantz", "Lieberman",
        "Eisenkot", "Smotrich", "Ben-Gvir", "Saar", "Deri",
    ]
    keyword_regex = "|".join(re.escape(k) for k in election_keywords)

    def _to_payload(article) -> dict:
        if hasattr(article, "model_dump"):
            payload = article.model_dump(exclude_none=True)
        elif isinstance(article, dict):
            payload = dict(article)
        else:
            payload = {}
        title = payload.get("title") or ""
        description = payload.get("description") or ""
        if not re.search(keyword_regex, f"{title} {description}", flags=re.IGNORECASE):
            return {}
        payload.setdefault("id", payload.get("guid") or payload.get("link") or payload.get("title"))
        payload.setdefault("source", payload.get("source") or "unknown")
        return payload

    articles: list[dict] = []
    try:
        live_news = await fetch_news("politics", max(limit * 2, 12), language="english")
        for article in getattr(live_news, "articles", []) or []:
            payload = _to_payload(article)
            if payload:
                articles.append(payload)
    except Exception as exc:
        logger.warning("Election news live fetch failed: %s", exc)

    if not articles:
        try:
            live_news = await fetch_news("knesset", max(limit * 2, 12), language="english")
            for article in getattr(live_news, "articles", []) or []:
                payload = _to_payload(article)
                if payload:
                    articles.append(payload)
        except Exception as exc:
            logger.warning("Election news knesset feed fallback failed: %s", exc)

    if not articles:
        query = {
            "$or": [
                {"title": {"$regex": keyword_regex, "$options": "i"}},
                {"description": {"$regex": keyword_regex, "$options": "i"}},
            ]
        }
        if category:
            query["category"] = category
        cached_articles = await db.cached_articles.find(
            query,
            {
                "_id": 1, "guid": 1, "title": 1, "description": 1,
                "source": 1, "source_type": 1, "link": 1, "image_url": 1,
                "pub_date": 1, "first_seen": 1, "sentiment": 1, "bias": 1, "category": 1,
            }
        ).sort("pub_date", -1).limit(limit).to_list(limit)
        for article in cached_articles:
            article["id"] = str(article.pop("_id"))
            articles.append(article)

    seen_urls = set()
    deduped: list[dict] = []
    for article in articles:
        link = article.get("link") or article.get("guid") or article.get("url")
        if not link or link in seen_urls:
            continue
        seen_urls.add(link)
        deduped.append(article)

    deduped = deduped[:limit]

    return {
        "total": len(deduped),
        "election_year": 2026,
        "category_filter": category,
        "articles": deduped,
        "note": "Election articles are now sourced from live news feeds first, with cached articles as fallback.",
        "source": "live_news_feeds",
    }


async def get_election_candidates_list() -> dict:
    """
    Return all announced candidates for the 2026 election (all parties).
    Pulls from MP database + election party data.
    Used for the candidate voting poll UI.
    """
    db = get_db()

    # Get all active MPs (they are the potential candidates)
    all_mps = await db.mps.find(
        {"is_active": True},
        {"_id": 1, "knesset_id": 1, "name": 1, "name_hebrew": 1, "party_name": 1, "photo_url": 1, "role": 1}
    ).sort("name", 1).to_list(200)

    candidates = []
    for mp in all_mps:
        mp_id = str(mp.get("_id"))
        knesset_id = mp.get("knesset_id")
        photo_url = mp.get("photo_url")
        if not photo_url and knesset_id:
            photo_url = f"https://knesset.gov.il/mk/images/members/{knesset_id}.jpg"
        if not photo_url:
            photo_url = "https://oknesset.org/static/img/Male_portrait_placeholder_cropped.jpg"
        party_info = next(
            (p for p in ELECTION_2026_PARTIES if p["name"] == mp.get("party_name")), {}
        )
        candidates.append({
            "id": mp_id,
            "type": "candidate",
            "name": mp.get("name"),
            "name_hebrew": mp.get("name_hebrew"),
            "party": mp.get("party_name"),
            "photo_url": photo_url,
            "role": mp.get("role"),
            "bloc": party_info.get("bloc", "opposition"),
        })

    # Sort: coalition first, then opposition, then arab
    bloc_order = {"coalition": 0, "opposition": 1, "arab_parties": 2}
    candidates.sort(key=lambda c: (bloc_order.get(c.get("bloc", "opposition"), 1), c.get("name") or ""))

    return {
        "total": len(candidates),
        "candidates": candidates,
        "note": "Candidate list sourced from Open Knesset active MP registry.",
        "data_freshness": "2026-06-15",
    }


async def get_election_participants() -> dict:
    """
    Return a unified list of parties and candidates for the 2026 election.
    Each item has a distinct id and a type field: party or candidate.
    """
    db = get_db()

    known_parties = {}
    for party in ELECTION_2026_PARTIES:
        name = party.get("name")
        if name:
            known_parties[name] = party

    party_docs = await db.parties.find(
        {},
        {"_id": 0, "name": 1, "name_hebrew": 1, "leader": 1, "website": 1, "official_website": 1, "wikipedia_url": 1, "wing": 1, "bloc": 1}
    ).to_list(200)
    for party_doc in party_docs:
        name = party_doc.get("name")
        if name and name not in known_parties:
            known_parties[name] = {
                "name": name,
                "name_hebrew": party_doc.get("name_hebrew"),
                "leader": party_doc.get("leader"),
                "website": party_doc.get("website"),
                "official_website": party_doc.get("official_website"),
                "wikipedia_url": party_doc.get("wikipedia_url"),
                "wing": party_doc.get("wing"),
                "bloc": party_doc.get("bloc"),
            }

    all_mps = await db.mps.find(
        {"is_active": True},
        {"_id": 1, "knesset_id": 1, "name": 1, "name_hebrew": 1, "party_name": 1, "photo_url": 1, "role": 1}
    ).sort("name", 1).to_list(200)
    for mp in all_mps:
        party_name = mp.get("party_name")
        if party_name and party_name not in known_parties:
            known_parties[party_name] = {
                "name": party_name,
                "name_hebrew": None,
                "leader": None,
                "website": None,
                "official_website": None,
                "wikipedia_url": None,
                "wing": None,
                "bloc": None,
            }

    parties = []
    for index, (party_name, party) in enumerate(known_parties.items()):
        official_website = party.get("official_website") or party.get("website") or party.get("official_link")
        parties.append({
            "id": f"party_{index + 1}",
            "type": "party",
            "name": party.get("name") or party_name,
            "name_hebrew": party.get("name_hebrew"),
            "leader": party.get("leader"),
            "bloc": party.get("bloc"),
            "wing": party.get("wing"),
            "poll_seats_range": party.get("poll_seats_range"),
            "official_link": official_website,
            "official_website": official_website,
            "website": official_website,
            "wikipedia_url": party.get("wikipedia_url"),
        })

    parties.sort(key=lambda item: (item.get("bloc") or "", item.get("name") or ""))

    # Build candidate entries

    candidates = []
    for mp in all_mps:
        mp_id = str(mp.get("_id"))
        knesset_id = mp.get("knesset_id")
        photo_url = mp.get("photo_url")
        if not photo_url and knesset_id:
            photo_url = f"https://knesset.gov.il/mk/images/members/{knesset_id}.jpg"
        if not photo_url:
            photo_url = "https://oknesset.org/static/img/Male_portrait_placeholder_cropped.jpg"
        party_info = next(
            (p for p in ELECTION_2026_PARTIES if p["name"] == mp.get("party_name")), {}
        )
        candidates.append({
            "id": f"candidate_{mp_id}",
            "type": "candidate",
            "name": mp.get("name"),
            "name_hebrew": mp.get("name_hebrew"),
            "party": mp.get("party_name"),
            "photo_url": photo_url,
            "role": mp.get("role"),
            "bloc": party_info.get("bloc", "opposition"),
        })

    participants = parties + candidates

    return {
        "total": len(participants),
        "participants": participants,
        "party_count": len(parties),
        "candidate_count": len(candidates),
        "note": "Combined list of all parties and active candidates for the 2026 election.",
        "data_freshness": "2026-06-15",
    }
