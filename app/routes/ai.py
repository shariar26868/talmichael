# app/routes/ai.py
"""
Phase 2 — AI Analysis endpoints.
Free users  → rule-based analysis (instant, no API cost)
Paid users  → GPT-4o powered deep analysis
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.models.schemas import ArticleAnalysis
from app.services.ai_service import analyze_article, analyze_batch, get_source_bias

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
):
    """
    Analyze a single article.
    - Public → GPT-4o powered
    """
    use_ai = True
    return await analyze_article(
        guid=body.guid,
        title=body.title,
        description=body.description,
        source=body.source,
        source_url=body.source_url,
        use_ai=use_ai,
    )


@router.post("/analyze/batch", response_model=list[ArticleAnalysis])
async def analyze_batch_endpoint(
    body: BatchAnalyzeRequest,
):
    """
    Analyze up to 20 articles at once.
    - Public → GPT-4o
    """
    if len(body.articles) > 20:
        raise HTTPException(status_code=400, detail="Max 20 articles per batch")

    use_ai = True
    return await analyze_batch(
        [a.model_dump() for a in body.articles],
        use_ai=use_ai,
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
