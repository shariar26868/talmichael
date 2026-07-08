# app/services/summary_service.py
"""
News Summary Service — 7-day and 30-day digest generation.

Strategy (two-layer):
  1. PRIMARY  — Query MongoDB `cached_articles` for articles stored in the
                past N days. This gives real historical coverage whenever the
                collection has been populated by prior fetches.
  2. FALLBACK — If MongoDB returns < MIN_ARTICLES_THRESHOLD per category, fall
                back to a live RSS fetch (same logic as news_service.fetch_news)
                so the endpoint always returns *something* useful even on a
                fresh deployment with no historical data.

For each category we then:
  a. Extract the top-5 headlines and unique source names.
  b. Call OpenAI GPT-4o-mini to produce a prose digest + key_themes list.
     If no API key is set we produce a rule-based digest (no AI prose).
  c. Tally rough sentiment from stored `sentiment` fields or keyword heuristics.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

from app.core.cache import (
    cache_get, cache_set,
    summary_key, SUMMARY_7D_TTL, SUMMARY_30D_TTL,
)
from app.core.config import settings
from app.models.schemas import CategorySummary, NewsSummaryResponse
from app.services.news_service import fetch_news
from app.utils.feed_config import RSS_FEEDS
from app.utils.filters import is_negative

logger = logging.getLogger(__name__)

# Minimum articles we need from MongoDB before we consider it sufficient
_MIN_ARTICLES_THRESHOLD = 5

# Categories to summarise (same keys as RSS_FEEDS, minus knesset which is bills)
_SUMMARY_CATEGORIES = [
    "international", "political", "economy", "security",
    "sport", "culture", "science", "environment",
    "education", "community",
]


# ── DB helpers ────────────────────────────────────────────────────────────────

async def _fetch_from_db(category: str, since: datetime) -> list[dict]:
    """Query MongoDB cached_articles for a category within the date range."""
    try:
        from app.core.database import get_db
        db = get_db()
        cursor = db.cached_articles.find(
            {
                "category": category,
                "fetched_at": {"$gte": since.isoformat()},
            },
            {
                "title": 1, "description": 1, "source": 1,
                "sentiment": 1, "pub_date": 1, "link": 1, "_id": 0,
            },
        ).sort("fetched_at", -1).limit(200)
        return await cursor.to_list(length=200)
    except Exception as e:
        logger.warning(f"[summary] MongoDB query failed for {category}: {e}")
        return []


# ── Sentiment tallying ────────────────────────────────────────────────────────

def _tally_sentiment(articles: list) -> dict[str, int]:
    """Count positive/neutral/negative from stored sentiment or keyword heuristics."""
    tally = {"positive": 0, "neutral": 0, "negative": 0}
    for a in articles:
        # Articles may be dicts (from DB) or NewsArticle objects (from RSS)
        sent = (
            a.get("sentiment") if isinstance(a, dict)
            else getattr(a, "sentiment", None)
        )
        if sent in ("positive", "neutral", "negative"):
            tally[sent] += 1
        else:
            # Keyword heuristic fallback
            title = a.get("title", "") if isinstance(a, dict) else getattr(a, "title", "")
            desc = a.get("description", "") if isinstance(a, dict) else getattr(a, "description", "")
            if is_negative(title, desc):
                tally["negative"] += 1
            else:
                tally["neutral"] += 1
    return tally


# ── AI summarisation ──────────────────────────────────────────────────────────

async def _ai_summarise(
    category: str,
    headlines: list[str],
    period_days: int,
) -> tuple[str, list[str]]:
    """
    Call OpenAI GPT-4o-mini to generate:
      - prose_summary  (2-4 sentences about the period)
      - key_themes     (list of 3-6 strings)

    Returns ("", []) on any failure so the caller degrades gracefully.
    """
    if not settings.openai_api_key:
        return "", []

    prompt = (
        f"You are a professional news editor. Based on the following top headlines "
        f"from the '{category}' news category over the past {period_days} days, "
        f"write a concise 2-4 sentence summary of the major developments, and list "
        f"3-6 key recurring themes as short phrases.\n\n"
        f"Headlines:\n" + "\n".join(f"- {h}" for h in headlines[:20]) + "\n\n"
        f"Respond ONLY with a valid JSON object in this exact format:\n"
        f'{{"summary": "...", "key_themes": ["theme1", "theme2", "theme3"]}}'
    )

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 400,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return parsed.get("summary", ""), parsed.get("key_themes", [])
    except Exception as e:
        logger.warning(f"[summary] AI call failed for {category}: {e}")
        return "", []


# ── Per-category digest builder ───────────────────────────────────────────────

async def _build_category_digest(
    category: str,
    period_days: int,
    since: datetime,
) -> CategorySummary:
    """
    Build a CategorySummary for one category.
    Tries MongoDB first; falls back to live RSS fetch.
    """
    # ── 1. Try MongoDB ─────────────────────────────────────────────────────
    db_articles = await _fetch_from_db(category, since)

    if len(db_articles) >= _MIN_ARTICLES_THRESHOLD:
        raw_headlines = [
            a.get("title", "") for a in db_articles if a.get("title")
        ]
        sources = list({a.get("source", "") for a in db_articles if a.get("source")})
        article_count = len(db_articles)
        sentiment = _tally_sentiment(db_articles)
    else:
        # ── 2. Fallback: live RSS ──────────────────────────────────────────
        logger.info(
            f"[summary] Insufficient DB articles for {category} "
            f"({len(db_articles)} < {_MIN_ARTICLES_THRESHOLD}), falling back to RSS"
        )
        try:
            news_resp = await fetch_news(
                category, limit=80, language="english", use_cache=True
            )
            rss_articles = news_resp.articles
        except Exception as e:
            logger.warning(f"[summary] RSS fallback failed for {category}: {e}")
            rss_articles = []

        raw_headlines = [a.title for a in rss_articles if a.title]
        sources = list({a.source for a in rss_articles if a.source})
        article_count = len(rss_articles)
        sentiment = _tally_sentiment(rss_articles)

    top_headlines = raw_headlines[:5]

    # ── 3. AI prose summary ────────────────────────────────────────────────
    ai_summary, key_themes = await _ai_summarise(category, raw_headlines, period_days)

    # Rule-based fallback when AI is unavailable
    if not ai_summary:
        if top_headlines:
            ai_summary = (
                f"Over the past {period_days} days, {article_count} articles were "
                f"tracked in the {category} category. Key stories included topics "
                f"covered by sources such as {', '.join(sources[:3]) or 'various outlets'}."
            )
        else:
            ai_summary = f"No significant {category} news was found for this period."

    if not key_themes:
        # Use first 3 headlines as pseudo-themes when AI is not available
        key_themes = [h[:60] for h in top_headlines[:3]]

    return CategorySummary(
        category=category,
        article_count=article_count,
        top_headlines=top_headlines,
        summary=ai_summary,
        key_themes=key_themes,
        sentiment_breakdown=sentiment,
        sources_cited=sorted(sources)[:10],
    )


# ── Main orchestrator ─────────────────────────────────────────────────────────

async def fetch_period_summary(period_days: int) -> NewsSummaryResponse:
    """
    Build the full news digest for the given period (7 or 30 days).

    Steps:
      1. Check in-memory cache.
      2. Compute date range.
      3. Build a digest for every category concurrently.
      4. Assemble NewsSummaryResponse.
      5. Store in cache and return.
    """
    # ── Cache ──────────────────────────────────────────────────────────────
    cache_key = summary_key(period_days)
    cached = await cache_get(cache_key)
    if cached:
        return NewsSummaryResponse(**cached)

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=period_days)

    logger.info(
        f"[summary] Building {period_days}-day digest "
        f"({since.date()} → {now.date()})"
    )

    # ── Concurrently build all category digests ────────────────────────────
    tasks = [
        _build_category_digest(cat, period_days, since)
        for cat in _SUMMARY_CATEGORIES
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    summaries: dict[str, CategorySummary] = {}
    total_articles = 0
    for cat, result in zip(_SUMMARY_CATEGORIES, results):
        if isinstance(result, Exception):
            logger.warning(f"[summary] Category {cat} failed: {result}")
            # Insert an empty placeholder so the key is always present
            summaries[cat] = CategorySummary(
                category=cat,
                article_count=0,
                top_headlines=[],
                summary="Summary unavailable for this category.",
                key_themes=[],
                sentiment_breakdown={"positive": 0, "neutral": 0, "negative": 0},
                sources_cited=[],
            )
        else:
            summaries[cat] = result
            total_articles += result.article_count

    ttl = SUMMARY_7D_TTL if period_days <= 7 else SUMMARY_30D_TTL
    period_label = f"{period_days}days"

    response = NewsSummaryResponse(
        period=period_label,
        period_days=period_days,
        generated_at=now.isoformat(),
        date_range={
            "from": since.date().isoformat(),
            "to": now.date().isoformat(),
        },
        total_articles_processed=total_articles,
        categories_included=_SUMMARY_CATEGORIES,
        summaries=summaries,
    )

    await cache_set(cache_key, response.model_dump(), ttl)
    logger.info(
        f"[summary] {period_days}-day digest built: "
        f"{total_articles} articles across {len(summaries)} categories"
    )
    return response
