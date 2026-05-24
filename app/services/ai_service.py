# app/services/ai_service.py
"""
Phase 2 — AI Analysis Layer.

Provides per-article:
  - Sentiment analysis      (positive / neutral / negative)
  - Bias detection          (left / center / right / unknown)
  - Credibility scoring     (0.0 – 1.0)
  - Fact-check score        (0.0 – 1.0)
  - Hebrew summary          (2–3 sentences)
  - Key topic extraction

Uses OpenAI GPT-4o.  Falls back to rule-based analysis when
OPENAI_API_KEY is not set (free-tier / dev mode).
"""

import json
import logging
from typing import Optional

from app.core.config import settings
from app.core.cache import cache_get, cache_set, ai_analysis_key, AI_TTL
from app.models.schemas import ArticleAnalysis
from app.utils.filters import (
    ISRAELI_SOURCES, is_negative, is_opinion,
    NEGATIVE_KEYWORDS,
)

logger = logging.getLogger(__name__)

# ── Source bias seed table (rule-based baseline) ──────────────────────────────
SOURCE_BIAS_SEED: dict[str, str] = {
    "Haaretz": "left",
    "haaretz.com": "left",
    "The Jerusalem Post": "right",
    "jpost.com": "right",
    "Times of Israel": "center",
    "timesofisrael.com": "center",
    "Ynet News": "center",
    "ynetnews.com": "center",
    "i24 News": "center",
    "i24news.tv": "center",
    "Arutz Sheva": "right",
    "israelnationalnews.com": "right",
    "Israel Hayom": "right",
    "israelhayom.com": "right",
    "The Algemeiner": "right",
    "algemeiner.com": "right",
    "Kan News": "center",
    "kan.org.il": "center",
    "Channel 12 News": "center",
    "mako.co.il": "center",
    "Globes": "center",
    "globes.co.il": "center",
    "TheMarker": "left",
    "themarker.com": "left",
}

# ── Credibility seed scores ───────────────────────────────────────────────────
SOURCE_CREDIBILITY_SEED: dict[str, float] = {
    "Times of Israel": 0.85,
    "timesofisrael.com": 0.85,
    "Haaretz": 0.82,
    "haaretz.com": 0.82,
    "The Jerusalem Post": 0.80,
    "jpost.com": 0.80,
    "Kan News": 0.88,
    "kan.org.il": 0.88,
    "i24 News": 0.78,
    "i24news.tv": 0.78,
    "Ynet News": 0.75,
    "ynetnews.com": 0.75,
    "Arutz Sheva": 0.65,
    "israelnationalnews.com": 0.65,
    "Israel Hayom": 0.68,
    "israelhayom.com": 0.68,
}


# ── Rule-based fallback (no API key needed) ───────────────────────────────────

def _rule_based_analysis(
    title: str,
    description: str,
    source: Optional[str],
    source_url: Optional[str],
) -> ArticleAnalysis:
    """
    Fast, zero-cost analysis using keyword rules and seed tables.
    Used when OpenAI key is absent or for free-tier users.
    """
    text = f"{title} {description}".lower()

    # Sentiment
    neg_hits = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)
    pos_keywords = (
        "success", "achievement", "breakthrough", "award", "peace",
        "growth", "innovation", "record", "victory", "celebrate",
        "improve", "advance", "launch", "discover", "win",
    )
    pos_hits = sum(1 for kw in pos_keywords if kw in text)

    if neg_hits > pos_hits:
        sentiment = "negative"
    elif pos_hits > 0:
        sentiment = "positive"
    else:
        sentiment = "neutral"

    # Bias
    bias = "unknown"
    for name in [source, source_url]:
        if name and name in SOURCE_BIAS_SEED:
            bias = SOURCE_BIAS_SEED[name]
            break

    # Credibility
    credibility = 0.5
    for name in [source, source_url]:
        if name and name in SOURCE_CREDIBILITY_SEED:
            credibility = SOURCE_CREDIBILITY_SEED[name]
            break

    # Fact-check score — rule-based proxy
    # Higher credibility + neutral/positive sentiment → higher fact-check score
    fact_check = round(credibility * (0.9 if sentiment != "negative" else 0.7), 2)

    # Topics — simple keyword extraction
    topic_map = {
        "economy": ["economy", "finance", "market", "gdp", "inflation", "shekel"],
        "security": ["security", "military", "idf", "defense", "terror", "attack"],
        "politics": ["knesset", "government", "minister", "election", "coalition"],
        "education": ["school", "university", "student", "education", "teacher"],
        "health": ["hospital", "health", "vaccine", "covid", "medical", "doctor"],
        "technology": ["tech", "startup", "innovation", "ai", "cyber", "software"],
        "environment": ["climate", "environment", "energy", "solar", "water"],
        "culture": ["culture", "art", "music", "film", "festival", "heritage"],
    }
    topics = [topic for topic, kws in topic_map.items() if any(kw in text for kw in kws)]

    # Hebrew summary placeholder (rule-based — no translation)
    summary_hebrew = f"[סיכום אוטומטי] {title[:120]}"

    return ArticleAnalysis(
        guid="",  # filled by caller
        sentiment=sentiment,
        bias=bias,
        credibility_score=round(credibility, 2),
        fact_check_score=fact_check,
        summary_hebrew=summary_hebrew,
        topics=topics or ["general"],
    )


# ── OpenAI-powered analysis ───────────────────────────────────────────────────

_SYSTEM_PROMPT = """
You are an expert Israeli news analyst. Analyze the given article and return a JSON object with:
- sentiment: "positive" | "neutral" | "negative"
- bias: "left" | "center" | "right" | "unknown"
- credibility_score: float 0.0-1.0 (based on source reputation and factual language)
- fact_check_score: float 0.0-1.0 (how verifiable the claims appear)
- summary_hebrew: 2-3 sentence summary in Hebrew
- topics: list of up to 5 relevant topic tags in English (e.g. ["economy", "politics"])

Respond ONLY with valid JSON. No markdown, no explanation.
"""


async def _openai_analysis(
    title: str,
    description: str,
    source: Optional[str],
) -> Optional[dict]:
    """Call OpenAI GPT-4o for deep analysis. Returns raw dict or None on failure."""
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        user_content = (
            f"Source: {source or 'Unknown'}\n"
            f"Title: {title}\n"
            f"Description: {description[:500]}"
        )

        response = await client.chat.completions.create(
            model="gpt-4o-mini",   # cost-efficient; swap to gpt-4o for higher quality
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=400,
            response_format={"type": "json_object"},
        )

        return json.loads(response.choices[0].message.content)

    except Exception as e:
        logger.warning("OpenAI analysis failed: %s", e)
        return None


# ── Public API ────────────────────────────────────────────────────────────────

async def analyze_article(
    guid: str,
    title: str,
    description: str,
    source: Optional[str] = None,
    source_url: Optional[str] = None,
    use_ai: bool = False,       # True only for paid users
) -> ArticleAnalysis:
    """
    Analyze a single article.

    Args:
        guid:        Unique article identifier (used as cache key).
        title:       Article headline.
        description: Article snippet/description.
        source:      Source outlet name.
        source_url:  Source outlet URL.
        use_ai:      When True and OPENAI_API_KEY is set, uses GPT-4o.
                     Otherwise falls back to rule-based analysis.
    """
    # Cache check
    cache_key = ai_analysis_key(guid)
    cached = await cache_get(cache_key)
    if cached:
        return ArticleAnalysis(**cached)

    result: Optional[ArticleAnalysis] = None

    # AI path (paid users + API key present)
    if use_ai and settings.openai_api_key:
        raw = await _openai_analysis(title, description, source)
        if raw:
            try:
                result = ArticleAnalysis(
                    guid=guid,
                    sentiment=raw.get("sentiment", "neutral"),
                    bias=raw.get("bias", "unknown"),
                    credibility_score=float(raw.get("credibility_score", 0.5)),
                    fact_check_score=float(raw.get("fact_check_score", 0.5)),
                    summary_hebrew=raw.get("summary_hebrew", ""),
                    topics=raw.get("topics", ["general"]),
                )
            except Exception as e:
                logger.warning("Failed to parse OpenAI response: %s", e)

    # Rule-based fallback
    if result is None:
        result = _rule_based_analysis(title, description, source, source_url)
        result.guid = guid

    # Cache result
    await cache_set(cache_key, result.model_dump(), AI_TTL)
    return result


async def analyze_batch(
    articles: list[dict],
    use_ai: bool = False,
) -> list[ArticleAnalysis]:
    """
    Analyze a list of articles concurrently.
    Each dict must have: guid, title, description, source (optional), source_url (optional).
    """
    import asyncio
    tasks = [
        analyze_article(
            guid=a.get("guid", ""),
            title=a.get("title", ""),
            description=a.get("description", ""),
            source=a.get("source"),
            source_url=a.get("source_url"),
            use_ai=use_ai,
        )
        for a in articles
    ]
    return await asyncio.gather(*tasks)


async def get_source_bias(source_name: str, source_url: Optional[str] = None) -> dict:
    """Return bias and credibility info for a given source."""
    bias = SOURCE_BIAS_SEED.get(source_name) or SOURCE_BIAS_SEED.get(source_url or "") or "unknown"
    credibility = (
        SOURCE_CREDIBILITY_SEED.get(source_name)
        or SOURCE_CREDIBILITY_SEED.get(source_url or "")
        or 0.5
    )
    return {
        "source_name": source_name,
        "bias": bias,
        "credibility_score": credibility,
        "bias_label": {"left": "⬅️ Left", "center": "⚖️ Center", "right": "➡️ Right"}.get(bias, "❓ Unknown"),
    }
