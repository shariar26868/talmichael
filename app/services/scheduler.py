from typing import Optional
import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import zoneinfo

from app.core.config import settings

logger = logging.getLogger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None


def _get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        tz = zoneinfo.ZoneInfo(settings.scheduler_timezone)
        _scheduler = AsyncIOScheduler(timezone=tz)
    return _scheduler


def start_scheduler():
    """Start the APScheduler and add periodic fetch jobs.

    This schedules an hourly incremental fetch at minute 0 and a nightly
    full refresh at 00:05 Israel time. The actual work is delegated to
    `app.services.news_service.fetch_all_news` which persists results.
    """
    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled via settings")
        return

    sched = _get_scheduler()

    try:
        # Hourly incremental fetch at minute 0
        sched.add_job(_hourly_fetch_job, CronTrigger(minute=0), id="hourly_fetch", replace_existing=True)

        # Nightly full refresh at 00:05
        sched.add_job(_nightly_full_refresh_job, CronTrigger(hour=0, minute=5), id="nightly_full_refresh", replace_existing=True)

        sched.start()
        logger.info("Scheduler started with hourly and nightly jobs (tz=%s)", settings.scheduler_timezone)
    except Exception as e:
        logger.exception("Failed to start scheduler: %s", e)


def stop_scheduler():
    global _scheduler
    if _scheduler:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None


async def _run_fetch_all(limit: int = 80):
    """Helper to call fetch_all_news in an async-safe way."""
    try:
        from app.services.news_service import fetch_all_news
        # Run and discard result (news_service persists to DB)
        await fetch_all_news(limit=limit, user_tier="system", with_analysis=False)
    except Exception as e:
        logger.exception("Scheduled fetch failed: %s", e)


def _hourly_fetch_job():
    # schedule into event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        asyncio.ensure_future(_run_fetch_all(limit=80))
    else:
        # If no running loop, run in new loop
        asyncio.run(_run_fetch_all(limit=80))


def _enqueue_precompute_batches(articles: list):
    """Helper to enqueue article ID batches into Celery for analysis."""
    try:
        from app.core.celery import celery_app
        from app.services.ai_tasks import batch_analyze_articles
    except Exception:
        return

    # Build simple IDs (link or generated)
    article_ids = []
    for a in articles:
        link = a.get("link") if isinstance(a, dict) else getattr(a, "link", None)
        if link:
            article_ids.append(link)

    batch_size = 20
    for i in range(0, len(article_ids), batch_size):
        batch = article_ids[i:i+batch_size]
        try:
            batch_analyze_articles.delay(batch, "system")
        except Exception:
            pass


def _nightly_full_refresh_job():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        asyncio.ensure_future(_run_fetch_all(limit=400))
    else:
        asyncio.run(_run_fetch_all(limit=400))
