# app/services/news_service.py
"""News fetching, filtering, and caching business logic."""

import asyncio
import httpx
from fastapi import HTTPException
from typing import Literal, Optional
from urllib.parse import quote

from app.core.cache import cache_get, cache_set, news_key, bills_key, NEWS_TTL, BILLS_TTL
from app.core.config import settings
from app.models.schemas import NewsResponse
from app.utils.rss_parser import parse_rss
from app.utils.filters import is_israeli_source, is_blocked_source, is_opinion, is_negative
from app.utils.feed_config import (
    RSS_FEEDS, KNESSET_BILLS_API, ISRAELI_SOURCES_FEEDS, 
    INTERNATIONAL_SOURCES_FEEDS, ARABIC_SOURCES_FEEDS,
    get_all_feeds, get_feeds_by_language, get_source_info
)


async def knesset_api_status() -> dict:
    """Check lightweight connectivity to the Knesset bills OData API.
    Returned dict: {"reachable": bool, "message": str}
    Cached at caller side if needed.
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json,text/plain,*/*;q=0.9",
        }
        async with httpx.AsyncClient(timeout=6.0, headers=headers, follow_redirects=True, trust_env=False) as client:
            url = KNESSET_BILLS_API.format(limit=1)
            resp = await client.get(url)
            resp.raise_for_status()
            return {"reachable": True, "message": "Knesset API reachable"}
    except Exception as e:
        return {"reachable": False, "message": f"Knesset API unreachable: {str(e)}"}


async def _fetch_single_feed(url: str, source_name: str, limit: int) -> list:
    """Fetch and parse a single RSS feed."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml,application/xml,text/xml,application/xhtml+xml,text/html;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        async with httpx.AsyncClient(timeout=8.0, headers=headers, follow_redirects=True, trust_env=False) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        news = parse_rss(resp.content, limit)
        # Tag with source
        for article in news.articles:
            if not article.source:
                article.source = source_name
        return news.articles
    except Exception as e:
        # Log but don't fail — continue with other sources
        import logging
        logging.warning(f"Failed to fetch {source_name}: {e}")
        return []


async def fetch_news(
    category: str,
    limit: int,
    israeli_only: bool,
    exclude_negative: bool = False,
    use_cache: bool = True,
    with_analysis: bool = False,   # AI analysis disabled by default (OpenAI key issues)
    language: str = "english",   # hebrew | english | arabic
    user_tier: str = "free",
    source_type: Optional[Literal["israel", "global"]] = None,
) -> NewsResponse:
    """Fetch, filter, cache, and optionally AI-analyze news from multiple sources."""

    # Normalize source_type (if provided) and derive israeli_only when explicitly specified.
    if source_type is not None:
        source_type = source_type.lower()
        if source_type == "israel":
            israeli_only = True
        elif source_type == "global":
            israeli_only = False

    # Cache check (do not include source_type since selection is derived from israeli_only/language)
    if use_cache:
        key = news_key(category, limit, israeli_only, exclude_negative, language, user_tier, with_analysis)
        cached = await cache_get(key)
        if cached:
            return NewsResponse(**cached)

    # ── Step 1: Select sources based on parameters ────────────────────────────
    
    sources_to_fetch: dict[str, str] = {}
    
    if source_type == "israel":
        sources_to_fetch = ISRAELI_SOURCES_FEEDS.copy()
    elif source_type == "global":
        if language.lower() == "arabic":
            sources_to_fetch = ARABIC_SOURCES_FEEDS.copy()
        else:
            sources_to_fetch = INTERNATIONAL_SOURCES_FEEDS.copy()
    elif israeli_only:
        sources_to_fetch = ISRAELI_SOURCES_FEEDS.copy()
    elif language.lower() == "hebrew":
        sources_to_fetch = ISRAELI_SOURCES_FEEDS.copy()
    elif language.lower() == "arabic":
        sources_to_fetch = ARABIC_SOURCES_FEEDS.copy()
    else:
        # English: combine international + Israeli sources
        sources_to_fetch = INTERNATIONAL_SOURCES_FEEDS.copy()
        sources_to_fetch.update(ISRAELI_SOURCES_FEEDS)
    
    # ── Step 2: Parallel fetch from multiple sources ──────────────────────────
    
    # Limit parallel requests to avoid overwhelming servers
    per_source_limit = max(3, limit // 8)  # Distribute limit across more sources
    
    fetch_tasks = [
        _fetch_single_feed(feed_url, source_name, per_source_limit)
        for source_name, feed_url in list(sources_to_fetch.items())[:25]  # Top 25 sources
    ]
    
    results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
    all_articles = []
    for result in results:
        if isinstance(result, list):
            all_articles.extend(result)
        # Silently skip errors (already logged in _fetch_single_feed)

    # Fill missing source_url from configured source metadata when RSS item omitted source info.
    for article in all_articles:
        if not article.source_url and article.source:
            article.source_url = get_source_info(article.source).get("url") or None
        # Set per-article source_type: 'israel' if source determined Israeli, else 'global'
        try:
            article.source_type = "israel" if is_israeli_source(article.source, article.source_url) else "global"
        except Exception:
            article.source_type = "global"

    # ── Step 3: Filter ────────────────────────────────────────────────────────
    
    filtered = [
        a for a in all_articles
        if not is_opinion(a.title, a.description)
        and not is_blocked_source(a.source, a.source_url)
    ]

    if israeli_only:
        filtered = [a for a in filtered if is_israeli_source(a.source, a.source_url)]

    if exclude_negative:
        filtered = [a for a in filtered if not is_negative(a.title, a.description)]

    # Remove duplicates (same URL)
    seen_urls = set()
    deduplicated = []
    for article in filtered:
        if article.link not in seen_urls:
            seen_urls.add(article.link)
            deduplicated.append(article)
    
    filtered = deduplicated[:limit]
    
    # ── Step 4: Create response ────────────────────────────────────────────────
    
    from app.utils.rss_parser import FeedMeta
    display_source = source_type.title() if source_type else ("Israel" if israeli_only else "Global")
    news = NewsResponse(
        meta=FeedMeta(
            title=f"{display_source} News - {category.title()}",
            description=f"Top {len(filtered)} articles from {len(sources_to_fetch)} sources",
            link="https://talmicahel.com",
            last_build_date="",
            fetched_at=""
        ),
        total=len(filtered),
        articles=filtered
    )

    # ── Step 5: Auto AI analysis ──────────────────────────────────────────────
    
    if with_analysis and news.articles:
        from app.services.ai_service import analyze_article
        analyses = await asyncio.gather(*[
            analyze_article(
                guid=a.guid or a.link,
                title=a.title,
                description=a.description,
                source=a.source,
                source_url=a.source_url,
                user_tier=user_tier,
            )
            for a in news.articles
        ], return_exceptions=True)

        for article, analysis in zip(news.articles, analyses):
            if not isinstance(analysis, Exception):
                article.sentiment = analysis.sentiment
                article.bias = analysis.bias
                article.bias_score = analysis.bias_score
                article.bias_types = analysis.bias_types
                article.bias_category = analysis.bias_category
                article.credibility_score = analysis.credibility_score
                article.credibility_label = analysis.credibility_label
                article.fact_check_score = analysis.fact_check_score
                article.summary_hebrew = analysis.summary_hebrew
                article.topics = analysis.topics
                article.claims = analysis.claims
                article.factual_points = analysis.factual_points
                article.claim_explanation = analysis.claim_explanation
                article.bias_explanation = analysis.bias_explanation

    if use_cache:
        key = news_key(category, limit, israeli_only, exclude_negative, language, user_tier, with_analysis)
        await cache_set(key, news.model_dump(), NEWS_TTL)

    return news


async def fetch_all_news(limit: int, user_tier: str = "free", with_analysis: bool = False) -> dict:
    """Fetch all categories concurrently."""
    from app.utils.feed_config import EXCLUDE_NEGATIVE_CATEGORIES

    tasks = [
        fetch_news(
            cat, limit,
            israeli_only=True,
            exclude_negative=(cat in EXCLUDE_NEGATIVE_CATEGORIES),
            user_tier=user_tier,
            with_analysis=with_analysis,
        )
        for cat in RSS_FEEDS
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Combine all fetched articles into a single list
    combined = []
    for r in results:
        if isinstance(r, Exception):
            continue
        # r is a NewsResponse
        try:
            combined.extend(r.articles)
        except Exception:
            # If it's a dict (error/fallback), try to extract 'articles'
            if isinstance(r, dict) and r.get("articles"):
                combined.extend(r.get("articles"))

    # Deduplicate by link while preserving order
    seen = set()
    deduped = []
    for a in combined:
        link = getattr(a, "link", None) or a.get("link") if isinstance(a, dict) else None
        if not link:
            continue
        if link in seen:
            continue
        seen.add(link)
        deduped.append(a)

    # Ensure per-article `source_type` exists
    for article in deduped:
        try:
            if not getattr(article, "source_type", None):
                article.source_type = "israel" if is_israeli_source(getattr(article, "source", None), getattr(article, "source_url", None)) else "global"
        except Exception:
            try:
                if isinstance(article, dict) and not article.get("source_type"):
                    article["source_type"] = "global"
            except Exception:
                pass

    # Limit the combined list to requested `limit`
    final_articles = deduped[:limit]

    # Build a unified NewsResponse-like dict
    from app.utils.rss_parser import FeedMeta
    news = {
        "meta": {
            "title": "All News",
            "description": f"Combined top {len(final_articles)} articles from {len(RSS_FEEDS)} categories",
            "link": "https://talmicahel.com",
            "last_build_date": "",
            "fetched_at": "",
        },
        "total": len(final_articles),
        "articles": [a.model_dump() if hasattr(a, "model_dump") else a for a in final_articles],
    }

    return news


async def fetch_knesset_bills(limit: int = 20) -> dict:
    """Fetch bills from Knesset OData API, fallback to RSS."""
    key = bills_key(limit)
    cached = await cache_get(key)
    if cached:
        return cached
    # Try official Knesset OData API first
    url = KNESSET_BILLS_API.format(limit=limit)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            data = resp.json()
            bills = data.get("value", [])
            result = {
                "source": "knesset.gov.il OData API",
                "official_api_reachable": True,
                "official_api_notice": "Connected to official Knesset OData API",
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
        # Primary fallback: Google News RSS (keeps previous behavior)
        try:
            news = await fetch_news("knesset", limit, israeli_only=True)
            result = {
                "source": "Google News RSS fallback",
                "official_api_reachable": False,
                "official_api_notice": "Official Knesset API unreachable; using Google News RSS fallback",
                "total": news.total,
                "articles": [a.model_dump() for a in news.articles],
            }
        except Exception:
            # Secondary fallback: Wikipedia search summaries
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        "https://en.wikipedia.org/w/api.php",
                        params={
                            "action": "query",
                            "list": "search",
                            "srsearch": "Knesset bills",
                            "format": "json",
                            "utf8": 1,
                            "srlimit": str(limit),
                        },
                        headers={"User-Agent": "Mozilla/5.0"},
                    )
                    resp.raise_for_status()
                    payload = resp.json()
                    items = payload.get("query", {}).get("search", [])
                    articles = []
                    for it in items:
                        title = it.get("title")
                        # fetch summary
                        try:
                            sresp = await client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title, safe='')}", headers={"User-Agent": "Mozilla/5.0"})
                            sresp.raise_for_status()
                            summary = sresp.json()
                        except Exception:
                            summary = {"extract": it.get("snippet", "")}
                        articles.append({
                            "title": title,
                            "summary": summary.get("extract"),
                            "source": "Wikipedia fallback",
                        })
                    result = {
                        "source": "Wikipedia fallback",
                        "official_api_reachable": False,
                        "official_api_notice": "Official Knesset API unreachable; using Wikipedia fallback",
                        "total": len(articles),
                        "articles": articles,
                    }
            except Exception:
                # Final degrade: empty response with flag
                result = {
                    "source": "unavailable",
                    "official_api_reachable": False,
                    "official_api_notice": "All sources failed to provide bill data",
                    "total": 0,
                    "bills": [],
                }

    await cache_set(key, result, BILLS_TTL)
    return result
