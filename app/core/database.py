# app/core/database.py
"""
MongoDB async client via Motor.
Single client instance shared across the app.
Collections are accessed as: db.users, db.articles, db.mps, etc.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel

from app.core.config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_url)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[settings.mongodb_db]


async def init_db() -> None:
    """Create indexes on startup."""
    db = get_db()

    # users
    await db.users.create_indexes([
        IndexModel([("email", ASCENDING)], unique=True),
        IndexModel([("username", ASCENDING)], unique=True),
    ])

    # cached_articles
    await db.cached_articles.create_indexes([
        IndexModel([("guid", ASCENDING)], unique=True),
        IndexModel([("category", ASCENDING)]),
        IndexModel([("fetched_at", DESCENDING)]),
    ])

    # knesset_bills
    await db.knesset_bills.create_indexes([
        IndexModel([("bill_id", ASCENDING)], unique=True),
    ])

    # bill vote records (Knesset official votes)
    await db.bill_vote_records.create_indexes([
        IndexModel([("bill_id", ASCENDING)]),
        IndexModel([("mp_object_id", ASCENDING)]),
        IndexModel([("knesset_person_id", ASCENDING)]),
    ])

    # mps
    await db.mps.create_indexes([
        IndexModel([("knesset_id", ASCENDING)], unique=True, sparse=True),
        IndexModel([("name", ASCENDING)]),
    ])

    # parties
    await db.parties.create_indexes([
        IndexModel([("name", ASCENDING)], unique=True),
    ])

    # mp_quotes, mp_actions, contradictions
    await db.mp_quotes.create_indexes([IndexModel([("mp_id", ASCENDING)])])
    await db.mp_actions.create_indexes([IndexModel([("mp_id", ASCENDING)])])
    await db.contradictions.create_indexes([IndexModel([("mp_id", ASCENDING)])])

    # community_articles
    await db.community_articles.create_indexes([
        IndexModel([("status", ASCENDING)]),
        IndexModel([("author_id", ASCENDING)]),
    ])

    # source_credibility
    await db.source_credibility.create_indexes([
        IndexModel([("source_name", ASCENDING)], unique=True),
    ])

    # bias_votes
    await db.bias_votes.create_indexes([
        IndexModel([("article_id", ASCENDING)]),
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("helpful_count", DESCENDING)]),
    ])

    # credibility_votes
    await db.credibility_votes.create_indexes([
        IndexModel([("source_name", ASCENDING)]),
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("helpful_count", DESCENDING)]),
    ])

    # article_flags
    await db.article_flags.create_indexes([
        IndexModel([("article_id", ASCENDING)]),
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("reason", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])


async def close_db() -> None:
    global _client
    if _client:
        _client.close()
        _client = None
