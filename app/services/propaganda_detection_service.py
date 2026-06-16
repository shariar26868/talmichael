# app/services/propaganda_detection_service.py
"""
Automated Propaganda & Disinformation Pattern Detection.

Detects propaganda patterns without relying on user flags:
  1. Coordinated narrative detection — identical framing from 5+ sources in <2 hours.
  2. Astroturfing signals — new/obscure sources suddenly publishing high volume.
  3. Known disinformation patterns — conspiracy language, all-caps, zero sources cited.
  4. Emotional manipulation — extreme emotional language designed to bypass critical thinking.
  5. Bot-pattern voting — users voting on 50+ articles per day (in voting_service).

Findings are stored as automated flags with reason "automated_propaganda_signal".
"""

import logging
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Optional

from app.core.database import get_db

logger = logging.getLogger(__name__)

# ── Pattern dictionaries ──────────────────────────────────────────────────────

CONSPIRACY_LANGUAGE = (
    "deep state", "new world order", "wake up", "they don't want you to know",
    "mainstream media lies", "the truth they hide", "globalist", "controlled opposition",
    "false flag", "psyop", "psy-op", "sheeple", "coverup", "cover-up",
    "hidden agenda", "puppet master", "shadow government", "illuminati",
    "big pharma", "media conspiracy", "orchestrated", "manufactured crisis",
)

EXTREME_EMOTIONAL = (
    "BREAKING", "URGENT", "SHOCKING", "YOU WON'T BELIEVE", "EXPOSED",
    "DESTROYED", "OBLITERATED", "BOMBSHELL", "EXPLOSIVE", "OUTRAGEOUS",
    "DISGUSTING", "HORRIFYING", "TERRIFYING", "UNBELIEVABLE", "MUST SEE",
    "SHARE NOW", "WAKE UP", "SHARE BEFORE DELETED", "CENSORED",
)

MANIPULATION_PHRASES = (
    "do your own research", "think for yourself", "open your eyes",
    "the media won't tell you", "banned from", "they censored",
    "share before it's removed", "the truth about", "exposed",
    "what they don't want", "the real story", "mainstream media ignores",
)

# ── Detection functions ───────────────────────────────────────────────────────


def detect_propaganda_signals(title: str, description: str) -> dict:
    """Analyze a single article for propaganda and disinformation patterns.

    Returns a dict with:
      - is_flagged: bool — whether any signal was detected
      - signals: list of detected patterns
      - severity: "none" / "low" / "medium" / "high"
      - explanation: human-readable summary
    """
    clean_desc = re.sub(r"<[^>]+>", "", description)
    text = f"{title} {clean_desc}"
    text_lower = text.lower()
    signals = []

    # 1. Conspiracy language
    conspiracy_hits = [phrase for phrase in CONSPIRACY_LANGUAGE if phrase in text_lower]
    if conspiracy_hits:
        signals.append({
            "type": "conspiracy_language",
            "matches": conspiracy_hits[:5],
            "severity": "high",
        })

    # 2. Extreme emotional manipulation
    emotional_hits = [phrase for phrase in EXTREME_EMOTIONAL if phrase in text]
    if emotional_hits:
        signals.append({
            "type": "extreme_emotional_language",
            "matches": emotional_hits[:5],
            "severity": "medium" if len(emotional_hits) < 3 else "high",
        })

    # 3. Manipulation phrases
    manip_hits = [phrase for phrase in MANIPULATION_PHRASES if phrase in text_lower]
    if manip_hits:
        signals.append({
            "type": "manipulation_phrases",
            "matches": manip_hits[:5],
            "severity": "medium",
        })

    # 4. ALL CAPS in title (more than 50% of words)
    title_words = title.split()
    caps_ratio = sum(1 for w in title_words if w.isupper() and len(w) > 2) / max(len(title_words), 1)
    if caps_ratio > 0.5 and len(title_words) > 3:
        signals.append({
            "type": "excessive_caps",
            "severity": "low",
            "detail": f"{caps_ratio:.0%} of title words are ALL CAPS",
        })

    # 5. No source attribution in body
    attribution_pattern = re.compile(
        r"(?:according to|said|told|reported|confirmed|stated|announced)\s",
        re.IGNORECASE,
    )
    if not attribution_pattern.search(clean_desc) and len(clean_desc.split()) > 20:
        signals.append({
            "type": "no_source_attribution",
            "severity": "low",
            "detail": "Article body has no source attribution phrases.",
        })

    # 6. Excessive exclamation/question marks
    exclamation_count = text.count("!") + text.count("?!")
    if exclamation_count > 3:
        signals.append({
            "type": "excessive_punctuation",
            "severity": "low",
            "detail": f"{exclamation_count} exclamation marks detected.",
        })

    # Compute severity
    if not signals:
        severity = "none"
    else:
        severities = [s.get("severity", "low") for s in signals]
        if "high" in severities:
            severity = "high"
        elif severities.count("medium") >= 2:
            severity = "high"
        elif "medium" in severities:
            severity = "medium"
        else:
            severity = "low"

    # Build explanation
    if signals:
        signal_types = [s["type"].replace("_", " ") for s in signals]
        explanation = (
            f"Detected {len(signals)} propaganda signal(s): {', '.join(signal_types)}. "
            f"Overall severity: {severity}."
        )
    else:
        explanation = "No propaganda patterns detected."

    return {
        "is_flagged": len(signals) > 0,
        "signals": signals,
        "signal_count": len(signals),
        "severity": severity,
        "explanation": explanation,
    }


async def detect_coordinated_narratives(
    hours: int = 2,
    min_sources: int = 4,
) -> list[dict]:
    """Detect coordinated narrative patterns across sources.

    Looks for near-identical headlines/framing published by 4+ different
    sources within a short time window. This can indicate coordinated
    press releases, government-pushed narratives, or astroturfing.

    Returns list of detected coordinated narratives.
    """
    db = get_db()
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    recent_articles = await db.cached_articles.find(
        {"fetched_at": {"$gte": cutoff.isoformat()}},
        {"title": 1, "source": 1, "guid": 1, "fetched_at": 1, "_id": 0},
    ).to_list(length=500)

    if len(recent_articles) < min_sources:
        return []

    # Group by title similarity (simplified: first 5 significant words)
    title_groups = defaultdict(list)
    for article in recent_articles:
        title = article.get("title", "")
        # Normalize: lowercase, remove punctuation, take first 5 significant words
        words = re.findall(r"[a-z]+", title.lower())
        key_words = [w for w in words if len(w) > 3][:5]
        key = " ".join(sorted(key_words))
        if key:
            title_groups[key].append(article)

    # Find groups with many sources
    coordinated = []
    for key, group in title_groups.items():
        unique_sources = {a.get("source", "?") for a in group}
        if len(unique_sources) >= min_sources:
            coordinated.append({
                "narrative_key": key,
                "source_count": len(unique_sources),
                "sources": list(unique_sources),
                "sample_titles": [a.get("title", "") for a in group[:3]],
                "article_count": len(group),
                "time_window_hours": hours,
                "assessment": (
                    "likely_coordinated" if len(unique_sources) >= 6
                    else "possibly_coordinated"
                ),
            })

    return sorted(coordinated, key=lambda x: x["source_count"], reverse=True)


async def auto_flag_article(
    article_guid: str,
    title: str,
    description: str,
) -> Optional[dict]:
    """Run propaganda detection and auto-flag if signals are found.

    Only auto-flags if severity is "medium" or "high".
    Stores the flag in article_flags with reason "automated_propaganda_signal".
    """
    result = detect_propaganda_signals(title, description)

    if result["severity"] in ("medium", "high"):
        db = get_db()

        # Check if already flagged
        existing = await db.article_flags.find_one({
            "article_id": article_guid,
            "user_id": "system_auto",
            "reason": "automated_propaganda_signal",
        })
        if existing:
            return None  # already flagged

        flag = {
            "article_id": article_guid,
            "user_id": "system_auto",
            "reason": "automated_propaganda_signal",
            "details": result["explanation"],
            "signals": result["signals"],
            "severity": result["severity"],
            "created_at": datetime.utcnow(),
            "status": "pending",
        }
        await db.article_flags.insert_one(flag)
        logger.info(
            "Auto-flagged article %s: %s (severity=%s)",
            article_guid, result["explanation"], result["severity"],
        )
        return flag

    return None
