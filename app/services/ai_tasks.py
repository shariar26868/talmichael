"""Celery tasks for batch AI analysis."""

import asyncio
import logging
from app.core.celery import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="batch_analyze_articles")
def batch_analyze_articles(article_ids: list, user_tier: str = "system"):
    """
    Entry task: receives a list of article identifiers and dispatches
    individual article analysis jobs.
    """
    logger.info(f"batch_analyze_articles received {len(article_ids)} articles")
    for aid in article_ids:
        try:
            analyze_article.delay(aid, user_tier)
        except Exception as e:
            logger.exception("Failed to enqueue analyze_article for %s: %s", aid, e)


async def _fetch_article_record(article_id: str) -> dict | None:
    from app.core.database import get_db

    db = get_db()
    doc = await db.cached_articles.find_one({"guid": article_id})
    if not doc:
        doc = await db.cached_articles.find_one({"link": article_id})
    return doc


@celery_app.task(name="analyze_article")
def analyze_article(article_id: str, user_tier: str = "system"):
    """Worker task to analyze a single cached article by GUID or link."""
    logger.info(f"analyze_article: {article_id} (tier={user_tier})")

    async def _run():
        from app.services.ai_service import analyze_article as analyze_article_async

        article = await _fetch_article_record(article_id)
        if not article:
            logger.warning("Article not found for AI analysis: %s", article_id)
            return {"article_id": article_id, "status": "missing"}

        guid = article.get("guid") or article.get("link")
        title = article.get("title", "")
        description = article.get("description", "")
        source = article.get("source")
        source_url = article.get("source_url")

        result = await analyze_article_async(
            guid=guid,
            title=title,
            description=description,
            source=source,
            source_url=source_url,
            user_tier=user_tier,
        )
        return result.model_dump(exclude_none=True)

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.exception("AI analysis task failed for %s: %s", article_id, e)
        return {"article_id": article_id, "status": "error", "error": str(e)}
