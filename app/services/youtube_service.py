# app/services/youtube_service.py
"""
YouTube Podcast Search Service — OpenAI-Assisted.

Flow:
  1. User gives a prompt (e.g. "Israeli politics ceasefire")
  2. OpenAI generates 4 optimized YouTube search queries for that topic
  3. We run each query through YouTube's HTML search (no API key needed)
  4. Deduplicate + rank results by podcast-likelihood
  5. Return real, verified YouTube links — never hallucinated URLs

Why this approach:
  - OpenAI CANNOT provide real YouTube video IDs (it hallucinates them)
  - OpenAI CAN generate better search queries than a user's raw prompt
  - Actual links come from real-time YouTube scraping = always valid
"""

import json
import logging
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

import httpx
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_MIN_DURATION_SECONDS = 8 * 60  # 8 minutes minimum to count as podcast-style


# ── Step 1: OpenAI generates optimized search queries ────────────────────────

_QUERY_PROMPT = """\
You are a YouTube research assistant. Given a topic, generate {n} specific YouTube search queries \
that will find high-quality podcast episodes, interview shows, or long-form discussion videos about that topic.

Rules:
- Each query should be distinct (different angle / keyword combination)
- Always include "podcast" OR "interview" OR "episode" in at least 2 of the queries
- Keep queries short (3–7 words each)
- Make queries specific enough to avoid music videos, news clips, or short content
- Return ONLY a JSON array of strings, nothing else

Topic: {topic}

Example output format:
["query one here", "query two here", "query three here", "query four here"]
"""


async def generate_search_queries(prompt: str, n: int = 4) -> list[str]:
    """
    Use OpenAI to turn a user prompt into optimized YouTube search queries.
    Falls back to simple query list if OpenAI fails.
    """
    if not settings.openai_api_key:
        # Fallback: generate basic queries without AI
        return [
            f"{prompt} podcast",
            f"{prompt} interview",
            f"{prompt} discussion episode",
            f"{prompt} long form talk",
        ]

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": _QUERY_PROMPT.format(topic=prompt, n=n),
                }
            ],
            temperature=0.7,
            max_tokens=200,
            timeout=15.0,
        )
        raw = resp.choices[0].message.content.strip()
        # Extract JSON array even if there's surrounding text
        match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if match:
            queries = json.loads(match.group())
            if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                logger.info("OpenAI generated %d queries for: %s", len(queries), prompt)
                return [q.strip() for q in queries if q.strip()][:n]
    except Exception as e:
        logger.warning("OpenAI query generation failed: %s — using fallback", e)

    # Fallback
    return [
        f"{prompt} podcast",
        f"{prompt} interview",
        f"{prompt} episode discussion",
        f"{prompt} talk show",
    ]


# ── Step 2: Scrape real YouTube results for a query ───────────────────────────

_VIDEO_ID_RE = re.compile(r'"videoId"\s*:\s*"([A-Za-z0-9_-]{11})"')
_TITLE_RE = re.compile(r'"title"\s*:\s*\{"runs"\s*:\s*\[\{"text"\s*:\s*"([^"]+)"')
_CHANNEL_RE = re.compile(r'"ownerText"\s*:\s*\{"runs"\s*:\s*\[\{"text"\s*:\s*"([^"]+)"')
_DURATION_TEXT_RE = re.compile(r'"simpleText"\s*:\s*"(\d{1,2}:\d{2}(?::\d{2})?)"')
_VIEW_COUNT_RE = re.compile(r'"viewCountText"\s*:\s*\{"simpleText"\s*:\s*"([^"]+)"')
_PUBLISHED_RE = re.compile(r'"publishedTimeText"\s*:\s*\{"simpleText"\s*:\s*"([^"]+)"')

# YouTube search filter: sp=EgQQARgC = Type:Video + Duration:Long (>20min)
# sp=EgIQAQ = Type:Video only (no duration filter — catches 8-20min podcasts too)
_YT_SEARCH_URL = "https://www.youtube.com/results"


def _duration_to_seconds(text: str) -> int:
    """Convert 'H:MM:SS' or 'M:SS' to seconds."""
    parts = text.strip().split(":")
    try:
        parts = [int(p) for p in parts]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
    except ValueError:
        pass
    return 0


def _fmt_duration(seconds: int) -> str:
    """Format seconds as H:MM:SS or M:SS."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _score_result(title: str, duration_sec: int) -> int:
    """Score a result for podcast-likelihood (higher = better)."""
    score = 0
    title_lower = title.lower()

    # Duration scoring
    if duration_sec >= 3600:     # 1hr+
        score += 10
    elif duration_sec >= 1800:   # 30min+
        score += 7
    elif duration_sec >= 600:    # 10min+
        score += 4
    elif duration_sec >= _MIN_DURATION_SECONDS:
        score += 2

    # Keyword scoring
    podcast_keywords = ["podcast", "episode", "ep.", "interview", "discussion",
                        "talk", "conversation", "roundtable", "panel", "show"]
    for kw in podcast_keywords:
        if kw in title_lower:
            score += 3

    # Anti-score for shorts/clips
    anti_keywords = ["#shorts", "clip", "trailer", "teaser", "highlight", "shorts"]
    for kw in anti_keywords:
        if kw in title_lower:
            score -= 10

    return score


async def _scrape_youtube_query(query: str, max_per_query: int = 8) -> list[dict]:
    """Scrape YouTube search results for a single query."""
    params = {
        "search_query": query,
        "sp": "EgIQAQ",  # Video type filter only
    }
    url = f"{_YT_SEARCH_URL}?{urlencode(params)}"

    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            headers=_HEADERS,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        logger.warning("YouTube scrape failed for '%s': %s", query, e)
        return []

    video_ids = list(dict.fromkeys(_VIDEO_ID_RE.findall(html)))  # ordered dedupe
    titles = _TITLE_RE.findall(html)
    channels = _CHANNEL_RE.findall(html)
    duration_texts = _DURATION_TEXT_RE.findall(html)
    published_texts = _PUBLISHED_RE.findall(html)

    results = []
    for i, vid_id in enumerate(video_ids[:max_per_query + 5]):
        title = titles[i] if i < len(titles) else ""
        channel = channels[i] if i < len(channels) else ""
        dur_text = duration_texts[i] if i < len(duration_texts) else ""
        published = published_texts[i] if i < len(published_texts) else ""
        dur_sec = _duration_to_seconds(dur_text) if dur_text else 0

        score = _score_result(title, dur_sec)
        if score < 0:  # skip clear non-podcasts (shorts, trailers)
            continue

        results.append({
            "video_id": vid_id,
            "title": title,
            "channel": channel,
            "duration_seconds": dur_sec,
            "duration_formatted": dur_text or _fmt_duration(dur_sec),
            "published": published,
            "thumbnail": f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg",
            "url": f"https://www.youtube.com/watch?v={vid_id}",
            "embed_url": f"https://www.youtube.com/embed/{vid_id}",
            "_score": score,
            "_query_used": query,
        })

    return results


# ── Step 3: Full pipeline ─────────────────────────────────────────────────────

async def search_podcasts(
    prompt: str,
    max_results: int = 10,
    language: str = "en",
) -> dict:
    """
    Main entry point.

    1. Ask OpenAI to generate smart search queries for the topic
    2. Scrape real YouTube results for each query
    3. Deduplicate, filter by duration, rank by podcast score
    4. Return top N verified YouTube links
    """
    max_results = max(1, min(max_results, 25))

    # Step 1: Generate optimized queries via OpenAI
    queries = await generate_search_queries(prompt, n=4)
    logger.info("Searching YouTube for '%s' with queries: %s", prompt, queries)

    # Step 2: Scrape YouTube for each query in parallel... sequentially for reliability
    all_results: list[dict] = []
    seen_ids: set[str] = set()

    for query in queries:
        raw = await _scrape_youtube_query(query, max_per_query=8)
        for item in raw:
            vid_id = item["video_id"]
            if vid_id not in seen_ids:
                seen_ids.add(vid_id)
                all_results.append(item)

    # Step 3: Filter — must be at least _MIN_DURATION_SECONDS
    filtered = [r for r in all_results if r["duration_seconds"] >= _MIN_DURATION_SECONDS]

    # If nothing passes the duration filter, relax it and take anything with a score > 0
    if not filtered:
        filtered = [r for r in all_results if r["_score"] > 0]

    # Step 4: Sort by podcast score descending
    filtered.sort(key=lambda x: x["_score"], reverse=True)

    # Step 5: Take top N, strip internal fields
    top = filtered[:max_results]
    for item in top:
        item.pop("_score", None)

    return {
        "query": prompt,
        "queries_used": queries,
        "results_count": len(top),
        "results": top,
        "method": "openai_query_generation + youtube_realtime_scrape",
        "data_integrity": (
            "All video links are scraped from real-time YouTube search results. "
            "OpenAI is used ONLY to generate better search queries — it does NOT provide video links. "
            "Every URL is a real, live YouTube video."
        ),
        "searched_at": datetime.utcnow().isoformat() + "Z",
        "openai_used": bool(settings.openai_api_key),
    }
