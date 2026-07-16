"""
Voting mechanism for credibility & bias validation.

Crowdsources trust and bias assessments from users, combines with AI analysis
for final consensus judgment.

Features:
  - Full bias spectrum (far-left → far-right)
  - Vote deduplication (one vote per user per article, upsert)
  - Rate limiting (max 30 votes per hour per user)
  - Tier-weighted consensus (Free=1x, Pro=1.5x, Expert=3x)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from bson import ObjectId

from app.core.database import get_db
from app.models.schemas import (
    VoteStats, BiasConsensus, CredibilityConsensus, BIAS_SPECTRUM,
)

logger = logging.getLogger(__name__)

# Full bias spectrum — matches schemas.BIAS_SPECTRUM
BIAS_TYPES = set(BIAS_SPECTRUM)

# Credibility levels enum
CREDIBILITY_LEVELS = {"very_low", "low", "medium", "high", "very_high"}

# Credibility level to score mapping
CREDIBILITY_SCORE_MAP = {
    "very_low": 0.1,
    "low": 0.3,
    "medium": 0.5,
    "high": 0.8,
    "very_high": 0.95,
}

# Rate limiting
MAX_VOTES_PER_HOUR = 30
VOTE_COOLDOWN_SECONDS = 10


async def _check_rate_limit(user_id: str, collection_name: str) -> None:
    """Enforce rate limiting: max 30 votes/hour, 10s cooldown."""
    db = get_db()
    collection = db[collection_name]

    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_count = await collection.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": one_hour_ago},
    })
    if recent_count >= MAX_VOTES_PER_HOUR:
        raise ValueError(
            f"Rate limit exceeded: max {MAX_VOTES_PER_HOUR} votes per hour. "
            "Please try again later."
        )

    cooldown_threshold = datetime.utcnow() - timedelta(seconds=VOTE_COOLDOWN_SECONDS)
    last_vote = await collection.find_one(
        {"user_id": user_id, "created_at": {"$gte": cooldown_threshold}},
        sort=[("created_at", -1)],
    )
    if last_vote:
        raise ValueError(
            f"Please wait {VOTE_COOLDOWN_SECONDS} seconds between votes."
        )


async def submit_bias_vote(
    article_id: str,
    user_id: str,
    user_tier: str,
    bias_assessment: str,
    confidence: float,
    user_notes: Optional[str] = None,
) -> dict:
    """Submit user's bias assessment for an article.

    Upsert logic: one vote per user per article.  If the user has already
    voted on this article their previous vote is replaced.
    """
    db = get_db()

    if bias_assessment not in BIAS_TYPES:
        raise ValueError(
            f"Invalid bias assessment: {bias_assessment}. "
            f"Must be one of: {', '.join(sorted(BIAS_TYPES))}"
        )

    if not (0.0 <= confidence <= 1.0):
        raise ValueError("Confidence must be between 0.0 and 1.0")

    # Rate limiting
    await _check_rate_limit(user_id, "bias_votes")

    now = datetime.utcnow()
    vote_doc = {
        "article_id": article_id,
        "user_id": user_id,
        "user_tier": user_tier,
        "bias_assessment": bias_assessment,
        "confidence": confidence,
        "user_notes": user_notes,
        "created_at": now,
        "updated_at": now,
        "helpful_count": 0,
    }

    # Upsert: one vote per user per article
    result = await db.bias_votes.update_one(
        {"article_id": article_id, "user_id": user_id},
        {
            "$set": {
                "user_tier": user_tier,
                "bias_assessment": bias_assessment,
                "confidence": confidence,
                "user_notes": user_notes,
                "updated_at": now,
            },
            "$setOnInsert": {
                "article_id": article_id,
                "user_id": user_id,
                "created_at": now,
                "helpful_count": 0,
            },
        },
        upsert=True,
    )

    vote_doc["_id"] = str(result.upserted_id or "updated")
    action = "created" if result.upserted_id else "updated"
    logger.info(f"Bias vote {action}: {user_id} on {article_id}")
    return vote_doc


async def submit_credibility_vote(
    source_name: str,
    user_id: str,
    user_tier: str,
    credibility_level: str,
    evidence: Optional[str] = None,
) -> dict:
    """Submit user's credibility assessment for a source.

    Upsert logic: one vote per user per source.
    """
    db = get_db()

    if credibility_level not in CREDIBILITY_LEVELS:
        raise ValueError(f"Invalid credibility level: {credibility_level}")

    # Rate limiting
    await _check_rate_limit(user_id, "credibility_votes")

    now = datetime.utcnow()
    score = CREDIBILITY_SCORE_MAP[credibility_level]

    # Upsert: one vote per user per source
    result = await db.credibility_votes.update_one(
        {"source_name": source_name, "user_id": user_id},
        {
            "$set": {
                "user_tier": user_tier,
                "credibility_level": credibility_level,
                "credibility_score": score,
                "evidence": evidence,
                "updated_at": now,
            },
            "$setOnInsert": {
                "source_name": source_name,
                "user_id": user_id,
                "created_at": now,
                "helpful_count": 0,
            },
        },
        upsert=True,
    )

    vote_doc = {
        "source_name": source_name,
        "user_id": user_id,
        "user_tier": user_tier,
        "credibility_level": credibility_level,
        "credibility_score": score,
        "evidence": evidence,
        "created_at": now,
        "_id": str(result.upserted_id or "updated"),
    }

    action = "created" if result.upserted_id else "updated"
    logger.info(f"Credibility vote {action}: {user_id} on {source_name}")
    return vote_doc


async def flag_article(
    article_id: str,
    user_id: str,
    reason: str,
    details: str,
) -> dict:
    """Flag article for misinformation or bias issues."""
    db = get_db()
    
    valid_reasons = {"misinformation", "propaganda", "biased", "unreliable_source"}
    if reason not in valid_reasons:
        raise ValueError(f"Invalid flag reason: {reason}")
    
    flag = {
        "article_id": article_id,
        "user_id": user_id,
        "reason": reason,
        "details": details,
        "created_at": datetime.utcnow(),
        "status": "pending",  # pending | reviewed | addressed
    }
    
    result = await db.article_flags.insert_one(flag)
    flag["_id"] = str(result.inserted_id)
    
    logger.info(f"Article flagged: {article_id} by {user_id} ({reason})")
    return flag


async def compute_bias_consensus(article_id: str, ai_bias: str) -> BiasConsensus:
    """
    Combine AI bias detection + user votes for final bias assessment.
    
    Rules:
    - If <5 user votes: trust AI assessment
    - If 5+ votes: use weighted majority from users
    - Pro votes weighted 1.5-2x more than free tier
    """
    db = get_db()
    
    # Fetch all bias votes for this article
    votes_cursor = db.bias_votes.find({"article_id": article_id})
    votes = await votes_cursor.to_list(length=1000)
    
    if not votes or len(votes) < 5:
        # Not enough user votes - trust AI
        return BiasConsensus(
            bias=ai_bias,
            confidence=0.7,
            based_on="ai",
            vote_count=len(votes),
            stats=None if not votes else await _compute_vote_stats(votes, "bias")
        )
    
    # Compute weighted consensus from user votes
    weighted_votes = {}
    tier_weights = {"free": 1.0, "pro": 1.5, "expert": 3.0}

    for vote in votes:
        tier = vote.get("user_tier", "free")
        weight = tier_weights.get(tier, 1.0)
        confidence = vote.get("confidence", 0.5)
        assessment = vote.get("bias_assessment")
        
        if assessment not in weighted_votes:
            weighted_votes[assessment] = 0.0
        weighted_votes[assessment] += confidence * weight
    
    # Determine consensus
    if not weighted_votes:
        return BiasConsensus(
            bias=ai_bias,
            confidence=0.7,
            based_on="ai",
            vote_count=0
        )
    
    consensus_bias = max(weighted_votes.items(), key=lambda x: x[1])[0]
    total_weight = sum(weighted_votes.values())
    consensus_confidence = weighted_votes[consensus_bias] / total_weight
    
    stats = await _compute_vote_stats(votes, "bias")
    
    return BiasConsensus(
        bias=consensus_bias,
        confidence=min(consensus_confidence, 0.99),
        based_on="user_consensus",
        vote_count=len(votes),
        stats=stats
    )


async def compute_credibility_consensus(source_name: str, ai_credibility: float) -> CredibilityConsensus:
    """
    Combine AI credibility scoring + user votes for final credibility assessment.
    
    Rules:
    - If <5 user votes: trust AI score
    - If 5+ votes: average user scores (weighted by tier)
    """
    db = get_db()
    
    # Fetch all credibility votes for this source
    votes_cursor = db.credibility_votes.find({"source_name": source_name})
    votes = await votes_cursor.to_list(length=1000)
    
    if not votes or len(votes) < 5:
        # Not enough user votes - trust AI
        label = _credibility_score_to_label(ai_credibility)
        return CredibilityConsensus(
            credibility_score=ai_credibility,
            credibility_label=label,
            based_on="ai",
            vote_count=len(votes),
            stats=None if not votes else await _compute_vote_stats(votes, "credibility")
        )
    
    # Compute weighted average from user votes
    tier_weights = {"free": 1.0, "pro": 1.5, "expert": 3.0}
    total_weight = 0.0
    weighted_sum = 0.0
    
    for vote in votes:
        tier = vote.get("user_tier", "free")
        weight = tier_weights.get(tier, 1.0)
        score = vote.get("credibility_score", 0.5)
        
        weighted_sum += score * weight
        total_weight += weight
    
    consensus_score = weighted_sum / total_weight if total_weight > 0 else ai_credibility
    label = _credibility_score_to_label(consensus_score)
    
    stats = await _compute_vote_stats(votes, "credibility")
    
    return CredibilityConsensus(
        credibility_score=consensus_score,
        credibility_label=label,
        based_on="user_consensus",
        vote_count=len(votes),
        stats=stats
    )


async def _compute_vote_stats(votes: list[dict], vote_type: str) -> VoteStats:
    """Compute statistics from a list of votes."""
    if vote_type == "bias":
        # Bias vote breakdown
        breakdown = {}
        for vote in votes:
            bias = vote.get("bias_assessment")
            breakdown[bias] = breakdown.get(bias, 0) + 1
        
        total = len(votes)
        consensus = max(breakdown.items(), key=lambda x: x[1])[0]
        consensus_pct = (breakdown[consensus] / total) * 100
        
        return VoteStats(
            total_votes=total,
            consensus=consensus,
            consensus_percentage=consensus_pct,
            breakdown=breakdown,
            flagged=0  # Count flags separately if needed
        )
    
    elif vote_type == "credibility":
        # Credibility vote breakdown (convert to buckets)
        breakdown = {}
        for vote in votes:
            level = vote.get("credibility_level")
            breakdown[level] = breakdown.get(level, 0) + 1
        
        total = len(votes)
        # Find most common level
        consensus = max(breakdown.items(), key=lambda x: x[1])[0]
        consensus_pct = (breakdown[consensus] / total) * 100
        
        return VoteStats(
            total_votes=total,
            consensus=consensus,
            consensus_percentage=consensus_pct,
            breakdown=breakdown,
            flagged=0
        )
    
    return VoteStats(total_votes=0, consensus="", consensus_percentage=0.0, breakdown={}, flagged=0)


def _credibility_score_to_label(score: float) -> str:
    """Convert credibility score to label."""
    if score >= 0.85:
        return "verified"
    elif score >= 0.70:
        return "likely credible"
    elif score >= 0.50:
        return "needs review"
    else:
        return "unverified"


async def upvote_vote(vote_id: str, vote_type: str) -> bool:
    """User marks a vote as helpful."""
    db = get_db()
    
    if vote_type == "bias":
        result = await db.bias_votes.update_one(
            {"_id": ObjectId(vote_id)},
            {"$inc": {"helpful_count": 1}}
        )
    elif vote_type == "credibility":
        result = await db.credibility_votes.update_one(
            {"_id": ObjectId(vote_id)},
            {"$inc": {"helpful_count": 1}}
        )
    else:
        return False
    
    return result.modified_count > 0


async def get_article_votes(article_id: str) -> dict:
    """Get all votes submitted for an article."""
    db = get_db()
    
    bias_votes = await db.bias_votes.find(
        {"article_id": article_id},
        {"_id": 0, "user_id": 0}  # Hide user_id for privacy
    ).to_list(length=1000)
    
    flags = await db.article_flags.find(
        {"article_id": article_id},
        {"_id": 0, "user_id": 0}
    ).to_list(length=100)
    
    return {
        "bias_votes": bias_votes,
        "flag_count": len(flags),
        "flags_by_reason": _group_flags_by_reason(flags) if flags else {}
    }


async def get_source_votes(source_name: str) -> dict:
    """Get all votes submitted for a source."""
    db = get_db()
    
    credibility_votes = await db.credibility_votes.find(
        {"source_name": source_name},
        {"_id": 0, "user_id": 0}
    ).to_list(length=1000)
    
    return {
        "credibility_votes": credibility_votes,
        "total_votes": len(credibility_votes),
    }


def _group_flags_by_reason(flags: list[dict]) -> dict:
    """Group flags by reason."""
    grouped = {}
    for flag in flags:
        reason = flag.get("reason", "unknown")
        grouped[reason] = grouped.get(reason, 0) + 1
    return grouped


async def get_user_vote_history(user_id: str, limit: int = 50) -> dict:
    """Get voting history for a user."""
    db = get_db()
    
    bias_votes = await db.bias_votes.find(
        {"user_id": user_id}
    ).sort("created_at", -1).to_list(length=limit)
    
    credibility_votes = await db.credibility_votes.find(
        {"user_id": user_id}
    ).sort("created_at", -1).to_list(length=limit)
    
    flags = await db.article_flags.find(
        {"user_id": user_id}
    ).sort("created_at", -1).to_list(length=limit)
    
    return {
        "bias_votes": len(bias_votes),
        "credibility_votes": len(credibility_votes),
        "flags": len(flags),
        "recent_bias_votes": bias_votes[:5],
        "recent_credibility_votes": credibility_votes[:5],
        "recent_flags": flags[:5],
    }


async def get_top_voters(limit: int = 10) -> list[dict]:
    """Get users with most helpful votes (reputation system)."""
    db = get_db()
    
    # Aggregate votes with highest helpful_count
    pipeline = [
        {
            "$group": {
                "_id": "$user_id",
                "total_votes": {"$sum": 1},
                "helpful_votes": {"$sum": "$helpful_count"}
            }
        },
        {"$sort": {"helpful_votes": -1}},
        {"$limit": limit}
    ]
    
    top_voters = await db.bias_votes.aggregate(pipeline).to_list(length=limit)
    return top_voters
