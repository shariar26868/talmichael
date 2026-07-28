# app/services/ai_cost_service.py
"""
AI Token Usage & Cost Tracking Service.

Tracks per-user and system-wide AI costs in USD based on model pricing:
- GPT-4o-mini  : $0.150 / 1M input,  $0.600 / 1M output
- GPT-4o       : $2.500 / 1M input, $10.000 / 1M output
- Gemini Flash : $0.075 / 1M input,  $0.300 / 1M output
- Gemini Pro   : $1.250 / 1M input,  $5.000 / 1M output
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.core.database import get_db

logger = logging.getLogger(__name__)

# Model Pricing per 1,000,000 Tokens (USD)
MODEL_RATES: Dict[str, Dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.150 / 1_000_000, "output": 0.600 / 1_000_000},
    "gpt-4o": {"input": 2.500 / 1_000_000, "output": 10.000 / 1_000_000},
    "gemini-1.5-flash": {"input": 0.075 / 1_000_000, "output": 0.300 / 1_000_000},
    "gemini-1.5-pro": {"input": 1.250 / 1_000_000, "output": 5.000 / 1_000_000},
    "default": {"input": 0.150 / 1_000_000, "output": 0.600 / 1_000_000},
}


def calculate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate USD cost based on token counts and model rates."""
    rates = MODEL_RATES.get(model.lower(), MODEL_RATES["default"])
    cost = (prompt_tokens * rates["input"]) + (completion_tokens * rates["output"])
    return round(cost, 6)


async def log_ai_usage(
    user_id: str,
    endpoint: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    extra_meta: Optional[dict] = None,
) -> None:
    """Log an AI request token usage and calculated USD cost into MongoDB ai_usage_logs."""
    try:
        db = get_db()
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = calculate_cost_usd(model, prompt_tokens, completion_tokens)
        now = datetime.utcnow()

        doc = {
            "user_id": user_id or "system",
            "endpoint": endpoint,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "created_at": now,
            "date": now.strftime("%Y-%m-%d"),
        }
        if extra_meta:
            doc["metadata"] = extra_meta

        await db.ai_usage_logs.insert_one(doc)
        logger.debug(f"[ai_usage_logs] Logged {total_tokens} tokens (${cost_usd}) for user={user_id}")
    except Exception as e:
        logger.warning(f"Failed to log AI usage: {e}")


async def get_user_daily_ai_cost(user_id: str, target_date: Optional[str] = None) -> Dict[str, Any]:
    """Get total AI usage and USD cost for a specific user on a given date (default today)."""
    try:
        db = get_db()
        date_str = target_date or datetime.utcnow().strftime("%Y-%m-%d")

        pipeline = [
            {"$match": {"user_id": user_id, "date": date_str}},
            {
                "$group": {
                    "_id": "$user_id",
                    "total_cost_usd": {"$sum": "$cost_usd"},
                    "total_tokens": {"$sum": "$total_tokens"},
                    "prompt_tokens": {"$sum": "$prompt_tokens"},
                    "completion_tokens": {"$sum": "$completion_tokens"},
                    "request_count": {"$sum": 1},
                }
            },
        ]
        results = await db.ai_usage_logs.aggregate(pipeline).to_list(length=1)

        if results:
            res = results[0]
            return {
                "user_id": user_id,
                "date": date_str,
                "total_cost_usd": round(res.get("total_cost_usd", 0.0), 6),
                "total_tokens": res.get("total_tokens", 0),
                "prompt_tokens": res.get("prompt_tokens", 0),
                "completion_tokens": res.get("completion_tokens", 0),
                "total_requests": res.get("request_count", 0),
            }

        return {
            "user_id": user_id,
            "date": date_str,
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_requests": 0,
        }
    except Exception as e:
        logger.error(f"get_user_daily_ai_cost failed: {e}")
        return {"error": str(e), "user_id": user_id, "total_cost_usd": 0.0}


async def get_system_ai_cost_summary() -> Dict[str, Any]:
    """
    Get full system AI expenditure summary:
    - Daily: Today vs Yesterday
    - Weekly: This Week vs Last Week
    - Monthly: This Month vs Last Month
    - Breakdown by Model
    - Top Consuming Users
    """
    try:
        db = get_db()
        now = datetime.utcnow()
        today_str = now.strftime("%Y-%m-%d")
        yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        start_this_week = now - timedelta(days=now.weekday())
        start_this_week_dt = datetime(start_this_week.year, start_this_week.month, start_this_week.day)
        start_last_week_dt = start_this_week_dt - timedelta(days=7)

        start_this_month_dt = datetime(now.year, now.month, 1)
        if now.month == 1:
            start_last_month_dt = datetime(now.year - 1, 12, 1)
        else:
            start_last_month_dt = datetime(now.year, now.month - 1, 1)

        # ── Daily Costs ───────────────────────────────────────────────────────
        today_pipeline = [
            {"$match": {"date": today_str}},
            {"$group": {"_id": None, "total": {"$sum": "$cost_usd"}, "tokens": {"$sum": "$total_tokens"}}},
        ]
        yesterday_pipeline = [
            {"$match": {"date": yesterday_str}},
            {"$group": {"_id": None, "total": {"$sum": "$cost_usd"}}},
        ]

        today_res = await db.ai_usage_logs.aggregate(today_pipeline).to_list(length=1)
        yesterday_res = await db.ai_usage_logs.aggregate(yesterday_pipeline).to_list(length=1)

        today_cost = round(today_res[0]["total"], 4) if today_res else 0.0
        today_tokens = today_res[0]["tokens"] if today_res else 0
        yesterday_cost = round(yesterday_res[0]["total"], 4) if yesterday_res else 0.0

        # ── Weekly Costs ──────────────────────────────────────────────────────
        this_week_res = await db.ai_usage_logs.aggregate([
            {"$match": {"created_at": {"$gte": start_this_week_dt}}},
            {"$group": {"_id": None, "total": {"$sum": "$cost_usd"}}},
        ]).to_list(length=1)

        last_week_res = await db.ai_usage_logs.aggregate([
            {"$match": {"created_at": {"$gte": start_last_week_dt, "$lt": start_this_week_dt}}},
            {"$group": {"_id": None, "total": {"$sum": "$cost_usd"}}},
        ]).to_list(length=1)

        this_week_cost = round(this_week_res[0]["total"], 4) if this_week_res else 0.0
        last_week_cost = round(last_week_res[0]["total"], 4) if last_week_res else 0.0

        # ── Monthly Costs ─────────────────────────────────────────────────────
        this_month_res = await db.ai_usage_logs.aggregate([
            {"$match": {"created_at": {"$gte": start_this_month_dt}}},
            {"$group": {"_id": None, "total": {"$sum": "$cost_usd"}}},
        ]).to_list(length=1)

        last_month_res = await db.ai_usage_logs.aggregate([
            {"$match": {"created_at": {"$gte": start_last_month_dt, "$lt": start_this_month_dt}}},
            {"$group": {"_id": None, "total": {"$sum": "$cost_usd"}}},
        ]).to_list(length=1)

        this_month_cost = round(this_month_res[0]["total"], 4) if this_month_res else 0.0
        last_month_cost = round(last_month_res[0]["total"], 4) if last_month_res else 0.0

        # ── Model Breakdown ───────────────────────────────────────────────────
        model_res = await db.ai_usage_logs.aggregate([
            {"$group": {"_id": "$model", "total_cost": {"$sum": "$cost_usd"}, "total_tokens": {"$sum": "$total_tokens"}}},
            {"$sort": {"total_cost": -1}},
        ]).to_list(length=20)

        cost_by_model = {
            r["_id"] or "unknown": {
                "total_cost_usd": round(r["total_cost"], 4),
                "total_tokens": r["total_tokens"],
            }
            for r in model_res
        }

        # ── Top Consuming Users ───────────────────────────────────────────────
        top_users_res = await db.ai_usage_logs.aggregate([
            {"$group": {"_id": "$user_id", "total_cost": {"$sum": "$cost_usd"}, "total_tokens": {"$sum": "$total_tokens"}, "requests": {"$sum": 1}}},
            {"$sort": {"total_cost": -1}},
            {"$limit": 10},
        ]).to_list(length=10)

        top_users = [
            {
                "user_id": r["_id"] or "anonymous",
                "total_cost_usd": round(r["total_cost"], 4),
                "total_tokens": r["total_tokens"],
                "total_requests": r["requests"],
            }
            for r in top_users_res
        ]

        return {
            "status": "success",
            "currency": "USD",
            "daily_summary": {
                "today_cost_usd": today_cost,
                "today_total_tokens": today_tokens,
                "yesterday_cost_usd": yesterday_cost,
            },
            "weekly_summary": {
                "this_week_cost_usd": this_week_cost,
                "last_week_cost_usd": last_week_cost,
            },
            "monthly_summary": {
                "this_month_cost_usd": this_month_cost,
                "last_month_cost_usd": last_month_cost,
            },
            "cost_by_model": cost_by_model,
            "top_consuming_users": top_users,
        }
    except Exception as e:
        logger.error(f"get_system_ai_cost_summary failed: {e}")
        return {"status": "error", "message": str(e)}
