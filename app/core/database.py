# app/core/database.py
"""
MongoDB async client via Motor.
Single client instance shared across the app.
Collections are accessed as: db.users, db.articles, db.mps, etc.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import DuplicateKeyError, OperationFailure

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
            existing_indexes = []
            try:
                async for idx in collection.list_indexes():
                    existing_indexes.append(idx)
            except Exception:
                pass

            indexes_to_create = []
            for idx_model in indexes:
                key_dict = dict(idx_model.document.get("key", {}))
                conflict = False
                for ext_idx in existing_indexes:
                    if dict(ext_idx.get("key", {})) == key_dict:
                        conflict = True
                        break
                if not conflict:
                    indexes_to_create.append(idx_model)

            if indexes_to_create:
                await collection.create_indexes(indexes_to_create)
        except OperationFailure as e:
            # Code 85 is IndexOptionsConflict; code 86 is IndexKeySpecsConflict; code 11000 is DuplicateKey.
            if e.code in (85, 86, 11000):
                logger.warning(f"Index conflict/build failed in {collection.name}, skipping: {e}")
            else:
                raise
        except DuplicateKeyError as e:
            logger.warning(f"Duplicate key index build failed in {collection.name}, skipping: {e}")

    # users
    await _safe_create_indexes(db.users, [
        IndexModel([("email", ASCENDING)], unique=True, sparse=True, name="users_email_key"),
        IndexModel([("username", ASCENDING)], unique=True, sparse=True, name="users_username_key"),
    ])

    # cached_articles
    await _safe_create_indexes(db.cached_articles, [
        IndexModel([("guid", ASCENDING)], unique=True, name="cached_articles_guid_key"),
        IndexModel([("category", ASCENDING)], name="cached_articles_category_key"),
        IndexModel([("fetched_at", DESCENDING)], name="cached_articles_fetched_at_key"),
    ])

    # knesset_bills
    await _safe_create_indexes(db.knesset_bills, [
        IndexModel([("bill_id", ASCENDING)], unique=True, name="knesset_bills_bill_id_key"),
    ])

    # bill vote records (Knesset official votes)
    await _safe_create_indexes(db.bill_vote_records, [
        IndexModel([("bill_id", ASCENDING)]),
        IndexModel([("mp_object_id", ASCENDING)]),
        IndexModel([("knesset_person_id", ASCENDING)]),
    ])

    # mps
    await _safe_create_indexes(db.mps, [
        IndexModel([("knesset_id", ASCENDING)], unique=True, sparse=True, name="mps_knesset_id_key"),
        IndexModel([("name", ASCENDING)], name="mps_name_key"),
    ])

    # parties
    await _safe_create_indexes(db.parties, [
        IndexModel([("name", ASCENDING)], unique=True, name="parties_name_key"),
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
        IndexModel([("source_name", ASCENDING)], unique=True, name="source_credibility_source_name_key"),
    ])

    # bias_votes (with deduplication index)
    await _safe_create_indexes(db.bias_votes, [
        IndexModel([("article_id", ASCENDING), ("user_id", ASCENDING)], unique=True, name="bias_votes_article_user_key"),
        IndexModel([("article_id", ASCENDING)], name="bias_votes_article_id_key"),
        IndexModel([("user_id", ASCENDING)], name="bias_votes_user_id_key"),
        IndexModel([("created_at", DESCENDING)], name="bias_votes_created_at_key"),
        IndexModel([("helpful_count", DESCENDING)], name="bias_votes_helpful_count_key"),
    ])

    # credibility_votes (with deduplication index)
    await _safe_create_indexes(db.credibility_votes, [
        IndexModel([("source_name", ASCENDING), ("user_id", ASCENDING)], unique=True, name="credibility_votes_source_user_key"),
        IndexModel([("source_name", ASCENDING)], name="credibility_votes_source_name_key"),
        IndexModel([("user_id", ASCENDING)], name="credibility_votes_user_id_key"),
        IndexModel([("created_at", DESCENDING)], name="credibility_votes_created_at_key"),
        IndexModel([("helpful_count", DESCENDING)], name="credibility_votes_helpful_count_key"),
    ])

    # article_flags
    await _safe_create_indexes(db.article_flags, [
        IndexModel([("article_id", ASCENDING)]),
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("reason", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])

    # ── New: Verification & Fact-Check collections ────────────────────────

    # cross_source_matches — event clusters with agreement scores
    await _safe_create_indexes(db.cross_source_matches, [
        IndexModel([("event_cluster_id", ASCENDING)], unique=True),
        IndexModel([("matching_articles.guid", ASCENDING)]),
        IndexModel([("updated_at", DESCENDING)]),
    ])

    # verified_claims — per-claim fact-check results
    await _safe_create_indexes(db.verified_claims, [
        IndexModel([("article_id", ASCENDING)]),
        IndexModel([("verification_status", ASCENDING)]),
    ])

    # framing_analyses — article framing analysis results
    await _safe_create_indexes(db.framing_analyses, [
        IndexModel([("article_id", ASCENDING)], unique=True),
    ])

    # analysis_audit_log — transparency trail
    await _safe_create_indexes(db.analysis_audit_log, [
        IndexModel([("article_id", ASCENDING)]),
        IndexModel([("timestamp", DESCENDING)]),
    ])

    # source_bias_history — rolling bias tracking per source
    await _safe_create_indexes(db.source_bias_history, [
        IndexModel([("source_name", ASCENDING), ("recorded_at", DESCENDING)]),
    ])


async def close_db() -> None:
    global _client
    if _client:
        _client.close()
        _client = None

