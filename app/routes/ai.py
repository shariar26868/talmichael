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

from app.core.database import get_db
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


# ── Verification & Fact-Check Endpoints ───────────────────────────────────────

@router.post("/articles/{article_id}/verify")
async def verify_article_endpoint(
    article_id: str,
    title: str = Query(..., description="Article title"),
    description: str = Query("", description="Article description/body text"),
):
    """
    Run full verification pipeline on an article:
      - Extract and verify individual claims
      - Analyze framing (headline consistency, attribution, perspective)
      - Compute composite verification confidence score

    Returns detailed breakdown of all verification signals.
    """
    from app.services.fact_check_service import (
        verify_article_claims,
        analyze_framing,
        compute_verification_confidence,
    )
    from app.services.cross_source_verification_service import get_cross_source_match

    # 1. Verify claims
    verified_claims = await verify_article_claims(title, description, article_id)

    # 2. Analyze framing
    framing = analyze_framing(title, description)

    # 3. Get cross-source match if available
    cross_match = await get_cross_source_match(article_id)
    cross_data = cross_match.model_dump() if cross_match else None

    # 4. Get source credibility
    source_cred = 0.5  # default
    try:
        db = get_db()
        cached = await db.cached_articles.find_one({"guid": article_id})
        if cached and cached.get("source"):
            from app.services.ai_service import SOURCE_CREDIBILITY_SEED
            source_cred = SOURCE_CREDIBILITY_SEED.get(
                cached["source"], 0.5
            )
    except Exception:
        pass

    # 5. Compute composite score
    confidence = await compute_verification_confidence(
        article_guid=article_id,
        source_credibility=source_cred,
        claims=verified_claims,
        framing=framing,
        cross_source=cross_data,
    )

    return {
        "article_id": article_id,
        "verified_claims": [c.model_dump() for c in verified_claims],
        "framing_analysis": framing.model_dump(),
        "cross_source_match": cross_data,
        "verification_confidence": confidence.model_dump(),
    }


@router.post("/verify/cross-source")
async def cross_source_verify(
    body: BatchAnalyzeRequest,
):
    """
    Run cross-source verification on a batch of articles.
    Groups articles about the same event and compares how different
    sources frame the story. Returns event clusters with agreement scores.
    """
    from app.services.cross_source_verification_service import (
        cross_verify_recent_articles,
    )

    articles = [a.model_dump() for a in body.articles]
    matches = await cross_verify_recent_articles(articles)

    return {
        "total_articles": len(articles),
        "clusters_found": len(matches),
        "clusters": [m.model_dump() for m in matches],
    }


@router.get("/articles/{article_id}/cross-source")
async def get_article_cross_source(article_id: str):
    """
    Get cross-source verification data for a specific article.
    Shows which other sources covered the same event and how
    consistent the reporting is.
    """
    from app.services.cross_source_verification_service import (
        get_cross_source_match,
    )

    match = await get_cross_source_match(article_id)
    if not match:
        return {
            "article_id": article_id,
            "status": "no_cross_source_data",
            "message": "No cross-source verification available for this article yet.",
        }

    return {
        "article_id": article_id,
        "status": "verified",
        "cross_source": match.model_dump(),
    }


@router.get("/factcheck/search")
async def factcheck_search(
    query: str = Query(..., description="Claim or topic to fact-check"),
):
    """
    Search Google Fact Check API for published fact-checks on a claim.
    Returns matching fact-checks from organizations like Snopes,
    PolitiFact, AFP, etc.

    Requires GOOGLE_FACTCHECK_API_KEY in .env.
    """
    from app.services.fact_check_service import check_google_factcheck

    results = await check_google_factcheck(query)
    return {
        "query": query,
        "results_count": len(results),
        "fact_checks": results,
        "note": "Results from published fact-checkers via Google Fact Check Tools API."
            if results else "No published fact-checks found, or API key not configured.",
    }


@router.get("/articles/{article_id}/audit-trail")
async def article_audit_trail(article_id: str):
    """
    Get the transparency audit trail for an article's analysis.
    Shows which models were used, how many user votes contributed,
    and how the final bias/credibility scores were determined.
    """
    from app.core.database import get_db
    db = get_db()

    logs = await db.analysis_audit_log.find(
        {"article_id": article_id},
    ).sort("timestamp", -1).to_list(length=20)

    for log in logs:
        log["_id"] = str(log["_id"])

    return {
        "article_id": article_id,
        "audit_entries": logs,
        "total_entries": len(logs),
    }


# ── Temporal Bias Tracking ────────────────────────────────────────────────────

@router.get("/sources/{source_name}/bias-history")
async def source_bias_history(
    source_name: str,
    days: int = Query(90, ge=7, le=365, description="Number of days to look back"),
):
    """
    Get bias trend history for a news source.

    Shows 7/30/90-day moving averages, drift detection, and
    label distribution over time. Answers the question:
    "Has this source shifted left or right recently?"
    """
    from app.services.bias_tracking_service import get_source_bias_history

    return await get_source_bias_history(source_name, days)


@router.get("/sources/drifting")
async def drifting_sources():
    """
    List all sources whose bias has shifted significantly in the last 90 days.

    Useful for transparency dashboards and editorial monitoring.
    A source "drifts" when its 7-day average diverges from its 90-day
    average by more than 0.5 on the -3 to +3 bias scale.
    """
    from app.services.bias_tracking_service import get_drifting_sources

    sources = await get_drifting_sources()
    return {
        "drifting_sources": sources,
        "total": len(sources),
        "description": "Sources whose bias has shifted significantly in the last 90 days.",
    }


# ── Propaganda Detection ──────────────────────────────────────────────────────

@router.post("/articles/{article_id}/propaganda-check")
async def propaganda_check(
    article_id: str,
    title: str = Query(..., description="Article title"),
    description: str = Query("", description="Article body text"),
    auto_flag: bool = Query(False, description="Auto-flag if propaganda detected"),
):
    """
    Check an article for propaganda and disinformation patterns.

    Detects:
      - Conspiracy language
      - Extreme emotional manipulation
      - Manipulation phrases ("do your own research", "share before deleted")
      - Excessive ALL CAPS
      - No source attribution
      - Excessive punctuation

    Set auto_flag=true to automatically flag articles with medium/high severity.
    """
    from app.services.propaganda_detection_service import (
        detect_propaganda_signals,
        auto_flag_article,
    )

    result = detect_propaganda_signals(title, description)

    if auto_flag and result["severity"] in ("medium", "high"):
        flag = await auto_flag_article(article_id, title, description)
        result["auto_flagged"] = flag is not None

    return {
        "article_id": article_id,
        **result,
    }


@router.get("/propaganda/coordinated-narratives")
async def coordinated_narratives(
    hours: int = Query(2, ge=1, le=24, description="Time window in hours"),
    min_sources: int = Query(4, ge=2, le=10, description="Minimum sources for detection"),
):
    """
    Detect coordinated narrative patterns across sources.

    Looks for near-identical headlines published by multiple sources
    within a short time window. May indicate:
      - Coordinated government press releases
      - PR/propaganda campaigns
      - Wire agency stories (legitimate)
    """
    from app.services.propaganda_detection_service import detect_coordinated_narratives

    results = await detect_coordinated_narratives(hours, min_sources)
    return {
        "time_window_hours": hours,
        "min_sources": min_sources,
        "narratives_found": len(results),
        "narratives": results,
    }


# ── Source Ownership & Transparency ───────────────────────────────────────────

@router.get("/sources/{source_name}/ownership")
async def source_ownership(source_name: str):
    """
    Get ownership, funding, and transparency data for a news source.

    Shows who owns and funds the source, notable political affiliations,
    transparency score, and press freedom notes. Essential for evaluating
    potential conflicts of interest.
    """
    from app.utils.feed_config import get_source_ownership

    return get_source_ownership(source_name)


@router.get("/sources/ownership/all")
async def all_source_ownership():
    """
    Get ownership and funding data for all sources with available data.

    Returns a comprehensive list showing who controls each media outlet,
    how they're funded, and their transparency scores.
    """
    from app.utils.feed_config import SOURCE_OWNERSHIP_DATA

    sources = []
    for name, data in SOURCE_OWNERSHIP_DATA.items():
        sources.append({"source_name": name, **data})

    sources.sort(key=lambda x: x.get("transparency_score", 0), reverse=True)

    return {
        "total": len(sources),
        "sources": sources,
    }

