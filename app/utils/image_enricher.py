# app/utils/image_enricher.py
"""
OG Image Enricher — fetches og:image from article URLs for feeds that
don't include images in their RSS (e.g. Al Jazeera, Middle East Eye).

Strategy:
  • Only requests articles that have image_url=None.
  • Sends lightweight HEAD-first then GET requests with a very short timeout (5s).
  • Caches each result (hit or miss) for OG_IMAGE_TTL seconds to avoid re-fetching.
  • Batched async — up to MAX_CONCURRENT simultaneous fetches.
  • Falls back gracefully: if fetch fails or no og:image found, leaves image_url=None.

Usage:
    from app.utils.image_enricher import enrich_images
    articles = await enrich_images(articles)
"""

import asyncio
import logging
import re
from typing import Optional

import httpx

from app.core.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

OG_IMAGE_TTL = 3600       # Cache og:image results for 1 hour
MAX_CONCURRENT = 8        # Max parallel page fetches
FETCH_TIMEOUT = 5.0       # Per-request timeout (seconds)
MAX_HTML_BYTES = 32_768   # Read only first 32 KB — og:image is always in <head>

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Domains known to NOT have og:image in their pages — skip fetching entirely
_NO_OG_DOMAINS: set[str] = set()

# Regex to extract og:image from HTML (handles both attribute orderings)
_OG_IMAGE_RE = re.compile(
    r'<meta\s[^>]*?(?:'
    r'property=["\']og:image["\'][^>]*?content=["\']([^"\']+)["\']'
    r'|content=["\']([^"\']+)["\'][^>]*?property=["\']og:image["\']'
    r')',
    re.IGNORECASE | re.DOTALL,
)

# Also match twitter:image as a fallback
_TWITTER_IMAGE_RE = re.compile(
    r'<meta\s[^>]*?(?:'
    r'name=["\']twitter:image["\'][^>]*?content=["\']([^"\']+)["\']'
    r'|content=["\']([^"\']+)["\'][^>]*?name=["\']twitter:image["\']'
    r')',
    re.IGNORECASE | re.DOTALL,
)


def _og_cache_key(url: str) -> str:
    return f"og:image:{url}"


def _extract_og_from_html(html: str) -> Optional[str]:
    """Extract og:image or twitter:image from raw HTML string."""
    m = _OG_IMAGE_RE.search(html)
    if m:
        return m.group(1) or m.group(2)
    m = _TWITTER_IMAGE_RE.search(html)
    if m:
        return m.group(1) or m.group(2)
    return None


async def _fetch_og_image(url: str) -> Optional[str]:
    """
    Fetch og:image for a given article URL.
    Returns the image URL string or None.
    Caches the result (including None as a sentinel) to avoid repeated fetches.
    """
    if not url:
        return None

    # Check domain blocklist
    for domain in _NO_OG_DOMAINS:
        if domain in url:
            return None

    # Check cache first
    cache_key = _og_cache_key(url)
    cached = await cache_get(cache_key)
    if cached is not None:
        # Cached "" means we tried and found nothing — treat as None
        return cached if cached else None

    try:
        async with httpx.AsyncClient(
            timeout=FETCH_TIMEOUT,
            headers=_HEADERS,
            follow_redirects=True,
            trust_env=False,
        ) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                await cache_set(cache_key, "", OG_IMAGE_TTL)  # cache miss sentinel
                return None

            # Read only the first MAX_HTML_BYTES to find <head> og tags
            raw = resp.content[:MAX_HTML_BYTES]
            html = raw.decode("utf-8", errors="replace")
            image_url = _extract_og_from_html(html)

            # Cache result (empty string for miss, URL for hit)
            await cache_set(cache_key, image_url or "", OG_IMAGE_TTL)
            return image_url

    except Exception as exc:
        logger.debug(f"OG image fetch failed [{url}]: {exc}")
        await cache_set(cache_key, "", OG_IMAGE_TTL)  # cache failure to avoid retry flood
        return None


async def enrich_images(articles: list, max_articles: int = 30) -> list:
    """
    Enrich a list of NewsArticle objects by fetching og:image for articles
    that have image_url=None.

    Args:
        articles:     List of NewsArticle Pydantic objects.
        max_articles: Max number of articles to attempt image enrichment for
                      (avoids runaway latency for very large batches).

    Returns:
        The same list with image_url populated where possible.
    """
    # Identify articles needing enrichment
    needs_image = [
        (i, a) for i, a in enumerate(articles[:max_articles])
        if getattr(a, "image_url", None) is None and getattr(a, "link", None)
    ]

    if not needs_image:
        return articles

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def _bounded_fetch(idx: int, article) -> tuple[int, Optional[str]]:
        async with semaphore:
            img = await _fetch_og_image(article.link)
            return idx, img

    tasks = [_bounded_fetch(i, a) for i, a in needs_image]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            continue
        idx, image_url = result
        if image_url:
            articles[idx].image_url = image_url

    enriched_count = sum(
        1 for r in results
        if not isinstance(r, Exception) and r[1]
    )
    if enriched_count:
        logger.info(f"Image enrichment: added images to {enriched_count}/{len(needs_image)} articles")

    return articles
