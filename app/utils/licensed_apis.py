"""
Wrapper functions for licensed news APIs.
Fallback to RSS if API key is missing or request fails.
"""

import httpx
import logging
from typing import Optional, List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

async def fetch_from_newsapi(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch from NewsAPI.org if key is configured."""
    key = getattr(settings, "newsapi_key", None)
    if not key:
        return []

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": limit,
        "apiKey": key,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get("articles", [])
            logger.warning("NewsAPI returned %s: %s", response.status_code, response.text)
    except Exception as e:
        logger.warning(f"NewsAPI fetch failed: {e}")
    return []

async def fetch_from_newsdata_io(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch from NewsData.io if key is configured."""
    key = getattr(settings, "newsdata_io_key", None)
    if not key:
        return []

    url = "https://newsdata.io/api/1/news"
    params = {
        "q": query,
        "language": "en,he",
        "size": limit,
        "apikey": key,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            logger.warning("NewsData.io returned %s: %s", response.status_code, response.text)
    except Exception as e:
        logger.warning(f"NewsData.io fetch failed: {e}")
    return []

async def fetch_from_gdelt(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch from GDELT (free, no key needed)."""
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": query,
        "mode": "ArtList",
        "maxrecords": limit,
        "format": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get("articles", [])
            logger.warning("GDELT returned %s: %s", response.status_code, response.text)
    except Exception as e:
        logger.warning(f"GDELT fetch failed: {e}")
    return []
