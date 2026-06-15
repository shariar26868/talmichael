# app/core/database.py
"""
MongoDB async client via Motor.
Single client instance shared across the app.
Collections are accessed as: db.users, db.articles, db.mps, etc.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import OperationFailure

from app.core.config import settings

logger = logging.getLogger(__name__)

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

    async def _safe_create_indexes(collection, indexes):
        try:
            await collection.create_indexes(indexes)
        except OperationFailure as e:
            # Code 85 is IndexOptionsConflict (e.g. index already exists with different name/options)
            if e.code == 85:
                logger.warning(f"Index conflict in {collection.name}, skipping: {e}")
            else:
                raise

    # users
    await _safe_create_indexes(db.users, [
        IndexModel([("email", ASCENDING)], unique=True),
        IndexModel([("username", ASCENDING)], unique=True),
    ])

    # cached_articles
    await _safe_create_indexes(db.cached_articles, [
        IndexModel([("guid", ASCENDING)], unique=True),
        IndexModel([("category", ASCENDING)]),
        IndexModel([("fetched_at", DESCENDING)]),
    ])

    # knesset_bills
    await _safe_create_indexes(db.knesset_bills, [
        IndexModel([("bill_id", ASCENDING)], unique=True),
    ])

    # bill vote records (Knesset official votes)
    await _safe_create_indexes(db.bill_vote_records, [
        IndexModel([("bill_id", ASCENDING)]),
        IndexModel([("mp_object_id", ASCENDING)]),
        IndexModel([("knesset_person_id", ASCENDING)]),
    ])

    # mps
    await _safe_create_indexes(db.mps, [
        IndexModel([("knesset_id", ASCENDING)], unique=True, sparse=True),
        IndexModel([("name", ASCENDING)]),
    ])

    # parties
    await _safe_create_indexes(db.parties, [
        IndexModel([("name", ASCENDING)], unique=True),
    ])

    # mp_quotes, mp_actions, contradictions
    await _safe_create_indexes(db.mp_quotes, [IndexModel([("mp_id", ASCENDING)])])
    await _safe_create_indexes(db.mp_actions, [IndexModel([("mp_id", ASCENDING)])])
    await _safe_create_indexes(db.contradictions, [IndexModel([("mp_id", ASCENDING)])])

    # community_articles
    await _safe_create_indexes(db.community_articles, [
        IndexModel([("status", ASCENDING)]),
        IndexModel([("author_id", ASCENDING)]),
    ])

    # source_credibility
    await _safe_create_indexes(db.source_credibility, [
        IndexModel([("source_name", ASCENDING)], unique=True),
    ])

    # bias_votes
    await _safe_create_indexes(db.bias_votes, [
        IndexModel([("article_id", ASCENDING)]),
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("helpful_count", DESCENDING)]),
    ])

    # credibility_votes
    await _safe_create_indexes(db.credibility_votes, [
        IndexModel([("source_name", ASCENDING)]),
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("helpful_count", DESCENDING)]),
    ])

    # article_flags
    await _safe_create_indexes(db.article_flags, [
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

