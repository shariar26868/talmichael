"""Cache layer with optional Redis backend and in-memory fallback.

If `settings.redis_url` is set, uses `redis.asyncio` to store JSON-serialized
values. Otherwise falls back to the lightweight in-memory TTL cache used by
the project previously.
"""

import time
import json
import asyncio
from typing import Any, Optional

from app.core.config import settings

_redis = None
_store: dict[str, tuple[Any, float]] = {}   # key → (value, expires_at)
_lock = asyncio.Lock()

# TTL defaults
NEWS_TTL = 300
BILLS_TTL = 600
SOURCE_TTL = 3600
AI_TTL = 1800
INSIGHTS_TTL = 900
TRENDS_TTL = 600
QA_TTL = 300
SUMMARY_7D_TTL = 3600
SUMMARY_30D_TTL = 10800


def _ensure_redis():
    """Lazily initialize the redis client if configured."""
    global _redis
    if _redis is not None:
        return _redis
    if not settings.redis_url:
        return None
    try:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        return _redis
    except Exception:
        _redis = None
        return None


async def cache_get(key: str) -> Optional[Any]:
    """Get value from Redis (if configured) else from in-memory store."""
    r = _ensure_redis()
    if r:
        try:
            raw = await r.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            # Fall back to in-memory on Redis errors
            pass

    async with _lock:
        entry = _store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del _store[key]
            return None
        return value


async def cache_set(key: str, value: Any, ttl: int = NEWS_TTL) -> None:
    r = _ensure_redis()
    if r:
        try:
            await r.set(key, json.dumps(value), ex=ttl)
            return
        except Exception:
            pass

    async with _lock:
        _store[key] = (value, time.time() + ttl)


async def cache_delete(key: str) -> None:
    r = _ensure_redis()
    if r:
        try:
            await r.delete(key)
            return
        except Exception:
            pass
    async with _lock:
        _store.pop(key, None)


async def cache_delete_pattern(pattern: str) -> None:
    """Delete keys that start with a given prefix (strip trailing *)."""
    prefix = pattern.rstrip("*")
    r = _ensure_redis()
    if r:
        try:
            # SCAN to avoid blocking redis
            cur = b"0"
            # redis-py asyncio returns strings when decode_responses=True
            cursor = 0
            while True:
                cursor, keys = await r.scan(cursor=cursor, match=prefix + "*", count=1000)
                if keys:
                    await r.delete(*keys)
                if cursor == 0:
                    break
            return
        except Exception:
            pass

    async with _lock:
        keys_to_delete = [k for k in _store if k.startswith(prefix)]
        for k in keys_to_delete:
            del _store[k]


# ── Key builders ──────────────────────────────────────────────────────────────

def news_key(category: str, limit: int, israeli_only: bool, exclude_negative: bool, language: str = "english", user_tier: str = "free", with_analysis: bool = False, source_type: str = "israel") -> str:
    return f"news:{category}:{limit}:{int(israeli_only)}:{int(exclude_negative)}:{language.lower()}:{user_tier.lower()}:{int(with_analysis)}:{source_type.lower()}"


def bills_key(limit: int) -> str:
    return f"knesset:bills:{limit}"


def source_key(source_name: str) -> str:
    return f"source:{source_name.lower().replace(' ', '_')}"


def ai_analysis_key(article_guid: str) -> str:
    return f"ai:analysis:{article_guid}"


def summary_key(period_days: int) -> str:
    return f"news:summary:{period_days}d"
