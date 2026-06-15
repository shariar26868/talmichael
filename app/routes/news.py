# app/routes/news.py

from typing import Optional
from fastapi import APIRouter, Query
from app.services.news_service import fetch_news, fetch_all_news, fetch_knesset_bills
from app.models.schemas import NewsResponse
from app.utils.feed_config import (
    RSS_FEEDS, ISRAELI_SOURCES_FEEDS, INTERNATIONAL_SOURCES_FEEDS, 
    ARABIC_SOURCES_FEEDS, SOURCE_REGISTRY, get_source_info, get_all_feeds,
    get_source_count,
)
from app.utils.filters import ISRAELI_SOURCES, BLOCKED_SOURCES

router = APIRouter(tags=["News"])


@router.get("/categories")
async def get_categories():
    """Get all news categories."""
    return {
        "categories": list(RSS_FEEDS.keys()),
        "count": len(RSS_FEEDS)
    }


@router.get("/sources")
async def get_sources(
    language: Optional[str] = Query(None, description="Filter by language: hebrew|english|arabic"),
    country: Optional[str] = Query(None, description="Filter by country"),
    detailed: bool = Query(False, description="Include source metadata")
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
    
    # Filter by country if specified
    if country:
        filtered_sources = {}
        for name, url in sources.items():
            info = get_source_info(name)
            if info.get("country", "").lower() == country.lower():
                filtered_sources[name] = url
        sources = filtered_sources
    
    if detailed:
        # Return with metadata
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
                "category": info.get("category", "general")
            })
        return {
            "sources": sorted(result, key=lambda x: x["credibility"], reverse=True),
            "total": len(result)
        }
    else:
        # Return simple list with count breakdown
        counts = get_source_count()
        return {
            "israeli_sources": sorted(ISRAELI_SOURCES_FEEDS.keys()),
            "international_sources": sorted(INTERNATIONAL_SOURCES_FEEDS.keys()),
            "arabic_sources": sorted(ARABIC_SOURCES_FEEDS.keys()),
            "total": len(sources),
            "counts": counts,
            "blocked_sources": sorted(BLOCKED_SOURCES),
        }


@router.get("/news/international", response_model=NewsResponse)
async def international(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    return await fetch_news(
        "international", limit,
        israeli_only=True,
        exclude_negative=True,
        language="english",
        user_tier=user_tier,
        with_analysis=with_analysis,
    )


@router.get("/news/economy", response_model=NewsResponse)
async def economy(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    return await fetch_news(
        "economy", limit,
        israeli_only=True,
        language="english",
        user_tier=user_tier,
        with_analysis=with_analysis,
    )


@router.get("/news/defence", response_model=NewsResponse)
async def defence(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    return await fetch_news(
        "defence", limit,
        israeli_only=True,
        language="english",
        user_tier=user_tier,
        with_analysis=with_analysis,
    )


@router.get("/news/education", response_model=NewsResponse)
async def education(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    return await fetch_news(
        "education", limit,
        israeli_only=True,
        language="english",
        user_tier=user_tier,
        with_analysis=with_analysis,
    )


@router.get("/news/community", response_model=NewsResponse)
async def community(
    limit: int = Query(20, ge=1, le=100),
    exclude_negative: bool = Query(False),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    return await fetch_news(
        "community", limit,
        israeli_only=True,
        exclude_negative=exclude_negative,
        language="english",
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
    return await fetch_news(
        "political", limit,
        israeli_only=True,
        exclude_negative=exclude_negative,
        language="english",
        user_tier=user_tier,
        with_analysis=with_analysis,
    )


@router.get("/news/positive", response_model=NewsResponse)
async def positive(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    return await fetch_news(
        "positive", limit,
        israeli_only=True,
        exclude_negative=True,
        language="english",
        user_tier=user_tier,
        with_analysis=with_analysis,
    )


@router.get("/news/sport", response_model=NewsResponse)
async def sport(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    return await fetch_news(
        "sport", limit,
        israeli_only=True,
        language="english",
        user_tier=user_tier,
        with_analysis=with_analysis,
    )


@router.get("/news/culture", response_model=NewsResponse)
async def culture(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    return await fetch_news(
        "culture", limit,
        israeli_only=True,
        language="english",
        user_tier=user_tier,
        with_analysis=with_analysis,
    )


@router.get("/news/environment", response_model=NewsResponse)
async def environment(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    return await fetch_news(
        "environment", limit,
        israeli_only=True,
        language="english",
        user_tier=user_tier,
        with_analysis=with_analysis,
    )


@router.get("/news/science", response_model=NewsResponse)
async def science(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    return await fetch_news(
        "science", limit,
        israeli_only=True,
        language="english",
        user_tier=user_tier,
        with_analysis=with_analysis,
    )


@router.get("/news/knesset")
async def knesset(limit: int = Query(20, ge=1, le=50)):
    return await fetch_knesset_bills(limit)


@router.get("/news/arabic", response_model=NewsResponse)
async def arabic(
    limit: int = Query(20, ge=1, le=100),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
    with_analysis: bool = Query(False, description="Enable AI analysis (pro/platinum only)"),
):
    return await fetch_news(
        "arabic",
        limit,
        israeli_only=False,
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
    return await fetch_all_news(limit, user_tier=user_tier, with_analysis=with_analysis)
