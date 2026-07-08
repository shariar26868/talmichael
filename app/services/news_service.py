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
from app.utils.licensed_apis import fetch_from_newsapi, fetch_from_newsdata_io, fetch_from_gdelt
from app.utils.image_enricher import enrich_images

logger = logging.getLogger(__name__)


def normalize_language(language: Optional[str]) -> str:
    """Normalize the requested UI language to a supported backend language."""
    if not language:
        return "hebrew"
    lang = str(language).strip().lower()
    if lang in {"he", "hebrew", "iw", "iwrit"}:
        return "hebrew"
    if lang in {"en", "eng", "english"}:
        return "english"
    if lang in {"ar", "arabic", "arab", "arabe"}:
        return "arabic"
    return "hebrew"


def _infer_fact_check_label(score: float) -> str:
    if score >= 0.85:
        return "highly_verified"
    if score >= 0.70:
        return "verified"
    if score >= 0.55:
        return "partially_verified"
    if score >= 0.40:
        return "needs_review"
    return "disputed"


def _article_attr(article, name: str, default=None):
    if isinstance(article, dict):
        return article.get(name, default)
    return getattr(article, name, default)


def _set_article_attr(article, name: str, value) -> None:
    if isinstance(article, dict):
        article[name] = value
        return
    setattr(article, name, value)


def _apply_fact_check_fallbacks(article) -> None:
    if getattr(article, "fact_check_percentage", None) is None:
        score = getattr(article, "fact_check_score", None)
        if score is not None:
            try:
                percent = float(score) * 100.0
                article.fact_check_percentage = percent
            except Exception:
                pass

    if getattr(article, "fact_check_details", None) is None:
        pct = getattr(article, "fact_check_percentage", None)
        if pct is not None:
            article.fact_check_details = {
                "label": _infer_fact_check_label(float(pct) / 100.0),
                "components": {},
                "explanation": (
                    "Estimated from the article's fact_check_score until full analysis details "
                    "are available."
                ),
            }


def _apply_category_placeholders(articles: list, category: str) -> None:
    """
    Apply placeholder images for articles that still lack images after enrichment.
    With Unsplash fallback, this should rarely be needed, but provides a minimal SVG
    fallback if all sources fail.
    """
    articles_without_images = [a for a in articles if not getattr(a, "image_url", None)]
    if articles_without_images:
        logger.debug(
            f"Image enrichment incomplete: {len(articles_without_images)}/{len(articles)} "
            f"articles in {category} still lack images (falling back to blank)"
        )
        # Leave image_url as None — client should handle gracefully
        # Or optionally add a minimal placeholder here if needed


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


def _select_sources_for_fetch(
    source_map: dict[str, str],
    category: str,
    language: str,
    max_sources: int = 24,
) -> list[tuple[str, str]]:
    """Order source feeds so global categories receive meaningful international coverage."""
    if not source_map:
        return []

    israeli_names = set(ISRAELI_SOURCES_FEEDS)
    international_names = set(INTERNATIONAL_SOURCES_FEEDS)
    arabic_names = set(ARABIC_SOURCES_FEEDS)

    source_items = list(source_map.items())
    israeli = [(name, url) for name, url in source_items if name in israeli_names]
    international = [(name, url) for name, url in source_items if name in international_names]
    arabic = [(name, url) for name, url in source_items if name in arabic_names]

    used_names = {name for name, _ in israeli} | {name for name, _ in international} | {name for name, _ in arabic}
    topic = [(name, url) for name, url in source_items if name not in used_names]

    if language.lower() == "arabic":
        priority_groups = [arabic, israeli, topic]
    elif category == "positive":
        priority_groups = [topic, israeli, international]
    elif category in {"international", "community", "science", "education"}:
        priority_groups = [international, topic, israeli]
    else:
        priority_groups = [topic, international, israeli]

    selected: list[tuple[str, str]] = []
    seen_names: set[str] = set()
    for group in priority_groups:
        for name, url in group:
            if name in seen_names:
                continue
            selected.append((name, url))
            seen_names.add(name)
            if len(selected) >= max_sources:
                return selected

    return selected[:max_sources]


async def fetch_news(
    category: str,
    limit: int,
    israeli_only: bool = False,
    exclude_negative: bool = False,
    exclude_positive: bool = False,
    use_cache: bool = True,
    with_analysis: bool = False,
    language: Optional[str] = None,
    user_tier: str = "free",
    source_type: Optional[Literal["israel", "global"]] = None,
    force_refresh: bool = False,
    force_today_priority: bool = False,
) -> NewsResponse:
    """
    Fetch mixed Israel + Global news for the given category.

    Parameters:
    • israeli_only: If True, filter to Israeli sources only (e.g., for Sport).
    • exclude_negative: Remove negative sentiment articles.
    • exclude_positive: Remove positive sentiment articles (for Science/Education/Culture).
    • force_today_priority: If True, prioritize today's articles and stop showing older articles
      if threshold reached (for Security, Politics, Economy, Sport).
    • with_analysis: Enable AI sentiment/bias analysis (pro/platinum users only).
    """
    normalized_language = normalize_language(language)

    # ── Cache key (include category, limit, language, tier, analysis) ─────────
    if use_cache and not force_refresh:
        key = news_key(category, limit, False, exclude_negative, normalized_language, user_tier, with_analysis)
        cached = await cache_get(key)
        if cached:
            return NewsResponse(**cached)

    # ── Step 1: Build mixed source list ───────────────────────────────────────
    if israeli_only:
        # Sport Israeli-only: use only Israeli sources
        sources_to_fetch = ISRAELI_SOURCES_FEEDS.copy()
    else:
        sources_to_fetch = _build_mixed_source_list(category, normalized_language)

    # Limit parallel requests while keeping global coverage broad enough for the app.
    MAX_SOURCES = min(24, max(18, limit + 4))
    per_source_limit = max(5, min(10, (limit // 3) + 3))
    selected_sources = _select_sources_for_fetch(
        sources_to_fetch,
        category=category,
        language=normalized_language,
        max_sources=MAX_SOURCES,
    )

    logger.info(
        f"[{category}] Fetching from {len(selected_sources)} mixed sources "
        f"(Israel + Global), {per_source_limit} articles/source"
    )

    # ── Step 2: Parallel fetch ────────────────────────────────────────────────
    fetch_tasks = [
        _fetch_single_feed(feed_url, source_name, per_source_limit)
        for source_name, feed_url in selected_sources
    ]
    # Add licensed API fetches in parallel where available (non-blocking)
    # NOTE: Disabled to avoid rate limiting (100 req/24hr limit reached)
    # Uncomment when using paid API tiers or when rate limit has reset
    # try:
    #     # Use topic_query based on category
    #     topic_query = category
    #     fetch_tasks.append(fetch_from_newsapi(topic_query, limit=per_source_limit))
    #     fetch_tasks.append(fetch_from_newsdata_io(topic_query, limit=per_source_limit))
    #     fetch_tasks.append(fetch_from_gdelt(topic_query, limit=per_source_limit))
    # except Exception:
    #     pass
    results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

    all_articles = []
    for result in results:
        if isinstance(result, list):
            all_articles.extend(result)
        # Silently skip exceptions (already logged in _fetch_single_feed)

    # ── Step 3: Enrich each article with source_url + source_type ─────────────
    for article in all_articles:
        source = _article_attr(article, "source")
        source_url = _article_attr(article, "source_url")
        if not source_url and source:
            source_url = get_source_info(source).get("url") or None
            _set_article_attr(article, "source_url", source_url)
        try:
            source_type = (
                "israel"
                if is_israeli_source(source, source_url)
                else "global"
            )
        except Exception:
            source_type = "global"
        _set_article_attr(article, "source_type", source_type)

    # ── Step 4: Filters ───────────────────────────────────────────────────────

    filtered = []
    from datetime import datetime, timedelta
    today_date = datetime.utcnow().date()
    yesterday_date = today_date - timedelta(days=1)
    two_days_ago = today_date - timedelta(days=2)
    three_days_ago = today_date - timedelta(days=3)

    for a in all_articles:
        source = _article_attr(a, "source")
        source_url = _article_attr(a, "source_url")
        title = _article_attr(a, "title", "")
        description = _article_attr(a, "description", "")

        # Block known spam/wiki sources
        if is_blocked_source(source, source_url):
            continue
        # Opinion pieces out
        if is_opinion(title, description):
            continue
        # 🔑 TOPIC RELEVANCE — this is the key guard that keeps content on-topic
        if not is_topic_relevant(category, title, description, source, source_url):
            continue
        # Sentiment filtering: exclude negative if requested
        if exclude_negative and is_negative(title, description):
            continue
        # Sentiment filtering: exclude positive (Science, Education, Culture show negative only)
        if exclude_positive:
            positive_keywords = (
                "achievement", "success", "breakthrough", "award", "positive",
                "hope", "recovery", "progress", "improve", "winner",
            )
            title_desc = f"{title or ''} {description or ''}".lower()
            if any(kw in title_desc for kw in positive_keywords):
                continue
        filtered.append(a)

    # ── Step 5: Date-based prioritization (if force_today_priority) ─────────────
    if force_today_priority:
        today_articles = []
        yesterday_articles = []
        two_days_articles = []
        three_days_articles = []
        older_articles = []

        for a in filtered:
            pub_date_value = _article_attr(a, "pub_date")
            try:
                article_date = pub_date_value.date() if hasattr(pub_date_value, 'date') else pub_date_value
            except Exception:
                article_date = None
            if article_date == today_date:
                today_articles.append(a)
            elif article_date == yesterday_date:
                yesterday_articles.append(a)
            elif article_date == two_days_ago:
                two_days_articles.append(a)
            elif article_date == three_days_ago:
                three_days_articles.append(a)
            else:
                older_articles.append(a)

        # Priority: TODAY first, then yesterday, then 2 days, then 3 days, then older
        # If today's articles >= limit, don't show older
        prioritized = today_articles.copy()
        if len(prioritized) < limit:
            prioritized.extend(yesterday_articles)
        if len(prioritized) < limit:
            prioritized.extend(two_days_articles)
        if len(prioritized) < limit:
            prioritized.extend(three_days_articles)
        if len(prioritized) < limit:
            prioritized.extend(older_articles)

        filtered = prioritized

    # ── Step 5b: Deduplicate by URL ────────────────────────────────────────────
    seen_urls: set[str] = set()
    deduplicated = []
    for article in filtered:
        if article.link and article.link not in seen_urls:
            seen_urls.add(article.link)
            deduplicated.append(article)

    final_articles = deduplicated[:limit]

    # ── Step 5b: Image enrichment ───────────────────────────────────────────────
    # Enriches images via fallback chain:
    #   1. OG image from article URL (publisher's image)
    #   2. Title-specific Unsplash search
    #   3. Category-specific Unsplash image
    # Results are cached per-URL for 1 hour.
    final_articles = await enrich_images(final_articles, category=category)
    _apply_category_placeholders(final_articles, category)

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

    # ── Enrich articles with DB-stored fact-check fields if available ────────
    try:
        from app.core.database import get_db
        db = get_db()
        ids = []
        guid_map = {}
        for a in news.articles:
            gid = getattr(a, "guid", None) or getattr(a, "link", None)
            if gid:
                ids.append(gid)
                guid_map[gid] = a

        if ids:
            rows = await db.cached_articles.find({"guid": {"$in": ids}}, {"guid": 1, "fact_check_percentage": 1, "fact_check_details": 1}).to_list(length=len(ids))
            for r in rows:
                g = r.get("guid")
                obj = guid_map.get(g)
                if not obj:
                    continue
                try:
                    if r.get("fact_check_percentage") is not None:
                        setattr(obj, "fact_check_percentage", float(r.get("fact_check_percentage")))
                    if r.get("fact_check_details") is not None:
                        setattr(obj, "fact_check_details", r.get("fact_check_details"))
                except Exception:
                    pass
    except Exception:
        pass

    # ── Step 6.5: Fallback immediate fact-check fields from existing score ───
    for a in news.articles:
        _apply_fact_check_fallbacks(a)

    # ── Step 6.6: Attach automatic social context to articles ───────────────
    try:
        from app.routes.social_media import build_social_query, _get_tw_api, _TWSCRAPE_AVAILABLE
        if _TWSCRAPE_AVAILABLE and news.articles:
            async def _attach_social_context(article):
                try:
                    if not getattr(article, "link", None):
                        return
                    query = build_social_query(article)
                    api = _get_tw_api()
                    tweets = []
                    async for tweet in api.search(query, limit=3):
                        tweets.append({
                            "id": str(tweet.id),
                            "username": tweet.user.username if tweet.user else "unknown",
                            "text": getattr(tweet, "rawContent", "") or "",
                            "url": f"https://twitter.com/{tweet.user.username}/status/{tweet.id}" if tweet.user else None,
                        })
                        if len(tweets) >= 3:
                            break
                    if tweets:
                        setattr(article, "social_context", tweets)
                except Exception as exc:
                    logger.warning("Automatic social context failed for %s: %s", article.link, exc)

            await asyncio.gather(*[_attach_social_context(a) for a in news.articles[:8]])
    except Exception as exc:
        logger.warning("Social context enrichment failed: %s", exc)

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
    if use_cache or force_refresh:
        key = news_key(category, limit, False, exclude_negative, normalized_language, user_tier, with_analysis)
        await cache_set(key, news.model_dump(exclude_none=True), NEWS_TTL)

    # ── Persist articles to MongoDB (fire-and-forget) ─────────────────────────
    # Save every fetched article to db.cached_articles so they are available
    # for search, history, and cross-source analysis without re-fetching.
    asyncio.create_task(_save_articles_to_db(news.articles, category))

    return news


async def _save_articles_to_db(articles: list, category: str) -> None:
    """
    Upsert fetched articles into db.cached_articles.
    Uses guid (or link) as the unique key — safe to call multiple times.
    Runs as a background task so it never blocks the API response.
    """
    try:
        from app.core.database import get_db
        from datetime import datetime

        db = get_db()
        now = datetime.utcnow()

        ops = []
        from pymongo import UpdateOne

        for art in articles:
            try:
                d = art.model_dump() if hasattr(art, "model_dump") else dict(art)
            except Exception:
                continue

            unique_key = d.get("guid") or d.get("link")
            if not unique_key:
                continue

            d["category"] = category
            d["fetched_at"] = now
            # Normalize fact-check percentage for storage (0-100)
            try:
                if "fact_check_score" in d and "fact_check_percentage" not in d:
                    score = d.get("fact_check_score")
                    if isinstance(score, (int, float)):
                        d["fact_check_percentage"] = float(score) * 100.0
            except Exception:
                pass

            ops.append(
                UpdateOne(
                    {"guid": unique_key},
                    {"$setOnInsert": {"first_seen": now}, "$set": d},
                    upsert=True,
                )
            )
            # enqueue lightweight fact-check analysis (non-blocking)
            try:
                from app.services.fact_check_service import analyze_and_store_article
                asyncio.create_task(analyze_and_store_article(d))
            except Exception:
                pass

        if ops:
            result = await db.cached_articles.bulk_write(ops, ordered=False)
            logger.debug(
                "[cached_articles] category=%s upserted=%d matched=%d",
                category, result.upserted_count, result.matched_count,
            )
    except Exception as e:
        logger.warning("Failed to save articles to MongoDB: %s", e)




async def fetch_all_news(
    limit: int,
    user_tier: str = "free",
    with_analysis: bool = False,
    use_cache: bool = True,
) -> dict:
    """Fetch all categories concurrently, each with mixed Israel + Global content."""
    from app.utils.feed_config import EXCLUDE_NEGATIVE_CATEGORIES

    tasks = [
        fetch_news(
            cat, limit,
            exclude_negative=(cat in EXCLUDE_NEGATIVE_CATEGORIES),
            user_tier=user_tier,
            with_analysis=with_analysis,
            use_cache=use_cache,
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
            source = article.get("source") if isinstance(article, dict) else getattr(article, "source", None)
            source_url = article.get("source_url") if isinstance(article, dict) else getattr(article, "source_url", None)
            current_source_type = (
                article.get("source_type") if isinstance(article, dict) else getattr(article, "source_type", None)
            )
            if not current_source_type:
                source_type = "israel" if is_israeli_source(source, source_url) else "global"
                if isinstance(article, dict):
                    article["source_type"] = source_type
                else:
                    article.source_type = source_type
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
        "articles": [
            a.model_dump(exclude_none=True) if hasattr(a, "model_dump") else a
            for a in final_articles
        ],
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
                "articles": [a.model_dump(exclude_none=True) for a in news.articles],
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
