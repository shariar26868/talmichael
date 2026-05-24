# app/core/cache.py
"""
Lightweight in-memory TTL cache (replaces Redis).
Uses a simple dict with expiry timestamps.
Good for single-instance dev/prod. For multi-instance, swap with Redis later.
"""

import time
import json
import asyncio
from typing import Any, Optional

_store: dict[str, tuple[Any, float]] = {}   # key → (value, expires_at)
_lock = asyncio.Lock()

NEWS_TTL    = 300    # 5 min
BILLS_TTL   = 600    # 10 min
SOURCE_TTL  = 3600   # 1 hour
AI_TTL      = 1800   # 30 min
INSIGHTS_TTL = 900   # 15 min
TRENDS_TTL   = 600   # 10 min
QA_TTL       = 300   # 5 min


async def cache_get(key: str) -> Optional[Any]:
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
    async with _lock:
        _store[key] = (value, time.time() + ttl)


async def cache_delete(key: str) -> None:
    async with _lock:
        _store.pop(key, None)


async def cache_delete_pattern(pattern: str) -> None:
    """Delete all keys that start with the pattern prefix (strips trailing *)."""
    prefix = pattern.rstrip("*")
    async with _lock:
        keys_to_delete = [k for k in _store if k.startswith(prefix)]
        for k in keys_to_delete:
            del _store[k]


# ── Key builders ──────────────────────────────────────────────────────────────

def news_key(category: str, limit: int, israeli_only: bool, exclude_negative: bool) -> str:
    return f"news:{category}:{limit}:{int(israeli_only)}:{int(exclude_negative)}"

def bills_key(limit: int) -> str:
    return f"knesset:bills:{limit}"

def source_key(source_name: str) -> str:
    return f"source:{source_name.lower().replace(' ', '_')}"

def ai_analysis_key(article_guid: str) -> str:
    return f"ai:analysis:{article_guid}"
