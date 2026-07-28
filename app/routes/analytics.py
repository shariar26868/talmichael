# app/routes/analytics.py
"""API routes for AI Token Usage and Cost Analytics."""

from typing import Optional
from fastapi import APIRouter, Query, Path
from app.services.ai_cost_service import (
    get_user_daily_ai_cost,
    get_system_ai_cost_summary,
)

router = APIRouter(prefix="/analytics", tags=["Analytics & AI Costs"])


@router.get("/ai-cost/user/{user_id}")
async def get_user_ai_cost(
    user_id: str = Path(..., description="Unique User ID"),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (defaults to today)"),
):
    """
    Get daily AI usage and cost in USD for a specific user.
    - user_id: ID of the target user
    - date: YYYY-MM-DD format (defaults to current date)
    """
    return await get_user_daily_ai_cost(user_id=user_id, target_date=date)


@router.get("/ai-cost/summary")
async def get_system_ai_cost():
    """
    Get full system AI expenditure summary.
    Returns:
    - Daily Cost: Today vs Yesterday
    - Weekly Cost: This Week vs Last Week
    - Monthly Cost: This Month vs Last Month
    - Breakdown by Model (GPT-4o, GPT-4o-mini, Gemini, etc.)
    - Top Consuming Users
    """
    return await get_system_ai_cost_summary()
