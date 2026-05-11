# app/Api/google_news.py

import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from fastapi import HTTPException
from app.models import NewsResponse, NewsArticle, FeedMeta
from fastapi import FastAPI, HTTPException, Query

RSS_FEEDS = {
    "social":    "https://news.google.com/rss/search?q=social&hl=en-US&gl=US&ceid=US:en",
    "economics": "https://news.google.com/rss/search?q=economics&hl=en-US&gl=US&ceid=US:en",
    "security":  "https://news.google.com/rss/search?q=security&hl=en-US&gl=US&ceid=US:en",
    "education": "https://news.google.com/rss/search?q=education&hl=en-US&gl=US&ceid=US:en",
    "political": "https://news.google.com/rss/search?q=political+knesset&hl=en-US&gl=US&ceid=US:en",
    "positive":  "https://news.google.com/rss/search?q=positive+news&hl=en-US&gl=US&ceid=US:en",
    "world":     "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
}


app = FastAPI()

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
        pub_date_raw = item.findtext("pubDate", "")
        try:
            pub_date = datetime.strptime(pub_date_raw, "%a, %d %b %Y %H:%M:%S %Z").isoformat() + "Z"
        except Exception:
            pub_date = pub_date_raw

        articles.append(
            NewsArticle(
                title=item.findtext("title", ""),
                link=item.findtext("link", ""),
                description=item.findtext("description", "") or "",
                pub_date=pub_date,
                source=source_el.text if source_el is not None else None,
                source_url=source_el.get("url") if source_el is not None else None,
                guid=item.findtext("guid", ""),
            )
        )

    return NewsResponse(meta=meta, total=len(articles), articles=articles)


async def fetch_news(category: str, limit: int) -> NewsResponse:
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
    


# ── Meta ─────────────────────────────────────────────────────────────────
@app.get("/categories", tags=["Meta"])
async def get_categories():
    """List all available news categories."""
    return {"categories": list(RSS_FEEDS.keys())}


# ── Category Routes ───────────────────────────────────────────────────────
@app.get("/news/world", response_model=NewsResponse, tags=["News"])
async def get_world_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch world news."""
    return await fetch_news("world", limit)


@app.get("/news/social", response_model=NewsResponse, tags=["News"])
async def get_social_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch social news."""
    return await fetch_news("social", limit)


@app.get("/news/economics", response_model=NewsResponse, tags=["News"])
async def get_economics_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch economics news."""
    return await fetch_news("economics", limit)


@app.get("/news/security", response_model=NewsResponse, tags=["News"])
async def get_security_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch security news."""
    return await fetch_news("security", limit)


@app.get("/news/education", response_model=NewsResponse, tags=["News"])
async def get_education_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch education news."""
    return await fetch_news("education", limit)


@app.get("/news/political", response_model=NewsResponse, tags=["News"])
async def get_political_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch political / Knesset news."""
    return await fetch_news("political", limit)


@app.get("/news/positive", response_model=NewsResponse, tags=["News"])
async def get_positive_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch positive news."""
    return await fetch_news("positive", limit)