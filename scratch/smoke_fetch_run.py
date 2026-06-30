"""Smoke test: run a small fetch + fact-check cycle.

Usage:
  python scratch/smoke_fetch_run.py

Make sure `.env` has `MONGODB_URL` (and `REDIS_URL` if used) and Mongo is reachable.
"""
import asyncio
import os
import logging

logging.basicConfig(level=logging.INFO)


async def main():
    # Import lazily so app config picks up .env
    from app.core.database import init_db, close_db
    from app.services.news_service import fetch_all_news

    print("Initializing DB and running a small fetch...")
    await init_db()
    try:
        # Run a small fetch (limit=10) which will enqueue fact-check tasks
        result = await fetch_all_news(limit=10, user_tier="system", with_analysis=False)
        total = result.get("total") if isinstance(result, dict) else getattr(result, "total", None)
        print(f"Fetch completed — total articles returned: {total}")
        # Print top-level meta if available
        try:
            meta = result.get("meta") if isinstance(result, dict) else getattr(result, "meta", None)
            print("Meta:", meta)
        except Exception:
            pass
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
