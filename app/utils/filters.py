# app/utils/filters.py
"""Article filtering utilities — source whitelist, opinion, sentiment, topic relevance."""

from typing import Optional

# ── Israeli source whitelist ──────────────────────────────────────────────────
ISRAELI_SOURCES: set[str] = {
    "The Jerusalem Post", "jpost.com",
    "Times of Israel", "timesofisrael.com",
    "Haaretz", "haaretz.com",
    "Ynet News", "ynetnews.com",
    "i24 News", "i24news.tv",
    "Arutz Sheva", "israelnationalnews.com",
    "Israel Hayom", "israelhayom.com",
    "The Algemeiner", "algemeiner.com",
    "Israel National News", "arutzsheva.com",
    "Jewish Telegraphic Agency", "jta.org",
    "The Media Line", "themedialine.org",
    "Ynetnews", "ynet.co.il",
    "Walla News", "walla.co.il", "news.walla.co.il",
    "Calcalist", "calcalist.co.il",
    "Globes", "globes.co.il",
    "Channel 12 News", "mako.co.il",
    "Channel 13 News",
    "Kan News", "kan.org.il",
    "N12",
    "Maariv", "maariv.co.il",
    "Zman Israel", "zman.co.il",
    "Reshet Bet",
    "103FM", "103fm.maariv.co.il",
    "Galatz",
    "YNET", "ynet.co.il",
    "sport5.co.il",
    "one.co.il",
    "TheMarker", "themarker.com",
    "Bizportal", "bizportal.co.il",
    "Funder", "funder.co.il",
    "Geektime", "geektime.com", "geektime.co.il",
    "IVC", "ivc-online.com",
    "Israel Ministry of Foreign Affairs", "mfa.gov.il",
    "Knesset", "knesset.gov.il",
    "Israel Government Press Office", "gov.il",
    "Haaretz English",
    "Ynet Hebrew",
    "Israel Hayom Hebrew",
    "Channel 12 (Mako)",
    "Channel 13 (Reshet)",
    "Nrg (Maariv Online)",
    "CTech (Calcalist)",
    "Jewish Press",
    "One (Sport)",
    "Sport5",
    "Israel Democracy Institute",
    "+972 Magazine",
    "Local Call (Sikha Mekomit)",
    "Israel Policy Forum",
    "Google News Israel",
    # ── .co.il domains (Israeli Hebrew editions) ──────────────────────────
    "haaretz.co.il",
    "israelhayom.co.il",
    "nrg.co.il",
    "mynet.co.il",
    "behadrei.co.il",
    "srugim.co.il",
    "kikar.co.il",
    "inn.co.il",            # Arutz Sheva Hebrew
    "arutz7.co.il",
    "hidabroot.com",
    # ── Hebrew display names (from Google News RSS <source> tags) ─────────
    "הארץ",                 # Haaretz Hebrew
    "ידיעות אחרונות",       # Yedioth Ahronoth
    "מעריב",                # Maariv
    "ישראל היום", "היום",   # Israel Hayom Hebrew
    "ynet", "וואלה",        # Ynet / Walla Hebrew
    "כאן", "כאן 11",        # Kan public broadcast
    "N12", "ערוץ 12",       # Channel 12
    "ערוץ 13",              # Channel 13
    "גלובס",                # Globes Hebrew
    "כלכליסט",              # Calcalist Hebrew
    "TheMarker", "דה מרקר",
    "ספורט 5",              # Sport5 Hebrew
    "mako",                 # Mako (Channel 12 website)
    "nrg",                  # NRG (Maariv Online)
    "walla",
    "בחדרי חרדים",          # Behadrei Haredim
    "כיכר השבת",            # Kikar Hashabbat
    "סרוגים",               # Srugim
    "ערוץ 7",               # Arutz 7
    "גלי ישראל",            # Galei Israel
    "www.israelhayom.com",  # Google News source tag variant
}

BLOCKED_SOURCES: set[str] = {
    "wikipedia.org", "en.wikipedia.org", "wikimedia.org", "wikidata.org",
    "medium.com", "substack.com",
}

NEGATIVE_KEYWORDS: tuple[str, ...] = (
    "crisis", "catastrophe", "disaster", "terror", "attack",
    "killed", "dead", "casualties", "war crime", "massacre",
    "riot", "protest", "strike", "sanction", "collapse",
    "arrested", "indicted", "corruption", "scandal", "fraud",
)

OPINION_KEYWORDS: tuple[str, ...] = (
    "opinion", "op-ed", "editorial", "columnist", "commentary",
    "analysis:", "perspective:", "view:", "think:", "column:",
)

# ── Topic-based keyword filter ─────────────────────────────────────────────────
# Each topic defines REQUIRED keywords (article must match ≥1 of these)
# and EXCLUDED keywords (article must NOT match any of these).
# An article from ANY source (Israel or global) must pass this gate
# before appearing in a topic-specific feed.
#
# Logic: match if ANY required keyword found in title+description,
#        AND NONE of the excluded keywords dominate the content.

TOPIC_KEYWORDS: dict[str, dict] = {
    "political": {
        "required": [
            "politic", "government", "parliament", "knesset", "election",
            "minister", "prime minister", "president", "senate", "congress",
            "coalition", "opposition", "policy", "legislation", "law", "bill",
            "democrat", "republican", "vote", "diplomat", "foreign policy",
            "sanctions", "treaty", "summit", "netanyahu", "biden", "trump",
            "cabinet", "party", "governance", "regime", "referendum",
        ],
        "excluded": [
            "sport", "football", "soccer", "basketball", "tennis", "olympics",
            "match", "goal", "score", "championship", "league",
        ],
    },
    "economy": {
        "required": [
            "economy", "economic", "finance", "financial", "market", "stock",
            "gdp", "inflation", "interest rate", "trade", "export", "import",
            "investment", "startup", "business", "company", "corporation",
            "bank", "currency", "dollar", "shekel", "euro", "budget",
            "fiscal", "monetary", "recession", "growth", "unemployment",
            "industry", "manufacturing", "revenue", "profit", "loss",
            "ipo", "merger", "acquisition", "venture", "fund",
        ],
        "excluded": [
            "sport", "football", "soccer", "basketball", "goal", "score",
            "match", "championship", "tournament",
        ],
    },
    "defence": {
        "required": [
            "defense", "defence", "military", "army", "navy", "air force",
            "idf", "soldier", "weapon", "missile", "drone", "security",
            "war", "conflict", "combat", "operation", "strike", "attack",
            "hamas", "hezbollah", "iran", "nuclear", "intelligence",
            "mossad", "shin bet", "nato", "pentagon", "arms", "airstrike",
            "battalion", "troops", "hostage", "ceasefire", "terror",
            "terrorist", "warfare", "artillery",
        ],
        "excluded": [
            "sport", "football", "soccer", "basketball", "goal",
            "entertainment", "film", "music",
        ],
    },
    "education": {
        "required": [
            "education", "school", "university", "college", "student",
            "teacher", "curriculum", "academic", "research", "scholarship",
            "tuition", "campus", "degree", "graduate", "undergraduate",
            "professor", "classroom", "learning", "study", "exam",
            "training", "vocational", "literacy", "kindergarten",
        ],
        "excluded": [
            "sport", "football", "soccer", "basketball", "military",
            "combat", "weapon",
        ],
    },
    "community": {
        "required": [
            "community", "society", "social", "people", "citizen",
            "neighborhood", "local", "welfare", "charity", "nonprofit",
            "volunteer", "immigration", "refugee", "diaspora", "religion",
            "jewish", "muslim", "christian", "culture", "tradition",
            "family", "health", "hospital", "mental health", "housing",
            "poverty", "inequality", "human rights", "protest", "rally",
        ],
        "excluded": [
            "sport", "football", "soccer", "basketball", "finance",
            "stock", "market",
        ],
    },
    "sport": {
        "required": [
            "sport", "sports", "football", "soccer", "basketball", "tennis",
            "volleyball", "swimming", "athletics", "olympic", "olympics",
            "match", "game", "goal", "score", "league", "championship",
            "tournament", "player", "team", "coach", "stadium", "transfer",
            "athlete", "boxing", "cycling", "marathon", "cricket",
            "rugby", "baseball", "hockey", "gym", "fitness",
            "maccabi", "hapoel", "beitar",
        ],
        "excluded": [
            "politic", "government", "military", "war", "conflict",
            "economy", "finance", "stock",
        ],
    },
    "culture": {
        "required": [
            "culture", "art", "music", "film", "movie", "theater", "theatre",
            "museum", "exhibition", "festival", "concert", "literature",
            "book", "poetry", "dance", "fashion", "design", "architecture",
            "heritage", "tradition", "cultural", "artist", "actor",
            "director", "singer", "band", "gallery", "performance",
            "television", "tv show", "series", "documentary",
        ],
        "excluded": [
            "sport", "military", "war", "economy", "stock market",
        ],
    },
    "environment": {
        "required": [
            "environment", "environmental", "climate", "climate change",
            "global warming", "renewable energy", "solar", "wind power",
            "carbon", "emissions", "pollution", "sustainability", "green",
            "ecology", "wildlife", "nature", "conservation", "biodiversity",
            "water", "drought", "flood", "fire", "earthquake", "disaster",
            "clean energy", "electric vehicle", "recycling",
        ],
        "excluded": [
            "sport", "football", "soccer", "entertainment", "film",
        ],
    },
    "science": {
        "required": [
            "science", "scientific", "research", "technology", "tech",
            "innovation", "discovery", "ai", "artificial intelligence",
            "machine learning", "cybersecurity", "space", "nasa", "esa",
            "medicine", "medical", "drug", "vaccine", "cancer", "dna",
            "genetic", "quantum", "physics", "chemistry", "biology",
            "robot", "startup", "software", "hardware", "data", "digital",
            "internet", "5g", "semiconductor", "chip",
        ],
        "excluded": [
            "sport", "football", "soccer", "political scandal",
            "entertainment gossip",
        ],
    },
    "positive": {
        "required": [
            "achievement", "breakthrough", "success", "award", "record",
            "innovation", "discovery", "milestone", "hero", "rescued",
            "recovery", "hope", "peace", "agreement", "cooperation",
            "celebration", "winner", "champion", "inspire", "help",
            "improve", "growth", "progress", "initiative", "solution",
            "donation", "volunteer", "community", "together",
        ],
        "excluded": [],
    },
    "international": {
        "required": [
            "international", "global", "world", "united nations", "un",
            "nato", "eu", "european union", "g7", "g20", "imf",
            "foreign", "bilateral", "multilateral", "diplomatic",
            "relations", "accord", "agreement", "summit", "conflict",
            "crisis", "humanitarian", "aid", "sanction", "trade war",
            "geopolitic", "alliance", "security council",
        ],
        "excluded": [],
    },
    "knesset": {
        "required": [
            "knesset", "legislation", "bill", "law", "parliament",
            "member of knesset", "mk ", "plenum", "committee",
            "vote", "coalition", "opposition", "minister",
        ],
        "excluded": [
            "sport", "football", "soccer", "entertainment",
        ],
    },
    "arabic": {
        "required": [],  # No topic restriction for Arabic feed
        "excluded": [],
    },
}

# Minimum score to pass topic relevance (number of required keyword hits needed)
TOPIC_MIN_HITS: int = 1


def is_israeli_source(source_name: Optional[str], source_url: Optional[str]) -> bool:
    # 1. Fast exact set lookup on display name
    if source_name:
        if source_name in ISRAELI_SOURCES:
            return True
        # Case-insensitive fallback (handles 'www.israelhayom.com' Google News tags)
        if source_name.lower() in {s.lower() for s in ISRAELI_SOURCES}:
            return True

    # 2. URL-based checks
    if source_url:
        url_lower = source_url.lower()
        # Shortcut: any .co.il domain is Israeli by definition
        if ".co.il" in url_lower:
            return True
        # Whitelist domain scan
        for domain in ISRAELI_SOURCES:
            if domain and domain in url_lower:
                return True

    return False


def is_blocked_source(source_name: Optional[str], source_url: Optional[str]) -> bool:
    if source_url:
        for domain in BLOCKED_SOURCES:
            if domain in source_url:
                return True
    if source_name and source_name.lower() in {s.lower() for s in BLOCKED_SOURCES}:
        return True
    return False


def is_opinion(title: Optional[str], description: Optional[str] = None) -> bool:
    text = " ".join(filter(None, [title, description])).lower()
    return any(kw in text for kw in OPINION_KEYWORDS)


def is_negative(title: Optional[str], description: Optional[str] = None) -> bool:
    text = " ".join(filter(None, [title, description])).lower()
    return any(kw in text for kw in NEGATIVE_KEYWORDS)


def is_topic_relevant(
    category: str,
    title: Optional[str],
    description: Optional[str] = None,
    source_name: Optional[str] = None,
    source_url: Optional[str] = None,
) -> bool:
    """
    Check if an article is relevant to the given topic/category.

    Returns True if:
      - No topic filter defined for this category (pass-through), OR
      - No required keywords defined (pass-through), OR
      - At least TOPIC_MIN_HITS required keywords found in title+description
        AND no excluded keywords match.

    This prevents e.g. sports news from appearing in the political feed
    even when fetched from a global/Israeli source that mixes content.
    """
    config = TOPIC_KEYWORDS.get(category)
    if not config:
        return True  # Unknown category — let it pass

    required = config.get("required", [])
    excluded = config.get("excluded", [])

    text = " ".join(filter(None, [title, description])).lower()

    # If no required keywords specified, skip required check
    if required:
        hits = sum(1 for kw in required if kw in text)
        if hits < TOPIC_MIN_HITS:
            return False

    # If any excluded keyword matches, reject
    if any(kw in text for kw in excluded):
        return False

    if category == "positive":
        if source_name or source_url:
            if not is_israeli_source(source_name, source_url):
                israel_terms = [
                    "israel", "israeli", "jerusalem", "tel aviv", "haifa",
                    "beersheva", "knesset", "idf", "netanyahu", "benjamin",
                    "jerusalem", "gaza", "west bank",
                ]
                if not any(term in text for term in israel_terms):
                    return False

    return True
