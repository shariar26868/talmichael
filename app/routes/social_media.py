# app/routes/social_media.py
"""Twitter/X scraping routes (moved from old Api/ folder)."""

import asyncio
import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import NewsArticle

logger = logging.getLogger(__name__)

try:
    from twscrape import API as TwAPI
    _TWSCRAPE_AVAILABLE = True
except ImportError:
    _TWSCRAPE_AVAILABLE = False
    logger.warning("twscrape not installed. Social endpoints will return 503.")

router = APIRouter(prefix="/social", tags=["Social Media"])

_DB_PATH = os.environ.get("TWSCRAPE_DB", "twscrape_accounts.db")
_tw_api: Optional["TwAPI"] = None

ISRAELI_TWITTER_ACCOUNTS = [
    "Jerusalem_Post", "TimesofIsrael", "haaretzcom", "ynetnews",
    "i24NEWS_EN", "IsraelHayomEng", "KnessetIsrael", "IsraeliPM",
    "IDF", "IsraelMFA",
]

ISRAELI_HASHTAGS = ["#Israel", "#IsraelNews", "#Knesset", "#TelAviv", "#Jerusalem"]


def _get_tw_api() -> "TwAPI":
    global _tw_api
    if _tw_api is None:
        _tw_api = TwAPI(_DB_PATH)
    return _tw_api


def _unavailable():
    raise HTTPException(
        status_code=503,
        detail="twscrape not installed. Run: pip install twscrape",
    )


def _build_query(base: str, israeli_only: bool) -> str:
    if not israeli_only:
        return f"({base}) lang:en"
    accounts = " OR ".join(f"from:{a}" for a in ISRAELI_TWITTER_ACCOUNTS[:5])
    hashtags = " OR ".join(ISRAELI_HASHTAGS[:3])
    return f"({base}) ({accounts} OR {hashtags}) lang:en"


def _to_article(tweet) -> NewsArticle:
    username = tweet.user.username if tweet.user else "unknown"
    pub_date = tweet.date.isoformat() + "Z" if isinstance(tweet.date, datetime) else str(tweet.date)
    return NewsArticle(
        title=f"Tweet by @{username}",
        link=f"https://twitter.com/{username}/status/{tweet.id}",
        description=tweet.rawContent or "",
        pub_date=pub_date,
        source="Twitter / X",
        source_url=f"https://twitter.com/{username}",
        guid=str(tweet.id),
    )


@router.get("/twitter/search")
async def search_twitter(
    query: str = Query(...),
    limit: int = Query(10, ge=1, le=100),
    israeli_only: bool = Query(True),
):
    if not _TWSCRAPE_AVAILABLE:
        _unavailable()
    api = _get_tw_api()
    full_query = _build_query(query, israeli_only)
    tweets = []
    try:
        async for tweet in api.search(full_query, limit=limit):
            tweets.append(_to_article(tweet))
            if len(tweets) >= limit:
                break
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Twitter search failed: {e}")
    return {"query": query, "full_query": full_query, "count": len(tweets), "tweets": tweets}


@router.get("/twitter/user/{username}")
async def user_tweets(username: str, limit: int = Query(10, ge=1, le=100)):
    if not _TWSCRAPE_AVAILABLE:
        _unavailable()
    api = _get_tw_api()
    tweets = []
    try:
        user = await api.user_by_login(username)
        if not user:
            raise HTTPException(status_code=404, detail=f"@{username} not found")
        async for tweet in api.user_tweets(user.id, limit=limit):
            tweets.append(_to_article(tweet))
            if len(tweets) >= limit:
                break
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"username": username, "count": len(tweets), "tweets": tweets}


@router.get("/twitter/israeli-accounts")
async def israeli_account_tweets(limit: int = Query(5, ge=1, le=20)):
    if not _TWSCRAPE_AVAILABLE:
        _unavailable()
    api = _get_tw_api()

    async def _fetch(username: str):
        try:
            user = await api.user_by_login(username)
            if not user:
                return username, {"error": "not found"}
            items = []
            async for tweet in api.user_tweets(user.id, limit=limit):
                items.append(_to_article(tweet))
                if len(items) >= limit:
                    break
            return username, items
        except Exception as e:
            return username, {"error": str(e)}

    results = await asyncio.gather(*[_fetch(a) for a in ISRAELI_TWITTER_ACCOUNTS])
    return {"accounts": ISRAELI_TWITTER_ACCOUNTS, "data": dict(results)}
