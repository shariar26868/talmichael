# app/routes/correlation.py
"""
Smart Correlation Engine endpoints.

POST /correlation/cluster        — group articles by theme
POST /correlation/cross-reference — match articles to Knesset bills
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from app.services.correlation_service import correlate_articles, cross_reference_bills
from app.services.news_service import fetch_all_news, fetch_knesset_bills

router = APIRouter(prefix="/correlation", tags=["Smart Correlation"])


class ArticleInput(BaseModel):
    guid: Optional[str] = ""
    title: str
    description: Optional[str] = ""
    source: Optional[str] = None
    source_url: Optional[str] = None


class ClusterRequest(BaseModel):
    articles: list[ArticleInput]
    use_ai: bool = False


class CrossRefRequest(BaseModel):
    articles: list[ArticleInput]
    bills: list[dict]
    use_ai: bool = False


@router.post("/cluster", summary="Group articles by theme and detect inconsistencies")
async def cluster_articles(body: ClusterRequest):
    """
    Cluster a list of articles by story theme.
    Detects when different sources contradict each other on the same story.

    - use_ai=false → fast rule-based keyword clustering (free)
    - use_ai=true  → GPT-4o semantic clustering (requires OPENAI_API_KEY)
    """
    articles = [a.model_dump() for a in body.articles]
    clusters = await correlate_articles(articles, use_ai=body.use_ai)
    return {
        "total_articles": len(articles),
        "total_clusters": len(clusters),
        "clusters_with_inconsistency": sum(1 for c in clusters if c.get("inconsistency")),
        "clusters": clusters,
    }


@router.get("/cluster/live", summary="Cluster live news from all categories")
async def cluster_live(
    limit: int = Query(10, ge=1, le=30),
    use_ai: bool = Query(False),
):
    """
    Fetch live news from all categories and cluster them automatically.
    """
    all_news = await fetch_all_news(limit)

    # Flatten all articles
    all_articles = []
    for cat, data in all_news.items():
        if isinstance(data, dict) and "articles" in data:
            for a in data["articles"]:
                article = a if isinstance(a, dict) else a.model_dump()
                article["category"] = cat
                all_articles.append(article)

    clusters = await correlate_articles(
        all_articles,
        use_ai=use_ai,
        cache_key=f"correlation:live:{limit}:{int(use_ai)}",
    )

    return {
        "total_articles": len(all_articles),
        "total_clusters": len(clusters),
        "clusters_with_inconsistency": sum(1 for c in clusters if c.get("inconsistency")),
        "clusters": clusters,
    }


@router.post("/cross-reference", summary="Match articles to related Knesset bills")
async def cross_ref(body: CrossRefRequest):
    """
    Find Knesset bills related to each article by keyword overlap.
    """
    articles = [a.model_dump() for a in body.articles]
    matches = await cross_reference_bills(articles, body.bills, use_ai=body.use_ai)
    return {
        "total_articles": len(articles),
        "articles_with_bill_matches": len(matches),
        "matches": matches,
    }


@router.get("/cross-reference/live", summary="Cross-reference live news with Knesset bills")
async def cross_ref_live(
    limit: int = Query(10, ge=1, le=30),
):
    """
    Fetch live news + Knesset bills and find correlations automatically.
    """
    news_data, bills_data = await fetch_all_news(limit), await fetch_knesset_bills(20)

    all_articles = []
    for cat, data in news_data.items():
        if isinstance(data, dict) and "articles" in data:
            for a in data["articles"]:
                article = a if isinstance(a, dict) else a.model_dump()
                all_articles.append(article)

    bills = bills_data.get("bills", bills_data.get("articles", []))
    matches = await cross_reference_bills(all_articles, bills)

    return {
        "total_articles": len(all_articles),
        "total_bills": len(bills),
        "articles_with_bill_matches": len(matches),
        "matches": matches,
    }
