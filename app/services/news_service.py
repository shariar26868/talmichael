# app/services/news_service.py
"""News fetching, filtering, and caching business logic.

Architecture (Mixed Israel + Global per topic):
─────────────────────────────────────────────
Every category API now returns a MIXED feed of:
  • Israel-specific articles (from ISRAELI_SOURCES_FEEDS + topic Google News IL)
  • Global articles (from INTERNATIONAL_SOURCES_FEEDS + topic Google News World)

Topic relevance is enforced by keyword filters (filters.py → is_topic_relevant)
so that e.g. sport articles never bleed into the political feed regardless of
which source produced them.

Flow per request:
  1. Build source list  → TOPIC_MIXED_FEEDS[category] +
                          ISRAELI_SOURCES_FEEDS (always) +
                          INTERNATIONAL_SOURCES_FEEDS (always)
  2. Parallel fetch     → asyncio.gather over all sources
  3. Topic filter       → is_topic_relevant(category, title, description)
  4. Standard filters   → opinion, blocked, negative (if requested)
  5. Deduplicate + sort → by published date
  6. Tag source_type    → "israel" | "global"
  7. Cache + return
"""

import asyncio
import logging
import httpx
from fastapi import HTTPException
from typing import Literal, Optional
from urllib.parse import quote

from app.core.cache import cache_get, cache_set, news_key, bills_key, NEWS_TTL, BILLS_TTL
from app.core.config import settings
from app.models.schemas import NewsResponse
from app.utils.rss_parser import parse_rss
from app.utils.filters import (
    is_israeli_source, is_blocked_source, is_opinion, is_negative,
    is_topic_relevant,
)
from app.utils.feed_config import (
    RSS_FEEDS, TOPIC_MIXED_FEEDS, KNESSET_BILLS_API,
    ISRAELI_SOURCES_FEEDS, INTERNATIONAL_SOURCES_FEEDS, ARABIC_SOURCES_FEEDS,
    get_all_feeds, get_feeds_by_language, get_source_info,
)
from app.utils.image_enricher import enrich_images

logger = logging.getLogger(__name__)


# ── HTTP headers shared across all fetches ─────────────────────────────────────
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/rss+xml,application/xml,text/xml,"
        "application/xhtml+xml,text/html;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.5,he;q=0.3",
}


async def knesset_api_status() -> dict:
    """Check lightweight connectivity to the Knesset bills OData API."""
    try:
        async with httpx.AsyncClient(
            timeout=6.0, headers=_HEADERS,
            follow_redirects=True, trust_env=False,
        ) as client:
            url = KNESSET_BILLS_API.format(limit=1)
            resp = await client.get(url)
            resp.raise_for_status()
            return {"reachable": True, "message": "Knesset API reachable"}
    except Exception as e:
        return {"reachable": False, "message": f"Knesset API unreachable: {str(e)}"}


async def _fetch_single_feed(url: str, source_name: str, limit: int) -> list:
    """Fetch and parse a single RSS feed. Returns [] on any error (non-fatal)."""
    try:
        async with httpx.AsyncClient(
            timeout=10.0, headers=_HEADERS,
            follow_redirects=True, trust_env=False,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        news = parse_rss(resp.content, limit)
        for article in news.articles:
            if not article.source:
                article.source = source_name
        return news.articles
    except Exception as e:
        logger.warning(f"Feed fetch failed [{source_name}]: {e}")
        return []


def _build_mixed_source_list(category: str, language: str) -> dict[str, str]:
    """
    Build the full mixed source dict for a given category.

    Always includes:
      • All Israeli sources  (Israeli media covering Israel + global events)
      • All International sources  (global media, includes Israel coverage)
      • TOPIC_MIXED_FEEDS[category]  (targeted Google News RSS for Israel + global)

    For Arabic language: uses Arabic sources instead of International.

    Returns: {source_name: feed_url}
    """
    sources: dict[str, str] = {}

    if language.lower() == "arabic":
        # Arabic feed: all Arabic + Israeli sources mixed
        sources.update(ARABIC_SOURCES_FEEDS)
        sources.update(ISRAELI_SOURCES_FEEDS)
    else:
        # Default: Israeli + International sources (always mixed)
        sources.update(ISRAELI_SOURCES_FEEDS)
        sources.update(INTERNATIONAL_SOURCES_FEEDS)

    # Layer on topic-targeted Google News feeds (both IL + Global per topic)
    topic_feeds = TOPIC_MIXED_FEEDS.get(category, {})
    sources.update(topic_feeds)

    return sources


async def fetch_news(
    category: str,
    limit: int,
    israeli_only: bool = False,          # Kept for backward-compat; ignored in new logic
    exclude_negative: bool = False,
    use_cache: bool = True,
    with_analysis: bool = False,
    language: str = "english",
    user_tier: str = "free",
    source_type: Optional[Literal["israel", "global"]] = None,  # Kept for compat; ignored
) -> NewsResponse:
    """
    Fetch mixed Israel + Global news for the given category.

    Key design decisions:
    • ALL categories fetch BOTH Israeli and global sources simultaneously.
    • Topic relevance is enforced via keyword filters (TOPIC_KEYWORDS in filters.py),
      so political feeds won't show sport articles even from general news sources.
    • The `israeli_only` and `source_type` params are intentionally ignored —
      every API now returns mixed content by design.
    • Articles are tagged with source_type="israel" | "global" so clients can
      still filter/display by origin if desired.
    """
    # ── Cache key (include category, limit, language, tier, analysis) ─────────
    if use_cache:
        key = news_key(category, limit, False, exclude_negative, language, user_tier, with_analysis)
        cached = await cache_get(key)
        if cached:
            return NewsResponse(**cached)

    # ── Step 1: Build mixed source list ───────────────────────────────────────
    sources_to_fetch = _build_mixed_source_list(category, language)

    # Limit parallel requests: top 30 sources max to keep latency acceptable
    MAX_SOURCES = 30
    per_source_limit = max(5, limit // max(1, min(len(sources_to_fetch), MAX_SOURCES)))
    selected_sources = list(sources_to_fetch.items())[:MAX_SOURCES]

    logger.info(
        f"[{category}] Fetching from {len(selected_sources)} mixed sources "
        f"(Israel + Global), {per_source_limit} articles/source"
    )

    # ── Step 2: Parallel fetch ────────────────────────────────────────────────
    fetch_tasks = [
        _fetch_single_feed(feed_url, source_name, per_source_limit)
        for source_name, feed_url in selected_sources
    ]
    results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

    all_articles = []
    for result in results:
        if isinstance(result, list):
            all_articles.extend(result)
        # Silently skip exceptions (already logged in _fetch_single_feed)

    # ── Step 3: Enrich each article with source_url + source_type ─────────────
    for article in all_articles:
        if not article.source_url and article.source:
            article.source_url = get_source_info(article.source).get("url") or None
        try:
            article.source_type = (
                "israel"
                if is_israeli_source(article.source, article.source_url)
                else "global"
            )
        except Exception:
            article.source_type = "global"

    # ── Step 4: Filters ───────────────────────────────────────────────────────

    filtered = []
    for a in all_articles:
        # Block known spam/wiki sources
        if is_blocked_source(a.source, a.source_url):
            continue
        # Opinion pieces out
        if is_opinion(a.title, a.description):
            continue
        # 🔑 TOPIC RELEVANCE — this is the key guard that keeps content on-topic
        # across ALL sources (both Israeli general news and global general news)
        if not is_topic_relevant(category, a.title, a.description):
            continue
        filtered.append(a)

    # Optional: exclude negative sentiment articles
    if exclude_negative:
        filtered = [a for a in filtered if not is_negative(a.title, a.description)]

    # ── Step 5: Deduplicate by URL ────────────────────────────────────────────
    seen_urls: set[str] = set()
    deduplicated = []
    for article in filtered:
        if article.link and article.link not in seen_urls:
            seen_urls.add(article.link)
            deduplicated.append(article)

    final_articles = deduplicated[:limit]

    # ── Step 5b: OG Image enrichment ─────────────────────────────────────────
    # Fetch og:image for articles missing image_url (e.g. Al Jazeera, Middle East Eye).
    # Runs concurrently with semaphore; results are cached per-URL for 1 hour.
    final_articles = await enrich_images(final_articles)

    # Count how many are Israeli vs global for metadata
    israel_count = sum(1 for a in final_articles if getattr(a, "source_type", "") == "israel")
    global_count = len(final_articles) - israel_count

    # ── Step 6: Build response ────────────────────────────────────────────────
    from app.utils.rss_parser import FeedMeta
    news = NewsResponse(
        meta=FeedMeta(
            title=f"Mixed News — {category.title()} (Israel + Global)",
            description=(
                f"{len(final_articles)} articles from {len(selected_sources)} sources "
                f"[{israel_count} Israel / {global_count} Global]"
            ),
            link="https://talmicahel.com",
            last_build_date="",
            fetched_at="",
        ),
        total=len(final_articles),
        articles=final_articles,
    )

    # ── Step 7: Optional AI analysis ─────────────────────────────────────────
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

    # ── Cache result ──────────────────────────────────────────────────────────
    if use_cache:
        key = news_key(category, limit, False, exclude_negative, language, user_tier, with_analysis)
        await cache_set(key, news.model_dump(), NEWS_TTL)

    return news


async def fetch_all_news(limit: int, user_tier: str = "free", with_analysis: bool = False) -> dict:
    """Fetch all categories concurrently, each with mixed Israel + Global content."""
    from app.utils.feed_config import EXCLUDE_NEGATIVE_CATEGORIES

    tasks = [
        fetch_news(
            cat, limit,
            exclude_negative=(cat in EXCLUDE_NEGATIVE_CATEGORIES),
            user_tier=user_tier,
            with_analysis=with_analysis,
        )
        for cat in RSS_FEEDS
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    combined = []
    for r in results:
        if isinstance(r, Exception):
            logger.warning(f"fetch_all_news task error: {r}")
            continue
        try:
            combined.extend(r.articles)
        except Exception:
            if isinstance(r, dict) and r.get("articles"):
                combined.extend(r.get("articles"))

    # Deduplicate
    seen: set[str] = set()
    deduped = []
    for a in combined:
        link = a.get("link") if isinstance(a, dict) else getattr(a, "link", None)
        if not link or link in seen:
            continue
        seen.add(link)
        deduped.append(a)

    # Ensure source_type on all
    for article in deduped:
        try:
            if not getattr(article, "source_type", None):
                article.source_type = (
                    "israel"
                    if is_israeli_source(
                        getattr(article, "source", None),
                        getattr(article, "source_url", None),
                    )
                    else "global"
                )
        except Exception:
            pass

    final_articles = deduped[:limit]
    israel_count = sum(
        1 for a in final_articles
        if (a.get("source_type") if isinstance(a, dict) else getattr(a, "source_type", "")) == "israel"
    )

    return {
        "meta": {
            "title": "All News — Mixed Israel + Global",
            "description": (
                f"Combined {len(final_articles)} articles from {len(RSS_FEEDS)} categories "
                f"[{israel_count} Israel / {len(final_articles) - israel_count} Global]"
            ),
            "link": "https://talmicahel.com",
            "last_build_date": "",
            "fetched_at": "",
        },
        "total": len(final_articles),
        "articles": [a.model_dump() if hasattr(a, "model_dump") else a for a in final_articles],
    }


async def fetch_knesset_bills(limit: int = 20) -> dict:
    """Fetch bills from Knesset OData API, fallback to RSS."""
    key = bills_key(limit)
    cached = await cache_get(key)
    if cached:
        return cached

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
        # Fallback: fetch_news with knesset category (mixed)
        try:
            news = await fetch_news("knesset", limit)
            result = {
                "source": "Google News RSS fallback (mixed)",
                "official_api_reachable": False,
                "official_api_notice": "Official Knesset API unreachable; using mixed RSS fallback",
                "total": news.total,
                "articles": [a.model_dump() for a in news.articles],
            }
        except Exception:
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
                        try:
                            sresp = await client.get(
                                f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title, safe='')}",
                                headers={"User-Agent": "Mozilla/5.0"},
                            )
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
                        "official_api_notice": "All primary sources failed; using Wikipedia fallback",
                        "total": len(articles),
                        "articles": articles,
                    }
            except Exception:
                result = {
                    "source": "unavailable",
                    "official_api_reachable": False,
                    "official_api_notice": "All sources failed to provide bill data",
                    "total": 0,
                    "bills": [],
                }

    await cache_set(key, result, BILLS_TTL)
    return result
