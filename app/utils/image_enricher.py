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


# Regex to extract real article URL from Google News RSS description HTML.
# Google News RSS descriptions look like:
#   <a href="https://news.google.com/rss/articles/CBM...">Title</a> ... Source
# But we want the resolved URL. We detect google news links and use the description
# href or follow the HTTP redirect to find the canonical URL.
_GNEWS_RE = re.compile(r"news\.google\.com", re.IGNORECASE)
_HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)


def _resolve_gnews_url_from_description(description: str) -> Optional[str]:
    """
    Google News RSS articles often have descriptions like:
      <a href="https://news.google.com/rss/articles/CBM...?oc=5">Title</a> Source
    The link tag inside points back to Google News, not the publisher.
    
    Some feeds embed the real source URL differently. We scan the description
    for any non-Google-News href and return it as the canonical URL.
    """
    if not description:
        return None
    hrefs = _HREF_RE.findall(description)
    for href in hrefs:
        if href.startswith("http") and "google.com" not in href:
            return href
    return None


async def _get_resolved_url(url: str, description: str = "") -> str:
    """
    For Google News RSS links, attempt to find the real article URL:
    1. From a non-Google href in the article description HTML
    2. Using googlenewsdecoder (batchexecute internal API) inside a thread pool
    3. Falling back to HTTP redirect following (legacy)
    Returns the original URL unchanged for non-Google links.
    """
    if not _GNEWS_RE.search(url):
        return url  # Not a Google News link — use as-is

    # 1. Try description first (zero network cost)
    real_url = _resolve_gnews_url_from_description(description)
    if real_url:
        return real_url

    # 2. Try googlenewsdecoder (new method using batchexecute RPC)
    try:
        from googlenewsdecoder import new_decoderv1
        res = await asyncio.to_thread(new_decoderv1, url)
        if res.get("status") and res.get("decoded_url"):
            return res["decoded_url"]
    except Exception as exc:
        logger.debug(f"googlenewsdecoder failed for {url}: {exc}")

    # 3. Follow the redirect to discover the real URL (legacy fallback)
    try:
        async with httpx.AsyncClient(
            timeout=FETCH_TIMEOUT,
            headers=_HEADERS,
            follow_redirects=True,
            trust_env=False,
        ) as client:
            resp = await client.get(url)
            final_url = str(resp.url)
            # Only use if we actually landed on a non-Google page
            if "google.com" not in final_url:
                return final_url
    except Exception:
        pass

    return url  # Give up — use original Google News URL



async def _fetch_og_image(url: str, description: str = "") -> Optional[str]:
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

    # Check cache first (use original URL as key)
    cache_key = _og_cache_key(url)
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached if cached else None

    # Resolve real URL for Google News links
    resolved_url = await _get_resolved_url(url, description)

    try:
        async with httpx.AsyncClient(
            timeout=FETCH_TIMEOUT,
            headers=_HEADERS,
            follow_redirects=True,
            trust_env=False,
        ) as client:
            resp = await client.get(resolved_url)
            if resp.status_code >= 400:
                await cache_set(cache_key, "", OG_IMAGE_TTL)
                return None

            # Read only the first MAX_HTML_BYTES to find <head> og tags
            raw = resp.content[:MAX_HTML_BYTES]
            html = raw.decode("utf-8", errors="replace")
            image_url = _extract_og_from_html(html)

            # Cache result against original URL
            await cache_set(cache_key, image_url or "", OG_IMAGE_TTL)
            return image_url

    except Exception as exc:
        logger.debug(f"OG image fetch failed [{resolved_url}]: {exc}")
        await cache_set(cache_key, "", OG_IMAGE_TTL)
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
            desc = getattr(article, "description", "") or ""
            img = await _fetch_og_image(article.link, description=desc)
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
