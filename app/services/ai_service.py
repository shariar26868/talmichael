# app/services/ai_service.py
"""
Phase 2 — AI Analysis Layer.

Provides per-article:
  - Sentiment analysis      (positive / neutral / negative)
  - Bias detection          (left / center / right / unknown)
  - Credibility scoring     (0.0 – 1.0)
  - Fact-check score        (0.0 – 1.0)
  - Hebrew summary          (2–3 sentences)
  - Key topic extraction

Uses OpenAI GPT-4o.  Falls back to rule-based analysis when
OPENAI_API_KEY is not set (free-tier / dev mode).
"""

import json
import logging
from typing import Optional

from app.core.config import settings
from app.core.cache import cache_get, cache_set, ai_analysis_key, AI_TTL
from app.models.schemas import ArticleAnalysis
from app.utils.filters import (
    ISRAELI_SOURCES, is_negative, is_opinion,
    NEGATIVE_KEYWORDS,
)

logger = logging.getLogger(__name__)

# ── Source bias seed table (rule-based baseline) ──────────────────────────────
SOURCE_BIAS_SEED: dict[str, str] = {
    "Haaretz": "left",
    "haaretz.com": "left",
    "The Jerusalem Post": "right",
    "jpost.com": "right",
    "Times of Israel": "center",
    "timesofisrael.com": "center",
    "Ynet News": "center",
    "ynetnews.com": "center",
    "i24 News": "center",
    "i24news.tv": "center",
    "Arutz Sheva": "right",
    "israelnationalnews.com": "right",
    "Israel Hayom": "right",
    "israelhayom.com": "right",
    "The Algemeiner": "right",
    "algemeiner.com": "right",
    "Kan News": "center",
    "kan.org.il": "center",
    "Channel 12 News": "center",
    "mako.co.il": "center",
    "Globes": "center",
    "globes.co.il": "center",
    "TheMarker": "left",
    "themarker.com": "left",
}

# ── Credibility seed scores ───────────────────────────────────────────────────
SOURCE_CREDIBILITY_SEED: dict[str, float] = {
    "Times of Israel": 0.85,
    "timesofisrael.com": 0.85,
    "Haaretz": 0.82,
    "haaretz.com": 0.82,
    "The Jerusalem Post": 0.80,
    "jpost.com": 0.80,
    "Kan News": 0.88,
    "kan.org.il": 0.88,
    "i24 News": 0.78,
    "i24news.tv": 0.78,
    "Ynet News": 0.75,
    "ynetnews.com": 0.75,
    "Arutz Sheva": 0.65,
    "israelnationalnews.com": 0.65,
    "Israel Hayom": 0.68,
    "israelhayom.com": 0.68,
}


# ── Rule-based fallback (no API key needed) ───────────────────────────────────

CLAIM_INDICATORS = (
    "allege", "claim", "report", "according to", "sources say", "experts say",
    "could", "might", "may", "would", "should", "plan", "expect", "suggest",
    "warn", "appear", "likely", "possibly", "told", "sources", "according",
    "claim", "said", "believe", "think", "argue", "assert", "state", "declare",
)
LOADED_LANGUAGE = (
    "radical", "extreme", "enemy", "traitor", "hero", "disaster", "catastrophe",
    "brutal", "outrage", "scandal", "shocking", "urgent", "threat", "boasts",
    "extraordinary", "remarkable", "exceptional", "stunning", "impressive",
    "shine", "excellent", "brilliant", "amazing", "beautiful",
)
ABSOLUTE_LANGUAGE = ("always", "never", "only", "all", "none", "every", "everybody", "everyone")
SUPERLATIVES = ("best", "worst", "greatest", "highest", "lowest", "most", "least", "#1", "number one")
EVALUATIVE_VERBS = ("praise", "criticize", "condemn", "celebrate", "attack", "bash", "hail", "slam")


def _split_sentences(text: str) -> list[str]:
    import re
    cleaned = re.sub(r'\s+', ' ', text.strip())
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned) if s.strip()]


def _extract_claims_and_facts(text: str) -> tuple[list[str], list[str]]:
    import re
    sentences = _split_sentences(text)
    claims = []
    facts = []

    for sentence in sentences:
        if not sentence or len(sentence.split()) < 2:
            continue
        low = sentence.lower()
        
        # Detect claims based on language patterns
        has_claim_indicator = any(k in low for k in CLAIM_INDICATORS)
        has_modal = any(w in low for w in ("could", "might", "may", "would", "should"))
        has_superlative = any(s in low for s in SUPERLATIVES)
        has_evaluative = any(v in low for v in EVALUATIVE_VERBS)
        has_question = "?" in sentence
        has_opinion_words = any(w in low for w in ("positive", "negative", "good", "bad", "best", "worst", "shine", "praise", "criticize"))
        
        is_claim = has_claim_indicator or has_modal or has_superlative or has_evaluative or has_question or has_opinion_words
        
        if is_claim:
            claims.append(sentence)
        elif len(sentence.split()) >= 4:
            facts.append(sentence)
        
        if len(claims) >= 2 and len(facts) >= 2:
            break

    # Ensure there is some distinction
    claims = claims[:3]
    facts = facts[:3]
    
    # Fallback: if no claims, extract from title/first sentence if it has opinions
    if not claims and sentences:
        first_sent = sentences[0]
        if any(w in first_sent.lower() for w in ("best", "positive", "negative", "good", "bad", "excellent", "extraordinary")):
            claims.append(first_sent)
    
    # Fallback: if no facts, extract substantive sentences
    if not facts and sentences:
        for s in sentences:
            if len(s.split()) >= 4 and not any(w in s.lower() for w in SUPERLATIVES):
                facts.append(s)
            if len(facts) >= 1:
                break
        if not facts and len(sentences) > 0:
            # Last resort: use first non-tiny sentence
            facts = [s for s in sentences if len(s.split()) >= 3][:1]
    
    return claims or [sentences[0]] if sentences else [], facts or [sentences[0]] if sentences else []


def _compute_bias_types(text: str, bias: str, sentiment: str) -> list[str]:
    types = []
    low = text.lower()
    
    if any(w in low for w in LOADED_LANGUAGE):
        types.append("loaded language")
    if any(w in low for w in ABSOLUTE_LANGUAGE):
        types.append("absolutism")
    if any(w in low for w in CLAIM_INDICATORS):
        types.append("source attribution")
    if "?" in text or any(w in low for w in ("could", "might", "may", "possible", "likely")):
        types.append("speculation")
    if bias != "unknown":
        types.append("source leaning")
    if any(v in low for v in EVALUATIVE_VERBS):
        types.append("evaluative language")
    if any(s in low for s in SUPERLATIVES):
        types.append("superlatives")
    
    # Additional framing detection
    if any(w in low for w in ("positive", "good", "best", "shine", "excellent", "extraordinary", "remarkable")):
        if "positive framing" not in types:
            types.append("positive framing")
    if any(w in low for w in ("negative", "bad", "worst", "crisis", "disaster", "collapse", "condemn")):
        if "negative framing" not in types:
            types.append("negative framing")
    
    # Fallback: detect bias from sentiment framing if no language patterns found
    if not types or len(types) == 1:
        if sentiment == "positive" and "positive framing" not in types:
            types.append("positive framing")
        elif sentiment == "negative" and "negative framing" not in types:
            types.append("negative framing")
        elif sentiment == "neutral" and not types:
            types.append("neutral framing")
    
    # Always ensure at least one type
    types = list(dict.fromkeys(types)) or ["editorial framing"]
    return types[:5]  # cap at 5 types


def _compute_bias_score(bias: str, bias_types: list[str]) -> float:
    score = 0.05
    if bias == "center":
        score += 0.15
    elif bias in ("left", "right"):
        score += 0.35
    else:
        score += 0.05

    if "loaded language" in bias_types:
        score += 0.2
    if "absolutism" in bias_types:
        score += 0.1
    if "source attribution" in bias_types:
        score += 0.05
    if "speculation" in bias_types:
        score += 0.1
    if "evaluative language" in bias_types:
        score += 0.15
    if "superlatives" in bias_types:
        score += 0.12
    if "positive framing" in bias_types:
        score += 0.08
    if "negative framing" in bias_types:
        score += 0.08

    return round(min(score, 0.98), 2)


def _derive_bias_category(bias: str, bias_types: list[str]) -> str:
    # 1. Speculative Reporting: has speculation signal
    if "speculation" in bias_types:
        return "Speculative Reporting"
        
    # 2. Ad Hominem Attack / Loaded Language
    if "loaded language" in bias_types:
        # If highly negative/aggressive evaluative language, classify as Ad Hominem or Loaded Language
        if "negative framing" in bias_types and "evaluative language" in bias_types:
            return "Ad Hominem Attack"
        return "Loaded Language"
        
    # 3. Sensationalism: superlatives or heavy evaluative framing
    if "superlatives" in bias_types or "evaluative language" in bias_types:
        return "Sensationalism"
        
    # 4. Partisan Framing: strongly left/right lean with positive/negative/loaded language framing
    if bias in ("left", "right") and ("positive framing" in bias_types or "negative framing" in bias_types):
        return "Partisan Framing"
        
    # 5. Cherry-picking: if we have source attribution signals but also loaded language/framing
    if "source attribution" in bias_types and ("positive framing" in bias_types or "negative framing" in bias_types):
        return "Cherry-picking"
        
    # 6. Unsubstantiated Claims: claims but minimal attribution (rule-based heuristic)
    if "absolutism" in bias_types and "source attribution" not in bias_types:
        return "Unsubstantiated Claims"
        
    # 7. Context Omission: minimal detail / unknown leaning with short text/opinion markers
    if "editorial framing" in bias_types and bias == "unknown":
        return "Context Omission"
        
    # 8. Emotional Appeal: framing loaded with emotions
    if "positive framing" in bias_types or "negative framing" in bias_types:
        return "Emotional Appeal"
        
    # 9. Source Bias: basic source leaning (left or right only)
    if bias in ("left", "right"):
        return "Source Bias"
        
    # 10. Objective Reporting: center bias, unknown, or neutral framing
    if bias in ("center", "unknown") or "neutral framing" in bias_types:
        return "Objective Reporting"
        
    return "Objective Reporting"


def _bias_score_explanation(bias: str, bias_types: list[str]) -> str:
    parts = [f"source lean = {bias}"] if bias != "unknown" else ["source lean unknown"]
    if bias_types:
        parts.append(f"language/frame signals = {', '.join(bias_types)}")
    return (
        "Bias score is calculated from source leaning and editorial signals. "
        f"It reflects how strongly the article frames the story through {', '.join(bias_types)} and source perspective. "
        "Lower values mean less apparent bias; higher values mean more pronounced bias signals."
    )


def _credibility_label(score: float) -> str:
    if score >= 0.8:
        return "verified"
    if score >= 0.65:
        return "likely credible"
    if score >= 0.45:
        return "needs review"
    return "unverified"


def _rule_based_analysis(
    title: str,
    description: str,
    source: Optional[str],
    source_url: Optional[str],
) -> ArticleAnalysis:
    """
    Fast, zero-cost analysis using keyword rules and seed tables.
    Used when OpenAI key is absent or for free-tier users.
    """
    import re
    # Strip HTML tags from description before analysis
    clean_desc = re.sub(r'<[^>]+>', '', description)
    text = f"{title} {clean_desc}".lower()

    # Sentiment
    neg_hits = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)
    pos_keywords = (
        "success", "achievement", "breakthrough", "award", "peace",
        "growth", "innovation", "record", "victory", "celebrate",
        "improve", "advance", "launch", "discover", "win", "positive",
        "happiness", "happy", "shine", "best", "top", "rank", "pride",
        "hope", "progress", "develop", "thrive", "boom", "rise",
        "yes", "approve", "support", "agree", "extraordinary", "boast",
    )
    pos_hits = sum(1 for kw in pos_keywords if kw in text)

    if neg_hits > pos_hits:
        sentiment = "negative"
    elif pos_hits > 0:
        sentiment = "positive"
    else:
        sentiment = "neutral"

    # Bias
    bias = "unknown"
    for name in [source, source_url]:
        if not name:
            continue
        # exact match
        if name in SOURCE_BIAS_SEED:
            bias = SOURCE_BIAS_SEED[name]
            break
        # partial match — handles "The Times of Israel" vs "Times of Israel"
        for seed_name, seed_bias in SOURCE_BIAS_SEED.items():
            if seed_name.lower() in name.lower() or name.lower() in seed_name.lower():
                bias = seed_bias
                break
        if bias != "unknown":
            break

    # Credibility
    credibility = 0.5
    for name in [source, source_url]:
        if not name:
            continue
        if name in SOURCE_CREDIBILITY_SEED:
            credibility = SOURCE_CREDIBILITY_SEED[name]
            break
        for seed_name, seed_score in SOURCE_CREDIBILITY_SEED.items():
            if seed_name.lower() in name.lower() or name.lower() in seed_name.lower():
                credibility = seed_score
                break
        if credibility != 0.5:
            break

    # Fact-check score — rule-based proxy
    fact_check = round(credibility * (0.9 if sentiment != "negative" else 0.7), 2)

    # Topics — simple keyword extraction
    topic_map = {
        "economy": ["economy", "finance", "market", "gdp", "inflation", "shekel"],
        "security": ["security", "military", "idf", "defense", "terror", "attack"],
        "politics": ["knesset", "government", "minister", "election", "coalition"],
        "education": ["school", "university", "student", "education", "teacher"],
        "health": ["hospital", "health", "vaccine", "covid", "medical", "doctor"],
        "technology": ["tech", "startup", "innovation", "ai", "cyber", "software"],
        "environment": ["climate", "environment", "energy", "solar", "water"],
        "culture": ["culture", "art", "music", "film", "festival", "heritage"],
    }
    topics = [topic for topic, kws in topic_map.items() if any(kw in text for kw in kws)]

    claims, facts = _extract_claims_and_facts(f"{title}. {clean_desc}")
    bias_types = _compute_bias_types(text, bias, sentiment)
    bias_score = _compute_bias_score(bias, bias_types)
    bias_category = _derive_bias_category(bias, bias_types)
    bias_score_explanation = _bias_score_explanation(bias, bias_types)
    claim_explanation = (
        "Claims are statements that present assertions, source attributions, or speculative language. "
        "Facts are objective statements and reported events that can be verified independently."
    )
    bias_explanation = (
        f"This article shows a {bias} lean and uses {', '.join(bias_types)}. "
        "Bias is detected from the source perspective and from the language choices that frame the event."
    )
    credibility_label = _credibility_label(credibility)

    clean_title = re.sub(r'\s*-\s*[^-]+$', '', title).strip()
    summary_hebrew = f"[סיכום אוטומטי] {clean_title[:120]}"

    return ArticleAnalysis(
        guid="",  # filled by caller
        sentiment=sentiment,
        bias=bias,
        bias_score=bias_score,
        bias_types=bias_types,
        bias_category=bias_category,
        credibility_score=round(credibility, 2),
        credibility_label=credibility_label,
        fact_check_score=fact_check,
        summary_hebrew=summary_hebrew,
        topics=topics or ["general"],
        claims=claims,
        factual_points=facts,
        claim_explanation=claim_explanation,
        bias_explanation=bias_explanation,
    )


# ── OpenAI-powered analysis ───────────────────────────────────────────────────

_SYSTEM_PROMPT = """
You are an expert Israeli news analyst. Analyze the given article and return a JSON object with:
- sentiment: "positive" | "neutral" | "negative"
- bias: "left" | "center" | "right" | "unknown"
- bias_types: list of strings describing bias style, e.g. ["loaded language", "source leaning", "framing"]
- bias_category: short descriptive category for the article's bias style. MUST be exactly one of: "Sensationalism", "Loaded Language", "Cherry-picking", "Speculative Reporting", "Partisan Framing", "False Equivalence", "Ad Hominem Attack", "Context Omission", "Emotional Appeal", "Unsubstantiated Claims", "Source Bias", "Objective Reporting"
- bias_score: float 0.0-1.0 (how strongly biased the article appears)
- bias_score_explanation: short text explaining how the bias score was calculated
- credibility_score: float 0.0-1.0 (based on source reputation and factual language)
- credibility_label: string (e.g. "verified", "likely credible", "needs review", "unverified")
- fact_check_score: float 0.0-1.0 (how verifiable the claims appear)
- claims: list of key assertions or statements that should be treated as claims
- factual_points: list of objective statements or facts mentioned in the article
- claim_explanation: short text explaining why these are claims vs facts
- bias_explanation: short text explaining why this article is biased or not
- summary_hebrew: 2-3 sentence summary in Hebrew
- topics: list of up to 5 relevant topic tags in English (e.g. ["economy", "politics"])

Important: always return non-empty arrays for bias_types, claims, and factual_points. If the article has no clearly labeled claims, return the headline or a short summary sentence as a fallback claim, and use the main article assertion as a factual_point.

Respond ONLY with valid JSON. No markdown, no explanation.
"""


async def _openai_analysis(
    title: str,
    description: str,
    source: Optional[str],
) -> Optional[dict]:
    """Call OpenAI GPT-4o for deep analysis. Returns raw dict or None on failure."""
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        user_content = (
            f"Source: {source or 'Unknown'}\n"
            f"Title: {title}\n"
            f"Description: {description[:500]}"
        )

        response = await client.chat.completions.create(
            model="gpt-4o-mini",   # cost-efficient; swap to gpt-4o for higher quality
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=400,
            response_format={"type": "json_object"},
        )

        return json.loads(response.choices[0].message.content)

    except Exception as e:
        logger.warning("OpenAI analysis failed: %s", e)
        return None


# ── Public API ────────────────────────────────────────────────────────────────

async def analyze_article(
    guid: str,
    title: str,
    description: str,
    source: Optional[str] = None,
    source_url: Optional[str] = None,
    use_ai: bool = False,       # True only for paid users
) -> ArticleAnalysis:
    """
    Analyze a single article.

    Args:
        guid:        Unique article identifier (used as cache key).
        title:       Article headline.
        description: Article snippet/description.
        source:      Source outlet name.
        source_url:  Source outlet URL.
        use_ai:      When True and OPENAI_API_KEY is set, uses GPT-4o.
                     Otherwise falls back to rule-based analysis.
    """
    # Cache check
    cache_key = ai_analysis_key(guid)
    cached = await cache_get(cache_key)
    if cached:
        return ArticleAnalysis(**cached)

    result: Optional[ArticleAnalysis] = None

    # AI path (paid users + API key present)
    if use_ai and settings.openai_api_key:
        raw = await _openai_analysis(title, description, source)
        if raw:
            try:
                result = ArticleAnalysis(
                    guid=guid,
                    sentiment=raw.get("sentiment", "neutral"),
                    bias=raw.get("bias", "unknown"),
                    bias_score=float(raw.get("bias_score", 0.5)),
                    bias_types=raw.get("bias_types", []),
                    credibility_score=float(raw.get("credibility_score", 0.5)),
                    credibility_label=raw.get("credibility_label", "needs review"),
                    fact_check_score=float(raw.get("fact_check_score", 0.5)),
                    summary_hebrew=raw.get("summary_hebrew", ""),
                    topics=raw.get("topics", ["general"]),
                    claims=raw.get("claims", []),
                    factual_points=raw.get("factual_points", []),
                    bias_category=raw.get("bias_category", ""),
                    claim_explanation=raw.get("claim_explanation", ""),
                    bias_explanation=raw.get("bias_explanation", ""),
                    bias_score_explanation=raw.get("bias_score_explanation", ""),
                )
                # If OpenAI returns empty arrays for key extraction fields, merge rule-based fallback
                if not result.bias_types or not result.claims or not result.factual_points or not result.bias_category:
                    fallback = _rule_based_analysis(title, description, source, source_url)
                    if not result.bias_types:
                        result.bias_types = fallback.bias_types
                    if not result.claims:
                        result.claims = fallback.claims
                    if not result.factual_points:
                        result.factual_points = fallback.factual_points
                    if not result.claim_explanation:
                        result.claim_explanation = fallback.claim_explanation
                    if not result.bias_explanation:
                        result.bias_explanation = fallback.bias_explanation
                    if not result.bias_category:
                        result.bias_category = fallback.bias_category
            except Exception as e:
                logger.warning("Failed to parse OpenAI response: %s", e)

    # Rule-based fallback
    if result is None:
        result = _rule_based_analysis(title, description, source, source_url)
        result.guid = guid

    # Cache result
    await cache_set(cache_key, result.model_dump(), AI_TTL)
    return result


async def analyze_batch(
    articles: list[dict],
    use_ai: bool = False,
) -> list[ArticleAnalysis]:
    """
    Analyze a list of articles concurrently.
    Each dict must have: guid, title, description, source (optional), source_url (optional).
    """
    import asyncio
    tasks = [
        analyze_article(
            guid=a.get("guid", ""),
            title=a.get("title", ""),
            description=a.get("description", ""),
            source=a.get("source"),
            source_url=a.get("source_url"),
            use_ai=use_ai,
        )
        for a in articles
    ]
    return await asyncio.gather(*tasks)


async def get_source_bias(source_name: str, source_url: Optional[str] = None) -> dict:
    """Return bias and credibility info for a given source."""
    bias = SOURCE_BIAS_SEED.get(source_name) or SOURCE_BIAS_SEED.get(source_url or "") or "unknown"
    credibility = (
        SOURCE_CREDIBILITY_SEED.get(source_name)
        or SOURCE_CREDIBILITY_SEED.get(source_url or "")
        or 0.5
    )
    return {
        "source_name": source_name,
        "bias": bias,
        "credibility_score": credibility,
        "bias_label": {"left": "⬅️ Left", "center": "⚖️ Center", "right": "➡️ Right"}.get(bias, "❓ Unknown"),
    }
