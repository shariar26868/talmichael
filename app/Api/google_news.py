# app/Api/google_news.py

import asyncio
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.models import NewsResponse, NewsArticle, FeedMeta

router = APIRouter()

# ── Israeli locale parameters ─────────────────────────────────────────────────
# All feeds are scoped to Israel (hl=en-IL, gl=IL, ceid=IL:en) so that
# Google News surfaces Israeli publications first.
RSS_FEEDS = {
    "social":    "https://news.google.com/rss/search?q=Israel+society+community&hl=en-IL&gl=IL&ceid=IL:en",
    "economics": "https://news.google.com/rss/search?q=Israel+economy+finance&hl=en-IL&gl=IL&ceid=IL:en",
    "security":  "https://news.google.com/rss/search?q=Israel+security+defense&hl=en-IL&gl=IL&ceid=IL:en",
    "education": "https://news.google.com/rss/search?q=Israel+education+schools&hl=en-IL&gl=IL&ceid=IL:en",
    "political": "https://news.google.com/rss/search?q=Israel+politics+Knesset&hl=en-IL&gl=IL&ceid=IL:en",
    "positive":  "https://news.google.com/rss/search?q=Israel+positive+good+news&hl=en-IL&gl=IL&ceid=IL:en",
    "world":     "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pWVXlnQVAB?hl=en-IL&gl=IL&ceid=IL:en",
}

# ── Israeli news source whitelist ─────────────────────────────────────────────
# Only articles whose <source> element matches one of these domains are returned.
# This guarantees all content originates from Israeli publications.
ISRAELI_SOURCES: set[str] = {
    "The Jerusalem Post",
    "jpost.com",
    "Times of Israel",
    "timesofisrael.com",
    "Haaretz",
    "haaretz.com",
    "Ynet News",
    "ynetnews.com",
    "i24 News",
    "i24news.tv",
    "Arutz Sheva",
    "israelnationalnews.com",
    "Israel Hayom",
    "israelhayom.com",
    "The Algemeiner",
    "algemeiner.com",
    "Walla News",
    "walla.co.il",
    "Calcalist",
    "calcalist.co.il",
    "Globes",
    "globes.co.il",
    "Channel 12 News",
    "Channel 13 News",
    "Kan News",
    "mako.co.il",
    "N12",
    "news.walla.co.il",
}


def _is_israeli_source(source_name: Optional[str], source_url: Optional[str]) -> bool:
    """Return True if the article originates from a known Israeli outlet."""
    if source_name and source_name in ISRAELI_SOURCES:
        return True
    if source_url:
        for domain in ISRAELI_SOURCES:
            if domain in source_url:
                return True
    return False

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


async def fetch_news(category: str, limit: int, israeli_only: bool = True) -> NewsResponse:
    """
    Fetch and parse a Google News RSS feed for the given category.

    When `israeli_only=True` (default), only articles from verified Israeli
    news outlets are included in the response. We fetch up to 4× the
    requested limit so we still have enough after filtering.
    """
    url = RSS_FEEDS[category]
    # Over-fetch to compensate for articles that will be filtered out.
    raw_limit = limit * 4 if israeli_only else limit

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch RSS feed: {str(e)}")

    try:
        news = parse_rss(response.text, raw_limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse RSS feed: {str(e)}")

    if israeli_only:
        filtered = [
            article for article in news.articles
            if _is_israeli_source(article.source, article.source_url)
        ]
        # Honour the original limit after filtering
        news.articles = filtered[:limit]
        news.total = len(news.articles)

    return news


# ── Meta ─────────────────────────────────────────────────────────────────
@router.get("/categories", tags=["Meta"])
async def get_categories():
    """List all available news categories."""
    return {"categories": list(RSS_FEEDS.keys())}


@router.get("/sources", tags=["Meta"])
async def get_sources():
    """List all whitelisted Israeli news sources used to filter articles."""
    return {"israeli_sources": sorted(ISRAELI_SOURCES)}


# ── Category Routes ───────────────────────────────────────────────────────
@router.get("/news/world", response_model=NewsResponse, tags=["News"])
async def get_world_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch world news — Israeli sources only."""
    return await fetch_news("world", limit)


@router.get("/news/social", response_model=NewsResponse, tags=["News"])
async def get_social_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch Israeli society & community news — Israeli sources only."""
    return await fetch_news("social", limit)


@router.get("/news/economics", response_model=NewsResponse, tags=["News"])
async def get_economics_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch Israeli economy & finance news — Israeli sources only."""
    return await fetch_news("economics", limit)


@router.get("/news/security", response_model=NewsResponse, tags=["News"])
async def get_security_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch Israeli security & defense news — Israeli sources only."""
    return await fetch_news("security", limit)


@router.get("/news/education", response_model=NewsResponse, tags=["News"])
async def get_education_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch Israeli education news — Israeli sources only."""
    return await fetch_news("education", limit)


@router.get("/news/political", response_model=NewsResponse, tags=["News"])
async def get_political_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch Israeli politics & Knesset news — Israeli sources only."""
    return await fetch_news("political", limit)


@router.get("/news/positive", response_model=NewsResponse, tags=["News"])
async def get_positive_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch Israeli positive / good news — Israeli sources only."""
    return await fetch_news("positive", limit)


@router.get("/news/all", tags=["News"])
async def get_all_news(limit: int = Query(default=10, ge=1, le=50)):
    """
    Fetch `limit` articles from every category concurrently and return them
    grouped by category. All articles are from Israeli sources only.
    """
    categories = list(RSS_FEEDS.keys())
    results = await asyncio.gather(
        *[fetch_news(cat, limit) for cat in categories],
        return_exceptions=True,
    )
    payload: dict = {}
    for cat, result in zip(categories, results):
        if isinstance(result, Exception):
            payload[cat] = {"error": str(result)}
        else:
            payload[cat] = result
    return payload