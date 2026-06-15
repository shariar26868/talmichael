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

For platinum tier, the ensemble is designed to support OpenAI + Gemini + Claude.
Claude support is reserved for later integration.
"""

import asyncio
import json
import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.core.cache import cache_get, cache_set, ai_analysis_key, AI_TTL
from app.models.schemas import ArticleAnalysis
from app.utils.filters import (
    ISRAELI_SOURCES, is_negative, is_opinion,
    NEGATIVE_KEYWORDS,
)

logger = logging.getLogger(__name__)

# ── Source bias seed table (rule-based baseline) ──────────────────────────────
# 100+ sources: both display-name and domain-key for robust matching.
SOURCE_BIAS_SEED: dict[str, str] = {
    # ── Israeli Sources (30) ──────────────────────────────────────────────
    "Haaretz": "left",
    "Haaretz English": "left",
    "haaretz.com": "left",
    "Times of Israel": "center",
    "timesofisrael.com": "center",
    "Jerusalem Post": "center-right",
    "The Jerusalem Post": "center-right",
    "jpost.com": "center-right",
    "Ynet News": "center",
    "Ynet Hebrew": "center",
    "ynetnews.com": "center",
    "ynet.co.il": "center",
    "Kan News": "center",
    "kan.org.il": "center",
    "Israel Hayom": "right",
    "Israel Hayom Hebrew": "right",
    "israelhayom.com": "right",
    "israelhayom.co.il": "right",
    "Arutz Sheva": "right",
    "israelnationalnews.com": "right",
    "Channel 12 (Mako)": "center",
    "mako.co.il": "center",
    "Channel 13 (Reshet)": "center",
    "13tv.co.il": "center",
    "i24 News": "center",
    "i24news.tv": "center",
    "Walla News": "center",
    "walla.co.il": "center",
    "Maariv": "center-right",
    "maariv.co.il": "center-right",
    "Nrg (Maariv Online)": "center-right",
    "nrg.co.il": "center-right",
    "Globes": "center",
    "globes.co.il": "center",
    "TheMarker": "center-left",
    "themarker.com": "center-left",
    "CTech (Calcalist)": "center",
    "calcalistech.com": "center",
    "Calcalist": "center",
    "calcalist.co.il": "center",
    "Geektime": "center",
    "geektime.co.il": "center",
    "The Algemeiner": "right",
    "algemeiner.com": "right",
    "Jewish Press": "right",
    "jewishpress.com": "right",
    "Sport5": "center",
    "sport5.co.il": "center",
    "One (Sport)": "center",
    "one.co.il": "center",
    "Israel Democracy Institute": "center",
    "+972 Magazine": "left",
    "972mag.com": "left",
    "Local Call (Sikha Mekomit)": "left",
    "local-call.com": "left",
    "Israel Policy Forum": "center-left",
    "israelpolicyforum.org": "center-left",

    # ── International: Wire Agencies ──────────────────────────────────────
    "Reuters": "center",
    "reuters.com": "center",
    "Associated Press": "center",
    "apnews.com": "center",
    "AFP (Agence France-Presse)": "center",

    # ── International: BBC ────────────────────────────────────────────────
    "BBC News": "center",
    "BBC World": "center",
    "BBC Middle East": "center",
    "bbc.com": "center",

    # ── International: US ─────────────────────────────────────────────────
    "CNN World": "center-left",
    "CNN Middle East": "center-left",
    "cnn.com": "center-left",
    "NPR News": "center-left",
    "NPR World": "center-left",
    "npr.org": "center-left",
    "New York Times World": "center-left",
    "New York Times Middle East": "center-left",
    "nytimes.com": "center-left",
    "Washington Post World": "center-left",
    "washingtonpost.com": "center-left",
    "Wall Street Journal World": "center-right",
    "wsj.com": "center-right",
    "PBS NewsHour": "center",
    "pbs.org": "center",
    "Axios": "center",
    "axios.com": "center",
    "The Atlantic": "center-left",
    "theatlantic.com": "center-left",
    "Foreign Policy": "center",
    "foreignpolicy.com": "center",
    "Foreign Affairs": "center",
    "foreignaffairs.com": "center",

    # ── International: UK ─────────────────────────────────────────────────
    "The Guardian World": "center-left",
    "The Guardian Middle East": "center-left",
    "theguardian.com": "center-left",
    "The Telegraph World": "center-right",
    "telegraph.co.uk": "center-right",
    "The Independent": "center-left",
    "independent.co.uk": "center-left",
    "Financial Times": "center",
    "ft.com": "center",
    "The Economist": "center",
    "economist.com": "center",
    "Sky News": "center",
    "skynews.com": "center",

    # ── International: Europe ─────────────────────────────────────────────
    "Euronews": "center",
    "euronews.com": "center",
    "Deutsche Welle (DW)": "center",
    "dw.com": "center",
    "France24 English": "center",
    "France24 Middle East": "center",
    "france24.com": "center",
    "The Local (Sweden)": "center",
    "POLITICO Europe": "center",
    "politico.eu": "center",
    "Irish Times World": "center",
    "irishtimes.com": "center",

    # ── International: Asia-Pacific / Americas ────────────────────────────
    "The Straits Times": "center",
    "straitstimes.com": "center",
    "South China Morning Post": "center",
    "scmp.com": "center",
    "NHK World Japan": "center",
    "Globe and Mail (Canada)": "center",
    "theglobeandmail.com": "center",
    "Sydney Morning Herald": "center",
    "smh.com.au": "center",

    # ── Arabic & Regional Sources ─────────────────────────────────────────
    "Al Jazeera English": "center-left",
    "Al Jazeera Arabic": "center-left",
    "aljazeera.com": "center-left",
    "aljazeera.net": "center-left",
    "BBC Arabic": "center",
    "Al Arabiya English": "center-right",
    "Al Arabiya Arabic": "center-right",
    "alarabiya.net": "center-right",
    "Sky News Arabia": "center-right",
    "skynewsarabia.com": "center-right",
    "Arab News": "center-right",
    "arabnews.com": "center-right",
    "Middle East Eye": "center-left",
    "middleeasteye.net": "center-left",
    "Middle East Monitor": "left",
    "middleeastmonitor.com": "left",
    "WAFA (Palestinian News Agency)": "left",
    "Ma'an News": "center-left",
    "Palestine Chronicle": "left",
    "Gulf News": "center-right",
    "gulfnews.com": "center-right",
    "Khaleej Times": "center",
    "khaleejtimes.com": "center",
    "The National (UAE)": "center-right",
    "thenationalnews.com": "center-right",
    "Saudi Gazette": "center-right",
    "Ahram Online": "center",
    "Egypt Independent": "center",
    "Daily News Egypt": "center",
    "Roya News (Jordan)": "center",
    "Jordan Times": "center",
    "jordantimes.com": "center",
    "Daily Star (Lebanon)": "center",
    "L'Orient Today (Lebanon)": "center",
    "Naharnet (Lebanon)": "center",
    "Anadolu Agency": "center-right",
    "aa.com.tr": "center-right",
    "TRT World": "center-right",
    "trtworld.com": "center-right",
    "Daily Sabah": "right",
    "dailysabah.com": "right",
    "Hürriyet Daily News": "center",
    "hurriyetdailynews.com": "center",
    "Morocco World News": "center",
    "The North Africa Journal": "center",
}

# ── Credibility seed scores ───────────────────────────────────────────────────
# 100+ sources: 0.0–1.0 scale based on editorial standards, fact-check record,
# independence, and media-bias-fact-check.com ratings.
SOURCE_CREDIBILITY_SEED: dict[str, float] = {
    # ── Israeli Sources ───────────────────────────────────────────────────
    "Haaretz": 0.85,                    "haaretz.com": 0.85,
    "Haaretz English": 0.85,
    "Times of Israel": 0.82,            "timesofisrael.com": 0.82,
    "Jerusalem Post": 0.78,             "jpost.com": 0.78,
    "The Jerusalem Post": 0.78,
    "Ynet News": 0.75,                  "ynetnews.com": 0.75,
    "Ynet Hebrew": 0.75,                "ynet.co.il": 0.75,
    "Kan News": 0.88,                   "kan.org.il": 0.88,
    "Israel Hayom": 0.68,               "israelhayom.com": 0.68,
    "Israel Hayom Hebrew": 0.68,        "israelhayom.co.il": 0.68,
    "Arutz Sheva": 0.62,                "israelnationalnews.com": 0.62,
    "Channel 12 (Mako)": 0.82,          "mako.co.il": 0.82,
    "Channel 13 (Reshet)": 0.80,        "13tv.co.il": 0.80,
    "i24 News": 0.78,                   "i24news.tv": 0.78,
    "Walla News": 0.74,                 "walla.co.il": 0.74,
    "Maariv": 0.72,                     "maariv.co.il": 0.72,
    "Nrg (Maariv Online)": 0.70,        "nrg.co.il": 0.70,
    "Globes": 0.80,                     "globes.co.il": 0.80,
    "TheMarker": 0.82,                  "themarker.com": 0.82,
    "CTech (Calcalist)": 0.78,          "calcalistech.com": 0.78,
    "Calcalist": 0.78,                  "calcalist.co.il": 0.78,
    "Geektime": 0.72,                   "geektime.co.il": 0.72,
    "The Algemeiner": 0.65,             "algemeiner.com": 0.65,
    "Jewish Press": 0.60,               "jewishpress.com": 0.60,
    "Sport5": 0.72,                     "sport5.co.il": 0.72,
    "One (Sport)": 0.70,                "one.co.il": 0.70,
    "Israel Democracy Institute": 0.92,
    "+972 Magazine": 0.70,              "972mag.com": 0.70,
    "Local Call (Sikha Mekomit)": 0.68,  "local-call.com": 0.68,
    "Israel Policy Forum": 0.82,        "israelpolicyforum.org": 0.82,

    # ── Wire Agencies (highest credibility) ───────────────────────────────
    "Reuters": 0.95,                    "reuters.com": 0.95,
    "Associated Press": 0.95,           "apnews.com": 0.95,
    "AFP (Agence France-Presse)": 0.90,

    # ── BBC ───────────────────────────────────────────────────────────────
    "BBC News": 0.90,                   "bbc.com": 0.90,
    "BBC World": 0.90,
    "BBC Middle East": 0.90,

    # ── US Sources ────────────────────────────────────────────────────────
    "CNN World": 0.78,                  "cnn.com": 0.78,
    "CNN Middle East": 0.78,
    "NPR News": 0.85,                  "npr.org": 0.85,
    "NPR World": 0.85,
    "New York Times World": 0.88,       "nytimes.com": 0.88,
    "New York Times Middle East": 0.88,
    "Washington Post World": 0.86,      "washingtonpost.com": 0.86,
    "Wall Street Journal World": 0.88,  "wsj.com": 0.88,
    "PBS NewsHour": 0.88,              "pbs.org": 0.88,
    "Axios": 0.82,                     "axios.com": 0.82,
    "The Atlantic": 0.84,              "theatlantic.com": 0.84,
    "Foreign Policy": 0.88,            "foreignpolicy.com": 0.88,
    "Foreign Affairs": 0.92,           "foreignaffairs.com": 0.92,

    # ── UK Sources ────────────────────────────────────────────────────────
    "The Guardian World": 0.82,         "theguardian.com": 0.82,
    "The Guardian Middle East": 0.82,
    "The Telegraph World": 0.78,        "telegraph.co.uk": 0.78,
    "The Independent": 0.76,            "independent.co.uk": 0.76,
    "Financial Times": 0.90,            "ft.com": 0.90,
    "The Economist": 0.90,             "economist.com": 0.90,
    "Sky News": 0.78,                  "skynews.com": 0.78,

    # ── Europe ────────────────────────────────────────────────────────────
    "Euronews": 0.78,                  "euronews.com": 0.78,
    "Deutsche Welle (DW)": 0.85,       "dw.com": 0.85,
    "France24 English": 0.82,          "france24.com": 0.82,
    "France24 Middle East": 0.82,
    "The Local (Sweden)": 0.72,
    "POLITICO Europe": 0.84,           "politico.eu": 0.84,
    "Irish Times World": 0.80,         "irishtimes.com": 0.80,

    # ── Asia-Pacific / Americas ───────────────────────────────────────────
    "The Straits Times": 0.80,         "straitstimes.com": 0.80,
    "South China Morning Post": 0.78,  "scmp.com": 0.78,
    "NHK World Japan": 0.85,
    "Globe and Mail (Canada)": 0.82,   "theglobeandmail.com": 0.82,
    "Sydney Morning Herald": 0.80,     "smh.com.au": 0.80,

    # ── Arabic & Regional Sources ─────────────────────────────────────────
    "Al Jazeera English": 0.75,        "aljazeera.com": 0.75,
    "Al Jazeera Arabic": 0.72,         "aljazeera.net": 0.72,
    "BBC Arabic": 0.88,
    "Al Arabiya English": 0.74,        "alarabiya.net": 0.72,
    "Al Arabiya Arabic": 0.72,
    "Sky News Arabia": 0.72,           "skynewsarabia.com": 0.72,
    "Arab News": 0.72,                 "arabnews.com": 0.72,
    "Middle East Eye": 0.72,           "middleeasteye.net": 0.72,
    "Middle East Monitor": 0.65,       "middleeastmonitor.com": 0.65,
    "WAFA (Palestinian News Agency)": 0.55,
    "Ma'an News": 0.60,
    "Palestine Chronicle": 0.55,
    "Gulf News": 0.72,                 "gulfnews.com": 0.72,
    "Khaleej Times": 0.72,            "khaleejtimes.com": 0.72,
    "The National (UAE)": 0.75,        "thenationalnews.com": 0.75,
    "Saudi Gazette": 0.65,
    "Ahram Online": 0.70,
    "Egypt Independent": 0.68,
    "Daily News Egypt": 0.65,
    "Roya News (Jordan)": 0.70,
    "Jordan Times": 0.72,             "jordantimes.com": 0.72,
    "Daily Star (Lebanon)": 0.68,
    "L'Orient Today (Lebanon)": 0.75,
    "Naharnet (Lebanon)": 0.65,
    "Anadolu Agency": 0.68,            "aa.com.tr": 0.68,
    "TRT World": 0.68,                "trtworld.com": 0.68,
    "Daily Sabah": 0.60,              "dailysabah.com": 0.60,
    "Hürriyet Daily News": 0.70,      "hurriyetdailynews.com": 0.70,
    "Morocco World News": 0.65,
    "The North Africa Journal": 0.60,
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


async def _perplexity_analysis(
    title: str,
    description: str,
    source: Optional[str],
) -> Optional[dict]:
    """Call Perplexity for article analysis and return a parsed JSON object."""
    if not settings.perplexity_api_key:
        return None

    try:
        user_content = (
            f"Source: {source or 'Unknown'}\n"
            f"Title: {title}\n"
            f"Description: {description[:1000]}"
        )
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={"Authorization": f"Bearer {settings.perplexity_api_key}"},
                json={
                    "model": "pplx-7b-online",
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 800,
                },
            )
            resp.raise_for_status()
            payload = resp.json()

        content = None
        if isinstance(payload, dict):
            choices = payload.get("choices") or []
            if choices:
                message = choices[0].get("message") or {}
                content = message.get("content") or choices[0].get("text")
            elif payload.get("content"):
                content = payload.get("content")
            elif payload.get("answer"):
                content = payload.get("answer")

        if not content:
            return None

        if isinstance(content, str):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                import re
                match = re.search(r"\{.*\}", content, re.S)
                if match:
                    return json.loads(match.group(0))
        elif isinstance(content, dict):
            return content
    except Exception as e:
        logger.warning("Perplexity analysis failed: %s", e)

    return None


async def _gemini_analysis(
    title: str,
    description: str,
    source: Optional[str],
) -> Optional[dict]:
    """Call Gemini for article analysis and return a parsed JSON object."""
    if not settings.gemini_api_key:
        return None

    try:
        user_content = (
            f"Source: {source or 'Unknown'}\n"
            f"Title: {title}\n"
            f"Description: {description[:1000]}"
        )
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.gemini.ai/v1/generate",
                headers={
                    "Authorization": f"Bearer {settings.gemini_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gemini-1",
                    "prompt": user_content,
                    "max_output_tokens": 800,
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
            payload = resp.json()

        content = None
        if isinstance(payload, dict):
            # Support multiple response shapes
            content = payload.get("output") or payload.get("completion") or payload.get("response") or payload.get("answer")

        if not content:
            return None

        if isinstance(content, str):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                import re
                match = re.search(r"\{.*\}", content, re.S)
                if match:
                    return json.loads(match.group(0))
        elif isinstance(content, dict):
            return content
    except Exception as e:
        logger.warning("Gemini analysis failed: %s", e)

    return None


async def _claude_analysis(
    title: str,
    description: str,
    source: Optional[str],
) -> Optional[dict]:
    """Placeholder for future Claude analysis integration."""
    if not settings.claude_api_key:
        return None

    logger.debug("Claude analysis requested, but Claude integration is not yet implemented.")
    return None


def _merge_analysis(results: list[ArticleAnalysis], guid: str) -> ArticleAnalysis:
    """Aggregate multiple ArticleAnalysis results into a single consensus output."""
    if not results:
        raise ValueError("No analysis results to merge")

    primary = results[0]
    numeric_fields = ["bias_score", "credibility_score", "fact_check_score"]
    averages = {}
    for field in numeric_fields:
        values = [getattr(r, field) for r in results if getattr(r, field, None) is not None]
        averages[field] = round(sum(values) / len(values), 2) if values else getattr(primary, field)

    bias_votes = {}
    category_votes = {}
    label_votes = {}
    for result in results:
        bias_votes[result.bias] = bias_votes.get(result.bias, 0) + 1
        category_votes[result.bias_category] = category_votes.get(result.bias_category, 0) + 1
        label_votes[result.credibility_label] = label_votes.get(result.credibility_label, 0) + 1

    bias = max(bias_votes, key=bias_votes.get)
    bias_category = max(category_votes, key=category_votes.get)
    credibility_label = max(label_votes, key=label_votes.get)

    merged_types = []
    merged_topics = []
    merged_claims = []
    merged_facts = []
    for result in results:
        for value, target, limit in [
            (result.bias_types, merged_types, 5),
            (result.topics, merged_topics, 5),
            (result.claims, merged_claims, 5),
            (result.factual_points, merged_facts, 5),
        ]:
            for item in value:
                if item not in target and len(target) < limit:
                    target.append(item)

    explanations = [r.bias_explanation for r in results if r.bias_explanation]
    claim_explanations = [r.claim_explanation for r in results if r.claim_explanation]
    summaries = [r.summary_hebrew for r in results if r.summary_hebrew]

    result = ArticleAnalysis(
        guid=guid,
        sentiment=primary.sentiment,
        bias=bias,
        bias_score=averages["bias_score"],
        bias_types=merged_types or primary.bias_types,
        bias_category=bias_category,
        credibility_score=averages["credibility_score"],
        credibility_label=credibility_label,
        fact_check_score=averages["fact_check_score"],
        summary_hebrew=summaries[0] if summaries else primary.summary_hebrew,
        topics=merged_topics or primary.topics,
        claims=merged_claims or primary.claims,
        factual_points=merged_facts or primary.factual_points,
        claim_explanation=claim_explanations[0] if claim_explanations else primary.claim_explanation,
        bias_explanation=explanations[0] if explanations else primary.bias_explanation,
    )
    return result


# ── Public API ────────────────────────────────────────────────────────────────

async def analyze_article(
    guid: str,
    title: str,
    description: str,
    source: Optional[str] = None,
    source_url: Optional[str] = None,
    user_tier: str = "free",
) -> ArticleAnalysis:
    """
    Analyze a single article using a tiered model strategy.

        Tiers:
            - free: rule-based only
            - pro: GPT-4o-mini with rule-based fallback
            - platinum: GPT-4o-mini + Perplexity + Gemini + rule-based fallback
    """
    cache_key = ai_analysis_key(guid)
    cached = await cache_get(cache_key)
    if cached:
        return ArticleAnalysis(**cached)

    tier = (user_tier or "free").strip().lower()
    result: Optional[ArticleAnalysis] = None

    if tier == "free":
        result = _rule_based_analysis(title, description, source, source_url)
        result.guid = guid

    elif tier == "pro":
        if settings.openai_api_key:
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
                except Exception as e:
                    logger.warning("Failed to parse OpenAI response: %s", e)

        if result is None:
            result = _rule_based_analysis(title, description, source, source_url)
            result.guid = guid

    elif tier == "platinum":
        tasks = []
        if settings.openai_api_key:
            tasks.append(_openai_analysis(title, description, source))
        if settings.perplexity_api_key:
            tasks.append(_perplexity_analysis(title, description, source))
        if settings.gemini_api_key:
            tasks.append(_gemini_analysis(title, description, source))
        if settings.claude_api_key:
            tasks.append(_claude_analysis(title, description, source))

        responses = await asyncio.gather(*tasks, return_exceptions=True) if tasks else []
        analyses: list[ArticleAnalysis] = []

        for response in responses:
            if isinstance(response, Exception) or response is None:
                continue
            if isinstance(response, dict):
                try:
                    analysis = ArticleAnalysis(
                        guid=guid,
                        sentiment=response.get("sentiment", "neutral"),
                        bias=response.get("bias", "unknown"),
                        bias_score=float(response.get("bias_score", 0.5)),
                        bias_types=response.get("bias_types", []),
                        credibility_score=float(response.get("credibility_score", 0.5)),
                        credibility_label=response.get("credibility_label", "needs review"),
                        fact_check_score=float(response.get("fact_check_score", 0.5)),
                        summary_hebrew=response.get("summary_hebrew", ""),
                        topics=response.get("topics", ["general"]),
                        claims=response.get("claims", []),
                        factual_points=response.get("factual_points", []),
                        bias_category=response.get("bias_category", ""),
                        claim_explanation=response.get("claim_explanation", ""),
                        bias_explanation=response.get("bias_explanation", ""),
                    )
                    analyses.append(analysis)
                except Exception as e:
                    logger.warning("Failed to parse ensemble response: %s", e)

        if analyses:
            result = _merge_analysis(analyses, guid)
        else:
            result = _rule_based_analysis(title, description, source, source_url)
            result.guid = guid

    else:
        result = _rule_based_analysis(title, description, source, source_url)
        result.guid = guid

    await cache_set(cache_key, result.model_dump(), AI_TTL)
    return result


async def analyze_batch(
    articles: list[dict],
    user_tier: str = "free",
) -> list[ArticleAnalysis]:
    """
    Analyze a list of articles concurrently.
    Each dict must have: guid, title, description, source (optional), source_url (optional).
    """
    tasks = [
        analyze_article(
            guid=a.get("guid", ""),
            title=a.get("title", ""),
            description=a.get("description", ""),
            source=a.get("source"),
            source_url=a.get("source_url"),
            user_tier=user_tier,
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
