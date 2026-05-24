# app/services/correlation_service.py
"""
Smart Correlation Engine.

- Groups articles by theme/topic using TF-IDF-style keyword overlap
- Detects inconsistencies between sources covering the same story
- Cross-references news articles with Knesset bills
- Returns clustered story groups with conflict flags
"""

import asyncio
import json
import logging
import re
from collections import defaultdict
from typing import Optional

from app.core.cache import cache_get, cache_set, AI_TTL
from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Stop words to ignore in topic matching ────────────────────────────────────
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "has", "have", "had", "will", "would", "could", "should", "may", "might",
    "that", "this", "these", "those", "it", "its", "as", "up", "out", "about",
    "israel", "israeli",  # too common in this corpus
}


def _extract_keywords(text: str, top_n: int = 10) -> set[str]:
    """Extract meaningful keywords from text."""
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    return {w for w in words if w not in STOP_WORDS}[:top_n] if words else set()


def _keyword_overlap(kw1: set[str], kw2: set[str]) -> float:
    """Jaccard similarity between two keyword sets."""
    if not kw1 or not kw2:
        return 0.0
    return len(kw1 & kw2) / len(kw1 | kw2)


def _rule_based_cluster(articles: list[dict], threshold: float = 0.15) -> list[list[dict]]:
    """
    Group articles into clusters by keyword overlap.
    Returns list of clusters (each cluster = list of articles).
    """
    if not articles:
        return []

    # Extract keywords for each article
    kw_list = []
    for a in articles:
        text = f"{a.get('title', '')} {a.get('description', '')}"
        kw_list.append(_extract_keywords(text))

    clusters: list[list[int]] = []
    assigned = set()

    for i in range(len(articles)):
        if i in assigned:
            continue
        cluster = [i]
        assigned.add(i)
        for j in range(i + 1, len(articles)):
            if j in assigned:
                continue
            if _keyword_overlap(kw_list[i], kw_list[j]) >= threshold:
                cluster.append(j)
                assigned.add(j)
        clusters.append(cluster)

    return [[articles[idx] for idx in cluster] for cluster in clusters]


def _detect_inconsistency_rule(articles: list[dict]) -> Optional[str]:
    """
    Rule-based inconsistency detection within a cluster.
    Flags when articles from different sources use opposing sentiment keywords
    about the same story.
    """
    POSITIVE_WORDS = {"success", "win", "achieve", "approve", "support", "agree", "advance"}
    NEGATIVE_WORDS = {"fail", "reject", "oppose", "crisis", "collapse", "condemn", "deny"}

    pos_sources, neg_sources = [], []
    for a in articles:
        text = f"{a.get('title', '')} {a.get('description', '')}".lower()
        pos_hits = sum(1 for w in POSITIVE_WORDS if w in text)
        neg_hits = sum(1 for w in NEGATIVE_WORDS if w in text)
        if pos_hits > neg_hits:
            pos_sources.append(a.get("source", "Unknown"))
        elif neg_hits > pos_hits:
            neg_sources.append(a.get("source", "Unknown"))

    if pos_sources and neg_sources:
        return (
            f"Conflicting coverage detected: "
            f"{', '.join(pos_sources[:2])} report positively while "
            f"{', '.join(neg_sources[:2])} report negatively on the same story."
        )
    return None


# ── OpenAI-powered clustering ─────────────────────────────────────────────────

_CLUSTER_PROMPT = """
You are a news editor. Given these article headlines, group them by story theme.
Return JSON: {{"clusters": [{{"theme": "...", "article_indices": [0,1,2], "inconsistency": "..." or null}}]}}
Inconsistency = when sources contradict each other on the same story.
Headlines:
{headlines}
Respond ONLY with valid JSON.
"""


async def _openai_cluster(articles: list[dict]) -> Optional[list[dict]]:
    if not settings.openai_api_key:
        return None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        headlines = "\n".join(
            f"{i}. [{a.get('source', '?')}] {a.get('title', '')}"
            for i, a in enumerate(articles[:30])  # cap at 30 to control tokens
        )
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": _CLUSTER_PROMPT.format(headlines=headlines)}],
            temperature=0.1,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        raw_clusters = data.get("clusters", [])
        result = []
        for c in raw_clusters:
            indices = c.get("article_indices", [])
            cluster_articles = [articles[i] for i in indices if i < len(articles)]
            result.append({
                "theme": c.get("theme", "General"),
                "article_count": len(cluster_articles),
                "articles": cluster_articles,
                "inconsistency": c.get("inconsistency"),
                "method": "ai",
            })
        return result
    except Exception as e:
        logger.warning("OpenAI clustering failed: %s", e)
        return None


# ── Public API ────────────────────────────────────────────────────────────────

async def correlate_articles(
    articles: list[dict],
    use_ai: bool = False,
    cache_key: Optional[str] = None,
) -> list[dict]:
    """
    Cluster articles by theme and detect inconsistencies.

    Args:
        articles:  List of article dicts (title, description, source, guid).
        use_ai:    Use GPT-4o for smarter clustering (paid).
        cache_key: Optional Redis key for caching results.

    Returns:
        List of cluster dicts: {theme, article_count, articles, inconsistency}
    """
    if cache_key:
        cached = await cache_get(cache_key)
        if cached:
            return cached

    clusters = None

    if use_ai:
        clusters = await _openai_cluster(articles)

    if clusters is None:
        # Rule-based fallback
        raw_clusters = _rule_based_cluster(articles)
        clusters = []
        for i, cluster in enumerate(raw_clusters):
            if not cluster:
                continue
            # Derive theme from most common keywords
            all_text = " ".join(f"{a.get('title','')} {a.get('description','')}" for a in cluster)
            kws = _extract_keywords(all_text, top_n=3)
            theme = ", ".join(sorted(kws)[:3]) or f"Story Group {i+1}"
            inconsistency = _detect_inconsistency_rule(cluster) if len(cluster) > 1 else None
            clusters.append({
                "theme": theme,
                "article_count": len(cluster),
                "articles": cluster,
                "inconsistency": inconsistency,
                "method": "rule-based",
            })

    # Sort: clusters with inconsistencies first, then by size
    clusters.sort(key=lambda c: (c["inconsistency"] is None, -c["article_count"]))

    if cache_key:
        await cache_set(cache_key, clusters, AI_TTL)

    return clusters


async def cross_reference_bills(
    articles: list[dict],
    bills: list[dict],
    use_ai: bool = False,
) -> list[dict]:
    """
    Match news articles to related Knesset bills by keyword overlap.
    Returns list of matches: {article, related_bills, relevance_score}
    """
    results = []
    for article in articles:
        a_text = f"{article.get('title','')} {article.get('description','')}".lower()
        a_kw = _extract_keywords(a_text)

        matches = []
        for bill in bills:
            b_text = f"{bill.get('name','')} {bill.get('name_hebrew','')}".lower()
            b_kw = _extract_keywords(b_text)
            score = _keyword_overlap(a_kw, b_kw)
            if score > 0.05:
                matches.append({**bill, "relevance_score": round(score, 3)})

        if matches:
            matches.sort(key=lambda x: -x["relevance_score"])
            results.append({
                "article_title": article.get("title"),
                "article_source": article.get("source"),
                "related_bills": matches[:3],
            })

    return results
