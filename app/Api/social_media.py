#app/Api/social_media.py
import asyncio
import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from app.models import NewsArticle

logger = logging.getLogger(__name__)

# ── twscrape lazy import ──────────────────────────────────────────────────────
# Wrapped in a try/except so the rest of the app still starts even if twscrape
# is not installed yet.
try:
    from twscrape import API as TwAPI, gather
    _TWSCRAPE_AVAILABLE = True
except ImportError:
    _TWSCRAPE_AVAILABLE = False
    logger.warning(
        "twscrape is not installed. Run: pip install twscrape  "
        "Social-media endpoints will return 503 until it is available."
    )

router = APIRouter()

# ── Account pool path ────────────────────────────────────────────────────────
# Defaults to a file next to this module; override via env var TWSCRAPE_DB.
_DB_PATH = os.environ.get("TWSCRAPE_DB", "twscrape_accounts.db")

# ── Module-level API singleton ────────────────────────────────────────────────
# Reusing one instance across requests avoids re-opening the SQLite DB on
# every call and preserves the login session cookies.
_tw_api: Optional["TwAPI"] = None


def _get_tw_api() -> "TwAPI":
    """Return (or lazily create) the module-level twscrape API instance."""
    global _tw_api
    if _tw_api is None:
        _tw_api = TwAPI(_DB_PATH)
    return _tw_api


def _unavailable() -> None:
    """Raise a friendly 503 when twscrape is not installed."""
    raise HTTPException(
        status_code=503,
        detail=(
            "twscrape is not installed. "
            "Run `pip install twscrape` then add and login accounts: "
            "`python -m twscrape add_accounts accounts.txt && python -m twscrape login_all`"
        ),
    )


# ── Israeli Twitter accounts / hashtags to include ───────────────────────────
# Appending these to user queries helps surface Israeli content even when the
# user's query is generic.
ISRAELI_TWITTER_ACCOUNTS: list[str] = [
    "Jerusalem_Post",
    "TimesofIsrael",
    "haaretzcom",
    "ynetnews",
    "i24NEWS_EN",
    "IsraelHayomEng",
    "KnessetIsrael",
    "IsraeliPM",
    "IDF",
    "IsraelMFA",
]

ISRAELI_HASHTAGS: list[str] = [
    "#Israel",
    "#IsraelNews",
    "#Knesset",
    "#TelAviv",
    "#Jerusalem",
]


def _build_israeli_query(base_query: str, israeli_only: bool) -> str:
    """
    Augment a raw user query with Israeli context when israeli_only=True.
    Also appends lang:en to keep results in English.
    """
    if not israeli_only:
        return f"({base_query}) lang:en"
    account_filter = " OR ".join(f"from:{a}" for a in ISRAELI_TWITTER_ACCOUNTS[:5])
    hashtag_filter = " OR ".join(ISRAELI_HASHTAGS[:3])
    return f"({base_query}) ({account_filter} OR {hashtag_filter}) lang:en"


def _tweet_to_article(tweet) -> NewsArticle:
    """Convert a twscrape Tweet object into a NewsArticle."""
    username = tweet.user.username if tweet.user else "unknown"
    pub_date = (
        tweet.date.isoformat() + "Z"
        if isinstance(tweet.date, datetime)
        else str(tweet.date)
    )
    return NewsArticle(
        title=f"Tweet by @{username}",
        link=f"https://twitter.com/{username}/status/{tweet.id}",
        description=tweet.rawContent or "",
        pub_date=pub_date,
        source="Twitter / X",
        source_url=f"https://twitter.com/{username}",
        guid=str(tweet.id),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/social/twitter/search", tags=["Social Media"])
async def search_twitter(
    query: str = Query(..., description="Search query for Twitter / X"),
    limit: int = Query(10, ge=1, le=100),
    israeli_only: bool = Query(
        True,
        description="When true, restrict results to known Israeli accounts / hashtags",
    ),
):
    """
    Search Twitter / X for recent tweets matching `query`.

    - Uses **twscrape** (the maintained snscrape replacement).
    - Requires at least one Twitter/X account to be added to the pool first
      (see module docstring for setup instructions).
    - When `israeli_only=True` (default), results are filtered to tweets from
      verified Israeli news accounts or with Israeli hashtags.
    """
    if not _TWSCRAPE_AVAILABLE:
        _unavailable()

    api = _get_tw_api()
    full_query = _build_israeli_query(query, israeli_only)

    tweets: list[NewsArticle] = []
    try:
        async for tweet in api.search(full_query, limit=limit):
            tweets.append(_tweet_to_article(tweet))
            if len(tweets) >= limit:
                break
    except Exception as e:
        logger.error("twscrape search failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=(
                f"Twitter search failed: {e}. "
                "Make sure accounts are logged in: "
                "`python -m twscrape login_all`"
            ),
        )

    return {
        "query": query,
        "full_query": full_query,
        "israeli_only": israeli_only,
        "count": len(tweets),
        "tweets": tweets,
    }


@router.get("/social/twitter/user/{username}", tags=["Social Media"])
async def get_user_tweets(
    username: str,
    limit: int = Query(10, ge=1, le=100),
):
    """
    Fetch the most recent tweets from a specific Twitter / X user.

    Useful for pulling feeds from official Israeli accounts such as
    @KnessetIsrael, @IDF, @IsraelMFA, @TimesofIsrael, etc.
    """
    if not _TWSCRAPE_AVAILABLE:
        _unavailable()

    api = _get_tw_api()
    tweets: list[NewsArticle] = []

    try:
        user = await api.user_by_login(username)
        if user is None:
            raise HTTPException(status_code=404, detail=f"Twitter user @{username} not found")

        async for tweet in api.user_tweets(user.id, limit=limit):
            tweets.append(_tweet_to_article(tweet))
            if len(tweets) >= limit:
                break
    except HTTPException:
        raise
    except Exception as e:
        logger.error("twscrape user_tweets failed for @%s: %s", username, e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch tweets for @{username}: {e}")

    return {
        "username": username,
        "profile_url": f"https://twitter.com/{username}",
        "count": len(tweets),
        "tweets": tweets,
    }


@router.get("/social/twitter/israeli-accounts", tags=["Social Media"])
async def get_israeli_account_tweets(
    limit: int = Query(5, ge=1, le=20),
):
    """
    Fetch recent tweets from all whitelisted Israeli Twitter accounts concurrently.
    Returns results grouped by account.
    """
    if not _TWSCRAPE_AVAILABLE:
        _unavailable()

    api = _get_tw_api()

    async def _fetch_one(username: str) -> tuple[str, list | dict]:
        try:
            user = await api.user_by_login(username)
            if user is None:
                return username, {"error": "User not found"}
            items: list[NewsArticle] = []
            async for tweet in api.user_tweets(user.id, limit=limit):
                items.append(_tweet_to_article(tweet))
                if len(items) >= limit:
                    break
            return username, items
        except Exception as e:
            return username, {"error": str(e)}

    results = await asyncio.gather(*[_fetch_one(acc) for acc in ISRAELI_TWITTER_ACCOUNTS])
    return {
        "accounts": ISRAELI_TWITTER_ACCOUNTS,
        "data": {username: data for username, data in results},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Account management helpers (admin use — not exposed publicly by default)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/social/twitter/accounts/status", tags=["Social Media – Admin"])
async def accounts_status():
    """
    Return the login status of all Twitter accounts in the pool.
    Useful for diagnosing rate-limit or auth issues.
    """
    if not _TWSCRAPE_AVAILABLE:
        _unavailable()

    api = _get_tw_api()
    try:
        accounts = await api.pool.get_all()
        return {
            "total": len(accounts),
            "accounts": [
                {
                    "username": a.username,
                    "logged_in": a.active,
                    "last_used": str(a.last_used) if hasattr(a, "last_used") else None,
                }
                for a in accounts
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve account pool: {e}")


@router.post("/social/twitter/accounts/add", tags=["Social Media – Admin"])
async def add_account(
    username: str = Query(...),
    password: str = Query(...),
    email: str = Query(...),
    email_password: str = Query(...),
):
    """
    Add a Twitter / X account to the scraping pool and attempt login.

    All four fields are required. Credentials are stored locally in the
    twscrape SQLite database (`TWSCRAPE_DB` env var or `twscrape_accounts.db`).

    ⚠️  Call this endpoint over HTTPS only — credentials travel in query params.
    For production, prefer running `python -m twscrape add_accounts accounts.txt`
    from the server CLI instead of exposing this endpoint.
    """
    if not _TWSCRAPE_AVAILABLE:
        _unavailable()

    api = _get_tw_api()
    try:
        await api.pool.add_account(username, password, email, email_password)
        await api.pool.login_all()
        return {"status": "ok", "message": f"Account @{username} added and login attempted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add account: {e}")