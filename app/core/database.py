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
        IndexModel([("first_seen", DESCENDING)], name="cached_articles_first_seen_key"),
        IndexModel([("source_type", ASCENDING)], name="cached_articles_source_type_key"),
        # ── Compound indexes for DB-first fast path ───────────────────────
        # Used by fetch_from_db(): filters by category + sorts by pub_date
        IndexModel(
            [("category", ASCENDING), ("pub_date", DESCENDING)],
            name="cached_articles_cat_pubdate_key",
        ),
        # Used by _db_has_fresh_articles(): filters by category + fetched_at cutoff
        IndexModel(
            [("category", ASCENDING), ("fetched_at", DESCENDING)],
            name="cached_articles_cat_fetchedat_key",
        ),
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

    # Seed mock bills for the dashboard layout
    await _seed_mock_bills(db)


async def _seed_mock_bills(db) -> None:
    """Seed the 4 mockup bills if they don't already exist or need updating."""
    from datetime import datetime
    mock_bills = [
        {
            "bill_id": "security-2026",
            "title": "National Security Enhancement Bill",
            "name": "National Security Enhancement Bill",
            "proposed_by": "Defense Committee",
            "committee": "Defense Committee",
            "date": "March 1, 2026",
            "publication_date": "2026-03-01",
            "status": "In Voting Stage",
            "explanation": "This bill aims to enhance national security measures through improved coordination between security agencies and updated technology infrastructure.",
            "key_provisions": [
                "Enhanced inter-agency data sharing protocols",
                "Investment in cybersecurity infrastructure (₪1.2B)",
                "Creation of emergency response task force",
                "Privacy oversight committee establishment"
            ],
            "category_tags": ["Security", "Technology"],
            "updated_at": datetime.utcnow()
        },
        {
            "bill_id": "education-2026",
            "title": "Education System Reform Act",
            "name": "Education System Reform Act",
            "proposed_by": "Education Ministry",
            "committee": "Education Ministry",
            "date": "February 15, 2026",
            "publication_date": "2026-02-15",
            "status": "Committee Review",
            "explanation": "A comprehensive reform act focusing on modernizing school curricula, increasing teacher salaries, and integrating advanced technology into classrooms.",
            "key_provisions": [
                "Curriculum modernization focusing on STEM",
                "20% increase in teacher base salaries",
                "Digital classroom transformation initiatives",
                "Standardized testing methodology overhaul"
            ],
            "category_tags": ["Education", "Budget"],
            "updated_at": datetime.utcnow()
        },
        {
            "bill_id": "tax-2026",
            "title": "Tax Reform Legislation",
            "name": "Tax Reform Legislation",
            "proposed_by": "Finance Committee",
            "committee": "Finance Committee",
            "date": "January 10, 2026",
            "publication_date": "2026-01-10",
            "status": "Approved",
            "explanation": "Legislation aimed at boosting the economy by lowering corporate tax rates for tech startups while introducing tax relief brackets for middle-income households.",
            "key_provisions": [
                "Corporate tax reduction for certified tech startups",
                "New income tax brackets providing middle-class relief",
                "Streamlined online tax filing system integration",
                "Closure of major corporate tax loopholes"
            ],
            "category_tags": ["Economy", "Finance"],
            "updated_at": datetime.utcnow()
        },
        {
            "bill_id": "tech-2025",
            "title": "Technology Regulation Bill",
            "name": "Technology Regulation Bill",
            "proposed_by": "Innovation Committee",
            "committee": "Innovation Committee",
            "date": "December 5, 2025",
            "publication_date": "2025-12-05",
            "status": "Rejected",
            "explanation": "A proposed regulation bill to govern artificial intelligence deployment, data privacy compliance, and impose penalties for tech firms violating user privacy.",
            "key_provisions": [
                "Strict licensing for high-risk AI deployments",
                "Mandatory user data portability options",
                "Heavy penalties for unauthorized data brokers",
                "Establishment of an independent AI Ethics board"
            ],
            "category_tags": ["Technology", "Regulation"],
            "updated_at": datetime.utcnow()
        },
        # ── Passed mockup bills from the last 30 days (June 2026 / late May 2026) ──
        {
            "bill_id": "energy-2026",
            "title": "Renewable Energy Integration Act",
            "name": "Renewable Energy Integration Act",
            "proposed_by": "Infrastructure and Energy Committee",
            "committee": "Infrastructure and Energy Committee",
            "date": "June 10, 2026",
            "publication_date": "2026-06-10",
            "status": "Approved",
            "explanation": "This bill mandates the integration of solar and wind energy sources into the national power grid, establishing subsidies for residential solar installations.",
            "key_provisions": [
                "Grid capacity expansion for renewable inputs",
                "Tax credits for private solar installations",
                "Phasing out coal-fired power stations by 2030"
            ],
            "category_tags": ["Energy", "Environment", "Infrastructure"],
            "updated_at": datetime.utcnow()
        },
        {
            "bill_id": "health-2026",
            "title": "Healthcare Digitalization Law",
            "name": "Healthcare Digitalization Law",
            "proposed_by": "Health and Welfare Committee",
            "committee": "Health and Welfare Committee",
            "date": "June 3, 2026",
            "publication_date": "2026-06-03",
            "status": "Approved",
            "explanation": "A law to fully digitize patient records across all public hospitals, enabling secure cross-hospital data sharing and telemedicine services.",
            "key_provisions": [
                "Centralized secure patient record registry",
                "Subsidies for regional hospital tech upgrades",
                "Strict patient data privacy standards"
            ],
            "category_tags": ["Health", "Technology", "Privacy"],
            "updated_at": datetime.utcnow()
        },
        {
            "bill_id": "startup-2026",
            "title": "Startup Capital Incentive Bill",
            "name": "Startup Capital Incentive Bill",
            "proposed_by": "Finance Committee",
            "committee": "Finance Committee",
            "date": "May 28, 2026",
            "publication_date": "2026-05-28",
            "status": "Approved",
            "explanation": "A bill providing tax exemptions for early-stage investments in tech startups, aimed at revitalizing capital inflows to the high-tech sector.",
            "key_provisions": [
                "Zero capital gains tax on investments held for 3+ years",
                "Simplified registration for foreign venture funds",
                "Matching grants for deep-tech research"
            ],
            "category_tags": ["Finance", "Economy", "Technology"],
            "updated_at": datetime.utcnow()
        }
    ]

    for bill in mock_bills:
        try:
            await db.knesset_bills.update_one(
                {"bill_id": bill["bill_id"]},
                {"$set": bill},
                upsert=True
            )
        except Exception as e:
            logger.warning(f"Failed to seed mock bill {bill['bill_id']}: {e}")


async def close_db() -> None:

    global _client
    if _client:
        _client.close()
        _client = None

