"""Celery tasks for batch AI analysis."""

from celery import Celery, group
from app.core.celery import celery_app
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="batch_analyze_articles")
def batch_analyze_articles(article_ids: list, user_tier: str = "system"):
    """
    Entry task: receives a list of article identifiers and dispatches
    simple per-article tasks. Real analysis tasks should be implemented
    in `app.services.ai_service` and called from worker processes.
    """
    logger.info(f"batch_analyze_articles received {len(article_ids)} articles")
    # For now, spawn individual analyze tasks
    for aid in article_ids:
        try:
            # For simplicity, call a placeholder task name
            celery_app.send_task("analyze_article", args=[aid, user_tier])
        except Exception as e:
            logger.exception("Failed to enqueue analyze_article for %s: %s", aid, e)

@celery_app.task(name="analyze_article")
def analyze_article(article_id: str, user_tier: str = "system"):
    # Placeholder worker task: actual logic should call ai_service
    logger.info(f"analyze_article: {article_id} (tier={user_tier})")
    return {"article_id": article_id, "status": "queued"}
