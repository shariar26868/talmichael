# app/services/insights_service.py
"""
Real-time AI Insights + Trend Detection Engine.

Per-category:
  - AI-generated Hebrew insight paragraph
  - Top trending topics (keyword frequency + velocity)
  - Theme-based digest
  - Global trend across all categories
"""

import asyncio
import json
import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

from app.core.cache import cache_get, cache_set, AI_TTL
from app.core.config import settings

logger = logging.getLogger(__name__)

INSIGHTS_TTL = 900   # 15 min — insights refresh faster than raw news
TRENDS_TTL   = 600   # 10 min


# ── Trend Detection (rule-based) ──────────────────────────────────────────────

TREND_STOP_WORDS = {
    "israel", "israeli", "the", "and", "for", "that", "with",
    "from", "this", "have", "will", "says", "said", "news",
    "report", "after", "over", "more", "also", "been", "were",
}


def _extract_trend_keywords(articles: list[dict], top_n: int = 15) -> list[dict]:
    """
    Count keyword frequency across article titles.
    Returns top_n keywords with count and sample headlines.
    """
    counter: Counter = Counter()
    keyword_headlines: dict[str, list[str]] = {}

    for a in articles:
        title = a.get("title", "").lower()
        words = [
            w.strip(".,!?\"'()[]")
            for w in title.split()
            if len(w) > 4 and w.lower() not in TREND_STOP_WORDS
        ]
        for w in words:
            counter[w] += 1
            if w not in keyword_headlines:
                keyword_headlines[w] = []
            if len(keyword_headlines[w]) < 2:
                keyword_headlines[w].append(a.get("title", ""))

    return [
        {
            "keyword": kw,
            "count": count,
            "sample_headlines": keyword_headlines.get(kw, []),
        }
        for kw, count in counter.most_common(top_n)
        if count >= 2  # only keywords appearing in 2+ articles
    ]


def _rule_based_insight(category: str, articles: list[dict], trends: list[dict]) -> str:
    """Generate a simple rule-based insight string (English fallback)."""
    if not articles:
        return f"No recent articles found for {category}."

    top_keywords = [t["keyword"] for t in trends[:5]]
    sources = list({a.get("source") for a in articles if a.get("source")})[:3]
    count = len(articles)

    return (
        f"[{category.upper()}] {count} articles analyzed. "
        f"Key topics: {', '.join(top_keywords) or 'general'}. "
        f"Sources: {', '.join(sources) or 'various'}."
    )


# ── OpenAI Insights ───────────────────────────────────────────────────────────

_INSIGHT_PROMPT = """
You are an Israeli news analyst. Based on these {count} recent articles about "{category}", 
write a concise 3-sentence insight paragraph IN HEBREW.
Focus on: what is happening, why it matters, and what to watch next.

Top trending keywords: {keywords}

Sample headlines:
{headlines}

Respond ONLY with the Hebrew paragraph. No JSON, no English.
"""

_TREND_PROMPT = """
You are a news trend analyst. Given these article headlines from the "{category}" category,
identify the 5 most important trending topics right now.

Headlines:
{headlines}

Return JSON: {{"trends": [{{"topic": "...", "importance": "high|medium|low", "summary": "one sentence in English"}}]}}
"""


async def _openai_insight(category: str, articles: list[dict], trends: list[dict]) -> Optional[str]:
    if not settings.openai_api_key or not articles:
        return None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        headlines = "\n".join(
            f"- [{a.get('source','?')}] {a.get('title','')}"
            for a in articles[:20]
        )
        keywords = ", ".join(t["keyword"] for t in trends[:8])

        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": _INSIGHT_PROMPT.format(
                    count=len(articles),
                    category=category,
                    keywords=keywords,
                    headlines=headlines,
                ),
            }],
            temperature=0.4,
            max_tokens=300,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("OpenAI insight failed for %s: %s", category, e)
        return None


async def _openai_trends(category: str, articles: list[dict]) -> Optional[list[dict]]:
    if not settings.openai_api_key or not articles:
        return None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        headlines = "\n".join(
            f"{i+1}. {a.get('title','')}" for i, a in enumerate(articles[:25])
        )
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": _TREND_PROMPT.format(category=category, headlines=headlines),
            }],
            temperature=0.2,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        return data.get("trends", [])
    except Exception as e:
        logger.warning("OpenAI trends failed for %s: %s", category, e)
        return None


# ── Public API ────────────────────────────────────────────────────────────────

async def generate_category_insight(
    category: str,
    articles: list[dict],
    use_ai: bool = False,
) -> dict:
    """
    Generate insight + trends for a single category.

    Returns:
        {
          category, article_count,
          insight_hebrew (str),
          trends (list of {keyword, count, sample_headlines}),
          ai_trends (list — only if use_ai=True),
          generated_at
        }
    """
    cache_key = f"insights:{category}:{int(use_ai)}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # Rule-based trends always computed
    rule_trends = _extract_trend_keywords(articles)

    # AI paths
    insight_hebrew = None
    ai_trends = None

    if use_ai:
        insight_hebrew, ai_trends = await asyncio.gather(
            _openai_insight(category, articles, rule_trends),
            _openai_trends(category, articles),
        )

    # Fallback
    if not insight_hebrew:
        insight_hebrew = _rule_based_insight(category, articles, rule_trends)

    result = {
        "category": category,
        "article_count": len(articles),
        "insight_hebrew": insight_hebrew,
        "trends": rule_trends[:10],
        "ai_trends": ai_trends or [],
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    await cache_set(cache_key, result, INSIGHTS_TTL)
    return result


async def generate_all_insights(
    category_articles: dict[str, list[dict]],
    use_ai: bool = False,
) -> dict:
    """
    Generate insights for all categories concurrently.

    Args:
        category_articles: {category_name: [article_dicts]}
        use_ai: Use GPT-4o for Hebrew insights

    Returns:
        {category: insight_dict, ..., global_trends: [...]}
    """
    tasks = {
        cat: generate_category_insight(cat, articles, use_ai=use_ai)
        for cat, articles in category_articles.items()
        if articles
    }

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    output = {}
    for cat, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            output[cat] = {"error": str(result)}
        else:
            output[cat] = result

    # Global trend — aggregate all keywords
    all_keywords: Counter = Counter()
    for cat_data in output.values():
        if isinstance(cat_data, dict) and "trends" in cat_data:
            for t in cat_data["trends"]:
                all_keywords[t["keyword"]] += t["count"]

    output["global_trends"] = [
        {"keyword": kw, "total_count": count}
        for kw, count in all_keywords.most_common(20)
    ]

    return output


async def get_trending_topics(
    all_articles: list[dict],
    use_ai: bool = False,
    top_n: int = 20,
) -> list[dict]:
    """
    Get trending topics across ALL categories combined.
    """
    cache_key = f"trends:global:{int(use_ai)}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    rule_trends = _extract_trend_keywords(all_articles, top_n=top_n)

    if use_ai and settings.openai_api_key:
        ai_trends = await _openai_trends("global", all_articles)
        if ai_trends:
            # Merge AI trends with rule-based counts
            ai_kw_set = {t["topic"].lower() for t in ai_trends}
            for rt in rule_trends:
                if rt["keyword"] not in ai_kw_set:
                    ai_trends.append({
                        "topic": rt["keyword"],
                        "importance": "low",
                        "summary": f"Appears in {rt['count']} articles",
                    })
            result = ai_trends[:top_n]
            await cache_set(cache_key, result, TRENDS_TTL)
            return result

    await cache_set(cache_key, rule_trends, TRENDS_TTL)
    return rule_trends
