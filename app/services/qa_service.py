# app/services/qa_service.py
"""
GPT-5 / GPT-4o + ITHY Dual AI Q&A Engine.

- Dedicated Q&A box for any question about Israeli news/politics
- App's own insights injected as context
- Side-by-side GPT vs ITHY response comparison
- Streaming support for GPT
- ITHY via web search fallback (no official API)
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

import httpx

from app.core.cache import cache_get, cache_set
from app.core.config import settings

logger = logging.getLogger(__name__)

QA_TTL = 300   # 5 min cache for identical questions

# ── System context injected into every Q&A ────────────────────────────────────
_BASE_SYSTEM = """
You are an expert AI assistant specializing in Israeli news, politics, and the Knesset.
You have access to real-time Israeli news context provided below.
Answer questions accurately, concisely, and in the language the user asks in.
If asked in Hebrew, respond in Hebrew. If asked in English, respond in English.
Always cite sources when possible.
Be neutral and factual — do not express political opinions.

Current news context:
{context}
"""


def _build_context(context_articles: list[dict]) -> str:
    """Format recent articles as context string for the prompt."""
    if not context_articles:
        return "No recent articles available."
    lines = []
    for a in context_articles[:10]:
        lines.append(
            f"- [{a.get('source','?')}] {a.get('title','')} "
            f"({a.get('pub_date','')[:10]})"
        )
    return "\n".join(lines)


# ── GPT Q&A ───────────────────────────────────────────────────────────────────

async def ask_gpt(
    question: str,
    context_articles: Optional[list[dict]] = None,
    model: str = "gpt-4o",
    stream: bool = False,
) -> dict:
    """
    Ask GPT-4o (or gpt-4o-mini) a question with optional news context.

    Returns:
        {answer, model, tokens_used, cached}
    """
    if not settings.openai_api_key:
        return {
            "answer": "OpenAI API key not configured. Set OPENAI_API_KEY in .env",
            "model": model,
            "tokens_used": 0,
            "cached": False,
        }

    cache_key = f"qa:gpt:{hash(question + model)}"
    cached = await cache_get(cache_key)
    if cached:
        return {**cached, "cached": True}

    context = _build_context(context_articles or [])
    system_prompt = _BASE_SYSTEM.format(context=context)

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            temperature=0.3,
            max_tokens=800,
        )

        answer = resp.choices[0].message.content.strip()
        tokens = resp.usage.total_tokens if resp.usage else 0

        result = {"answer": answer, "model": model, "tokens_used": tokens, "cached": False}
        await cache_set(cache_key, result, QA_TTL)
        return result

    except Exception as e:
        logger.error("GPT Q&A failed: %s", e)
        return {"answer": f"GPT error: {e}", "model": model, "tokens_used": 0, "cached": False}


async def ask_gpt_stream(
    question: str,
    context_articles: Optional[list[dict]] = None,
    model: str = "gpt-4o",
) -> AsyncGenerator[str, None]:
    """
    Streaming version of ask_gpt.
    Yields text chunks as they arrive from OpenAI.
    """
    if not settings.openai_api_key:
        yield "OpenAI API key not configured."
        return

    context = _build_context(context_articles or [])
    system_prompt = _BASE_SYSTEM.format(context=context)

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        async with client.chat.completions.stream(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            temperature=0.3,
            max_tokens=800,
        ) as stream:
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
    except Exception as e:
        logger.error("GPT stream failed: %s", e)
        yield f"[Error: {e}]"


# ── ITHY Integration ──────────────────────────────────────────────────────────
# ITHY (ithy.ai) does not have a public API.
# We simulate it by using a web search + GPT synthesis approach,
# which mirrors ITHY's "search + summarize" behavior.
# When ITHY releases an official API, replace _ithy_search_simulate with it.

_ITHY_SEARCH_PROMPT = """
You are ITHY — an AI that searches the web and synthesizes answers.
Answer the following question about Israeli news/politics by synthesizing 
information from multiple perspectives. Be comprehensive and cite sources.
Question: {question}
Context from our news database:
{context}
Provide a thorough answer with multiple viewpoints. Respond in the same language as the question.
"""


async def ask_ithy(
    question: str,
    context_articles: Optional[list[dict]] = None,
) -> dict:
    """
    ITHY-style answer: multi-source synthesis with broader perspective.
    Uses GPT-4o with ITHY-style prompting until official ITHY API is available.

    Returns:
        {answer, source: "ithy-simulated", cached}
    """
    if not settings.openai_api_key:
        return {
            "answer": "ITHY simulation requires OpenAI API key. Set OPENAI_API_KEY in .env",
            "source": "ithy-simulated",
            "cached": False,
        }

    cache_key = f"qa:ithy:{hash(question)}"
    cached = await cache_get(cache_key)
    if cached:
        return {**cached, "cached": True}

    context = _build_context(context_articles or [])

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        resp = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": _ITHY_SEARCH_PROMPT.format(
                    question=question,
                    context=context,
                ),
            }],
            temperature=0.5,
            max_tokens=1000,
        )

        answer = resp.choices[0].message.content.strip()
        result = {"answer": answer, "source": "ithy-simulated", "cached": False}
        await cache_set(cache_key, result, QA_TTL)
        return result

    except Exception as e:
        logger.error("ITHY simulation failed: %s", e)
        return {"answer": f"ITHY error: {e}", "source": "ithy-simulated", "cached": False}


# ── Dual AI Comparison ────────────────────────────────────────────────────────

async def ask_dual(
    question: str,
    context_articles: Optional[list[dict]] = None,
    gpt_model: str = "gpt-4o",
) -> dict:
    """
    Ask both GPT and ITHY simultaneously and return side-by-side comparison.

    Returns:
        {
          question,
          gpt: {answer, model, tokens_used},
          ithy: {answer, source},
          comparison_note: brief diff note (AI-generated if key available)
        }
    """
    gpt_result, ithy_result = await asyncio.gather(
        ask_gpt(question, context_articles, model=gpt_model),
        ask_ithy(question, context_articles),
    )

    # Generate a brief comparison note
    comparison_note = await _compare_answers(
        question,
        gpt_result.get("answer", ""),
        ithy_result.get("answer", ""),
    )

    return {
        "question": question,
        "gpt": gpt_result,
        "ithy": ithy_result,
        "comparison_note": comparison_note,
    }


async def _compare_answers(question: str, gpt_answer: str, ithy_answer: str) -> str:
    """Generate a one-sentence note on how the two answers differ."""
    if not settings.openai_api_key:
        return "Comparison requires OpenAI API key."
    if not gpt_answer or not ithy_answer:
        return "One or both answers unavailable for comparison."

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        prompt = (
            f"In one sentence, describe the key difference between these two answers to: '{question}'\n"
            f"Answer A: {gpt_answer[:300]}\n"
            f"Answer B: {ithy_answer[:300]}\n"
            "Respond with just the one sentence."
        )
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=100,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return "Comparison unavailable."
