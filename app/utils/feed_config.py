# app/utils/feed_config.py
"""RSS feed URLs and category configuration.

Sources: 70+ outlets including Israeli, international, and Arabic news.
Organized by category for better filtering and context injection.
"""

# ── ISRAELI SOURCES (Primary: Google News; Fallback: Open RSS) ──────────────

ISRAELI_SOURCES_FEEDS: dict[str, str] = {
    # PRIMARY: Google News feeds (work reliably)
    "Google News Israel": "https://news.google.com/rss/search?q=Israel&hl=en-IL&gl=IL&ceid=IL:en",
    "Google News Knesset": "https://news.google.com/rss/search?q=Knesset+Israel&hl=en-IL&gl=IL&ceid=IL:en",
    "Google News Israel Politics": "https://news.google.com/rss/search?q=Israel+politics&hl=en-IL&gl=IL&ceid=IL:en",
}

# ── INTERNATIONAL SOURCES (Primary: Google News + BBC; Fallback: Open sources) ────

INTERNATIONAL_SOURCES_FEEDS: dict[str, str] = {
    # PRIMARY: Working news feeds (Google News + BBC which allows scraping)
    "Google News World": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    "Google News Business": "https://news.google.com/rss/topics/CAAqJggKIiBDQklTQ2dBU0JBMU9nQXhNQXx1dW5pdmVyc2U",
    "BBC News": "https://feeds.bbci.co.uk/news/rss.xml",
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "BBC Middle East": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
    "Reuters": "https://www.reuters.com/world",  # Feed may need parsing
    "NPR": "https://feeds.npr.org/1001/rss.xml",
}

# ── ARABIC SOURCES (Primary: Google News Arabic + BBC Arabic) ─────────────────

ARABIC_SOURCES_FEEDS: dict[str, str] = {
    # PRIMARY: Working sources
    "Google News Arabic": "https://news.google.com/rss?hl=ar&gl=SA&ceid=SA:ar",
    "BBC Arabic": "https://www.bbc.com/arabic/feed.xml",
}

# ── CATEGORY-BASED RSS FEEDS (Fallback/supplement) ────────────────────────

RSS_FEEDS: dict[str, str] = {
    # Primary: Direct source feeds aggregated by category
    "political": "https://news.google.com/rss/search?q=Israel+politics+Knesset+government&hl=en-IL&gl=IL&ceid=IL:en",
    "economy": "https://news.google.com/rss/search?q=Israel+economy+finance+market+business&hl=en-IL&gl=IL&ceid=IL:en",
    "defence": "https://news.google.com/rss/search?q=Israel+security+defense+military+IDF&hl=en-IL&gl=IL&ceid=IL:en",
    "education": "https://news.google.com/rss/search?q=Israel+education+schools+university+students&hl=en-IL&gl=IL&ceid=IL:en",
    "community": "https://news.google.com/rss/search?q=Israel+society+community+social&hl=en-IL&gl=IL&ceid=IL:en",
    "sport": "https://news.google.com/rss/search?q=Israel+sport+football+basketball&hl=en-IL&gl=IL&ceid=IL:en",
    "culture": "https://news.google.com/rss/search?q=Israel+culture+arts+music&hl=en-IL&gl=IL&ceid=IL:en",
    "environment": "https://news.google.com/rss/search?q=Israel+environment+climate+energy&hl=en-IL&gl=IL&ceid=IL:en",
    "science": "https://news.google.com/rss/search?q=Israel+science+technology+innovation&hl=en-IL&gl=IL&ceid=IL:en",
    "positive": "https://news.google.com/rss/search?q=Israel+positive+achievement+breakthrough&hl=en-IL&gl=IL&ceid=IL:en",
    "international": "https://news.google.com/rss/search?q=Israel+international&hl=en-IL&gl=IL&ceid=IL:en",
    "knesset": "https://news.google.com/rss/search?q=Knesset+legislation+bill+Israel+law&hl=en-IL&gl=IL&ceid=IL:en",
}

# ── SOURCE REGISTRY ───────────────────────────────────────────────────────

SOURCE_REGISTRY: dict[str, dict] = {
    # Israeli sources with metadata
    "Haaretz": {
        "url": "https://www.haaretz.com",
        "country": "Israel",
        "language": "Hebrew/English",
        "bias": "left",
        "credibility": 0.85,
        "category": "general"
    },
    "Times of Israel": {
        "url": "https://www.timesofisrael.com",
        "country": "Israel",
        "language": "English",
        "bias": "center",
        "credibility": 0.82,
        "category": "general"
    },
    "Jerusalem Post": {
        "url": "https://www.jpost.com",
        "country": "Israel",
        "language": "English",
        "bias": "right",
        "credibility": 0.78,
        "category": "general"
    },
    "Ynet News": {
        "url": "https://www.ynet.co.il",
        "country": "Israel",
        "language": "Hebrew",
        "bias": "center",
        "credibility": 0.75,
        "category": "general"
    },
    "Kan News": {
        "url": "https://www.kan.org.il",
        "country": "Israel",
        "language": "Hebrew",
        "bias": "center",
        "credibility": 0.88,
        "category": "public_broadcast"
    },
    "BBC Arabic": {
        "url": "https://www.bbc.com/arabic",
        "country": "UK",
        "language": "Arabic",
        "bias": "center",
        "credibility": 0.88,
        "category": "international"
    },
    "Al Jazeera": {
        "url": "https://www.aljazeera.com",
        "country": "Qatar",
        "language": "English/Arabic",
        "bias": "left",
        "credibility": 0.72,
        "category": "international"
    },
}

# Categories that always exclude negative sentiment
EXCLUDE_NEGATIVE_CATEGORIES: set[str] = {"positive", "international"}

# Categories that always require Israeli sources
ISRAELI_ONLY_CATEGORIES: set[str] = set(RSS_FEEDS.keys())

# Language flags for multilingual filtering
SOURCE_LANGUAGES: dict[str, list[str]] = {
    "hebrew": list(ISRAELI_SOURCES_FEEDS.keys()),
    "english": list(INTERNATIONAL_SOURCES_FEEDS.keys()),
    "arabic": list(ARABIC_SOURCES_FEEDS.keys()),
}

KNESSET_BILLS_API = (
    "https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Bill"
    "?$format=json&$top={limit}&$orderby=LastUpdatedDate desc"
)

# ── HELPER FUNCTIONS ──────────────────────────────────────────────────────

def get_all_feeds() -> dict[str, str]:
    """Combine all source feeds into single dictionary."""
    all_feeds = {}
    all_feeds.update(ISRAELI_SOURCES_FEEDS)
    all_feeds.update(INTERNATIONAL_SOURCES_FEEDS)
    all_feeds.update(ARABIC_SOURCES_FEEDS)
    return all_feeds


def get_feeds_by_language(language: str) -> dict[str, str]:
    """Get feeds for specific language."""
    feeds = {}
    if language.lower() in ["hebrew", "he", "iw"]:
        feeds.update(ISRAELI_SOURCES_FEEDS)
    elif language.lower() in ["english", "en"]:
        feeds.update(INTERNATIONAL_SOURCES_FEEDS)
    elif language.lower() in ["arabic", "ar"]:
        feeds.update(ARABIC_SOURCES_FEEDS)
    return feeds


def get_feeds_by_country(country: str) -> dict[str, str]:
    """Get feeds for specific country."""
    feeds = {}
    for name, feed_url in get_all_feeds().items():
        if name in SOURCE_REGISTRY:
            if SOURCE_REGISTRY[name].get("country", "").lower() == country.lower():
                feeds[name] = feed_url
    return feeds


def get_source_info(source_name: str) -> dict:
    """Get metadata for a source."""
    return SOURCE_REGISTRY.get(source_name, {
        "url": "",
        "country": "Unknown",
        "language": "Unknown",
        "bias": "unknown",
        "credibility": 0.5,
        "category": "unknown"
    })
