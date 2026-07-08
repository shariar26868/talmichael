# app/utils/image_enricher.py
"""
Image Enricher — fetches relevant images for articles with fallback chain:
  1. og:image from article URLs (highest priority — direct publisher images)
  2. Unsplash API (free, unlimited, publicly available stock images)
  3. Category-specific Unsplash search queries (e.g. "political" → "government parliament")

Strategy:
  • OG image fetching: Sends lightweight GET requests with short timeout (5s).
  • Unsplash fallback: Uses keyword extraction from title + category to find relevant images.
  • Caches all results (hit or miss) for IMAGE_TTL seconds to avoid re-fetching.
  • Batched async — up to MAX_CONCURRENT simultaneous fetches.
  • Falls back gracefully: if all sources fail, leaves image_url=None (client uses placeholder).

Quality:
  • Unsplash images are high-resolution (2400x1600+), professionally curated, free to use.
  • Category-specific queries ensure relevance (e.g. "Education" → "school classroom students").

Usage:
    from app.utils.image_enricher import enrich_images
    articles = await enrich_images(articles, category="political")
"""

import asyncio
import json
import logging
import re
from typing import Optional
from urllib.parse import quote

import httpx

from app.core.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

IMAGE_TTL = 3600       # Cache all image results for 1 hour
MAX_CONCURRENT = 8     # Max parallel fetches
FETCH_TIMEOUT = 5.0    # Per-request timeout (seconds)
MAX_HTML_BYTES = 32_768  # Read only first 32 KB — og:image is always in <head>

# Category → Unsplash search query mapping (for fallback when no OG image)
CATEGORY_IMAGE_QUERIES = {
    "political": "government parliament democracy news",
    "security": "military defense army security operation",
    "economy": "business finance market economy trade commerce",
    "sport": "sports athletes team competition championship",
    "culture": "culture arts music theater cinema film",
    "education": "school classroom education students university learning",
    "science": "science technology innovation research laboratory discovery",
    "environment": "environment nature climate green renewable energy",
    "positive": "success achievement celebration joy hope inspiration",
    "international": "world map globe diplomacy international news",
    "israeli-international": "israel news world diplomacy middle east",
    "international-pure": "world news global event diplomacy",
}

# Unsplash API endpoints (free, no auth key required for basic search)
UNSPLASH_SEARCH_API = "https://unsplash.com/api/apps/xGBGo0gnWlg91JXqXJ15eIw36QyxzVgVYbb3zqa04Ow/search/photos"

# Domains known to NOT have og:image in their pages — skip fetching entirely
_NO_OG_DOMAINS: set[str] = set()

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

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


def _unsplash_cache_key(query: str) -> str:
    return f"unsplash:image:{query}"


async def _fetch_unsplash_image(query: str) -> Optional[str]:
    """
    Fetch a random high-quality image from Unsplash based on query.
    Returns the image URL or None on failure.
    Caches results to avoid repeated requests for same query.
    """
    if not query or len(query) < 2:
        return None

    # Check cache first
    cache_key = _unsplash_cache_key(query)
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached if cached else None

    try:
        async with httpx.AsyncClient(
            timeout=FETCH_TIMEOUT,
            headers=_HEADERS,
            follow_redirects=True,
            trust_env=False,
        ) as client:
            # Unsplash API: search for images by query
            params = {
                "query": query,
                "page": "1",
                "per_page": "1",
                "order_by": "relevant",
            }
            resp = await client.get(UNSPLASH_SEARCH_API, params=params)
            if resp.status_code != 200:
                await cache_set(cache_key, "", IMAGE_TTL)
                return None

            data = resp.json()
            if not data.get("results"):
                await cache_set(cache_key, "", IMAGE_TTL)
                return None

            # Get the first result's image URL (high resolution version)
            image = data["results"][0]
            image_url = image.get("urls", {}).get("regular")  # 1080x1080+ regular size

            await cache_set(cache_key, image_url or "", IMAGE_TTL)
            return image_url

    except Exception as exc:
        logger.debug(f"Unsplash fetch failed [{query}]: {exc}")
        await cache_set(cache_key, "", IMAGE_TTL)
        return None


def _extract_keywords_from_title(title: str, max_words: int = 3) -> str:
    """
    Extract 1-3 key words from article title for Unsplash search.
    Removes common stop words and returns a clean search query.
    """
    if not title:
        return ""

    # Remove common stop words
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "must", "shall", "new", "latest",
        "breaking", "news", "today", "yesterday", "israel", "says", "report",
    }

    words = title.lower().split()
    keywords = [w for w in words if w not in stop_words and len(w) > 3][:max_words]

    return " ".join(keywords) if keywords else title[:30]



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
            await cache_set(cache_key, image_url or "", IMAGE_TTL)
            return image_url

    except Exception as exc:
        logger.debug(f"OG image fetch failed [{resolved_url}]: {exc}")
        await cache_set(cache_key, "", IMAGE_TTL)
        return None


async def enrich_images(articles: list, category: str = "news", max_articles: int = 30) -> list:
    """
    Enrich a list of NewsArticle objects with images via fallback chain:
      1. Use existing image_url (from RSS feed)
      2. Fetch og:image from article URL (publisher's image)
      3. Search Unsplash using article title keywords (article-specific image)
      4. Fallback to category-specific Unsplash image (generic relevant image)

    Args:
        articles:     List of NewsArticle Pydantic objects.
        category:     Category name for fallback query (e.g. "political", "security").
        max_articles: Max number of articles to attempt image enrichment for.

    Returns:
        The same list with image_url populated where possible.
    """
    # Identify articles needing enrichment
    needs_image = []
    for i, a in enumerate(articles[:max_articles]):
        # Handle both Pydantic objects and dicts
        image_url = getattr(a, "image_url", None) if hasattr(a, "image_url") else a.get("image_url") if isinstance(a, dict) else None
        link = getattr(a, "link", None) if hasattr(a, "link") else a.get("link") if isinstance(a, dict) else None
        if not image_url and link:
            needs_image.append((i, a))

    if not needs_image:
        return articles

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    # Get category-specific fallback query (e.g. "political" → "government parliament democracy news")
    category_fallback_query = CATEGORY_IMAGE_QUERIES.get(category, category)

    async def _bounded_fetch(idx: int, article) -> tuple[int, Optional[str]]:
        async with semaphore:
            # Safe access for both objects and dicts
            desc = (getattr(article, "description", "") or "") if not isinstance(article, dict) else (article.get("description") or "")
            title = (getattr(article, "title", "") or "") if not isinstance(article, dict) else (article.get("title") or "")
            link = (getattr(article, "link", "") or "") if not isinstance(article, dict) else (article.get("link") or "")

            if not link:
                return idx, None

            # Step 1: Try OG image from article URL
            img = await _fetch_og_image(link, description=desc)
            if img:
                return idx, img

            # Step 2: Try title-specific Unsplash search
            keywords = _extract_keywords_from_title(title)
            if keywords:
                img = await _fetch_unsplash_image(keywords)
                if img:
                    return idx, img

            # Step 3: Fallback to category-specific Unsplash image
            if category_fallback_query:
                img = await _fetch_unsplash_image(category_fallback_query)
                if img:
                    return idx, img

            return idx, None

    tasks = [_bounded_fetch(i, a) for i, a in needs_image]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            continue
        idx, image_url = result
        if image_url:
            # Set image_url for both objects and dicts
            article = articles[idx]
            if isinstance(article, dict):
                article["image_url"] = image_url
            else:
                article.image_url = image_url

    enriched_count = sum(
        1 for r in results
        if not isinstance(r, Exception) and r[1]
    )
    if enriched_count:
        logger.info(f"Image enrichment: added images to {enriched_count}/{len(needs_image)} articles")

    return articles
