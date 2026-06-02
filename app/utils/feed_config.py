# app/utils/feed_config.py
"""RSS feed URLs and category configuration.

Sources: 70+ outlets including Israeli, international, and Arabic news.
Organized by category for better filtering and context injection.
"""

# ── ISRAELI SOURCES (25+ outlets) ──────────────────────────────────────────

ISRAELI_SOURCES_FEEDS: dict[str, str] = {
    # Major outlets
    "Haaretz": "https://www.haaretz.com/feed",
    "Haaretz_English": "https://www.haaretz.com/cmlink/2.271/1.3897848",
    "Times of Israel": "https://www.timesofisrael.com/feed",
    "Jerusalem Post": "https://www.jpost.com/rss/feeds",
    "Ynet News": "https://www.ynet.co.il/rss/",
    "Walla News": "https://news.walla.co.il/rss/",
    "Kan News": "https://www.kan.org.il/rss/",
    "Channel 12": "https://www.mako.co.il/rss",
    "Globes": "https://www.globes.co.il/rss/",
    "TheMarker": "https://www.themarker.com/rss",
    
    # Right-leaning outlets
    "Arutz Sheva": "https://www.israelnationalnews.com/feed",
    "Israel Hayom": "https://www.israelhayom.com/feed",
    "The Algemeiner": "https://www.algemeiner.com/feed",
    "Jewish Press": "https://www.jewishpress.com/feed",
    
    # Left-leaning outlets
    "Meretz": "https://meretz.org.il/feed",
    
    # Technology & startup news
    "CTech": "https://www.calcalistech.com/rss/",
    "Geektime": "https://www.geektime.co.il/feed/",
    
    # Business & economy
    "Business Insider Israel": "https://www.businessinsider.com.au/feed",
    
    # Local news outlets
    "Yedioth Ahronoth": "https://www.ynetnews.com/rss/",
    "Maariv": "https://www.maariv.co.il/rss/",
    "Nrg": "https://www.nrg.co.il/rss/",
    "Walla Politics": "https://news.walla.co.il/rss/?section=politics",
    "Ynet Politics": "https://www.ynet.co.il/Rss/RssHebrew?channel=3",
    
    # Sports
    "Sport5": "https://www.sport5.co.il/rss/",
    "One": "https://one.co.il/rss/",
}

# ── INTERNATIONAL SOURCES (25+ outlets) ────────────────────────────────────

INTERNATIONAL_SOURCES_FEEDS: dict[str, str] = {
    # Major news agencies
    "Reuters": "https://www.reutersagency.com/feed/?taxonomy=best-topics&ignore_taxonomy_filter_list",
    "AP News": "https://apnews.com/APF-Services/feed",
    "BBC News": "https://feeds.bbci.co.uk/news/rss.xml",
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "BBC Middle East": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
    
    # US News
    "CNN": "http://rss.cnn.com/rss/cnn_topstories.rss",
    "NPR": "https://feeds.npr.org/1001/rss.xml",
    "New York Times": "https://feeds.nytimes.com/services/xml/rss/nyt/World.xml",
    "Washington Post": "https://feeds.washingtonpost.com/rss/world",
    "Wall Street Journal": "https://feeds.wsj.com/xml/rss/3_7085.xml",
    
    # UK News
    "The Guardian": "https://www.theguardian.com/world/rss",
    "The Telegraph": "https://www.telegraph.co.uk/feed/rss/world/index.xml",
    "The Independent": "https://www.independent.co.uk/news/world/rss",
    "Financial Times": "https://feeds.ft.com/world",
    
    # Europe
    "Euronews": "https://www.euronews.com/feed/xml/en/news",
    "DW News": "https://feeds.dw.com/rss/en/rss-news-en-world",
    "France24": "https://www.france24.com/en/rss",
    
    # Middle East focused
    "Al Jazeera English": "https://www.aljazeera.com/xml/rss/all.xml",
    "Middle East Monitor": "https://www.middleeastmonitor.com/feed",
    "Middle East Eye": "https://www.middleeasteye.net/feeds/default",
    "Conflict Observatory": "https://www.conflictobservatory.org/feed/",
    
    # Asia-Pacific
    "Reuters Asia": "https://www.reutersagency.com/feed/?taxonomy=best-topics&taxonomy_tag_id=34",
    "The Straits Times": "https://www.straitstimes.com/feed/rss",
    
    # Commentary & Analysis
    "Axios": "https://www.axios.com/feed",
    "The Economist": "https://www.economist.com/printedition/rss.xml",
}

# ── ARABIC SOURCES (20+ outlets) ───────────────────────────────────────────

ARABIC_SOURCES_FEEDS: dict[str, str] = {
    # Major Arabic news agencies
    "BBC Arabic": "https://www.bbc.com/arabic/feed.xml",
    "Al Arabiya": "https://www.alarabiya.net/rss.xml",
    "Sky News Arabia": "https://www.skynewsarabia.com/rss.xml",
    "Arab News": "https://www.arabnews.com/node/feed",
    "Al Jazeera Arabic": "https://www.aljazeera.net/xml/rss/all.xml",
    
    # Regional sources
    "Middle East News Agency": "https://www.mena.org.eg/rss/",
    "Palestine Info": "https://www.palestineinfo.info/feed/",
    "Wafa News": "https://wafa.ps/rss",
    
    # Gulf sources
    "Saudi Press Agency": "https://www.spa.gov.sa/rss",
    "UAE News": "https://www.thenationalnews.com/rss.xml",
    
    # Pan-Arab outlets
    "Ahram Online": "https://english.ahram.org.eg/NewsArchiveRss.aspx",
    "Al Bab": "https://www.al-bab.com/feed",
    
    # Independent sources
    "+972 Magazine": "https://972mag.com/feed",
    "Local Call": "https://www.localcall.co.il/feed",
    "Roya News": "https://royanews.tv/rss",
    "TRT World": "https://www.trtworld.com/feed/rss.xml",
    
    # Turkish sources (regional)
    "Anadolu Agency": "https://www.aa.com.tr/en/world/rss-feed",
    "Daily Sabah": "https://www.dailysabah.com/rss/all/news",
    "Hürriyet": "https://www.hurriyet.com.tr/rss/",
    "Yeni Şafak": "https://www.yenisafak.com/rss/",
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
