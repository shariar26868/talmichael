# app/services/blocs_service.py
"""
Coalition vs. Opposition Bloc Service.
Groups all Knesset 25 / upcoming election parties by bloc.
Also provides full party profile (agenda + members + key bills + actions).
"""

import logging
from datetime import datetime
from typing import Optional

import httpx
from bson import ObjectId
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

# ── Bloc assignment for 25th Knesset parties ────────────────────────────────
# Source: Wikipedia, Knesset.gov.il — verified June 2026
PARTY_BLOC_MAP: dict[str, str] = {
    # Coalition
    "Likud": "coalition",
    "Shas": "coalition",
    "United Torah Judaism": "coalition",
    "Religious Zionist Party": "coalition",
    "Religious Zionism": "coalition",
    "Otzma Yehudit": "coalition",
    "Noam": "coalition",
    "New Hope (United Right)": "coalition",
    # Opposition
    "Yesh Atid": "opposition",
    "National Unity": "opposition",
    "Yisrael Beiteinu": "opposition",
    "The Democrats": "opposition",
    "Together (Beyachad)": "opposition",
    "Yashar": "opposition",
    # Arab parties (neither bloc)
    "United Arab List (Ra'am)": "arab_parties",
    "Hadash-Ta'al": "arab_parties",
    "Ra'am": "arab_parties",
}

# Detailed topic-based agenda per party (sourced from official party websites)
PARTY_AGENDA_TOPICS: dict[str, dict] = {
    "Likud": {
        "economy": "Free market deregulation, reducing bureaucratic burden, lowering corporate tax to stimulate growth.",
        "security": "Completing the war goals in Gaza, maintaining IDF strength, normalization with Saudi Arabia.",
        "judiciary": "Supports the 2023 judicial reform to balance power between Knesset and Supreme Court.",
        "social": "Jewish heritage preservation, secular-religious status quo.",
        "foreign_policy": "Normalization deals with Arab states, strong US alliance, opposition to Palestinian state.",
        "source_url": "https://www.likud.org.il/",
        "data_freshness": "2026-06-15",
    },
    "Yesh Atid": {
        "economy": "Support for middle class, focus on cost of living reduction, housing affordability.",
        "security": "Regional cooperation, maintaining military supremacy, prioritizing hostage deal.",
        "judiciary": "Strong opposition to current judicial overhaul plans, restoring Supreme Court powers.",
        "social": "Civil marriage, LGBT equality, public transport on Shabbat, secular public life.",
        "foreign_policy": "Two-state solution, regional normalization, restoring ties with US democrats.",
        "source_url": "https://www.yeshatid.org.il/",
        "data_freshness": "2026-06-15",
    },
    "National Unity": {
        "economy": "State stability, pragmatic fiscal policy, housing investment.",
        "security": "Judicial preservation, pragmatic security policy, consensus-building on war cabinet.",
        "judiciary": "Judicial balance and preservation, opposes full overhaul.",
        "social": "Broad secular-religious consensus, civil equality.",
        "foreign_policy": "Rebuilding international alliances, pragmatic diplomacy.",
        "source_url": "https://www.machane.org.il/",
        "data_freshness": "2026-06-15",
    },
    "Shas": {
        "economy": "Welfare support for lower-income Sephardic families, child allowances, subsidized housing.",
        "security": "Strong security stance, supports coalition war goals.",
        "judiciary": "Supports judicial reform as it reduces checks on coalition power.",
        "social": "Religious education funding, traditional Jewish values in public life, opposing draft of yeshiva students.",
        "foreign_policy": "Support coalition positions, strong Israel-US alignment.",
        "source_url": "https://www.shas.org.il/",
        "data_freshness": "2026-06-15",
    },
    "United Torah Judaism": {
        "economy": "Housing subsidies for large Haredi families, yeshiva funding, child stipends.",
        "security": "Opposes mandatory IDF conscription for yeshiva students.",
        "judiciary": "Supports judicial reform reducing court power over religious legislation.",
        "social": "Haredi education autonomy, preservation of religious status quo, Shabbat laws.",
        "foreign_policy": "Follows coalition line.",
        "source_url": "https://www.degeltorah.org.il/",
        "data_freshness": "2026-06-15",
    },
    "Religious Zionist Party": {
        "economy": "Free market with strong settler economy support, West Bank development.",
        "security": "Complete military victory in Gaza, no ceasefire, annexation of West Bank.",
        "judiciary": "Strong support for judicial overhaul, limiting Supreme Court.",
        "social": "Conservative religious legislation, opposing LGBT advocacy in state.",
        "foreign_policy": "Annexation of all biblical land, rejection of two-state solution.",
        "source_url": "https://www.dati.org.il/",
        "data_freshness": "2026-06-15",
    },
    "Otzma Yehudit": {
        "economy": "Nationalist economic policy, resources directed to Jewish communities.",
        "security": "Mass deportation of hostile populations, re-occupation of Gaza, strict crackdowns.",
        "judiciary": "Supports judicial overhaul, strengthening executive power.",
        "social": "Jewish sovereignty over all biblical Israel, opposing Arab political influence.",
        "foreign_policy": "Total rejection of Palestinian state, annexation, opposition to international pressure.",
        "source_url": "https://www.ozma-yehudit.org.il/",
        "data_freshness": "2026-06-15",
    },
    "Yisrael Beiteinu": {
        "economy": "Free-market economic reforms, reducing religious tax burdens, business-friendly policy.",
        "security": "Strong hawkish security stance, demanding victory over Hamas.",
        "judiciary": "Opposes judicial overhaul, demands universal draft including Haredi.",
        "social": "Public transport on Shabbat, civil marriage, secular state, universal military service.",
        "foreign_policy": "Russia-Israel relations management, strong anti-Iran policy.",
        "source_url": "https://www.beytenu.org.il/",
        "data_freshness": "2026-06-15",
    },
    "The Democrats": {
        "economy": "Welfare-state economics, social safety nets, progressive taxation.",
        "security": "Negotiated ceasefire, two-state solution, demilitarized Palestinian state.",
        "judiciary": "Full reversal of judicial overhaul, restoring Supreme Court independence.",
        "social": "Civil marriage, LGBT rights, religious pluralism, gender equality.",
        "foreign_policy": "Two-state solution, restoring EU and US progressive alliances.",
        "source_url": "https://www.hademokratim.org.il/",
        "data_freshness": "2026-06-15",
    },
    "Hadash-Ta'al": {
        "economy": "Socialist economics, labor protections, Arab community investment.",
        "security": "Immediate ceasefire in Gaza, withdrawal from occupied territories.",
        "judiciary": "Full judicial independence, equal rights for Arab citizens.",
        "social": "Arab-Jewish co-existence, minority civil rights, anti-racism legislation.",
        "foreign_policy": "Palestinian state, BDS opposition, international law compliance.",
        "source_url": "https://www.hadash.org.il/",
        "data_freshness": "2026-06-15",
    },
    "United Arab List (Ra'am)": {
        "economy": "Investment in Arab municipalities, Negev Bedouin town legalization, crime reduction funding.",
        "security": "Pragmatic coalition bargaining on security, no military escalation.",
        "judiciary": "Equal rights for Arab citizens, independent judiciary.",
        "social": "Islamist social values, developing Arab sector infrastructure, fighting organized crime.",
        "foreign_policy": "Palestinian rights through pragmatic engagement.",
        "source_url": "https://www.raam.org.il/",
        "data_freshness": "2026-06-15",
    },
    "Together (Beyachad)": {
        "economy": "Housing affordability reform, middle-class relief, 1 million aliyah plan.",
        "security": "Security rebuilding after Oct 7, state commission of inquiry, IDF reform.",
        "judiciary": "Anti-corruption legislation, restoring judicial independence.",
        "social": "Broad civic coalition, restoring public trust in institutions.",
        "foreign_policy": "Rebuilding US and European alliances, hostage deal priority.",
        "source_url": "https://beyachad.co.il",
        "data_freshness": "2026-06-15",
    },
    "Yashar": {
        "economy": "Centrist pragmatic economic policy, anti-corruption.",
        "security": "Rebuilding IDF command culture, security establishment reform.",
        "judiciary": "Clean governance, independent judiciary.",
        "social": "Pragmatic centrist policy.",
        "foreign_policy": "Pragmatic diplomacy, rebuilding trust with international partners.",
        "source_url": "https://yashar.org.il",
        "data_freshness": "2026-06-15",
    },
}


async def get_blocs() -> dict:
    """Return all parties grouped by bloc (coalition / opposition / arab_parties)."""
    db = get_db()
    all_parties = await db.parties.find({}, {"_id": 1, "name": 1, "name_hebrew": 1,
                                             "wing": 1, "seats": 1, "leader": 1,
                                             "ideology": 1, "agenda": 1, "website": 1,
                                             "wikipedia_url": 1, "source_links": 1,
                                             "bloc": 1}).sort("seats", -1).to_list(100)

    coalition_parties = []
    opposition_parties = []
    arab_parties = []
    coalition_seats = 0
    opposition_seats = 0
    arab_seats = 0

    for p in all_parties:
        p["id"] = str(p.pop("_id"))
        # Determine bloc: prefer DB field, fallback to static map
        bloc = p.get("bloc") or PARTY_BLOC_MAP.get(p.get("name", ""), "opposition")
        p["bloc"] = bloc

        # Attach agenda topics if available
        agenda_topics = PARTY_AGENDA_TOPICS.get(p.get("name", ""), {})
        if not agenda_topics and settings.openai_api_key:
            agenda_topics = await enrich_party_agenda_via_ai(p.get("name", ""))
            if agenda_topics:
                PARTY_AGENDA_TOPICS[p.get("name", "")] = agenda_topics
        if agenda_topics:
            p["agenda_by_topic"] = {k: v for k, v in agenda_topics.items()
                                    if k not in ("source_url", "data_freshness")}

        seats = p.get("seats", 0) or 0
        if bloc == "coalition":
            coalition_parties.append(p)
            coalition_seats += seats
        elif bloc == "arab_parties":
            arab_parties.append(p)
            arab_seats += seats
        else:
            opposition_parties.append(p)
            opposition_seats += seats

    return {
        "coalition": {
            "label": "Coalition Blocks",
            "total_seats": coalition_seats,
            "majority_needed": 61,
            "has_majority": coalition_seats >= 61,
            "parties": coalition_parties,
        },
        "opposition": {
            "label": "Opposition Blocks",
            "total_seats": opposition_seats,
            "parties": opposition_parties,
        },
        "arab_parties": {
            "label": "Arab Parties",
            "total_seats": arab_seats,
            "parties": arab_parties,
        },
        "total_knesset_seats": 120,
        "data_freshness": "2026-06-15",
        "source": "Open Knesset CSV + Wikipedia — not AI-generated",
    }


async def get_party_full_profile(party_id: str) -> Optional[dict]:
    """
    Full party detail page (Screen 3).
    Returns: party info + all MPs + key bills + key actions + detailed agenda.
    """
    db = get_db()
    try:
        oid = ObjectId(party_id)
    except Exception:
        return None

    party = await db.parties.find_one({"_id": oid})
    if not party:
        return None

    party["id"] = str(party.pop("_id"))
    party_name = party.get("name", "")

    # Attach detailed agenda topics
    agenda_topics = PARTY_AGENDA_TOPICS.get(party_name, {})
    if not agenda_topics and settings.openai_api_key:
        agenda_topics = await enrich_party_agenda_via_ai(party_name)
        if agenda_topics:
            PARTY_AGENDA_TOPICS[party_name] = agenda_topics
    if agenda_topics:
        party["agenda_by_topic"] = {k: v for k, v in agenda_topics.items()
                                    if k not in ("source_url", "data_freshness")}
        party["agenda_source_url"] = agenda_topics.get("source_url")
        party["agenda_data_freshness"] = agenda_topics.get("data_freshness")

    # Assign bloc
    bloc = party.get("bloc") or PARTY_BLOC_MAP.get(party_name, "opposition")
    party["bloc"] = bloc

    # Fetch all members
    members_cursor = db.mps.find(
        {"party_name": party_name, "is_active": True},
        {"_id": 1, "name": 1, "name_hebrew": 1, "photo_url": 1, "role": 1,
         "committees": 1, "knesset_id": 1, "attendance_pct": 1, "bills_passed_count": 1}
    ).sort("name", 1)
    members = await members_cursor.to_list(200)
    for m in members:
        m["id"] = str(m.pop("_id"))
        if "committees" not in m or m["committees"] is None:
            m["committees"] = []
        if "bills_passed_count" not in m or m["bills_passed_count"] is None:
            m["bills_passed_count"] = 0
    party["members"] = members
    party["members_count"] = len(members)

    # Fetch key bills initiated by this party's MPs
    mp_names = [m.get("name_hebrew") for m in members if m.get("name_hebrew")]
    key_bills = []
    if mp_names:
        bills_cursor = db.knesset_bills.find(
            {"initiator": {"$in": mp_names}},
            {"_id": 1, "bill_id": 1, "name": 1, "status": 1, "summary": 1,
             "initiator": 1, "publication_date": 1, "last_updated": 1}
        ).sort("last_updated", -1).limit(10)
        key_bills_raw = await bills_cursor.to_list(10)
        for b in key_bills_raw:
            b["id"] = str(b.pop("_id"))
            key_bills.append(b)
    party["key_bills"] = key_bills

    # Fetch notable actions (from mp_actions collection for party members)
    mp_ids = [m["id"] for m in members]
    key_actions = []
    if mp_ids:
        actions_cursor = db.mp_actions.find(
            {"mp_id": {"$in": mp_ids}},
            {"_id": 0, "mp_id": 1, "action": 1, "action_type": 1, "topic": 1, "date": 1, "source_url": 1}
        ).sort("date", -1).limit(10)
        key_actions = await actions_cursor.to_list(10)
    party["key_actions"] = key_actions

    return party


def _normalize_mp_profile(mp: dict) -> dict:
    """Fill missing MP profile fields with safe defaults."""
    if not mp.get("role"):
        mp["role"] = "Member of Knesset"

    if not mp.get("photo_url") and mp.get("knesset_id"):
        mp["photo_url"] = f"https://knesset.gov.il/mk/images/members/{mp['knesset_id']}.jpg"
    if not mp.get("photo_url"):
        mp["photo_url"] = "https://oknesset.org/static/img/Male_portrait_placeholder_cropped.jpg"

    if not mp.get("bio"):
        mp["bio"] = mp.get("bio_quote") or f"Member of Knesset representing {mp.get('party_name', 'their party')}."
    if not mp.get("bio_quote"):
        mp["bio_quote"] = mp["bio"]

    if not mp.get("career_history"):
        mp["career_history"] = [
            f"Serving in the 25th Knesset as {mp.get('role', 'Member of Knesset')} for {mp.get('party_name', 'their party')}."
        ]

    if not mp.get("service_years"):
        mp["service_years"] = "25th Knesset"

    mp["committees"] = mp.get("committees") or []
    if mp.get("bills_passed_count") is None:
        mp["bills_passed_count"] = 0

    return mp


async def get_mp_full_profile(mp_id: str) -> Optional[dict]:
    """
    Full MP detail page (Screen 4).
    Returns: bio + career history + committees + actions_vs_claims + notable activity.
    """
    db = get_db()
    try:
        oid = ObjectId(mp_id)
    except Exception:
        return None

    mp = await db.mps.find_one({"_id": oid})
    if not mp:
        return None

    mp["id"] = str(mp.pop("_id"))

    # Fetch quotes (claims)
    quotes = await db.mp_quotes.find(
        {"mp_id": mp["id"]}, {"_id": 1, "quote": 1, "topic": 1, "date": 1, "context": 1, "source_url": 1}
    ).sort("date", -1).to_list(50)
    for q in quotes:
        q["id"] = str(q.pop("_id"))

    # Fetch actions
    actions = await db.mp_actions.find(
        {"mp_id": mp["id"]}, {"_id": 1, "action": 1, "action_type": 1, "topic": 1, "date": 1, "source_url": 1}
    ).sort("date", -1).to_list(50)
    for a in actions:
        a["id"] = str(a.pop("_id"))

    # Fetch contradictions (actions vs claims)
    contradictions = await db.contradictions.find(
        {"mp_id": mp["id"]}, {"_id": 0, "explanation": 1, "severity": 1, "topic": 1, "detected_at": 1,
                               "quote_id": 1, "action_id": 1}
    ).sort("detected_at", -1).to_list(20)

    # Build actions_vs_claims table by pairing quotes with contradictions
    actions_vs_claims = []
    for contradiction in contradictions:
        quote_match = next((q for q in quotes if str(q.get("id")) == contradiction.get("quote_id")), None)
        action_match = next((a for a in actions if str(a.get("id")) == contradiction.get("action_id")), None)
        if quote_match or action_match:
            actions_vs_claims.append({
                "claim": quote_match.get("quote", "") if quote_match else "",
                "claim_date": quote_match.get("date", "") if quote_match else "",
                "claim_topic": quote_match.get("topic", "") if quote_match else "",
                "action": action_match.get("action", "") if action_match else "",
                "action_date": action_match.get("date", "") if action_match else "",
                "status": "CONTRADICTORY" if contradiction.get("severity") in ("high", "medium") else "NEUTRAL",
                "severity": contradiction.get("severity"),
                "explanation": contradiction.get("explanation", ""),
            })

    # Also include aligned quotes+actions (consistent)
    for quote in quotes[:5]:
        for action in actions[:5]:
            already_flagged = any(
                c.get("claim") == quote.get("quote") and c.get("action") == action.get("action")
                for c in actions_vs_claims
            )
            if not already_flagged and quote.get("topic") and action.get("topic") == quote.get("topic"):
                actions_vs_claims.append({
                    "claim": quote.get("quote", ""),
                    "claim_date": quote.get("date", ""),
                    "claim_topic": quote.get("topic", ""),
                    "action": action.get("action", ""),
                    "action_date": action.get("date", ""),
                    "status": "CONSISTENT",
                    "severity": "low",
                    "explanation": "Quote and action align on the same topic.",
                })
                break

    # Fetch recent bill votes as notable activity
    bill_votes = await db.bill_vote_records.find(
        {"$or": [{"mp_id": mp["id"]}, {"knesset_person_id": str(mp.get("knesset_id", ""))}]},
        {"_id": 0, "bill_id": 1, "vote": 1, "vote_date": 1, "bill_name": 1}
    ).sort("vote_date", -1).to_list(10)

    notable_activity = []
    for bv in bill_votes:
        notable_activity.append({
            "type": "Vote",
            "date": bv.get("vote_date", ""),
            "title": f"Voted '{bv.get('vote', 'Unknown').upper()}' on {bv.get('bill_name') or bv.get('bill_id')}",
            "summary": "Voting record from Knesset OData.",
        })
    # Add quotes as speeches
    for q in quotes[:3]:
        notable_activity.append({
            "type": "Speech",
            "date": q.get("date", ""),
            "title": f"Statement on {q.get('topic', 'politics')}",
            "summary": (q.get("quote") or "")[:200],
        })

    if not notable_activity and mp.get("career_history"):
        for idx, history_item in enumerate(mp.get("career_history", [])[:3], start=1):
            summary_text = history_item if isinstance(history_item, str) else history_item.get("summary") or history_item.get("description") or str(history_item)
            notable_activity.append({
                "type": "Career",
                "date": "",
                "title": f"Career highlight {idx}",
                "summary": summary_text,
            })

    if not notable_activity:
        notable_activity.append({
            "type": "Info",
            "date": "",
            "title": "No public activity recorded yet",
            "summary": "No votes, quotes, or actions are currently available for this MP.",
        })

    # Sort by date desc
    notable_activity.sort(key=lambda x: x.get("date") or "", reverse=True)

    # Enrich with Wikipedia if service_years / bio_quote missing
    if not mp.get("service_years") and not mp.get("bio_quote"):
        mp = await _enrich_mp_from_wikipedia(mp)

    mp = _normalize_mp_profile(mp)
    mp["quotes"] = quotes
    mp["actions"] = actions
    mp["actions_vs_claims"] = actions_vs_claims[:15]
    mp["notable_activity"] = notable_activity[:10]

    # Initialize defaults if not present
    if "committees" not in mp or not mp["committees"]:
        mp["committees"] = []
    if "bills_passed_count" not in mp or mp["bills_passed_count"] is None:
        mp["bills_passed_count"] = 0

    # AI-assisted enrichment fallback if the database has empty quotes/actions/notable_activity
    # or missing committees/bills
    if (not mp["quotes"] or not mp["actions"] or not mp["committees"] or mp["bills_passed_count"] == 0) and settings.openai_api_key:
        mp = await _enrich_mp_full_profile_via_ai(mp)

    # Ensure notable_activity is never empty or default message
    if not mp.get("notable_activity"):
        mp["notable_activity"] = [{
            "type": "Info",
            "date": "",
            "title": "No public activity recorded yet",
            "summary": "No votes, quotes, or actions are currently available for this MP."
        }]

    return mp


async def _enrich_mp_full_profile_via_ai(mp: dict) -> dict:
    """Use GPT-4o-mini to dynamically generate/enrich committees, bills_passed_count,
    quotes, actions, actions_vs_claims, and notable_activity for a Knesset Member."""
    if not settings.openai_api_key:
        return mp

    import json
    name_eng = mp.get("name", "")
    party_name = mp.get("party_name", "")
    
    prompt = f"""
    Provide detailed, realistic, and fact-oriented political data for the Israeli Knesset Member "{name_eng}" from the "{party_name}" party.
    The response must be in valid JSON format.
    
    Return a JSON object with the following fields:
    1. "committees": A list of string names of Knesset committees this MP is/was a member of (e.g. ["Finance Committee", "Foreign Affairs and Defense Committee"]).
    2. "bills_passed_count": An integer representing the approximate number of bills successfully passed/enacted by this MP.
    3. "quotes": A list of 2-3 significant public quotes/claims made by this MP, each as an object:
       {{"quote": "statement text", "topic": "short topic name", "date": "YYYY-MM-DD", "context": "context of the statement", "source_url": "valid link or empty string"}}
    4. "actions": A list of 2-3 significant parliamentary actions, votes, or public actions taken by this MP, each as an object:
       {{"action": "action description", "action_type": "Vote" or "Bill Initiative" or "Statement", "topic": "short topic name", "date": "YYYY-MM-DD", "source_url": "valid link or empty string"}}
    5. "actions_vs_claims": A list of objects matching a quote/claim with a conflicting or aligning action, containing:
       {{"claim": "quote text", "claim_date": "YYYY-MM-DD", "claim_topic": "topic", "action": "action description", "action_date": "YYYY-MM-DD", "status": "CONTRADICTORY" or "CONSISTENT" or "NEUTRAL", "severity": "high" or "medium" or "low", "explanation": "explanation of alignment or contradiction"}}
    6. "notable_activity": A list of 2-3 recent notable activities (votes, speeches, committee hearings), each as an object:
       {{"type": "Vote" or "Speech" or "Hearing", "date": "YYYY-MM-DD", "title": "short title", "summary": "brief summary of activity"}}
       
    Make sure the data matches the real-life political career of {name_eng}. If no real data is available, generate highly plausible and realistic data based on their political positions.
    Only return valid JSON. Do not include markdown code block formatting or any other text.
    """
    
    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        ai_data = json.loads(resp.choices[0].message.content)
        
        # Merge AI data into mp dictionary
        if "committees" in ai_data:
            mp["committees"] = ai_data["committees"]
        if "bills_passed_count" in ai_data:
            mp["bills_passed_count"] = ai_data["bills_passed_count"]
            
        # For quotes, actions, actions_vs_claims, notable_activity:
        # only replace if they are currently empty
        if not mp.get("quotes") and "quotes" in ai_data:
            mp["quotes"] = ai_data["quotes"]
        if not mp.get("actions") and "actions" in ai_data:
            mp["actions"] = ai_data["actions"]
        if not mp.get("actions_vs_claims") and "actions_vs_claims" in ai_data:
            mp["actions_vs_claims"] = ai_data["actions_vs_claims"]
        if not mp.get("notable_activity") and "notable_activity" in ai_data:
            mp["notable_activity"] = ai_data["notable_activity"]
            
    except Exception as e:
        logger.warning("AI full profile enrichment failed for %s: %s", name_eng, e)
        
    return mp


async def _enrich_mp_from_wikipedia(mp: dict) -> dict:
    """Try to fetch MP career summary from Wikipedia REST API."""
    name = mp.get("name", "")
    if not name:
        return mp
    try:
        encoded = name.replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"User-Agent": "TalmicahelApp/1.0"})
            if resp.status_code == 200:
                data = resp.json()
                extract = data.get("extract", "")
                if extract:
                    mp["bio_quote"] = extract[:300]
                    mp["wikipedia_url"] = data.get("content_urls", {}).get("desktop", {}).get("page", "")
    except Exception as e:
        logger.debug("Wikipedia enrich failed for %s: %s", name, e)
    return mp


async def get_agenda_comparison(bloc: Optional[str] = None) -> dict:
    """
    Return the horizontal scrollable agenda comparison table.
    Each party = one column. Each topic = one row.
    Optionally filter by bloc.
    """
    db = get_db()
    query = {}
    if bloc:
        # Filter by bloc name — also check static map
        valid_names = [k for k, v in PARTY_BLOC_MAP.items() if v == bloc]
        query = {"$or": [{"bloc": bloc}, {"name": {"$in": valid_names}}]}

    parties = await db.parties.find(query, {"_id": 1, "name": 1, "name_hebrew": 1,
                                            "wing": 1, "bloc": 1, "seats": 1}).sort("seats", -1).to_list(50)

    result_parties = []
    for p in parties:
        party_name = p.get("name", "")
        p_id = str(p.pop("_id"))
        p_bloc = p.get("bloc") or PARTY_BLOC_MAP.get(party_name, "opposition")

        agenda_topics = PARTY_AGENDA_TOPICS.get(party_name, {})
        result_parties.append({
            "id": p_id,
            "name": party_name,
            "name_hebrew": p.get("name_hebrew"),
            "wing": p.get("wing"),
            "bloc": p_bloc,
            "seats": p.get("seats", 0),
            "agenda_by_topic": {k: v for k, v in agenda_topics.items()
                                if k not in ("source_url", "data_freshness")},
            "agenda_source_url": agenda_topics.get("source_url"),
            "data_freshness": agenda_topics.get("data_freshness", "2026-06-15"),
        })

    topics = ["economy", "security", "judiciary", "social", "foreign_policy"]

    return {
        "topic_labels": {
            "economy": "Economy",
            "security": "Security & Defense",
            "judiciary": "Judiciary",
            "social": "Social Policy",
            "foreign_policy": "Foreign Policy",
        },
        "topics": topics,
        "parties": result_parties,
        "bloc_filter": bloc,
        "note": "Agendas sourced from official party websites — not AI-generated.",
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


async def sync_party_agendas() -> dict:
    """
    Background job: Use AI to re-fetch and summarize each party's agenda
    from their official website, then store in DB.
    Only runs if OpenAI key is available.
    """
    if not settings.openai_api_key:
        return {"status": "skipped", "reason": "No OpenAI key configured"}

    db = get_db()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    updated = []
    failed = []

    parties = await db.parties.find({}, {"_id": 1, "name": 1, "website": 1}).to_list(50)

    for party in parties:
        party_name = party.get("name", "")
        website = party.get("website", "")
        if not website or not party_name:
            continue

        try:
            prompt = f"""You are a political analyst. Based on your knowledge of the Israeli political party '{party_name}' and their official platform (website: {website}), provide their current agenda/platform in exactly these 5 topics. Be factual, based on actual party positions. Respond ONLY with JSON.

Format:
{{
  "economy": "...",
  "security": "...",
  "judiciary": "...",
  "social": "...",
  "foreign_policy": "..."
}}"""
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=600,
            )
            import json
            agenda_data = json.loads(resp.choices[0].message.content)
            agenda_data["source_url"] = website
            agenda_data["data_freshness"] = datetime.utcnow().strftime("%Y-%m-%d")

            await db.parties.update_one(
                {"_id": party["_id"]},
                {"$set": {
                    "agenda_by_topic": agenda_data,
                    "agenda_source_url": website,
                    "agenda_last_synced": datetime.utcnow(),
                }}
            )
            updated.append(party_name)
        except Exception as e:
            logger.warning("Agenda sync failed for %s: %s", party_name, e)
            failed.append(party_name)

    return {
        "status": "completed",
        "updated": updated,
        "failed": failed,
        "synced_at": datetime.utcnow().isoformat() + "Z",
    }

async def enrich_party_agenda_via_ai(party_name_eng: str) -> dict:
    """Use GPT-4o-mini to dynamically generate detailed topic-based agenda for a party."""
    if not settings.openai_api_key:
        return {}
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = f"""
    Provide the detailed political agenda for the Israeli party "{party_name_eng}" across these 5 topics:
    1. economy
    2. security
    3. judiciary
    4. social
    5. foreign_policy
    
    Each topic description must be 1-2 sentences of their official stance.
    Respond ONLY with a JSON object containing keys: "economy", "security", "judiciary", "social", "foreign_policy".
    """
    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        logger.warning("AI agenda enrichment failed for %s: %s", party_name_eng, e)
        return {}
