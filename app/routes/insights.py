# app/routes/insights.py
"""
AI Insights + Trend Detection endpoints.

GET /insights/{category}   — Hebrew insight + trends for one category
GET /insights/all          — insights for all categories
GET /insights/trends       — global trending topics
"""

from fastapi import APIRouter, Query
from typing import Optional

from app.services.insights_service import (
    generate_category_insight,
    generate_all_insights,
    get_trending_topics,
)
from app.services.news_service import fetch_news, fetch_all_news
from app.utils.feed_config import RSS_FEEDS

router = APIRouter(prefix="/insights", tags=["AI Insights & Trends"])


@router.get("/trends", summary="Global trending topics across all categories")
async def global_trends(
    limit: int = Query(20, ge=5, le=50),
    use_ai: bool = Query(False, description="Use GPT-4o for smarter trend analysis"),
):
    """
    Detect trending topics across all news categories combined.
    - use_ai=false → keyword frequency analysis (instant)
    - use_ai=true  → GPT-4o semantic trend detection
    """
    all_news = await fetch_all_news(10)
    all_articles = []
    for cat, data in all_news.items():
        if isinstance(data, dict) and "articles" in data:
            for a in data["articles"]:
                all_articles.append(a if isinstance(a, dict) else a.model_dump())

    trends = await get_trending_topics(all_articles, use_ai=use_ai, top_n=limit)
    return {
        "total_articles_analyzed": len(all_articles),
        "use_ai": use_ai,
        "trends": trends,
    }


@router.get("/all", summary="AI insights for all categories")
async def all_insights(
    limit: int = Query(15, ge=5, le=30),
    use_ai: bool = Query(False, description="Use GPT-4o for Hebrew insights"),
):
    """
    Generate insights for every news category simultaneously.
    Returns Hebrew insight paragraph + trending keywords per category.
    """
    all_news = await fetch_all_news(limit)

    category_articles: dict[str, list[dict]] = {}
    for cat, data in all_news.items():
        if isinstance(data, dict) and "articles" in data:
            category_articles[cat] = [
                a if isinstance(a, dict) else a.model_dump()
                for a in data["articles"]
            ]

    return await generate_all_insights(category_articles, use_ai=use_ai)


@router.get("/{category}", summary="AI insight + trends for a specific category")
async def category_insight(
    category: str,
    limit: int = Query(20, ge=5, le=50),
    use_ai: bool = Query(False, description="Use GPT-4o for Hebrew insight"),
):
    """
    Generate a Hebrew insight paragraph and trending topics for one category.

    Categories: social, economics, security, education, political, positive,
                sport, culture, environment, science, international, knesset
    """
    if category not in RSS_FEEDS:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Unknown category. Valid: {list(RSS_FEEDS.keys())}",
        )

    news = await fetch_news(category, limit, israeli_only=True)
    articles = [a.model_dump() for a in news.articles]

    return await generate_category_insight(category, articles, use_ai=use_ai)
