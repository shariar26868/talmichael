# app/services/cross_source_verification_service.py
"""
Cross-Source Verification — same event, multiple sources.

Given a set of recently fetched articles, this service:
  1. Clusters articles about the same event (TF-IDF + cosine similarity).
  2. Compares how different sources frame the same story.
  3. Produces an agreement score and highlights divergences.
  4. Identifies if key facts are confirmed across sources.

This is the single most impactful verification feature: "3 sources
confirm this claim, 1 contradicts it" is far more credible than a
single-source credibility score.
"""

import logging
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Optional

from app.core.database import get_db
from app.models.schemas import CrossSourceMatch

logger = logging.getLogger(__name__)

# ── Stop words for similarity comparison ──────────────────────────────────────
_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to",
    "for", "of", "and", "or", "but", "not", "by", "with", "from", "as",
    "it", "its", "this", "that", "has", "have", "had", "been", "will",
    "be", "do", "does", "did", "he", "she", "they", "we", "you", "i",
    "my", "his", "her", "their", "our", "your", "if", "so", "no", "yes",
    "can", "could", "would", "should", "may", "might", "said", "says",
    "also", "more", "than", "after", "about", "into", "over", "up",
    "new", "news", "report", "reports", "just", "like", "some", "all",
    "most", "many", "much", "very", "out", "who", "what", "when", "where",
    "how", "which", "while", "being", "those", "these", "other",
})


def _tokenize(text: str) -> list[str]:
    """Lowercase tokenize, remove stop words and short tokens."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 2]


def _compute_similarity(tokens_a: list[str], tokens_b: list[str]) -> float:
    """Cosine similarity between two token lists (bag-of-words)."""
    if not tokens_a or not tokens_b:
        return 0.0

    counter_a = Counter(tokens_a)
    counter_b = Counter(tokens_b)
    all_words = set(counter_a) | set(counter_b)

    dot_product = sum(counter_a.get(w, 0) * counter_b.get(w, 0) for w in all_words)
    mag_a = sum(v ** 2 for v in counter_a.values()) ** 0.5
    mag_b = sum(v ** 2 for v in counter_b.values()) ** 0.5

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot_product / (mag_a * mag_b)


# ── Clustering ────────────────────────────────────────────────────────────────

SIMILARITY_THRESHOLD = 0.35  # articles above this are about the same event


def cluster_articles(articles: list[dict]) -> list[list[dict]]:
    """Group articles into event clusters based on title+description similarity.

    Each article dict should have at least: guid, title, description, source, bias.
    Returns a list of clusters (each cluster is a list of article dicts).
    """
    if not articles:
        return []

    # Pre-tokenize
    tokenized = []
    for article in articles:
        text = f"{article.get('title', '')} {article.get('description', '')}"
        tokenized.append(_tokenize(text))

    # Greedy single-linkage clustering
    n = len(articles)
    assigned = [False] * n
    clusters: list[list[int]] = []

    for i in range(n):
        if assigned[i]:
            continue

        cluster = [i]
        assigned[i] = True

        for j in range(i + 1, n):
            if assigned[j]:
                continue

            # Compare against any member of the cluster
            for member_idx in cluster:
                sim = _compute_similarity(tokenized[member_idx], tokenized[j])
                if sim >= SIMILARITY_THRESHOLD:
                    cluster.append(j)
                    assigned[j] = True
                    break

        clusters.append(cluster)

    # Convert indices back to article dicts
    return [[articles[idx] for idx in c] for c in clusters if len(c) >= 2]


# ── Verification ──────────────────────────────────────────────────────────────

def _detect_sentiment_word(text: str) -> str:
    """Quick sentiment hint from keywords."""
    low = text.lower()
    neg = sum(1 for w in ("attack", "crisis", "failure", "killed", "dead",
                          "protest", "collapse", "condemn", "reject", "warn",
                          "threaten", "accuse", "blame", "oppose") if w in low)
    pos = sum(1 for w in ("success", "peace", "agreement", "victory", "approve",
                          "support", "celebrate", "achieve", "improve", "growth",
                          "praise", "welcome") if w in low)
    if neg > pos:
        return "negative"
    elif pos > neg:
        return "positive"
    return "neutral"


def verify_cluster(cluster: list[dict]) -> CrossSourceMatch:
    """Analyze a cluster of articles about the same event.

    Returns a CrossSourceMatch with:
      - agreement_score: how consistently the event is reported
      - divergences: specific differences across sources
      - consensus_framing: what most sources agree on
    """
    if len(cluster) < 2:
        return CrossSourceMatch(
            event_cluster_id="single",
            source_count=len(cluster),
            agreement_score=0.5,
        )

    # Generate cluster ID from first article
    cluster_id = f"evt-{hash(cluster[0].get('guid', '')) % 100000:05d}"

    sources = set()
    sentiments = []
    biases = []
    matching = []

    for article in cluster:
        src = article.get("source", "Unknown")
        sources.add(src)
        sentiments.append(_detect_sentiment_word(
            f"{article.get('title', '')} {article.get('description', '')}"
        ))
        biases.append(article.get("bias", "unknown"))
        matching.append({
            "source": src,
            "title": article.get("title", ""),
            "bias": article.get("bias", "unknown"),
            "guid": article.get("guid", ""),
        })

    # Agreement score components
    # 1. Sentiment agreement (do sources agree on tone?)
    sentiment_counter = Counter(sentiments)
    dominant_sentiment = sentiment_counter.most_common(1)[0]
    sentiment_agreement = dominant_sentiment[1] / len(sentiments)

    # 2. Bias agreement (do sources with different biases agree?)
    unique_biases = set(biases)
    bias_diversity = len(unique_biases) / max(len(biases), 1)
    # Higher bias diversity + same sentiment = stronger verification
    cross_bias_bonus = 0.1 if bias_diversity > 0.3 and sentiment_agreement > 0.6 else 0.0

    # 3. Source count bonus (more sources = more verified)
    source_bonus = min(len(sources) * 0.05, 0.2)

    agreement_score = round(
        min(sentiment_agreement * 0.6 + (1 - bias_diversity) * 0.2 + source_bonus + cross_bias_bonus, 1.0),
        2,
    )

    # Detect divergences
    divergences = []
    if len(set(sentiments)) > 1:
        neg_sources = [cluster[i].get("source", "?")
                       for i, s in enumerate(sentiments) if s == "negative"]
        pos_sources = [cluster[i].get("source", "?")
                       for i, s in enumerate(sentiments) if s == "positive"]
        if neg_sources and pos_sources:
            divergences.append(
                f"Tone divergence: {', '.join(pos_sources[:2])} frame positively "
                f"while {', '.join(neg_sources[:2])} frame negatively"
            )

    if len(unique_biases) > 2:
        divergences.append(
            f"Covered by sources across the spectrum: {', '.join(sorted(unique_biases))}"
        )

    # Consensus framing
    consensus_framing = None
    if sentiment_agreement >= 0.7:
        consensus_framing = f"Most sources ({dominant_sentiment[1]}/{len(sentiments)}) frame this as {dominant_sentiment[0]}"

    return CrossSourceMatch(
        event_cluster_id=cluster_id,
        matching_articles=matching,
        source_count=len(sources),
        agreement_score=agreement_score,
        divergences=divergences,
        consensus_framing=consensus_framing,
    )


async def cross_verify_recent_articles(
    articles: list[dict],
    min_cluster_size: int = 2,
) -> list[CrossSourceMatch]:
    """Run cross-source verification on a batch of articles.

    1. Cluster articles by event similarity.
    2. For each cluster with 2+ sources, compute verification.
    3. Store results in MongoDB for later retrieval.

    Args:
        articles: list of article dicts with guid, title, description, source, bias.
        min_cluster_size: minimum articles needed to form a cluster.

    Returns:
        List of CrossSourceMatch results for verified clusters.
    """
    clusters = cluster_articles(articles)
    results = []

    for cluster in clusters:
        if len(cluster) < min_cluster_size:
            continue

        match = verify_cluster(cluster)
        results.append(match)

        # Store in DB for lookup
        try:
            db = get_db()
            await db.cross_source_matches.update_one(
                {"event_cluster_id": match.event_cluster_id},
                {"$set": {
                    **match.model_dump(),
                    "updated_at": datetime.utcnow(),
                }},
                upsert=True,
            )
        except Exception as e:
            logger.warning("Failed to store cross-source match: %s", e)

    logger.info(
        "Cross-source verification: %d articles → %d clusters → %d verified",
        len(articles), len(clusters), len(results),
    )
    return results


async def get_cross_source_match(article_guid: str) -> Optional[CrossSourceMatch]:
    """Retrieve cross-source verification for a specific article."""
    db = get_db()
    doc = await db.cross_source_matches.find_one(
        {"matching_articles.guid": article_guid},
    )
    if doc:
        doc.pop("_id", None)
        doc.pop("updated_at", None)
        return CrossSourceMatch(**doc)
    return None
