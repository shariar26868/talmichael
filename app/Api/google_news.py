# app/Api/google_news.py

import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from app.models import NewsResponse, NewsArticle, FeedMeta

router = APIRouter()  # ← Create a router instead of using app directly

RSS_FEEDS = {
    "world": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
    "technology": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en&topic=technology",
    "business": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGwwTlY4U0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
    "science": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp0Y1RjU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
    "health": "https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNR3QwTlRFU0FtVnVLQUFQAQ?hl=en-US&gl=US&ceid=US:en",
}


def parse_rss(xml_text: str, limit: int) -> NewsResponse:
    root = ET.fromstring(xml_text)
    channel = root.find("channel")

    if channel is None:
        raise ValueError("Invalid RSS feed structure")

    meta = FeedMeta(
        title=channel.findtext("title", ""),
        description=channel.findtext("description", ""),
        link=channel.findtext("link", ""),
        last_build_date=channel.findtext("lastBuildDate", ""),
        fetched_at=datetime.utcnow().isoformat() + "Z",
    )

    articles = []
    for item in channel.findall("item")[:limit]:
        source_el = item.find("source")
        source = source_el.text if source_el is not None else None
        source_url = source_el.get("url") if source_el is not None else None

        pub_date_raw = item.findtext("pubDate", "")
        try:
            pub_date = datetime.strptime(pub_date_raw, "%a, %d %b %Y %H:%M:%S %Z").isoformat() + "Z"
        except Exception:
            pub_date = pub_date_raw

        description = item.findtext("description", "") or ""

        articles.append(
            NewsArticle(
                title=item.findtext("title", ""),
                link=item.findtext("link", ""),
                description=description,
                pub_date=pub_date,
                source=source,
                source_url=source_url,
                guid=item.findtext("guid", ""),
            )
        )

    return NewsResponse(meta=meta, total=len(articles), articles=articles)


# ↓ All @app routes become @router routes

@router.get("/news/{category}", response_model=NewsResponse, tags=["News"])
async def get_news(
    category: str = "world",
    limit: int = Query(default=20, ge=1, le=100, description="Number of articles to return"),
):
    if category not in RSS_FEEDS:
        raise HTTPException(
            status_code=404,
            detail=f"Category '{category}' not found. Available: {list(RSS_FEEDS.keys())}",
        )

    url = RSS_FEEDS[category]
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch RSS feed: {str(e)}")

    try:
        return parse_rss(response.text, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse RSS feed: {str(e)}")


@router.get("/news", response_model=NewsResponse, tags=["News"])
async def get_world_news(
    limit: int = Query(default=20, ge=1, le=100, description="Number of articles to return"),
):
    """Fetch world news (default endpoint)."""
    return await get_news("world", limit)


@router.get("/categories", tags=["News"])
async def get_categories():
    """List all available news categories."""
    return {"categories": list(RSS_FEEDS.keys())}


@router.get("/search", response_model=NewsResponse, tags=["News"])
async def search_news(
    q: str = Query(..., description="Search keyword or phrase"),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Search Google News RSS for any keyword."""
    encoded = q.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch RSS feed: {str(e)}")

    try:
        return parse_rss(response.text, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse feed: {str(e)}")