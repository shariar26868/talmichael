# app/routes/summary.py
"""
News Summary API routes.

Endpoints:
  GET /news/summary/7days   — AI digest of the past 7 days, by category
  GET /news/summary/30days  — AI digest of the past 30 days, by category

Both return a single JSON blob structured as:
  {
    "period": "7days",
    "generated_at": "...",
    "date_range": { "from": "...", "to": "..." },
    "summaries": {
      "international": { "summary": "...", "top_headlines": [...], ... },
      "political":     { ... },
      "sport":         { ... },
      ...
    }
  }
"""

from fastapi import APIRouter, Query, BackgroundTasks
from app.models.schemas import NewsSummaryResponse
from app.services.summary_service import fetch_period_summary

router = APIRouter(tags=["News Summary"])


@router.get(
    "/news/summary/7days",
    response_model=NewsSummaryResponse,
    summary="7-Day News Digest",
    description=(
        "Returns an AI-generated summary of the past 7 days of news, "
        "organised by category (international, political, sport, economy, etc.). "
        "Each category entry contains a prose summary, top headlines, key themes, "
        "and sentiment breakdown.\n\n"
        "**Caching:** Results are cached for 1 hour to avoid redundant AI calls."
    ),
)
async def summary_7days(
    background_tasks: BackgroundTasks,
    user_tier: str = Query(
        "free",
        description="User tier: free | pro | platinum. Platinum gets richer AI summaries.",
    ),
    refresh: bool = Query(
        False,
        description="Set to true to force-regenerate bypassing cache.",
    ),
):
    """7-day news digest across all categories."""
    if refresh:
        # Delete cached result so fetch_period_summary regenerates
        from app.core.cache import cache_delete, summary_key
        await cache_delete(summary_key(7))

    return await fetch_period_summary(period_days=7)


@router.get(
    "/news/summary/30days",
    response_model=NewsSummaryResponse,
    summary="30-Day News Digest",
    description=(
        "Returns an AI-generated summary of the past 30 days of news, "
        "organised by category (international, political, sport, economy, etc.). "
        "Each category entry contains a prose summary, top headlines, key themes, "
        "and sentiment breakdown.\n\n"
        "**Caching:** Results are cached for 3 hours to avoid redundant AI calls. "
        "**Note:** Historical depth depends on how long the system has been running "
        "and collecting articles into MongoDB. On a fresh deployment the digest is "
        "based on currently available RSS articles."
    ),
)
async def summary_30days(
    background_tasks: BackgroundTasks,
    user_tier: str = Query(
        "free",
        description="User tier: free | pro | platinum.",
    ),
    refresh: bool = Query(
        False,
        description="Set to true to force-regenerate bypassing cache.",
    ),
):
    """30-day news digest across all categories."""
    if refresh:
        from app.core.cache import cache_delete, summary_key
        await cache_delete(summary_key(30))

    return await fetch_period_summary(period_days=30)
