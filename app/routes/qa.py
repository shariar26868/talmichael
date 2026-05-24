# app/routes/qa.py
"""
GPT + ITHY Dual AI Q&A endpoints.

POST /qa/ask          — ask GPT-4o with news context
POST /qa/ask/stream   — streaming GPT response (SSE)
POST /qa/ask/ithy     — ask ITHY-style AI
POST /qa/ask/dual     — ask both GPT + ITHY, get side-by-side comparison
"""

import asyncio
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.qa_service import ask_gpt, ask_gpt_stream, ask_ithy, ask_dual
from app.services.news_service import fetch_all_news

router = APIRouter(prefix="/qa", tags=["AI Q&A"])


# ── Request schema ────────────────────────────────────────────────────────────

class QARequest(BaseModel):
    question: str
    category: Optional[str] = None      # inject context from this category
    use_context: bool = True             # inject recent news as context
    model: str = "gpt-4o"               # gpt-4o | gpt-4o-mini


# ── Context helper ────────────────────────────────────────────────────────────

async def _get_context(category: Optional[str], use_context: bool) -> list[dict]:
    if not use_context:
        return []
    try:
        if category:
            from app.services.news_service import fetch_news
            news = await fetch_news(category, 10, israeli_only=True)
            return [a.model_dump() for a in news.articles]
        else:
            all_news = await fetch_all_news(5)
            articles = []
            for data in all_news.values():
                if isinstance(data, dict) and "articles" in data:
                    articles.extend(
                        a if isinstance(a, dict) else a.model_dump()
                        for a in data["articles"]
                    )
            return articles[:20]
    except Exception:
        return []


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/ask", summary="Ask GPT-4o with Israeli news context")
async def ask(body: QARequest):
    """
    Ask any question about Israeli news, politics, or the Knesset.
    Recent news articles are automatically injected as context.

    - model: gpt-4o (default, best quality) or gpt-4o-mini (faster, cheaper)
    - use_context=false: pure GPT without news context
    - category: inject context from a specific news category
    """
    context = await _get_context(body.category, body.use_context)
    return await ask_gpt(body.question, context, model=body.model)


@router.post("/ask/stream", summary="Streaming GPT-4o response (SSE)")
async def ask_stream(body: QARequest):
    """
    Same as /qa/ask but streams the response token by token.
    Returns Server-Sent Events (text/event-stream).
    """
    context = await _get_context(body.category, body.use_context)

    async def event_generator():
        async for chunk in ask_gpt_stream(body.question, context, model=body.model):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/ask/ithy", summary="Ask ITHY-style multi-source AI")
async def ask_ithy_endpoint(body: QARequest):
    """
    ITHY-style answer: broader, multi-perspective synthesis.
    Simulates ITHY's search-and-summarize behavior using GPT-4o
    with a different prompting strategy.
    """
    context = await _get_context(body.category, body.use_context)
    return await ask_ithy(body.question, context)


@router.post("/ask/dual", summary="Ask both GPT and ITHY — side-by-side comparison")
async def ask_dual_endpoint(body: QARequest):
    """
    Sends the same question to both GPT-4o and ITHY simultaneously.
    Returns both answers + a one-sentence comparison note.

    Perfect for seeing how different AI approaches frame the same topic.
    """
    context = await _get_context(body.category, body.use_context)
    return await ask_dual(body.question, context, gpt_model=body.model)


@router.get("/ask", summary="Quick GET-based Q&A (for testing)")
async def ask_get(
    q: str = Query(..., description="Your question"),
    category: Optional[str] = Query(None),
    model: str = Query("gpt-4o-mini"),
):
    """Quick GET endpoint for testing Q&A from browser/curl."""
    context = await _get_context(category, True)
    return await ask_gpt(q, context, model=model)
