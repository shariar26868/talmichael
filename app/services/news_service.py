# app/services/news_service.py
"""News fetching, filtering, and caching business logic."""

import asyncio
import httpx
from fastapi import HTTPException

from app.core.cache import cache_get, cache_set, news_key, bills_key, NEWS_TTL, BILLS_TTL
from app.models.schemas import NewsResponse
from app.utils.rss_parser import parse_rss
from app.utils.filters import is_israeli_source, is_blocked_source, is_opinion, is_negative
from app.utils.feed_config import RSS_FEEDS, KNESSET_BILLS_API


async def fetch_news(
    category: str,
    limit: int,
    israeli_only: bool,
    exclude_negative: bool = False,
    use_cache: bool = True,
) -> NewsResponse:
    """Fetch, filter, and cache news for a given category."""

    # Cache check
    if use_cache:
        key = news_key(category, limit, israeli_only, exclude_negative)
        cached = await cache_get(key)
        if cached:
            return NewsResponse(**cached)

    url = RSS_FEEDS[category]
    multiplier = max(1, 4 if israeli_only else 1, 6 if exclude_negative else 1)
    raw_limit = limit * multiplier

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch RSS: {e}")

    try:
        news = parse_rss(resp.text, raw_limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse RSS: {e}")

    filtered = [
        a for a in news.articles
        if not is_opinion(a.title, a.description)
        and not is_blocked_source(a.source, a.source_url)
    ]

    if israeli_only:
        filtered = [a for a in filtered if is_israeli_source(a.source, a.source_url)]

    if exclude_negative:
        filtered = [a for a in filtered if not is_negative(a.title, a.description)]

    news.articles = filtered[:limit]
    news.total = len(news.articles)

    if use_cache:
        await cache_set(key, news.model_dump(), NEWS_TTL)

    return news


async def fetch_all_news(limit: int) -> dict:
    """Fetch all categories concurrently."""
    from app.utils.feed_config import EXCLUDE_NEGATIVE_CATEGORIES

    tasks = [
        fetch_news(
            cat, limit,
            israeli_only=True,
            exclude_negative=(cat in EXCLUDE_NEGATIVE_CATEGORIES),
        )
        for cat in RSS_FEEDS
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {
        cat: (r if not isinstance(r, Exception) else {"error": str(r)})
        for cat, r in zip(RSS_FEEDS.keys(), results)
    }


async def fetch_knesset_bills(limit: int = 20) -> dict:
    """Fetch bills from Knesset OData API, fallback to RSS."""
    key = bills_key(limit)
    cached = await cache_get(key)
    if cached:
        return cached

    url = KNESSET_BILLS_API.format(limit=limit)
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            data = resp.json()
            bills = data.get("value", [])
            result = {
                "source": "knesset.gov.il OData API",
                "total": len(bills),
                "bills": [
                    {
                        "id": b.get("BillID"),
                        "name": b.get("Name"),
                        "name_hebrew": b.get("NameHeb"),
                        "status": b.get("StatusDesc"),
                        "sub_type": b.get("SubTypeDesc"),
                        "last_updated": b.get("LastUpdatedDate"),
                        "initiator": b.get("InitiatorMKName"),
                    }
                    for b in bills
                ],
            }
        except Exception:
            # Fallback to RSS
            news = await fetch_news("knesset", limit, israeli_only=True)
            result = {
                "source": "Google News RSS (fallback)",
                "total": news.total,
                "articles": [a.model_dump() for a in news.articles],
            }

    await cache_set(key, result, BILLS_TTL)
    return result
