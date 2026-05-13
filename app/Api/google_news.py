import asyncio
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.models import NewsResponse, NewsArticle, FeedMeta

router = APIRouter()

# ── Feed definitions ──────────────────────────────────────────────────────────
# All feeds scoped to Israel (hl=en-IL, gl=IL, ceid=IL:en).
# "international" now fetches Israeli-perspective good/positive international news.
RSS_FEEDS = {
    # Israeli positive/good international news only (replaces old unrestricted international feed)
    "international": "https://news.google.com/rss/search?q=Israel+international+positive+good&hl=en-IL&gl=IL&ceid=IL:en",

    "economy":     "https://news.google.com/rss/search?q=Israel+economy+finance+market+business&hl=en-IL&gl=IL&ceid=IL:en",
    "defence":     "https://news.google.com/rss/search?q=Israel+security+defense+military+IDF&hl=en-IL&gl=IL&ceid=IL:en",
    "education":   "https://news.google.com/rss/search?q=Israel+education+schools+university+students&hl=en-IL&gl=IL&ceid=IL:en",
    "community":   "https://news.google.com/rss/search?q=Israel+society+community+social&hl=en-IL&gl=IL&ceid=IL:en",
    "sport":       "https://news.google.com/rss/search?q=Israel+sport+football+basketball&hl=en-IL&gl=IL&ceid=IL:en",
    "culture":     "https://news.google.com/rss/search?q=Israel+culture+arts+music&hl=en-IL&gl=IL&ceid=IL:en",
    "environment": "https://news.google.com/rss/search?q=Israel+environment+climate+energy&hl=en-IL&gl=IL&ceid=IL:en",
    "science":     "https://news.google.com/rss/search?q=Israel+science+technology+innovation&hl=en-IL&gl=IL&ceid=IL:en",
    "positive":    "https://news.google.com/rss/search?q=Israel+positive+achievement+breakthrough&hl=en-IL&gl=IL&ceid=IL:en",
    "political":   "https://news.google.com/rss/search?q=Israel+politics+Knesset+government&hl=en-IL&gl=IL&ceid=IL:en",

    # NEW: Official Israeli government / Knesset sources
    "knesset":     "https://news.google.com/rss/search?q=Knesset+legislation+bill+Israel+law&hl=en-IL&gl=IL&ceid=IL:en",
}

# ── Israeli news source whitelist ─────────────────────────────────────────────
# Expanded per client request — only articles from these outlets are returned
# when israeli_only=True.
ISRAELI_SOURCES: set[str] = {
    # English-language Israeli outlets
    "The Jerusalem Post", "jpost.com",
    "Times of Israel", "timesofisrael.com",
    "Haaretz", "haaretz.com",
    "Ynet News", "ynetnews.com",
    "i24 News", "i24news.tv",
    "Arutz Sheva", "israelnationalnews.com",
    "Israel Hayom", "israelhayom.com",
    "The Algemeiner", "algemeiner.com",
    "Israel National News", "arutzsheva.com",
    "Jewish Telegraphic Agency", "jta.org",
    "The Media Line", "themedialine.org",
    "Ynetnews", "ynet.co.il",

    # Hebrew-language / local Israeli outlets
    "Walla News", "walla.co.il", "news.walla.co.il",
    "Calcalist", "calcalist.co.il",
    "Globes", "globes.co.il",
    "Channel 12 News", "mako.co.il",
    "Channel 13 News",
    "Kan News", "kan.org.il",
    "N12",
    "Maariv", "maariv.co.il",
    "Zman Israel", "zman.co.il",
    "Reshet Bet",
    "103FM", "103fm.maariv.co.il",
    "Galatz",
    "YNET", "ynet.co.il",
    "sport5.co.il",
    "one.co.il",

    # Economy / business Israeli outlets
    "TheMarker", "themarker.com",
    "Bizportal", "bizportal.co.il",
    "Funder", "funder.co.il",
    "Geektime", "geektime.com",
    "IVC", "ivc-online.com",

    # Official / government adjacent
    "Israel Ministry of Foreign Affairs", "mfa.gov.il",
    "Knesset", "knesset.gov.il",
    "Israel Government Press Office", "gov.il",
}

# ── Non-Israeli / generic AI / wiki sources to explicitly block ───────────────
# Per client: Wikipedia and similar crowd-sourced/AI-aggregated sources must be excluded.
BLOCKED_SOURCES: set[str] = {
    "wikipedia.org",
    "en.wikipedia.org",
    "wikimedia.org",
    "wikidata.org",
    "medium.com",          # generic blog aggregator
    "substack.com",        # generic opinion platform
}

# ── Sentiment keywords that indicate potentially negative / risky content ─────
NEGATIVE_KEYWORDS: tuple[str, ...] = (
    "crisis", "catastrophe", "disaster", "terror", "attack",
    "killed", "dead", "casualties", "war crime", "massacre",
    "riot", "protest", "strike", "sanction", "collapse",
    "arrested", "indicted", "corruption", "scandal", "fraud",
)

# ── Opinion / editorial detection ────────────────────────────────────────────
OPINION_KEYWORDS: tuple[str, ...] = (
    "opinion", "op-ed", "editorial", "columnist", "commentary",
    "analysis:", "perspective:", "view:", "think:", "column:",
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _is_israeli_source(source_name: Optional[str], source_url: Optional[str]) -> bool:
    """Return True if the article originates from a known Israeli outlet."""
    if source_name and source_name in ISRAELI_SOURCES:
        return True
    if source_url:
        for domain in ISRAELI_SOURCES:
            if domain in source_url:
                return True
    return False


def _is_blocked_source(source_name: Optional[str], source_url: Optional[str]) -> bool:
    """Return True if the article comes from a blocked / unreliable source."""
    if source_url:
        for domain in BLOCKED_SOURCES:
            if domain in source_url:
                return True
    if source_name and source_name.lower() in {s.lower() for s in BLOCKED_SOURCES}:
        return True
    return False


def _is_opinion(title: Optional[str], description: Optional[str] = None) -> bool:
    """
    Return True if the article appears to be an opinion / editorial piece.
    Checks both title and description so opinion articles are reliably excluded
    across the entire app — per client requirement.
    """
    text = " ".join(filter(None, [title, description])).lower()
    return any(kw in text for kw in OPINION_KEYWORDS)


def _is_negative(title: Optional[str], description: Optional[str] = None) -> bool:
    """Return True if the article headline/description contains negative sentiment keywords."""
    text = " ".join(filter(None, [title, description])).lower()
    return any(kw in text for kw in NEGATIVE_KEYWORDS)


# ─────────────────────────────────────────────────────────────────────────────
# RSS parsing
# ─────────────────────────────────────────────────────────────────────────────

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
        title = item.findtext("title", "")
        description = item.findtext("description", "") or ""

        # Global opinion filter — applied to every category
        if _is_opinion(title, description):
            continue

        source_el = item.find("source")
        source_name = source_el.text if source_el is not None else None
        source_url = source_el.get("url") if source_el is not None else None

        # Block explicitly unreliable sources (Wikipedia, generic AI blogs, etc.)
        if _is_blocked_source(source_name, source_url):
            continue

        pub_date_raw = item.findtext("pubDate", "")
        try:
            pub_date = datetime.strptime(pub_date_raw, "%a, %d %b %Y %H:%M:%S %Z").isoformat() + "Z"
        except Exception:
            pub_date = pub_date_raw

        articles.append(
            NewsArticle(
                title=title,
                link=item.findtext("link", ""),
                description=description,
                pub_date=pub_date,
                source=source_name,
                source_url=source_url,
                guid=item.findtext("guid", ""),
            )
        )

    return NewsResponse(meta=meta, total=len(articles), articles=articles)


# ─────────────────────────────────────────────────────────────────────────────
# Core fetch
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_news(
    category: str,
    limit: int,
    israeli_only: bool,
    exclude_negative: bool = False,
) -> NewsResponse:
    """
    Fetch and parse a Google News RSS feed for the given category.

    Args:
        category:        Key in RSS_FEEDS.
        limit:           Max articles to return after all filtering.
        israeli_only:    When True, only verified Israeli outlets are included.
        exclude_negative: When True, articles with negative sentiment keywords
                         are removed (used for "positive" and "international" feeds).
    """
    url = RSS_FEEDS[category]
    # Over-fetch to compensate for articles filtered out downstream.
    multiplier = 1
    if israeli_only:
        multiplier = max(multiplier, 4)
    if exclude_negative:
        multiplier = max(multiplier, 6)  # positive feeds need more candidates
    raw_limit = limit * multiplier

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

    filtered = news.articles

    # Israeli source filter
    if israeli_only:
        filtered = [a for a in filtered if _is_israeli_source(a.source, a.source_url)]

    # Negative sentiment filter (positive / good-news feeds)
    if exclude_negative:
        filtered = [a for a in filtered if not _is_negative(a.title, a.description)]

    news.articles = filtered[:limit]
    news.total = len(news.articles)
    return news


# ─────────────────────────────────────────────────────────────────────────────
# Knesset / official Israeli bills scraper
# ─────────────────────────────────────────────────────────────────────────────

KNESSET_RSS = "https://main.knesset.gov.il/Activity/Legislation/Laws/Pages/Default.aspx"
KNESSET_BILLS_API = "https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Bill?$format=json&$top={limit}&$orderby=LastUpdatedDate desc"


async def fetch_knesset_bills(limit: int = 20) -> dict:
    """
    Fetch recent bills from the official Knesset OData API.
    Returns structured bill data including title, status, and last update.
    Falls back to the Knesset RSS Google News proxy if the API is unavailable.
    """
    url = KNESSET_BILLS_API.format(limit=limit)
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            data = response.json()
            bills = data.get("value", [])
            return {
                "source": "knesset.gov.il OData API",
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
            # Fallback: use Google News RSS for Knesset coverage
            news = await fetch_news("knesset", limit, israeli_only=True)
            return {
                "source": "Google News RSS (Knesset fallback)",
                "total": news.total,
                "articles": [a.dict() for a in news.articles],
            }


# ─────────────────────────────────────────────────────────────────────────────
# Meta routes
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/categories", tags=["Meta"])
async def get_categories():
    """List all available news categories."""
    return {"categories": list(RSS_FEEDS.keys())}


@router.get("/sources", tags=["Meta"])
async def get_sources():
    """List all whitelisted Israeli news sources used to filter articles."""
    return {
        "israeli_sources": sorted(ISRAELI_SOURCES),
        "blocked_sources": sorted(BLOCKED_SOURCES),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Category routes
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/news/international", response_model=NewsResponse, tags=["News"])
async def get_international_news(limit: int = Query(default=20, ge=1, le=100)):
    """
    Fetch international news from an Israeli perspective.
    Israeli sources only + negative sentiment articles excluded (good news only).
    """
    return await fetch_news("international", limit, israeli_only=True, exclude_negative=True)


@router.get("/news/community", response_model=NewsResponse, tags=["News"])
async def get_community_news(
    limit: int = Query(default=20, ge=1, le=100),
    exclude_negative: bool = Query(default=False, description="Set true to filter out negative sentiment articles"),
):
    """
    Fetch Israeli society & community news — Israeli sources only.
    Optionally exclude negative/sensitive content via ?exclude_negative=true.
    """
    return await fetch_news("community", limit, israeli_only=True, exclude_negative=exclude_negative)


@router.get("/news/economy", response_model=NewsResponse, tags=["News"])
async def get_economy_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch Israeli economy & finance news — Israeli sources only."""
    return await fetch_news("economy", limit, israeli_only=True)


@router.get("/news/defence", response_model=NewsResponse, tags=["News"])
async def get_defence_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch Israeli security & defence news — Israeli sources only."""
    return await fetch_news("defence", limit, israeli_only=True)


@router.get("/news/education", response_model=NewsResponse, tags=["News"])
async def get_education_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch Israeli education news — Israeli sources only."""
    return await fetch_news("education", limit, israeli_only=True)


@router.get("/news/political", response_model=NewsResponse, tags=["News"])
async def get_political_news(
    limit: int = Query(default=20, ge=1, le=100),
    exclude_negative: bool = Query(default=False, description="Set true to filter out negative/risky political articles"),
):
    """
    Fetch Israeli politics & Knesset news — Israeli sources only.
    Optionally exclude negative/sensitive content via ?exclude_negative=true.
    """
    return await fetch_news("political", limit, israeli_only=True, exclude_negative=exclude_negative)


@router.get("/news/positive", response_model=NewsResponse, tags=["News"])
async def get_positive_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch Israeli positive / good news — Israeli sources only, negative sentiment excluded."""
    return await fetch_news("positive", limit, israeli_only=True, exclude_negative=True)


@router.get("/news/sport", response_model=NewsResponse, tags=["News"])
async def get_sport_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch Israeli sport news — Israeli sources only."""
    return await fetch_news("sport", limit, israeli_only=True)


@router.get("/news/culture", response_model=NewsResponse, tags=["News"])
async def get_culture_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch Israeli culture news — Israeli sources only."""
    return await fetch_news("culture", limit, israeli_only=True)


@router.get("/news/environment", response_model=NewsResponse, tags=["News"])
async def get_environment_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch Israeli environment news — Israeli sources only."""
    return await fetch_news("environment", limit, israeli_only=True)


@router.get("/news/science", response_model=NewsResponse, tags=["News"])
async def get_science_news(limit: int = Query(default=20, ge=1, le=100)):
    """Fetch Israeli science & technology news — Israeli sources only."""
    return await fetch_news("science", limit, israeli_only=True)


@router.get("/news/knesset", tags=["News"])
async def get_knesset_bills(limit: int = Query(default=20, ge=1, le=50)):
    """
    Fetch recent Knesset bills from the official Knesset OData API.
    Falls back to Google News RSS (Israeli sources only) if the API is unavailable.
    """
    return await fetch_knesset_bills(limit)


@router.get("/news/all", tags=["News"])
async def get_all_news(limit: int = Query(default=10, ge=1, le=50)):
    """
    Fetch `limit` articles from every category concurrently and return them
    grouped by category.
    """
    categories = list(RSS_FEEDS.keys())

    # Determine per-category options
    category_options: dict[str, dict] = {
        "international": {"israeli_only": True, "exclude_negative": True},
        "positive":      {"israeli_only": True, "exclude_negative": True},
    }

    tasks = []
    for cat in categories:
        opts = category_options.get(cat, {"israeli_only": True, "exclude_negative": False})
        tasks.append(fetch_news(cat, limit, **opts))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    payload: dict = {}
    for cat, result in zip(categories, results):
        if isinstance(result, Exception):
            payload[cat] = {"error": str(result)}
        else:
            payload[cat] = result
    return payload