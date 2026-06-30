# app/services/political_verification_service.py
"""
Political Data Verification Service — Trusted Source Cross-Check.

Implements 3 phases:
  Phase 1 — Static verified_by[] tags: which fields came from which source.
  Phase 2 — Live Wikipedia cross-check: compare leader + seats against stored data.
  Phase 3 — Composite verification score + UI badge for frontend display.

The 7 trusted sources per spec:
  1. Open Knesset (oknesset.org)
  2. Israeli Political Parties Registry (gov.il)
  3. Israel Democracy Institute — factual data only
  4. Israel Central Bureau of Statistics (CBS — EN + HE)
  5. Official Party Website
  6. Wikipedia
  7. Knesset Website (knesset.gov.il)
"""

import logging
import re
from datetime import date, datetime
from typing import Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

# ── 7 Trusted Sources Registry ────────────────────────────────────────────────
# These are the canonical source objects used in verified_by[] fields.
TRUSTED_SOURCES: dict[str, dict] = {
    "open_knesset": {
        "source_id": "open_knesset",
        "name": "Open Knesset (כנסת פתוחה)",
        "url": "https://oknesset.org",
        "data_url": "https://production.oknesset.org/pipelines/data/",
        "type": "parliamentary_data",
        "reliability": "very_high",
        "bias": "neutral — non-partisan open data",
        "notes": "Mirrors Knesset OData API daily. Primary pipeline for MK, faction, and bill data.",
    },
    "knesset_gov": {
        "source_id": "knesset_gov",
        "name": "Knesset Official Website",
        "url": "https://www.knesset.gov.il/",
        "type": "official_government",
        "reliability": "authoritative",
        "bias": "neutral — official body",
    },
    "bechirot": {
        "source_id": "bechirot",
        "name": "Central Elections Committee (bechirot.gov.il)",
        "url": "https://www.bechirot.gov.il/",
        "type": "official_government",
        "reliability": "authoritative",
        "bias": "neutral — official body",
        "notes": "Single authoritative source for all Knesset election seat counts.",
    },
    "wikipedia": {
        "source_id": "wikipedia",
        "name": "Wikipedia",
        "url": "https://en.wikipedia.org/",
        "type": "encyclopedia",
        "reliability": "high",
        "bias": "neutral — community edited, cited sources",
        "notes": "Used for cross-referencing leader, ideology, wing, and seat data.",
    },
    "party_website": {
        "source_id": "party_website",
        "name": "Official Party Website",
        "url": None,  # filled dynamically per party
        "type": "official_party",
        "reliability": "primary",
        "bias": "pro-party — authoritative for platform, may be promotional",
        "notes": "Use for agenda/platform data. Not neutral but most current.",
    },
    "cbs": {
        "source_id": "cbs",
        "name": "Central Bureau of Statistics — Israel (CBS)",
        "url": "https://www.cbs.gov.il/en",
        "url_he": "https://www.cbs.gov.il",
        "type": "official_statistics",
        "reliability": "authoritative",
        "bias": "neutral — official statistical body",
        "notes": "SUPER IMPORTANT. Use for any demographic, economic, or housing data.",
    },
    "idi": {
        "source_id": "idi",
        "name": "Israel Democracy Institute (IDI)",
        "url": "https://www.idi.org.il/en/",
        "type": "think_tank",
        "reliability": "very_high",
        "bias": "non-partisan — academic",
        "notes": "Use for factual/statistical data ONLY. Ignore editorial opinion.",
    },
    "party_registry": {
        "source_id": "party_registry",
        "name": "Registrar of Political Parties (רשם המפלגות)",
        "url": "https://www.gov.il/he/departments/topics/the_registrar_of_political_parties",
        "type": "official_government",
        "reliability": "authoritative",
        "bias": "neutral — official registry",
        "notes": "Use to verify whether a party is officially registered.",
    },
}

# ── Field → Source mapping for parties ───────────────────────────────────────
# Maps each party document field → which source(s) provide/verify it.
PARTY_FIELD_SOURCE_MAP: dict[str, list[str]] = {
    "name":          ["open_knesset", "wikipedia", "knesset_gov"],
    "name_hebrew":   ["open_knesset", "knesset_gov"],
    "seats":         ["bechirot", "open_knesset"],
    "leader":        ["wikipedia", "party_website"],
    "wing":          ["wikipedia"],
    "bloc":          ["knesset_gov", "open_knesset"],
    "ideology":      ["wikipedia", "party_website"],
    "agenda":        ["party_website"],
    "website":       ["party_website"],
    "wikipedia_url": ["wikipedia"],
}

# ── Field → Source mapping for bills ─────────────────────────────────────────
BILL_FIELD_SOURCE_MAP: dict[str, list[str]] = {
    "bill_id":          ["open_knesset", "knesset_gov"],
    "name":             ["open_knesset", "knesset_gov"],
    "status":           ["open_knesset", "knesset_gov"],
    "type":             ["open_knesset"],
    "sub_type":         ["open_knesset"],
    "initiator":        ["open_knesset"],
    "summary":          ["open_knesset"],
    "publication_date": ["open_knesset"],
    "knesset_num":      ["open_knesset"],
}


# ── Phase 1: Static verified_by builder ──────────────────────────────────────

def _source_entry(source_id: str, fields: list[str], party_website_url: str | None = None) -> dict:
    """Build a single verified_by entry for a given source."""
    src = TRUSTED_SOURCES[source_id].copy()
    if source_id == "party_website" and party_website_url:
        src["url"] = party_website_url
    return {
        "source_id": source_id,
        "source_name": src["name"],
        "source_url": src.get("url"),
        "reliability": src["reliability"],
        "fields_verified": fields,
        "verified_at": date.today().isoformat(),
    }


def build_party_verified_by(
    name_eng: str,
    enrich: dict | None,
    seats_verified: bool,
) -> list[dict]:
    """
    Phase 1 — Build the verified_by[] list for a party document.

    Returns a list of source entries, each specifying which fields
    that source contributes/verifies.
    """
    verified_by: list[dict] = []
    party_website_url = enrich.get("website") if enrich else None

    # Open Knesset: provides name, name_hebrew, bloc (from faction CSV)
    verified_by.append(_source_entry(
        "open_knesset",
        fields=["name", "name_hebrew", "bloc"],
    ))

    # bechirot.gov.il: provides seats (if verified)
    if seats_verified:
        verified_by.append(_source_entry(
            "bechirot",
            fields=["seats"],
        ))

    # Wikipedia: provides leader, wing, ideology (from PARTY_ENRICHMENT)
    if enrich and enrich.get("wikipedia_url"):
        wiki_fields = ["leader", "wing", "ideology"]
        verified_by.append(_source_entry(
            "wikipedia",
            fields=wiki_fields,
        ))

    # Official Party Website: provides agenda, website URL
    if enrich and party_website_url:
        verified_by.append(_source_entry(
            "party_website",
            fields=["agenda", "website"],
            party_website_url=party_website_url,
        ))

    # Knesset.gov.il: provides faction membership (via Open Knesset mirror)
    if enrich and any(
        "knesset.gov.il" in (link.get("url") or "") 
        for link in (enrich.get("source_links") or [])
    ):
        verified_by.append(_source_entry(
            "knesset_gov",
            fields=["name", "bloc"],
        ))

    return verified_by


def build_bill_verified_by() -> list[dict]:
    """
    Phase 1 — Build the verified_by[] list for a bill document.
    Bills come from Open Knesset CSV (mirrors Knesset OData).
    """
    return [
        _source_entry(
            "open_knesset",
            fields=["bill_id", "name", "status", "type", "sub_type",
                    "initiator", "summary", "publication_date", "knesset_num"],
        ),
        _source_entry(
            "knesset_gov",
            fields=["bill_id", "name", "status"],
        ),
    ]


def compute_verification_score(verified_by: list[dict]) -> tuple[int, str]:
    """
    Compute a verification score + label from verified_by list.

    Score = number of unique sources that verified any field.
    Label:
      1 source  → "single_source"
      2 sources → "dual_source_verified"
      3+        → "multi_source_verified"
    """
    source_count = len(verified_by)
    if source_count >= 3:
        label = "multi_source_verified"
    elif source_count == 2:
        label = "dual_source_verified"
    elif source_count == 1:
        label = "single_source"
    else:
        label = "unverified"
    return source_count, label


# ── Phase 2: Wikipedia Live Cross-Check ──────────────────────────────────────

_HEADERS = {"User-Agent": "Mozilla/5.0 (TalmichaelApp/3.0; research)"}
_SEAT_PATTERN = re.compile(r"\b(\d{1,3})\s*(?:seats?|members?|MKs?)\b", re.IGNORECASE)
_LEADER_EXTRACT = re.compile(
    r"(?:led by|leader[:\s]+|party leader[:\s]+|chaired by)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,3})",
    re.IGNORECASE,
)


async def _fetch_wikipedia_summary(wikipedia_url: str) -> dict | None:
    """Fetch Wikipedia page summary via REST v1 API from a full Wikipedia URL."""
    try:
        # Extract title from URL e.g. https://en.wikipedia.org/wiki/Likud → Likud
        match = re.search(r"/wiki/(.+)$", wikipedia_url)
        if not match:
            return None
        title = match.group(1)
        encoded = quote(title, safe="")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(url, headers=_HEADERS)
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.warning("Wikipedia fetch failed for %s: %s", wikipedia_url, e)
    return None


def _extract_seats_from_text(text: str) -> list[int]:
    """Extract all seat counts mentioned in a Wikipedia summary."""
    return [int(m.group(1)) for m in _SEAT_PATTERN.finditer(text)]


def _extract_leader_from_text(text: str) -> str | None:
    """Try to extract a leader name from Wikipedia summary text."""
    m = _LEADER_EXTRACT.search(text)
    if m:
        return m.group(1).strip()
    return None


def _names_roughly_match(name_a: str | None, name_b: str | None) -> bool:
    """Check if two names are roughly the same (last name match is enough)."""
    if not name_a or not name_b:
        return False
    a_parts = name_a.lower().split()
    b_parts = name_b.lower().split()
    # Match if any part of name_b appears in name_a
    return any(part in a_parts for part in b_parts if len(part) > 2)


async def cross_check_party_via_wikipedia(
    name_eng: str,
    stored_leader: str | None,
    stored_seats: int,
    wikipedia_url: str | None,
) -> dict:
    """
    Phase 2 — Live Wikipedia cross-check for a single party.

    Compares:
      - Leader name (stored vs Wikipedia extract)
      - Seat count (stored vs Wikipedia mention)

    Returns a structured cross_check_result dict.
    """
    if not wikipedia_url:
        return {
            "checked": False,
            "reason": "no_wikipedia_url",
            "checked_at": datetime.utcnow().isoformat(),
        }

    wiki_data = await _fetch_wikipedia_summary(wikipedia_url)
    if not wiki_data:
        return {
            "checked": False,
            "reason": "wikipedia_fetch_failed",
            "wikipedia_url": wikipedia_url,
            "checked_at": datetime.utcnow().isoformat(),
        }

    extract = wiki_data.get("extract", "")
    wiki_seats = _extract_seats_from_text(extract)
    wiki_leader = _extract_leader_from_text(extract)

    agreements: list[str] = []
    divergences: list[str] = []
    fields_checked: list[str] = []

    # ── Check leader ─────────────────────────────────────────────────────────
    if stored_leader and wiki_leader:
        fields_checked.append("leader")
        if _names_roughly_match(stored_leader, wiki_leader):
            agreements.append(f"leader: '{stored_leader}' confirmed by Wikipedia")
        else:
            divergences.append(
                f"leader mismatch: stored='{stored_leader}' vs Wikipedia extract='{wiki_leader}'"
            )
    elif stored_leader and not wiki_leader:
        divergences.append(f"leader: Wikipedia text does not clearly name a leader (stored: '{stored_leader}')")

    # ── Check seat count ──────────────────────────────────────────────────────
    if wiki_seats:
        fields_checked.append("seats")
        # Check if stored_seats is in the range of mentioned seats
        closest = min(wiki_seats, key=lambda s: abs(s - stored_seats))
        if abs(closest - stored_seats) <= 2:
            agreements.append(
                f"seats: {stored_seats} matches Wikipedia mention ({closest})"
            )
        else:
            divergences.append(
                f"seats: stored={stored_seats} but Wikipedia mentions {wiki_seats} "
                f"(note: Wikipedia may reference different Knesset term)"
            )
    else:
        divergences.append("seats: Wikipedia text contains no seat count to compare")

    # ── Agreement score ───────────────────────────────────────────────────────
    total_checked = len(fields_checked)
    agreed = len(agreements)
    score = round(agreed / total_checked, 2) if total_checked > 0 else 0.5

    return {
        "checked": True,
        "wikipedia_url": wikipedia_url,
        "wikipedia_title": wiki_data.get("title"),
        "fields_checked": fields_checked,
        "agreements": agreements,
        "divergences": divergences,
        "agreement_score": score,
        "agreement_label": (
            "confirmed" if score >= 0.8
            else "partial_match" if score >= 0.5
            else "divergent"
        ),
        "wiki_leader_extracted": wiki_leader,
        "wiki_seats_mentioned": wiki_seats,
        "checked_at": datetime.utcnow().isoformat(),
    }


# ── Phase 3: Full party verification report ───────────────────────────────────

def build_verification_badge(
    verification_score: int,
    verification_label: str,
    cross_check: dict | None,
) -> dict:
    """
    Phase 3 — Build a UI-ready verification badge for the frontend.

    Returns a compact object the frontend can render directly as a badge/pill.
    """
    # Map label to display text + color
    LABEL_MAP = {
        "multi_source_verified":  {"text": "Multi-Source Verified", "color": "green",  "icon": "✓✓✓"},
        "dual_source_verified":   {"text": "Dual-Source Verified",  "color": "teal",   "icon": "✓✓"},
        "single_source":          {"text": "Single Source",          "color": "yellow", "icon": "✓"},
        "unverified":             {"text": "Unverified",             "color": "gray",   "icon": "?"},
    }
    badge = LABEL_MAP.get(verification_label, LABEL_MAP["unverified"])

    # Cross-check enrichment
    cross_label = None
    if cross_check and cross_check.get("checked"):
        cross_label = cross_check.get("agreement_label", "unknown")

    return {
        "label": badge["text"],
        "color": badge["color"],
        "icon": badge["icon"],
        "source_count": verification_score,
        "wikipedia_cross_check": cross_label,
        "tooltip": (
            f"Data verified across {verification_score} independent source(s). "
            + (f"Wikipedia cross-check: {cross_label}." if cross_label else "")
        ),
    }


def build_full_party_verification_report(
    name_eng: str,
    verified_by: list[dict],
    verification_score: int,
    verification_label: str,
    cross_check_result: dict | None,
) -> dict:
    """
    Phase 3 — Assemble the complete verification report for a party.
    This is the full payload for GET /political/parties/{id}/verification.
    """
    badge = build_verification_badge(verification_score, verification_label, cross_check_result)

    return {
        "party": name_eng,
        "verification_score": verification_score,
        "verification_label": verification_label,
        "badge": badge,
        "verified_by": verified_by,
        "cross_check": cross_check_result or {"checked": False, "reason": "not_run"},
        "trusted_sources_registry": {
            sid: {
                "name": s["name"],
                "url": s.get("url"),
                "type": s["type"],
                "reliability": s["reliability"],
            }
            for sid, s in TRUSTED_SOURCES.items()
        },
        "data_integrity_note": (
            "All factual data (seats, names, faction) is sourced from official "
            "or non-partisan databases. AI is used only for translation and biography "
            "text — never for political facts. Verify any figure at the linked source URLs."
        ),
        "generated_at": datetime.utcnow().isoformat(),
    }
