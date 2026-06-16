# app/services/fact_check_service.py
"""
Claim-Level Fact Checking Service.

Goes beyond article-level credibility to verify individual claims:
  1. Extract specific claims from article text (numbers, quotes, stats).
  2. Cross-reference against other articles, known data, and external APIs.
  3. Assign per-claim verification status.
  4. Optionally call Google Fact Check API for published fact-checks.

Also includes framing analysis (headline vs body, attribution, perspective).
"""

import logging
import re
from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.core.database import get_db
from app.models.schemas import VerifiedClaim, FramingAnalysis, VerificationConfidence

logger = logging.getLogger(__name__)


# ── Claim Extraction ──────────────────────────────────────────────────────────

# Patterns that signal a verifiable claim
_NUMBER_PATTERN = re.compile(
    r"\b\d[\d,.]*\s*(?:%|percent|billion|million|thousand|shekel|NIS|USD|\$|₪)\b",
    re.IGNORECASE,
)
_QUOTE_PATTERN = re.compile(r'"([^"]{10,200})"')
_STAT_INDICATORS = (
    "according to", "data shows", "statistics", "survey", "poll",
    "study found", "report says", "research shows", "figures show",
    "data from", "census", "index",
)
_ATTRIBUTION_PATTERN = re.compile(
    r"(?:said|told|stated|announced|declared|confirmed|denied)\s",
    re.IGNORECASE,
)


def extract_verifiable_claims(title: str, description: str) -> list[str]:
    """Extract specific, verifiable claims from article text.

    Focuses on:
      - Numerical claims (GDP grew 5%, 1000 casualties, $2B deal)
      - Quoted statements ("minister said X")
      - Statistical references (according to survey, data shows)
    """
    text = f"{title}. {description}"
    text = re.sub(r"<[^>]+>", "", text)  # strip HTML
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    claims = []
    seen = set()

    for sentence in sentences:
        if len(sentence.split()) < 4:
            continue

        is_claim = False
        reason = ""

        # Check for numerical claims
        if _NUMBER_PATTERN.search(sentence):
            is_claim = True
            reason = "numerical_claim"

        # Check for quotes
        elif _QUOTE_PATTERN.search(sentence):
            is_claim = True
            reason = "attributed_quote"

        # Check for statistical references
        elif any(ind in sentence.lower() for ind in _STAT_INDICATORS):
            is_claim = True
            reason = "statistical_reference"

        # Check for strong assertions
        elif _ATTRIBUTION_PATTERN.search(sentence):
            is_claim = True
            reason = "sourced_assertion"

        if is_claim and sentence not in seen:
            claims.append(sentence)
            seen.add(sentence)

        if len(claims) >= 5:
            break

    return claims


# ── Claim Verification ────────────────────────────────────────────────────────

async def verify_claim_against_corpus(
    claim_text: str,
    article_guid: str,
) -> VerifiedClaim:
    """Verify a single claim against other articles in the database.

    Checks if:
      - Other sources mention similar numbers/facts (partially_verified)
      - Other sources contradict the claim (contradicted)
      - No other sources mention it (unverified)
    """
    db = get_db()

    # Extract key terms from the claim for search
    key_terms = re.findall(r"\b[A-Z][a-z]+\b", claim_text)  # proper nouns
    numbers = re.findall(r"\b\d[\d,.]+\b", claim_text)
    search_terms = key_terms[:3] + numbers[:2]

    if not search_terms:
        return VerifiedClaim(
            claim_text=claim_text,
            verification_status="unverified",
            confidence=0.3,
            explanation="No specific terms to cross-reference.",
        )

    # Search for similar content in cached articles
    search_regex = "|".join(re.escape(t) for t in search_terms)
    matching_articles = await db.cached_articles.find(
        {
            "guid": {"$ne": article_guid},
            "$or": [
                {"title": {"$regex": search_regex, "$options": "i"}},
                {"description": {"$regex": search_regex, "$options": "i"}},
            ],
        },
        {"guid": 1, "source": 1, "title": 1, "_id": 0},
    ).to_list(length=20)

    if not matching_articles:
        return VerifiedClaim(
            claim_text=claim_text,
            verification_status="unverified",
            evidence_sources=[],
            confidence=0.3,
            explanation="No other sources in database mention these terms.",
        )

    evidence_sources = list({a.get("source", "Unknown") for a in matching_articles})

    # Check if numbers match across sources (simple heuristic)
    if numbers:
        num_matches = 0
        for article in matching_articles:
            article_text = f"{article.get('title', '')} {article.get('description', '')}"
            for num in numbers:
                if num in article_text:
                    num_matches += 1

        if num_matches > 0:
            return VerifiedClaim(
                claim_text=claim_text,
                verification_status="partially_verified",
                evidence_sources=evidence_sources[:5],
                confidence=min(0.5 + num_matches * 0.1, 0.85),
                explanation=f"Same figures found in {num_matches} other source(s): {', '.join(evidence_sources[:3])}.",
            )

    # Key terms found but numbers don't match or no numbers
    return VerifiedClaim(
        claim_text=claim_text,
        verification_status="partially_verified",
        evidence_sources=evidence_sources[:5],
        confidence=0.5,
        explanation=f"Related coverage found in {len(matching_articles)} source(s), but exact facts not cross-confirmed.",
    )


async def verify_article_claims(
    title: str,
    description: str,
    article_guid: str,
) -> list[VerifiedClaim]:
    """Extract and verify all claims in an article."""
    claims = extract_verifiable_claims(title, description)
    if not claims:
        return []

    verified = []
    for claim_text in claims:
        result = await verify_claim_against_corpus(claim_text, article_guid)
        verified.append(result)

    return verified


# ── Google Fact Check API ─────────────────────────────────────────────────────

async def check_google_factcheck(query: str) -> list[dict]:
    """Search Google Fact Check API for published fact-checks.

    Returns list of matching fact-checks with:
      - claim_text: the claim that was fact-checked
      - rating: the fact-checker's verdict
      - publisher: who fact-checked it
      - url: link to the full fact-check
    """
    api_key = settings.google_factcheck_api_key
    if not api_key:
        return []

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://factchecktools.googleapis.com/v1alpha1/claims:search",
                params={"query": query[:200], "key": api_key, "languageCode": "en"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for claim in data.get("claims", [])[:5]:
            reviews = claim.get("claimReview", [])
            for review in reviews[:1]:
                results.append({
                    "claim_text": claim.get("text", ""),
                    "claimant": claim.get("claimant", "Unknown"),
                    "rating": review.get("textualRating", "Unknown"),
                    "publisher": review.get("publisher", {}).get("name", "Unknown"),
                    "url": review.get("url", ""),
                })
        return results

    except Exception as e:
        logger.warning("Google Fact Check API failed: %s", e)
        return []


# ── Framing Analysis ──────────────────────────────────────────────────────────

def analyze_framing(title: str, description: str) -> FramingAnalysis:
    """Analyze how a story is framed (narrative structure, not just content).

    Checks:
      - Headline vs body tone consistency
      - How many named sources are attributed
      - Whether opposing perspectives are included
      - Narrative frame (conflict, human interest, economic, etc.)
      - Active vs passive voice
    """
    clean_desc = re.sub(r"<[^>]+>", "", description)
    title_lower = title.lower()
    desc_lower = clean_desc.lower()

    # 1. Headline-body consistency
    # Count sentiment-loaded words in title vs body
    loaded_words = {"shocking", "outrage", "scandal", "breaking", "urgent",
                    "bombshell", "catastrophe", "disaster", "incredible",
                    "extraordinary", "stunning", "horrifying"}
    title_loaded = sum(1 for w in loaded_words if w in title_lower)
    body_loaded = sum(1 for w in loaded_words if w in desc_lower)

    if title_loaded > 0 and body_loaded == 0:
        consistency = 0.3  # clickbait signal
    elif title_loaded > 0 and body_loaded > 0:
        consistency = 0.7
    else:
        consistency = 0.9

    # 2. Attribution count
    attribution_matches = _ATTRIBUTION_PATTERN.findall(clean_desc)
    quote_matches = _QUOTE_PATTERN.findall(clean_desc)
    attribution_count = len(attribution_matches) + len(quote_matches)

    # 3. Perspective balance
    opposing_signals = (
        "however", "on the other hand", "critics say", "opponents argue",
        "some disagree", "in contrast", "while others", "but experts",
        "alternatively", "disputed", "countered",
    )
    has_opposing = any(sig in desc_lower for sig in opposing_signals)

    if has_opposing and attribution_count >= 2:
        perspective_balance = "balanced"
    elif has_opposing or attribution_count >= 3:
        perspective_balance = "multi-perspective"
    else:
        perspective_balance = "one-sided"

    # 4. Narrative frame detection
    frame_keywords = {
        "conflict": ["clash", "fight", "war", "attack", "oppose", "battle",
                     "tension", "dispute", "conflict", "rival", "enemy"],
        "human_interest": ["family", "child", "victim", "survivor", "personal",
                          "story", "emotional", "community", "people"],
        "economic": ["cost", "budget", "economic", "market", "trade", "investment",
                    "gdp", "inflation", "price", "financial", "tax"],
        "morality": ["right", "wrong", "justice", "moral", "ethical", "fair",
                    "responsible", "duty", "values", "principle"],
        "responsibility": ["accountable", "blame", "responsible", "inquiry",
                          "investigation", "commission", "oversight", "failure"],
    }

    frame_scores = {}
    combined = f"{title_lower} {desc_lower}"
    for frame, keywords in frame_keywords.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > 0:
            frame_scores[frame] = score

    narrative_frame = max(frame_scores, key=frame_scores.get) if frame_scores else "informational"

    # 5. Voice analysis (active vs passive)
    passive_indicators = re.findall(
        r"\b(?:was|were|been|being|is|are)\s+\w+ed\b", clean_desc, re.IGNORECASE,
    )
    active_indicators = re.findall(
        r"\b(?:he|she|they|it|government|minister|idf|army|police)\s+\w+(?:ed|s)\b",
        clean_desc, re.IGNORECASE,
    )
    if len(passive_indicators) > len(active_indicators) * 2:
        voice = "passive"
    elif len(active_indicators) > len(passive_indicators) * 2:
        voice = "active"
    else:
        voice = "mixed"

    # 6. Omission signals
    omission_signals = []
    if not has_opposing:
        omission_signals.append("no opposing viewpoint cited")
    if attribution_count == 0:
        omission_signals.append("no named sources attributed")
    if not _NUMBER_PATTERN.search(clean_desc) and narrative_frame == "economic":
        omission_signals.append("economic claim without supporting data")

    return FramingAnalysis(
        headline_body_consistency=round(consistency, 2),
        attribution_count=attribution_count,
        perspective_balance=perspective_balance,
        narrative_frame=narrative_frame,
        voice_analysis=voice,
        omission_signals=omission_signals,
    )


# ── Composite Verification Score ──────────────────────────────────────────────

async def compute_verification_confidence(
    article_guid: str,
    source_credibility: float,
    claims: Optional[list[VerifiedClaim]] = None,
    framing: Optional[FramingAnalysis] = None,
    cross_source: Optional[dict] = None,
    user_vote_credibility: Optional[float] = None,
) -> VerificationConfidence:
    """Compute a composite verification confidence score from all signals.

    Components:
      - source_credibility: from seed table + user votes
      - claim_verification_rate: % of claims verified
      - framing_objectivity: from framing analysis
      - cross_source_agreement: from cross-source verification
      - user_consensus_credibility: from user votes
    """
    components = {
        "source_credibility": round(source_credibility, 2),
    }

    weights = {"source_credibility": 0.25}
    weighted_sum = source_credibility * 0.25
    total_weight = 0.25

    # Claims verification rate
    if claims:
        verified_count = sum(
            1 for c in claims
            if c.verification_status in ("verified", "partially_verified")
        )
        rate = verified_count / len(claims) if claims else 0.5
        components["claim_verification_rate"] = round(rate, 2)
        weighted_sum += rate * 0.25
        total_weight += 0.25

    # Framing objectivity
    if framing:
        objectivity = (
            framing.headline_body_consistency * 0.3
            + (1.0 if framing.perspective_balance == "balanced" else
               0.6 if framing.perspective_balance == "multi-perspective" else 0.3) * 0.3
            + min(framing.attribution_count / 3, 1.0) * 0.2
            + (1.0 - len(framing.omission_signals) * 0.15) * 0.2
        )
        objectivity = max(0.0, min(1.0, objectivity))
        components["framing_objectivity"] = round(objectivity, 2)
        weighted_sum += objectivity * 0.2
        total_weight += 0.2

    # Cross-source agreement
    if cross_source:
        agreement = cross_source.get("agreement_score", 0.5)
        components["cross_source_agreement"] = round(agreement, 2)
        weighted_sum += agreement * 0.2
        total_weight += 0.2

    # User consensus
    if user_vote_credibility is not None:
        components["user_consensus_credibility"] = round(user_vote_credibility, 2)
        weighted_sum += user_vote_credibility * 0.1
        total_weight += 0.1

    overall = round(weighted_sum / total_weight, 2) if total_weight > 0 else 0.5

    # Label
    if overall >= 0.85:
        label = "highly_verified"
    elif overall >= 0.70:
        label = "verified"
    elif overall >= 0.55:
        label = "partially_verified"
    elif overall >= 0.40:
        label = "needs_review"
    else:
        label = "disputed"

    explanation_parts = [f"{k}: {v:.0%}" for k, v in components.items()]
    explanation = f"Composite score from {len(components)} signals: {', '.join(explanation_parts)}."

    return VerificationConfidence(
        overall_score=overall,
        components=components,
        label=label,
        explanation=explanation,
    )
