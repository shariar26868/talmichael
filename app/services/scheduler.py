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

    Jobs:
      - Startup warmup  : runs IMMEDIATELY on boot to pre-fill the DB
      - Every 30 minutes: incremental fetch (keeps DB always fresh)
      - Nightly 00:05   : large full refresh (400 articles per category)
      - Daily 01:00     : AI precompute queue
    """
    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled via settings")
        return

    sched = _get_scheduler()

    try:
        # ── Startup warmup: runs once immediately after server boots ─────────
        # This ensures the DB is pre-filled right away, not after 30 min.
        sched.add_job(
            _hourly_fetch_job,
            trigger="date",       # run once at a specific time
            id="startup_warmup",
            replace_existing=True,
            misfire_grace_time=120,
        )

        # ── Every 30 minutes: keep DB fresh automatically ───────────────────
        sched.add_job(
            _hourly_fetch_job,
            CronTrigger(minute="0,30"),
            id="periodic_fetch",
            replace_existing=True,
        )

        # ── Nightly full refresh at 00:05 (large batch) ─────────────────────
        sched.add_job(
            _nightly_full_refresh_job,
            CronTrigger(hour=0, minute=5),
            id="nightly_full_refresh",
            replace_existing=True,
        )

        # ── Daily AI precompute queue at 01:00 ───────────────────────────
        sched.add_job(
            _precompute_analysis_job,
            CronTrigger(hour=1, minute=0),
            id="precompute_analysis",
            replace_existing=True,
        )

        sched.start()
        logger.info(
            "Scheduler started — immediate warmup + every-30min fetch + nightly refresh (tz=%s)",
            settings.scheduler_timezone,
        )
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


async def _run_fetch_all(limit: int = 80, use_cache: bool = False):
    """Helper to call fetch_all_news in an async-safe way."""
    try:
        from app.services.news_service import fetch_all_news
        # user_tier="system" triggers licensed APIs (NewsAPI, NewsData, etc.)
        # force_refresh=True ensures we bypass DB-first and always hit live sources
        # use_cache=False ensures fresh data is written to DB
        await fetch_all_news(
            limit=limit,
            user_tier="system",
            with_analysis=False,
            use_cache=False,
        )
        logger.info("Scheduled fetch completed: fetched up to %d articles per category", limit)
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


def _precompute_analysis_job():
    """Run a larger fetch and enqueue article batches for AI analysis."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    async def _run():
        from app.services.news_service import fetch_all_news
        try:
            result = await fetch_all_news(
                limit=200,
                user_tier="system",
                with_analysis=False,
                use_cache=False,
            )
            articles = result.get("articles", [])
            _enqueue_precompute_batches(articles)
            logger.info("Precompute analysis job queued %d articles", len(articles))
        except Exception as e:
            logger.exception("Precompute analysis job failed: %s", e)

    if loop and loop.is_running():
        asyncio.ensure_future(_run())
    else:
        asyncio.run(_run())


def _enqueue_precompute_batches(articles: list):
    """Helper to enqueue article ID batches into Celery for analysis."""
    try:
        from app.services.ai_tasks import batch_analyze_articles
    except Exception:
        return

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
