# app/routes/news.py
"""News API routes — every endpoint returns mixed Israel + Global content."""

from typing import Optional
from fastapi import APIRouter, Query
from app.services.news_service import fetch_news, fetch_all_news, fetch_knesset_bills
from app.routes.bills import list_bills as bills_list, get_bill as bills_get
from app.models.schemas import NewsResponse
from app.utils.feed_config import (
    RSS_FEEDS, TOPIC_MIXED_FEEDS, ISRAELI_SOURCES_FEEDS,
    INTERNATIONAL_SOURCES_FEEDS, ARABIC_SOURCES_FEEDS,
    SOURCE_REGISTRY, get_source_info, get_all_feeds, get_source_count,
)
from app.utils.filters import ISRAELI_SOURCES, BLOCKED_SOURCES, TOPIC_KEYWORDS

router = APIRouter(tags=["News"])


@router.get("/categories")
async def get_categories():
    """Get all news categories with topic keyword info."""
    return {
        "categories": list(RSS_FEEDS.keys()),
        "count": len(RSS_FEEDS),
        "note": "All categories return MIXED Israel + Global articles. Topic keywords ensure relevance.",
        "topic_keywords": {
            cat: {
                "required_sample": config.get("required", [])[:5],
                "excluded_sample": config.get("excluded", [])[:3],
            }
            for cat, config in TOPIC_KEYWORDS.items()
        },
    }


@router.get("/sources")
async def get_sources(
    language: Optional[str] = Query(None, description="Filter by language: hebrew|english|arabic"),
    country: Optional[str] = Query(None, description="Filter by country"),
    detailed: bool = Query(False, description="Include source metadata"),
):
    """
    Get available news sources.

    - language: Filter by language (hebrew, english, arabic)
    - country: Filter by country (Israel, UK, USA, etc.)
    - detailed: Include full metadata (bias, credibility, etc.)
    """
    sources = {}

    if language:
        lang = language.lower()
        if lang in ["hebrew", "he", "iw"]:
            sources = ISRAELI_SOURCES_FEEDS.copy()
        elif lang in ["english", "en"]:
            sources = INTERNATIONAL_SOURCES_FEEDS.copy()
        elif lang in ["arabic", "ar"]:
            sources = ARABIC_SOURCES_FEEDS.copy()
    else:
        sources = get_all_feeds()

    if country:
        filtered_sources = {}
        for name, url in sources.items():
            info = get_source_info(name)
            if info.get("country", "").lower() == country.lower():
                filtered_sources[name] = url
        sources = filtered_sources

    if detailed:
        result = []
        for name, url in sources.items():
            info = get_source_info(name)
            result.append({
                "name": name,
                "url": info.get("url", ""),
                "feed_url": url,
                "country": info.get("country", "Unknown"),
                "language": info.get("language", "Unknown"),
                "bias": info.get("bias", "unknown"),
                "credibility": info.get("credibility", 0.5),
                "category": info.get("category", "general"),
            })
        return {
            "sources": sorted(result, key=lambda x: x["credibility"], reverse=True),
            "total": len(result),
        }
    else:
        counts = get_source_count()
        return {
            "israeli_sources": sorted(ISRAELI_SOURCES_FEEDS.keys()),
            "international_sources": sorted(INTERNATIONAL_SOURCES_FEEDS.keys()),
            "arabic_sources": sorted(ARABIC_SOURCES_FEEDS.keys()),
            "total": len(sources),
            "counts": counts,
            "blocked_sources": sorted(BLOCKED_SOURCES),
        }


# ══════════════════════════════════════════════════════════════════════════════
# NEWS ENDPOINTS — All return MIXED Israel + Global content
# Topic keyword filters ensure topical relevance is maintained.
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/news/international", response_model=NewsResponse)
async def international(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    """
    International news: global affairs EXCLUDING Israel-related news.
    Returns pure international articles — world events, diplomacy, geopolitics WITHOUT Israel involved.
    For international perspective ON Israel, use /news/israeli-international instead.
    """
    return await fetch_news(
        "international-pure", limit,
        exclude_negative=True,
        language="hebrew",
        user_tier=user_tier,
        with_analysis=with_analysis,
    )


@router.get("/news/israeli-international", response_model=NewsResponse)
async def israeli_international(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    """
    Israeli-International news: what the world says ABOUT Israel ONLY.
    Returns international sources coverage of Israel — global media perspective on Israeli news.
    For pure international news without Israel, use /news/international instead.
    """
    return await fetch_news(
        "israeli-international", limit,
        exclude_negative=True,
        language="hebrew",
        user_tier=user_tier,
        with_analysis=with_analysis,
    )@router.get("/news/economy", response_model=NewsResponse)
async def economy(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    """
    Economy & finance news.
    Returns MIXED articles — Israel economy + global markets, trade, finance.
    Always shows today's articles first (no older articles if today's threshold reached).
    """
    return await fetch_news(
        "economy", limit,
        language="hebrew",
        user_tier=user_tier,
        with_analysis=with_analysis,
        force_today_priority=True,
    )


@router.get("/news/security", response_model=NewsResponse)
async def security(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    """
    Security & defence news.
    Returns MIXED articles — IDF/Israel security + global military conflicts.
    Always shows today's articles first (no older articles if today's threshold reached).
    """
    return await fetch_news(
        "security", limit,
        language="hebrew",
        user_tier=user_tier,
        with_analysis=with_analysis,
        force_today_priority=True,
    )


@router.get("/news/defence", response_model=NewsResponse)
async def defence(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    """
    Deprecated: use /news/security instead.
    """
    return await fetch_news(
        "security", limit,
        language="hebrew",
        user_tier=user_tier,
        with_analysis=with_analysis,
        force_today_priority=True,
    )


@router.get("/news/education", response_model=NewsResponse)
async def education(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    """
    Education news — negative only (positive on /news/positive).
    Returns MIXED articles — Israeli schools/universities + global education trends.
    """
    return await fetch_news(
        "education", limit,
        language="hebrew",
        user_tier=user_tier,
        with_analysis=with_analysis,
        exclude_positive=True,
    )


@router.get("/news/community", response_model=NewsResponse)
async def community(
    limit: int = Query(20, ge=1, le=100),
    exclude_negative: bool = Query(False),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    """
    Community & society news.
    Returns MIXED articles — Israeli society + global social/human rights.
    """
    return await fetch_news(
        "community", limit,
        exclude_negative=exclude_negative,
        language="hebrew",
        user_tier=user_tier,
        with_analysis=with_analysis,
    )


@router.get("/news/political", response_model=NewsResponse)
async def political(
    limit: int = Query(20, ge=1, le=100),
    exclude_negative: bool = Query(False),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    """
    Political news.
    Returns MIXED articles — Israeli politics (Knesset, Netanyahu) + global politics.
    Sport/entertainment articles are filtered out by topic keywords.
    Always shows today's articles first (no older articles if today's threshold reached).
    """
    return await fetch_news(
        "political", limit,
        exclude_negative=exclude_negative,
        language="hebrew",
        user_tier=user_tier,
        with_analysis=with_analysis,
        force_today_priority=True,
    )


@router.get("/news/positive", response_model=NewsResponse)
async def positive(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    """
    Positive & uplifting news — including social recommendations (restaurants, food, travel).
    Returns MIXED articles — Israeli achievements + global breakthroughs, good news, social recommendations.
    """
    return await fetch_news(
        "positive", limit,
        exclude_negative=True,
        language="hebrew",
        user_tier=user_tier,
        with_analysis=with_analysis,
    )


@router.get("/news/sport", response_model=NewsResponse)
async def sport(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    """
    Sports news — Israeli sports ONLY.
    Returns articles for Israeli teams (Maccabi, Hapoel) only, not global sport.
    Always shows today's articles first (no older articles if today's threshold reached).
    """
    return await fetch_news(
        "sport", limit,
        language="hebrew",
        user_tier=user_tier,
        with_analysis=with_analysis,
        israeli_only=True,
        force_today_priority=True,
    )


@router.get("/news/culture", response_model=NewsResponse)
async def culture(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    """
    Culture & entertainment news — negative only (positive on /news/positive).
    Returns MIXED articles — Israeli culture (arts, film, music) + global entertainment.
    """
    return await fetch_news(
        "culture", limit,
        language="hebrew",
        user_tier=user_tier,
        with_analysis=with_analysis,
        exclude_positive=True,
    )


@router.get("/news/environment", response_model=NewsResponse)
async def environment(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    """
    Environment & climate news.
    Returns MIXED articles — Israeli environment/energy + global climate change.
    """
    return await fetch_news(
        "environment", limit,
        language="hebrew",
        user_tier=user_tier,
        with_analysis=with_analysis,
    )


@router.get("/news/science", response_model=NewsResponse)
async def science(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    """
    Science & technology news — negative only (positive on /news/positive).
    Returns MIXED articles — Israeli tech startups/AI + global science breakthroughs.
    """
    return await fetch_news(
        "science", limit,
        language="hebrew",
        user_tier=user_tier,
        with_analysis=with_analysis,
        exclude_positive=True,
    )


@router.get("/news/knesset")
async def knesset(limit: int = Query(20, ge=1, le=50)):
    """
    Knesset bills and legislation.
    Primary: Knesset OData API. Fallback: mixed RSS (Knesset + global parliament news).
    """
    return await fetch_knesset_bills(limit)


@router.get("/news/bills")
async def news_bills(
    days: Optional[int] = Query(None, description="Filter by last updated days, e.g. 30"),
    user_tier: str = Query("free", description="User tier: free | pro"),
    with_analysis: bool = Query(False, description="Whether to include AI analysis"),
):
    """
    Proxy endpoint for Knesset bills. Returns the same payload as `GET /bills`.
    This keeps bills data separate from the /news/* article endpoints while
    providing a convenient route under the news namespace when required.
    """
    return await bills_list(days=days, user_tier=user_tier, with_analysis=with_analysis)


@router.get("/news/bills/{bill_id}")
async def news_get_bill(
    bill_id: str,
    user_tier: str = Query("free", description="User tier: free | pro"),
    with_analysis: bool = Query(False, description="Whether to include AI analysis"),
):
    """Proxy to `GET /bills/{bill_id}` returning the bill details."""
    return await bills_get(bill_id=bill_id, user_tier=user_tier, with_analysis=with_analysis)


@router.get("/news/arabic", response_model=NewsResponse)
async def arabic(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    """
    Arabic language news.
    Returns MIXED articles — Arabic regional sources + Israeli Arabic/English sources.
    """
    return await fetch_news(
        "arabic",
        limit,
        exclude_negative=False,
        language="arabic",
        user_tier=user_tier,
        with_analysis=with_analysis,
    )


@router.get("/news/all")
async def all_news(
    limit: int = Query(10, ge=1, le=50),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    """
    All categories combined.
    Returns a unified feed of MIXED Israel + Global articles across all topics.
    """
    return await fetch_all_news(limit, user_tier=user_tier, with_analysis=with_analysis)
