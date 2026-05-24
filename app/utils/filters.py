# app/utils/filters.py
"""Article filtering utilities — source whitelist, opinion, sentiment."""

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
    "Geektime", "geektime.com",
    "IVC", "ivc-online.com",
    "Israel Ministry of Foreign Affairs", "mfa.gov.il",
    "Knesset", "knesset.gov.il",
    "Israel Government Press Office", "gov.il",
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


def is_israeli_source(source_name: Optional[str], source_url: Optional[str]) -> bool:
    if source_name and source_name in ISRAELI_SOURCES:
        return True
    if source_url:
        for domain in ISRAELI_SOURCES:
            if domain in source_url:
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
