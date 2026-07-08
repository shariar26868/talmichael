# app/routes/statistics.py
"""
Israeli Social Statistics API.

GET /statistics?use_ai=true&refresh=false

Fetches live Israeli news from positive/social/education/environment categories,
runs GPT-4o-mini analysis to produce chart-ready sector & sentiment breakdown data,
caches results in MongoDB for 30 minutes, and returns:
  - Headline + AI summary paragraph
  - Community Volunteering pie chart (Tech Sector, Youth Orgs, Civilian Aid)
  - Sentiment bar chart (Positive, Neutral, Critical)
  - Top Sectors pie chart (Education, Healthcare, Environment, Security, Culture)
  - Top 5 positive news stories that drove the analysis
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_db
from app.services.news_service import fetch_news

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Israeli Statistics"])

_CACHE_KEY = "israel_social_stats"
_CACHE_TTL_MINUTES = 30

# ── Schemas ───────────────────────────────────────────────────────────────────

class ChartDataPoint(BaseModel):
    label: str
    value: float
    color: str


class StatSection(BaseModel):
    id: str
    title: str
    description: str
    chart_type: str          # "pie" | "bar"
    data: List[ChartDataPoint]
    unit: str = "%"
    news_driven: bool = True


class TopStory(BaseModel):
    title: str
    source: str
    url: str
    published: str


class StatisticsResponse(BaseModel):
    generated_at: str
    headline: str
    summary: str
    sections: List[StatSection]
    top_positive_stories: List[TopStory]
    cache_ttl_minutes: int = _CACHE_TTL_MINUTES
    cached: bool = False


# ── AI Prompt ─────────────────────────────────────────────────────────────────

_STATS_PROMPT = """
You are an expert Israeli social analyst. Based on the following recent Israeli news headlines and descriptions, generate statistical estimates for the social engagement and positive impact landscape in Israel right now.

News Articles:
{articles_text}

Respond ONLY with a valid JSON object in exactly this format:
{{
  "headline": "A short, punchy dashboard headline (max 10 words)",
  "summary": "A 2-3 sentence overview of Israeli social engagement and positive developments based on the news.",
  "community_volunteering": {{
    "tech_sector": <integer 0-100>,
    "youth_orgs": <integer 0-100>,
    "civilian_aid": <integer 0-100>
  }},
  "sentiment": {{
    "positive": <integer 0-100>,
    "neutral": <integer 0-100>,
    "critical": <integer 0-100>
  }},
  "sector_highlights": {{
    "education": <integer 0-100>,
    "healthcare": <integer 0-100>,
    "environment": <integer 0-100>,
    "security": <integer 0-100>,
    "culture": <integer 0-100>
  }}
}}

Rules:
- community_volunteering values must sum to 100
- sentiment values must sum to 100
- sector_highlights values must sum to 100
- Base percentages on the actual news content, not random guesses
- If news heavily covers education, reflect that in sector_highlights
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize(d: dict) -> dict:
    """Normalize a dict of int values so they sum to exactly 100."""
    total = sum(d.values())
    if total == 0:
        n = len(d)
        return {k: round(100 / n) for k in d}
    result = {k: round(v / total * 100) for k, v in d.items()}
    # Fix rounding drift on the largest key
    diff = 100 - sum(result.values())
    if diff != 0:
        largest = max(result, key=result.get)
        result[largest] += diff
    return result


def _fallback_stats(articles: list) -> dict:
    """
    Lightweight keyword-count fallback when OpenAI is unavailable.
    Counts keyword hits in article titles to derive proportional percentages.
    """
    counts = {
        "tech": 0, "youth": 0, "aid": 0,
        "positive": 0, "neutral": 0, "critical": 0,
        "education": 0, "health": 0, "environment": 0,
        "security": 0, "culture": 0,
    }
    keyword_map = {
        "tech": ["tech", "startup", "innovation", "software", "ai", "digital"],
        "youth": ["youth", "young", "student", "children", "teen"],
        "aid": ["volunteer", "aid", "help", "relief", "community", "charity"],
        "positive": ["success", "achieve", "growth", "positive", "improve", "win", "advance"],
        "neutral": ["update", "report", "announce", "plan", "meet"],
        "critical": ["crisis", "problem", "fail", "protest", "controversy", "concern", "lack"],
        "education": ["school", "education", "university", "student", "teacher", "learn"],
        "health": ["health", "hospital", "medical", "doctor", "vaccine", "care"],
        "environment": ["environment", "climate", "green", "nature", "water", "pollution"],
        "security": ["security", "army", "idf", "defense", "attack", "border"],
        "culture": ["culture", "art", "music", "film", "festival", "heritage"],
    }

    for art in articles:
        text = ((art.get("title") or "") + " " + (art.get("description") or "")).lower()
        for key, words in keyword_map.items():
            if any(w in text for w in words):
                counts[key] += 1

    vol = _normalize({"Tech Sector": max(1, counts["tech"]), "Youth Orgs": max(1, counts["youth"]), "Civilian Aid": max(1, counts["aid"])})
    sent = _normalize({"Positive": max(1, counts["positive"]), "Neutral": max(1, counts["neutral"]), "Critical": max(1, counts["critical"])})
    sec = _normalize({
        "Education": max(1, counts["education"]),
        "Healthcare": max(1, counts["health"]),
        "Environment": max(1, counts["environment"]),
        "Security": max(1, counts["security"]),
        "Culture": max(1, counts["culture"]),
    })

    return {
        "headline": "Israeli Social Landscape — Live Update",
        "summary": (
            f"Based on {len(articles)} recent news articles, Israeli social coverage is spread across "
            f"tech, youth, and civilian aid sectors. Education and healthcare dominate positive civic discourse."
        ),
        "community_volunteering": {"tech_sector": list(vol.values())[0], "youth_orgs": list(vol.values())[1], "civilian_aid": list(vol.values())[2]},
        "sentiment": {"positive": list(sent.values())[0], "neutral": list(sent.values())[1], "critical": list(sent.values())[2]},
        "sector_highlights": {
            "education": list(sec.values())[0],
            "healthcare": list(sec.values())[1],
            "environment": list(sec.values())[2],
            "security": list(sec.values())[3],
            "culture": list(sec.values())[4],
        },
    }


def _build_sections(ai_data: dict) -> List[StatSection]:
    vol = ai_data.get("community_volunteering", {})
    sent = ai_data.get("sentiment", {})
    sec = ai_data.get("sector_highlights", {})

    return [
        StatSection(
            id="community_volunteering",
            title="Community Volunteering 2026",
            description="Overview of societal contributions across sectors.",
            chart_type="pie",
            data=[
                ChartDataPoint(label="Tech Sector",  value=vol.get("tech_sector", 33), color="#4A90D9"),
                ChartDataPoint(label="Youth Orgs",   value=vol.get("youth_orgs", 34),  color="#2ECC71"),
                ChartDataPoint(label="Civilian Aid", value=vol.get("civilian_aid", 33), color="#9B59B6"),
            ],
        ),
        StatSection(
            id="social_impact_sentiment",
            title="Public Sentiment — Social Issues",
            description="Positive vs. neutral vs. critical coverage of social initiatives.",
            chart_type="bar",
            data=[
                ChartDataPoint(label="Positive", value=sent.get("positive", 50), color="#27AE60"),
                ChartDataPoint(label="Neutral",  value=sent.get("neutral", 30),  color="#F39C12"),
                ChartDataPoint(label="Critical", value=sent.get("critical", 20), color="#E74C3C"),
            ],
        ),
        StatSection(
            id="sector_highlights",
            title="Top Social Activity Sectors",
            description="Which sectors are most active in Israeli social initiatives.",
            chart_type="pie",
            data=[
                ChartDataPoint(label="Education",   value=sec.get("education", 20),    color="#3498DB"),
                ChartDataPoint(label="Healthcare",  value=sec.get("healthcare", 20),   color="#E74C3C"),
                ChartDataPoint(label="Environment", value=sec.get("environment", 20),  color="#2ECC71"),
                ChartDataPoint(label="Security",    value=sec.get("security", 20),     color="#E67E22"),
                ChartDataPoint(label="Culture",     value=sec.get("culture", 20),      color="#9B59B6"),
            ],
        ),
    ]


async def _run_openai_analysis(articles: list) -> dict:
    """Call GPT-4o-mini to analyze articles and return structured statistics."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    # Build article text (cap at 40 articles for prompt size)
    lines = []
    for a in articles[:40]:
        title = a.get("title") or ""
        desc = (a.get("description") or "")[:120]
        source = a.get("source") or ""
        lines.append(f"- [{source}] {title}: {desc}")
    articles_text = "\n".join(lines)

    prompt = _STATS_PROMPT.format(articles_text=articles_text)

    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    return json.loads(resp.choices[0].message.content)


async def _generate_fresh_statistics(use_ai: bool) -> dict:
    """Fetch news, run analysis, build full statistics payload."""
    # Fetch from multiple social/positive categories in parallel
    categories = ["positive", "social", "education", "environment", "science"]
    tasks = [fetch_news(cat, limit=15, use_cache=True) for cat in categories]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_articles = []
    top_stories_raw = []
    for res in results:
        if isinstance(res, Exception):
            continue
        for art in res.articles:
            d = art.model_dump()
            all_articles.append(d)
            # Collect positive/uplifting stories
            sentiment = d.get("sentiment", "")
            if sentiment == "positive" or not sentiment:
                top_stories_raw.append(d)

    # Get top 5 stories
    top_stories = []
    seen_titles = set()
    for art in top_stories_raw[:30]:
        title = art.get("title") or ""
        if title in seen_titles:
            continue
        seen_titles.add(title)
        top_stories.append(TopStory(
            title=title[:120],
            source=art.get("source") or "Unknown",
            url=art.get("link") or "",
            published=str(art.get("pub_date") or "")[:10],
        ))
        if len(top_stories) >= 5:
            break

    # Run AI or fallback
    if use_ai and settings.openai_api_key and all_articles:
        try:
            ai_data = await _run_openai_analysis(all_articles)
        except Exception as e:
            logger.warning("OpenAI stats generation failed, using fallback: %s", e)
            ai_data = _fallback_stats(all_articles)
    else:
        ai_data = _fallback_stats(all_articles)

    sections = _build_sections(ai_data)

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "headline": ai_data.get("headline", "Israeli Social Engagement Overview"),
        "summary": ai_data.get("summary", ""),
        "sections": [s.model_dump() for s in sections],
        "top_positive_stories": [s.model_dump() for s in top_stories],
        "cache_ttl_minutes": _CACHE_TTL_MINUTES,
        "cached": False,
    }


# ── Route ─────────────────────────────────────────────────────────────────────

@router.get("/statistics/positive")
async def get_positive_statistics():
    """Return a curated, infographic-friendly set of positive statistics for the Positive screen."""
    return {
        "headline": "Israel’s positive momentum",
        "summary": "A curated starter set of uplifting social and civic statistics with source links for the Positive screen.",
        "items": [
            {
                "id": "startup_ecosystem",
                "title": "Israel remains one of the world’s most startup-dense countries",
                "value": "~4,000 active startups",
                "description": "The country continues to be recognized for its innovation ecosystem and high concentration of startups.",
                "source_label": "Startup Nation Central",
                "source_url": "https://startupnationcentral.org/",
                "accent": "#2E8B57",
            },
            {
                "id": "tech_workers",
                "title": "High participation in technology and engineering careers",
                "value": "Strong engineering talent base",
                "description": "Israel’s workforce remains highly represented in technological and engineering fields.",
                "source_label": "OECD / World Bank",
                "source_url": "https://www.oecd.org/",
                "accent": "#3B82F6",
            },
            {
                "id": "universities",
                "title": "World-class university research output",
                "value": "Leading research institutions",
                "description": "Israeli universities continue to produce significant research and innovation activity.",
                "source_label": "Times Higher Education",
                "source_url": "https://www.timeshighereducation.com/",
                "accent": "#8B5CF6",
            },
            {
                "id": "social_tech",
                "title": "Social-tech initiatives are growing across Israeli civil society",
                "value": "Growing impact sector",
                "description": "Civic and nonprofit organizations increasingly use technology to advance community services.",
                "source_label": "Civic tech and nonprofit reports",
                "source_url": "https://www.un.org/en/",
                "accent": "#F59E0B",
            },
            {
                "id": "renewable_energy",
                "title": "Renewable energy adoption is steadily rising",
                "value": "Growing clean-energy mix",
                "description": "Israel continues to expand its clean-energy and efficiency investments.",
                "source_label": "IEA",
                "source_url": "https://www.iea.org/",
                "accent": "#10B981",
            },
            {
                "id": "healthcare_tech",
                "title": "Medical innovation remains a strength",
                "value": "Strong med-tech ecosystem",
                "description": "The country’s medical technology sector continues to develop practical solutions for care and health.",
                "source_label": "Israel Innovation Authority",
                "source_url": "https://innovationisrael.org.il/",
                "accent": "#EF4444",
            },
            {
                "id": "education_investment",
                "title": "Education remains a strategic national priority",
                "value": "Sustained public investment",
                "description": "The country continues to invest heavily in STEM education and future skills development.",
                "source_label": "World Bank",
                "source_url": "https://www.worldbank.org/",
                "accent": "#0F766E",
            },
            {
                "id": "volunteering",
                "title": "Community volunteering and civic participation remain strong",
                "value": "Active civic ecosystem",
                "description": "Israeli society continues to show strong volunteer and community engagement.",
                "source_label": "Israeli voluntary sector reports",
                "source_url": "https://www.gov.il/en/departments/",
                "accent": "#6366F1",
            },
            {
                "id": "diaspora_links",
                "title": "Israel’s global innovation and diaspora networks remain strong",
                "value": "Strong international linkages",
                "description": "The country’s innovation economy continues to benefit from deep global partnerships and talent exchange.",
                "source_label": "World Economic Forum",
                "source_url": "https://www.weforum.org/",
                "accent": "#D946EF",
            },
            {
                "id": "resilience",
                "title": "Israeli society continues to show resilience and adaptability",
                "value": "High civic resilience",
                "description": "The country’s institutions and communities continue to adapt quickly during disruptive periods.",
                "source_label": "OECD / World Bank",
                "source_url": "https://www.oecd.org/",
                "accent": "#14B8A6",
            },
        ],
    }


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    use_ai: bool = Query(True, description="Use GPT-4o-mini for AI-generated analysis"),
    refresh: bool = Query(False, description="Force re-fetch and re-analyze, bypassing cache"),
):
    """
    Get AI-powered Israeli social statistics dashboard data.

    - Fetches live Israeli news from social, positive, education, environment categories.
    - Uses GPT-4o-mini to analyze and produce chart-ready sector & sentiment breakdowns.
    - Results are cached in MongoDB for 30 minutes. Pass `refresh=true` to force update.

    Returns 3 chart sections:
    - **Community Volunteering** (pie): Tech Sector / Youth Orgs / Civilian Aid
    - **Sentiment** (bar): Positive / Neutral / Critical news coverage
    - **Sector Highlights** (pie): Education / Healthcare / Environment / Security / Culture

    Plus top 5 positive news stories driving the analysis.
    """
    db = get_db()

    # 1. Try cache first (unless refresh requested)
    if not refresh:
        cached_doc = await db.statistics_cache.find_one({"key": _CACHE_KEY})
        if cached_doc:
            expires_at = cached_doc.get("expires_at")
            if expires_at and datetime.utcnow() < expires_at:
                payload = cached_doc.get("payload", {})
                payload["cached"] = True
                return StatisticsResponse(**payload)

    # 2. Generate fresh statistics
    try:
        payload = await _generate_fresh_statistics(use_ai=use_ai)
    except Exception as e:
        logger.error("Statistics generation failed: %s", e)
        # Return a safe empty fallback
        payload = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "headline": "Israeli Statistics — Temporarily Unavailable",
            "summary": "Statistics are being refreshed. Please try again shortly.",
            "sections": [],
            "top_positive_stories": [],
            "cache_ttl_minutes": _CACHE_TTL_MINUTES,
            "cached": False,
        }

    # 3. Save to MongoDB cache with TTL
    await db.statistics_cache.update_one(
        {"key": _CACHE_KEY},
        {
            "$set": {
                "key": _CACHE_KEY,
                "payload": payload,
                "generated_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(minutes=_CACHE_TTL_MINUTES),
            }
        },
        upsert=True,
    )

    return StatisticsResponse(**payload)
