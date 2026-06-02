# app/routes/ai.py
"""
Phase 2 — AI Analysis endpoints.
Free users  → rule-based analysis (instant, no API cost)
Paid users  → GPT-4o powered deep analysis

Plus: User voting for bias/credibility validation (crowdsourced trust)
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.models.schemas import (
    ArticleAnalysis, BiasVoteCreate, CredibilityVoteCreate, FlagArticleCreate,
    BiasVoteResponse, CredibilityVoteResponse
)
from app.services.ai_service import analyze_article, analyze_batch, get_source_bias
from app.services.voting_service import (
    submit_bias_vote, submit_credibility_vote, flag_article,
    compute_bias_consensus, compute_credibility_consensus,
    upvote_vote, get_article_votes, get_source_votes,
    get_user_vote_history, get_top_voters
)

router = APIRouter(prefix="/ai", tags=["AI Analysis"])


# ── Request schemas ───────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    guid: str
    title: str
    description: str
    source: Optional[str] = None
    source_url: Optional[str] = None


class BatchAnalyzeRequest(BaseModel):
    articles: list[AnalyzeRequest]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/analyze", response_model=ArticleAnalysis)
async def analyze(
    body: AnalyzeRequest,
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
):
    """
    Analyze a single article.
    - free: rule-based
    - pro: GPT-4o-mini with fallback
    - platinum: GPT-4o-mini + Perplexity + Gemini
    """
    return await analyze_article(
        guid=body.guid,
        title=body.title,
        description=body.description,
        source=body.source,
        source_url=body.source_url,
        user_tier=user_tier,
    )


@router.post("/analyze/batch", response_model=list[ArticleAnalysis])
async def analyze_batch_endpoint(
    body: BatchAnalyzeRequest,
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
):
    """
    Analyze up to 20 articles at once.
    - free: rule-based
    - pro: GPT-4o-mini with fallback
    - platinum: GPT-4o-mini + Perplexity + Gemini
    """
    if len(body.articles) > 20:
        raise HTTPException(status_code=400, detail="Max 20 articles per batch")

    return await analyze_batch(
        [a.model_dump() for a in body.articles],
        user_tier=user_tier,
    )


@router.get("/source-bias")
async def source_bias(
    source: str = Query(..., description="Source outlet name"),
    source_url: Optional[str] = Query(None),
):
    return await get_source_bias(source, source_url)


@router.get("/source-bias/all")
async def all_source_bias():
    from app.services.ai_service import SOURCE_BIAS_SEED, SOURCE_CREDIBILITY_SEED
    from app.utils.filters import ISRAELI_SOURCES

    result = []
    seen = set()
    for name in ISRAELI_SOURCES:
        if name in seen:
            continue
        seen.add(name)
        bias = SOURCE_BIAS_SEED.get(name, "unknown")
        credibility = SOURCE_CREDIBILITY_SEED.get(name, 0.5)
        result.append({
            "source_name": name,
            "bias": bias,
            "credibility_score": credibility,
            "bias_label": {"left": "⬅️ Left", "center": "⚖️ Center", "right": "➡️ Right"}.get(bias, "❓ Unknown"),
        })

    return {"total": len(result), "sources": sorted(result, key=lambda x: x["source_name"])}


# ── Voting & Credibility Validation ───────────────────────────────────────────

@router.post("/articles/{article_id}/vote/bias", response_model=BiasVoteResponse)
async def vote_bias(
    article_id: str,
    vote: BiasVoteCreate,
    user_id: str = Query(..., description="User ID (from JWT)"),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
):
    """
    Submit bias assessment for an article.
    
    - article_id: unique article identifier
    - bias_assessment: "left" | "center" | "right" | "unclear"
    - confidence: 0.0-1.0 (how confident you are)
    
    Returns updated consensus bias if enough votes are collected.
    """
    try:
        vote_doc = await submit_bias_vote(
            article_id=article_id,
            user_id=user_id,
            user_tier=user_tier,
            bias_assessment=vote.bias_assessment,
            confidence=vote.confidence,
            user_notes=vote.user_notes,
        )
        
        # Compute new consensus (would need AI bias from cached article)
        # For now, just return the vote confirmation
        return BiasVoteResponse(
            status="recorded",
            vote_id=str(vote_doc.get("_id")),
            article_id=article_id,
            recorded_at=vote_doc["created_at"].isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sources/{source_name}/vote/credibility", response_model=CredibilityVoteResponse)
async def vote_credibility(
    source_name: str,
    vote: CredibilityVoteCreate,
    user_id: str = Query(..., description="User ID (from JWT)"),
    user_tier: str = Query("free", description="User tier: free|pro|platinum"),
):
    """
    Submit credibility assessment for a news source.
    
    - source_name: "Haaretz", "Times of Israel", etc.
    - credibility_level: "very_low" | "low" | "medium" | "high" | "very_high"
    
    Returns updated consensus credibility if enough votes are collected.
    """
    try:
        vote_doc = await submit_credibility_vote(
            source_name=source_name,
            user_id=user_id,
            user_tier=user_tier,
            credibility_level=vote.credibility_level,
            evidence=vote.evidence,
        )
        
        return CredibilityVoteResponse(
            status="recorded",
            vote_id=str(vote_doc.get("_id")),
            source_name=source_name,
            recorded_at=vote_doc["created_at"].isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/articles/{article_id}/flag")
async def flag_article_endpoint(
    article_id: str,
    body: FlagArticleCreate,
    user_id: str = Query(..., description="User ID (from JWT)"),
):
    """
    Flag an article for misinformation, propaganda, bias, or unreliable source.
    
    - reason: "misinformation" | "propaganda" | "biased" | "unreliable_source"
    - details: explain why you're flagging this
    
    Flags are reviewed by moderation team.
    """
    try:
        flag_doc = await flag_article(
            article_id=article_id,
            user_id=user_id,
            reason=body.reason,
            details=body.details,
        )
        
        return {
            "status": "flagged",
            "flag_id": str(flag_doc.get("_id")),
            "article_id": article_id,
            "reason": body.reason,
            "message": "Thank you for helping us maintain quality. Our team will review this."
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/articles/{article_id}/votes")
async def article_votes(article_id: str):
    """
    Get voting statistics for an article.
    Shows bias vote breakdown, flags, community validation.
    """
    votes = await get_article_votes(article_id)
    return {
        "article_id": article_id,
        "bias_votes_count": len(votes.get("bias_votes", [])),
        "flags_count": votes.get("flag_count", 0),
        "votes": votes
    }


@router.get("/sources/{source_name}/votes")
async def source_votes(source_name: str):
    """
    Get voting statistics for a news source.
    Shows credibility vote breakdown and community assessment.
    """
    votes = await get_source_votes(source_name)
    return {
        "source_name": source_name,
        "votes": votes
    }


@router.post("/votes/{vote_id}/helpful")
async def mark_vote_helpful(
    vote_id: str,
    vote_type: str = Query("bias", description="bias | credibility"),
):
    """
    Mark a vote as helpful (upvote).
    Helps surface most valuable votes for community consensus.
    """
    try:
        success = await upvote_vote(vote_id, vote_type)
        if not success:
            raise HTTPException(status_code=404, detail="Vote not found")
        return {"status": "upvoted", "vote_id": vote_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/vote-history")
async def user_vote_history(user_id: str, limit: int = Query(50, ge=1, le=100)):
    """
    Get user's voting history and reputation.
    Shows votes submitted, helpfulness, and participation stats.
    """
    history = await get_user_vote_history(user_id, limit)
    return {
        "user_id": user_id,
        "reputation": {
            "bias_votes": history["bias_votes"],
            "credibility_votes": history["credibility_votes"],
            "flags_submitted": history["flags"],
        },
        "recent_activity": {
            "bias_votes": history["recent_bias_votes"],
            "credibility_votes": history["recent_credibility_votes"],
            "flags": history["recent_flags"],
        }
    }


@router.get("/votes/leaderboard")
async def votes_leaderboard(limit: int = Query(10, ge=1, le=100)):
    """
    Get top community voters (reputation system).
    High-volume, high-quality voters help shape community consensus.
    """
    top_voters = await get_top_voters(limit)
    return {
        "leaderboard": top_voters,
        "description": "Top voters by helpful votes received"
    }

