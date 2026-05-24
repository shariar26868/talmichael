# app/routes/news.py

from fastapi import APIRouter, Query
from app.services.news_service import fetch_news, fetch_all_news, fetch_knesset_bills
from app.models.schemas import NewsResponse
from app.utils.feed_config import RSS_FEEDS
from app.utils.filters import ISRAELI_SOURCES, BLOCKED_SOURCES

router = APIRouter(tags=["News"])


@router.get("/categories")
async def get_categories():
    return {"categories": list(RSS_FEEDS.keys())}


@router.get("/sources")
async def get_sources():
    return {
        "israeli_sources": sorted(ISRAELI_SOURCES),
        "blocked_sources": sorted(BLOCKED_SOURCES),
    }


@router.get("/news/international", response_model=NewsResponse)
async def international(limit: int = Query(20, ge=1, le=100)):
    return await fetch_news("international", limit, israeli_only=True, exclude_negative=True)


@router.get("/news/economy", response_model=NewsResponse)
async def economy(limit: int = Query(20, ge=1, le=100)):
    return await fetch_news("economy", limit, israeli_only=True)


@router.get("/news/defence", response_model=NewsResponse)
async def defence(limit: int = Query(20, ge=1, le=100)):
    return await fetch_news("defence", limit, israeli_only=True)


@router.get("/news/education", response_model=NewsResponse)
async def education(limit: int = Query(20, ge=1, le=100)):
    return await fetch_news("education", limit, israeli_only=True)


@router.get("/news/community", response_model=NewsResponse)
async def community(
    limit: int = Query(20, ge=1, le=100),
    exclude_negative: bool = Query(False),
):
    return await fetch_news("community", limit, israeli_only=True, exclude_negative=exclude_negative)


@router.get("/news/political", response_model=NewsResponse)
async def political(
    limit: int = Query(20, ge=1, le=100),
    exclude_negative: bool = Query(False),
):
    return await fetch_news("political", limit, israeli_only=True, exclude_negative=exclude_negative)


@router.get("/news/positive", response_model=NewsResponse)
async def positive(limit: int = Query(20, ge=1, le=100)):
    return await fetch_news("positive", limit, israeli_only=True, exclude_negative=True)


@router.get("/news/sport", response_model=NewsResponse)
async def sport(limit: int = Query(20, ge=1, le=100)):
    return await fetch_news("sport", limit, israeli_only=True)


@router.get("/news/culture", response_model=NewsResponse)
async def culture(limit: int = Query(20, ge=1, le=100)):
    return await fetch_news("culture", limit, israeli_only=True)


@router.get("/news/environment", response_model=NewsResponse)
async def environment(limit: int = Query(20, ge=1, le=100)):
    return await fetch_news("environment", limit, israeli_only=True)


@router.get("/news/science", response_model=NewsResponse)
async def science(limit: int = Query(20, ge=1, le=100)):
    return await fetch_news("science", limit, israeli_only=True)


@router.get("/news/knesset")
async def knesset(limit: int = Query(20, ge=1, le=50)):
    return await fetch_knesset_bills(limit)


@router.get("/news/all")
async def all_news(limit: int = Query(10, ge=1, le=50)):
    return await fetch_all_news(limit)
