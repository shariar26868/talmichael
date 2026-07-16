"""
Wrapper functions for licensed news APIs.
Fallback to RSS if API key is missing, request fails, or daily quota is exhausted.

Rate limits (free tier):
  - NewsAPI.org     : 100 requests / 24 hours
  - NewsData.io     : 200 requests / 24 hours
  - GDELT           : Unlimited (free, no key)
  - Currents API    : 600 requests / hour (free tier)

Strategy:
  These APIs are ONLY called from the background scheduler (user_tier="system").
  Real-time user requests use RSS feeds only.
  A daily counter prevents accidentally blowing the quota.
"""

import httpx
import logging
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, date

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Daily rate-limit counters (resets at UTC midnight) ────────────────────────
_quota: Dict[str, Dict] = {
    "newsapi":    {"used": 0, "limit": 95,  "reset_date": None},
    "newsdata":   {"used": 0, "limit": 190, "reset_date": None},
    "currents":   {"used": 0, "limit": 590, "reset_date": None},
}


def _quota_ok(api_name: str) -> bool:
    """Return True if daily quota still has capacity."""
    q = _quota.get(api_name)
    if not q:
        return True
    today = date.today()
    if q["reset_date"] != today:
        q["used"] = 0
        q["reset_date"] = today
    return q["used"] < q["limit"]


def _quota_increment(api_name: str) -> None:
    q = _quota.get(api_name)
    if q:
        q["used"] = q.get("used", 0) + 1


def get_quota_status() -> Dict[str, Any]:
    """Return current quota usage for all licensed APIs (for health endpoint)."""
    status = {}
    today = date.today()
    for name, q in _quota.items():
        if q["reset_date"] != today:
            used = 0
        else:
            used = q["used"]
        status[name] = {
            "used": used,
            "limit": q["limit"],
            "remaining": max(0, q["limit"] - used),
            "reset_date": str(today),
        }
    return status


# ── Category → better search query mapping ────────────────────────────────────
_CATEGORY_QUERIES: Dict[str, str] = {
    "politics":      "Israel politics government Knesset",
    "security":      "Israel security military IDF Gaza",
    "economy":       "Israel economy finance market tech",
    "society":       "Israel society culture social",
    "international": "Israel world Middle East diplomacy",
    "sport":         "Israel sport football basketball",
    "technology":    "Israel tech startup innovation AI",
    "health":        "Israel health medicine COVID",
    "environment":   "Israel climate environment energy",
    "education":     "Israel education university",
    "culture":       "Israel culture art music",
    "community":     "Israel community diaspora Jewish",
    "positive":      "Israel positive good news innovation",
}


def _build_query(category: str) -> str:
    """Build an Israel-focused search query for the given category."""
    return _CATEGORY_QUERIES.get(category.lower(), f"Israel {category}")


# ── Article normalization helpers ─────────────────────────────────────────────

def _normalize_newsapi_article(raw: Dict[str, Any], category: str) -> Optional[Dict[str, Any]]:
    """Convert a NewsAPI article dict into NUZE internal format."""
    title = (raw.get("title") or "").strip()
    if not title or title == "[Removed]":
        return None
    source_name = (raw.get("source") or {}).get("name") or "NewsAPI"
    return {
        "title": title,
        "description": (raw.get("description") or "").strip(),
        "link": raw.get("url") or "",
        "guid": raw.get("url") or "",
        "pub_date": raw.get("publishedAt"),
        "source": source_name,
        "source_url": raw.get("url"),
        "image_url": raw.get("urlToImage"),
        "category": category,
        "api_source": "newsapi",
    }


def _normalize_newsdata_article(raw: Dict[str, Any], category: str) -> Optional[Dict[str, Any]]:
    """Convert a NewsData.io article dict into NUZE internal format."""
    title = (raw.get("title") or "").strip()
    if not title:
        return None
    link = raw.get("link") or raw.get("source_url") or ""
    return {
        "title": title,
        "description": (raw.get("description") or "").strip(),
        "link": link,
        "guid": link,
        "pub_date": raw.get("pubDate"),
        "source": raw.get("source_id") or raw.get("source_name") or "NewsData",
        "source_url": link,
        "image_url": raw.get("image_url"),
        "category": category,
        "api_source": "newsdata",
        "language": raw.get("language"),
        "country": raw.get("country"),
    }


def _normalize_currents_article(raw: Dict[str, Any], category: str) -> Optional[Dict[str, Any]]:
    """Convert a Currents API article dict into NUZE internal format."""
    title = (raw.get("title") or "").strip()
    if not title:
        return None
    link = raw.get("url") or ""
    return {
        "title": title,
        "description": (raw.get("description") or "").strip(),
        "link": link,
        "guid": raw.get("id") or link,
        "pub_date": raw.get("published"),
        "source": raw.get("author") or "Currents",
        "source_url": link,
        "image_url": raw.get("image"),
        "category": category,
        "api_source": "currents",
    }


def _normalize_gdelt_article(raw: Dict[str, Any], category: str) -> Optional[Dict[str, Any]]:
    """Convert a GDELT article dict into NUZE internal format."""
    title = (raw.get("title") or "").strip()
    if not title:
        return None
    link = raw.get("url") or ""
    return {
        "title": title,
        "description": (raw.get("seendate") or ""),
        "link": link,
        "guid": link,
        "pub_date": raw.get("seendate"),
        "source": raw.get("domain") or "GDELT",
        "source_url": link,
        "image_url": None,
        "category": category,
        "api_source": "gdelt",
        "language": raw.get("language"),
        "country": raw.get("country"),
    }


# ── API fetch functions ───────────────────────────────────────────────────────

async def fetch_from_newsapi(
    category: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Fetch from NewsAPI.org.

    Only runs when:
      - NEWSAPI_KEY is configured in .env
      - Daily quota is not exhausted (< 95 requests used)
    """
    key = getattr(settings, "newsapi_key", None)
    if not key:
        return []
    if not _quota_ok("newsapi"):
        logger.warning("NewsAPI daily quota exhausted (%d/%d). Skipping.", _quota["newsapi"]["used"], _quota["newsapi"]["limit"])
        return []

    query = _build_query(category)
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": min(limit, 20),   # free tier max = 20 per page
        "apiKey": key,
    }

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(url, params=params)
            _quota_increment("newsapi")

            if response.status_code == 429:
                logger.warning("NewsAPI rate limited (429). Marking quota full.")
                _quota["newsapi"]["used"] = _quota["newsapi"]["limit"]
                return []

            if response.status_code != 200:
                logger.warning("NewsAPI returned %s for query '%s': %s", response.status_code, query, response.text[:200])
                return []

            data = response.json()
            raw_articles = data.get("articles", [])
            normalized = [_normalize_newsapi_article(a, category) for a in raw_articles]
            result = [a for a in normalized if a is not None]
            logger.info("NewsAPI returned %d articles for category='%s' (query='%s')", len(result), category, query)
            return result

    except Exception as e:
        logger.warning("NewsAPI fetch failed for category='%s': %s", category, e)
    return []


async def fetch_from_newsdata_io(
    category: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Fetch from NewsData.io.

    Only runs when:
      - NEWSDATA_IO_KEY is configured in .env
      - Daily quota is not exhausted (< 190 requests used)
    """
    key = getattr(settings, "newsdata_io_key", None)
    if not key:
        return []
    if not _quota_ok("newsdata"):
        logger.warning("NewsData.io daily quota exhausted. Skipping.")
        return []

    query = _build_query(category)
    url = "https://newsdata.io/api/1/news"
    params = {
        "q": query,
        "language": "en,he",
        "size": min(limit, 10),    # free tier max = 10 per page
        "apikey": key,
    }

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(url, params=params)
            _quota_increment("newsdata")

            if response.status_code == 429:
                logger.warning("NewsData.io rate limited (429). Marking quota full.")
                _quota["newsdata"]["used"] = _quota["newsdata"]["limit"]
                return []

            if response.status_code != 200:
                logger.warning("NewsData.io returned %s for query '%s': %s", response.status_code, query, response.text[:200])
                return []

            data = response.json()
            raw_articles = data.get("results", [])
            normalized = [_normalize_newsdata_article(a, category) for a in raw_articles]
            result = [a for a in normalized if a is not None]
            logger.info("NewsData.io returned %d articles for category='%s' (query='%s')", len(result), category, query)
            return result

    except Exception as e:
        logger.warning("NewsData.io fetch failed for category='%s': %s", category, e)
    return []


async def fetch_from_currents(
    category: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Fetch from Currents API (600 req/hour free tier).

    Only runs when CURRENTS_API_KEY is configured in .env.
    """
    key = getattr(settings, "currents_api_key", None)
    if not key:
        return []
    if not _quota_ok("currents"):
        logger.warning("Currents API hourly quota exhausted. Skipping.")
        return []

    query = _build_query(category)
    url = "https://api.currentsapi.services/v1/search"
    params = {
        "keywords": query,
        "language": "en",
        "apiKey": key,
    }

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(url, params=params)
            _quota_increment("currents")

            if response.status_code == 429:
                logger.warning("Currents API rate limited (429). Marking quota full.")
                _quota["currents"]["used"] = _quota["currents"]["limit"]
                return []

            if response.status_code != 200:
                logger.warning("Currents API returned %s for query '%s': %s", response.status_code, query, response.text[:200])
                return []

            data = response.json()
            raw_articles = data.get("news", [])[:limit]
            normalized = [_normalize_currents_article(a, category) for a in raw_articles]
            result = [a for a in normalized if a is not None]
            logger.info("Currents API returned %d articles for category='%s'", len(result), category)
            return result

    except Exception as e:
        logger.warning("Currents API fetch failed for category='%s': %s", category, e)
    return []


async def fetch_from_gdelt(
    category: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Fetch from GDELT (free, no key needed, unlimited).
    Uses GDELT Article List API v2.
    """
    query = _build_query(category)
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": query,
        "mode": "ArtList",
        "maxrecords": min(limit, 25),
        "format": "json",
        "sort": "DateDesc",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            if response.status_code != 200:
                logger.warning("GDELT returned %s for query '%s'", response.status_code, query)
                return []

            data = response.json()
            raw_articles = data.get("articles", [])[:limit]
            normalized = [_normalize_gdelt_article(a, category) for a in raw_articles]
            result = [a for a in normalized if a is not None]
            logger.info("GDELT returned %d articles for category='%s'", len(result), category)
            return result

    except Exception as e:
        logger.warning("GDELT fetch failed for category='%s': %s", category, e)
    return []
