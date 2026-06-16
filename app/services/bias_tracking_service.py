# app/services/bias_tracking_service.py
"""
Temporal Bias Tracking — how source bias evolves over time.

Instead of relying on static seed tables, this service:
  1. Records every article-level bias assessment per source.
  2. Computes 7-day / 30-day / 90-day moving averages.
  3. Detects "bias drift" — when a source shifts significantly.
  4. Provides historical trend data for dashboards.

This lets us say: "Israel Hayom's coverage has shifted 0.12 points
rightward over the last 90 days" — based on actual article data,
not a hardcoded label.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from app.core.database import get_db

logger = logging.getLogger(__name__)

# Numerical encoding for bias positions (for computing averages)
BIAS_NUMERIC = {
    "far-left": -3.0,
    "left": -2.0,
    "center-left": -1.0,
    "center": 0.0,
    "center-right": 1.0,
    "right": 2.0,
    "far-right": 3.0,
    "unknown": 0.0,
    "unclear": 0.0,
}

# Reverse: numeric → label (for display)
def _numeric_to_label(value: float) -> str:
    """Convert a numeric bias value back to the closest label."""
    if value <= -2.5:
        return "far-left"
    elif value <= -1.5:
        return "left"
    elif value <= -0.5:
        return "center-left"
    elif value <= 0.5:
        return "center"
    elif value <= 1.5:
        return "center-right"
    elif value <= 2.5:
        return "right"
    else:
        return "far-right"


# Drift threshold — significant shift
DRIFT_THRESHOLD = 0.5  # if moving average shifts by this much, flag it


async def record_article_bias(
    source_name: str,
    article_guid: str,
    bias: str,
    bias_score: float,
    credibility_score: float,
) -> None:
    """Record a single article's bias assessment for temporal tracking.

    Called after every article analysis. Stores the data point in
    source_bias_history for rolling average computation.
    """
    db = get_db()
    await db.source_bias_history.insert_one({
        "source_name": source_name,
        "article_guid": article_guid,
        "bias_label": bias,
        "bias_numeric": BIAS_NUMERIC.get(bias, 0.0),
        "bias_score": bias_score,
        "credibility_score": credibility_score,
        "recorded_at": datetime.utcnow(),
    })


async def get_source_bias_history(
    source_name: str,
    days: int = 90,
    limit: int = 500,
) -> dict:
    """Get bias history and trend data for a source.

    Returns:
      - recent_entries: last N data points
      - averages: 7-day, 30-day, 90-day moving averages
      - drift: whether the source has shifted significantly
      - trend_direction: "stable", "shifting_left", "shifting_right"
    """
    db = get_db()
    cutoff = datetime.utcnow() - timedelta(days=days)

    entries = await db.source_bias_history.find(
        {"source_name": source_name, "recorded_at": {"$gte": cutoff}},
        {"_id": 0},
    ).sort("recorded_at", -1).to_list(length=limit)

    if not entries:
        return {
            "source_name": source_name,
            "data_points": 0,
            "message": "No bias history recorded for this source yet.",
        }

    now = datetime.utcnow()

    # Compute moving averages
    def _avg_for_window(window_days: int) -> Optional[dict]:
        window_cutoff = now - timedelta(days=window_days)
        window_entries = [
            e for e in entries
            if e.get("recorded_at") and e["recorded_at"] >= window_cutoff
        ]
        if not window_entries:
            return None

        avg_numeric = sum(e["bias_numeric"] for e in window_entries) / len(window_entries)
        avg_score = sum(e["bias_score"] for e in window_entries) / len(window_entries)
        avg_cred = sum(e["credibility_score"] for e in window_entries) / len(window_entries)

        return {
            "period_days": window_days,
            "data_points": len(window_entries),
            "avg_bias_numeric": round(avg_numeric, 2),
            "avg_bias_label": _numeric_to_label(avg_numeric),
            "avg_bias_score": round(avg_score, 2),
            "avg_credibility": round(avg_cred, 2),
        }

    avg_7d = _avg_for_window(7)
    avg_30d = _avg_for_window(30)
    avg_90d = _avg_for_window(90)

    # Detect drift
    drift_detected = False
    trend_direction = "stable"
    drift_magnitude = 0.0

    if avg_7d and avg_90d:
        drift_magnitude = avg_7d["avg_bias_numeric"] - avg_90d["avg_bias_numeric"]
        if abs(drift_magnitude) >= DRIFT_THRESHOLD:
            drift_detected = True
            trend_direction = "shifting_right" if drift_magnitude > 0 else "shifting_left"

    # Bias label distribution
    label_dist = defaultdict(int)
    for e in entries:
        label_dist[e.get("bias_label", "unknown")] += 1

    return {
        "source_name": source_name,
        "data_points": len(entries),
        "period_days": days,
        "averages": {
            "7_day": avg_7d,
            "30_day": avg_30d,
            "90_day": avg_90d,
        },
        "drift": {
            "detected": drift_detected,
            "magnitude": round(drift_magnitude, 2),
            "direction": trend_direction,
            "explanation": (
                f"Source has shifted {abs(drift_magnitude):.1f} points "
                f"{'rightward' if drift_magnitude > 0 else 'leftward'} "
                f"over the last 90 days."
            ) if drift_detected else "No significant bias shift detected.",
        },
        "label_distribution": dict(label_dist),
    }


async def get_drifting_sources(threshold: float = DRIFT_THRESHOLD) -> list[dict]:
    """Find all sources that have drifted significantly recently.

    Useful for admin dashboards and alerting.
    """
    db = get_db()

    # Get all unique source names
    source_names = await db.source_bias_history.distinct("source_name")

    drifting = []
    for source in source_names:
        history = await get_source_bias_history(source, days=90)
        drift = history.get("drift", {})
        if drift.get("detected"):
            drifting.append({
                "source_name": source,
                "drift_magnitude": drift["magnitude"],
                "direction": drift["direction"],
                "data_points": history["data_points"],
            })

    return sorted(drifting, key=lambda x: abs(x["drift_magnitude"]), reverse=True)
