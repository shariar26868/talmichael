# app/utils/feed_config.py
"""RSS feed URLs and category configuration."""

RSS_FEEDS: dict[str, str] = {
    "international": "https://news.google.com/rss/search?q=Israel+international+positive+good&hl=en-IL&gl=IL&ceid=IL:en",
    "economy":       "https://news.google.com/rss/search?q=Israel+economy+finance+market+business&hl=en-IL&gl=IL&ceid=IL:en",
    "defence":       "https://news.google.com/rss/search?q=Israel+security+defense+military+IDF&hl=en-IL&gl=IL&ceid=IL:en",
    "education":     "https://news.google.com/rss/search?q=Israel+education+schools+university+students&hl=en-IL&gl=IL&ceid=IL:en",
    "community":     "https://news.google.com/rss/search?q=Israel+society+community+social&hl=en-IL&gl=IL&ceid=IL:en",
    "sport":         "https://news.google.com/rss/search?q=Israel+sport+football+basketball&hl=en-IL&gl=IL&ceid=IL:en",
    "culture":       "https://news.google.com/rss/search?q=Israel+culture+arts+music&hl=en-IL&gl=IL&ceid=IL:en",
    "environment":   "https://news.google.com/rss/search?q=Israel+environment+climate+energy&hl=en-IL&gl=IL&ceid=IL:en",
    "science":       "https://news.google.com/rss/search?q=Israel+science+technology+innovation&hl=en-IL&gl=IL&ceid=IL:en",
    "positive":      "https://news.google.com/rss/search?q=Israel+positive+achievement+breakthrough&hl=en-IL&gl=IL&ceid=IL:en",
    "political":     "https://news.google.com/rss/search?q=Israel+politics+Knesset+government&hl=en-IL&gl=IL&ceid=IL:en",
    "knesset":       "https://news.google.com/rss/search?q=Knesset+legislation+bill+Israel+law&hl=en-IL&gl=IL&ceid=IL:en",
}

# Categories that always exclude negative sentiment
EXCLUDE_NEGATIVE_CATEGORIES: set[str] = {"positive", "international"}

# Categories that always require Israeli sources
ISRAELI_ONLY_CATEGORIES: set[str] = set(RSS_FEEDS.keys())

KNESSET_BILLS_API = (
    "https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Bill"
    "?$format=json&$top={limit}&$orderby=LastUpdatedDate desc"
)
