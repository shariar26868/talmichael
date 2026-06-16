# app/utils/feed_config.py
"""RSS feed URLs and category configuration.

Sources: 100+ outlets including Israeli, international, and Arabic news.
Organized by region, language, and category for filtering and context injection.

Last updated: 2026-06-15
"""

# ══════════════════════════════════════════════════════════════════════════════
# ISRAELI SOURCES — 30 outlets (Hebrew + English editions)
# ══════════════════════════════════════════════════════════════════════════════

ISRAELI_SOURCES_FEEDS: dict[str, str] = {
    # ── Major General News ────────────────────────────────────────────────
    "Haaretz": "https://www.haaretz.com/srv/haaretz-latest-rss",
    "Haaretz English": "https://www.haaretz.com/srv/haaretz-latest-en-rss",
    "Times of Israel": "https://www.timesofisrael.com/feed/",
    "Jerusalem Post": "https://www.jpost.com/rss/rssfeedsfrontpage.aspx",
    "Ynet News": "https://www.ynetnews.com/rss/all.xml",
    "Ynet Hebrew": "https://www.ynet.co.il/rss/news",
    "Kan News": "https://www.kan.org.il/feed/",
    "Israel Hayom": "https://www.israelhayom.com/feed/",
    "Israel Hayom Hebrew": "https://www.israelhayom.co.il/feed/",
    "Arutz Sheva": "https://www.israelnationalnews.com/rss.xml",

    # ── Mainstream / TV ───────────────────────────────────────────────────
    "Channel 12 (Mako)": "https://rss.mako.co.il/rssNew.xml",
    "Channel 13 (Reshet)": "https://13tv.co.il/feed/",
    "i24 News": "https://www.i24news.tv/en/rss",
    "Walla News": "https://rss.walla.co.il/feed/1",
    "Maariv": "https://www.maariv.co.il/rss/all",
    "Nrg (Maariv Online)": "https://www.nrg.co.il/rss/",

    # ── Business & Tech ───────────────────────────────────────────────────
    "Globes": "https://www.globes.co.il/webservice/rss/rssfeeder.asmx/FeederNode?iID=585",
    "TheMarker": "https://www.themarker.com/srv/themarker-latest-rss",
    "CTech (Calcalist)": "https://www.calcalistech.com/rss/all.xml",
    "Geektime": "https://www.geektime.co.il/feed/",
    "Calcalist": "https://www.calcalist.co.il/GeneralRss/0,16335,L-8,00.xml",

    # ── Niche / Sector ────────────────────────────────────────────────────
    "The Algemeiner": "https://www.algemeiner.com/feed/",
    "Jewish Press": "https://www.jewishpress.com/feed/",
    "Sport5": "https://www.sport5.co.il/rss/all.xml",
    "One (Sport)": "https://www.one.co.il/rss/",

    # ── Think Tanks / Analysis (Israeli) ──────────────────────────────────
    "Israel Democracy Institute": "https://en.idi.org.il/rss",
    "+972 Magazine": "https://www.972mag.com/feed/",
    "Local Call (Sikha Mekomit)": "https://www.local-call.com/feed/",
    "Israel Policy Forum": "https://israelpolicyforum.org/feed/",

    # ── Google News Israel (supplementary aggregator) ─────────────────────
    "Google News Israel": "https://news.google.com/rss/search?q=Israel&hl=en-IL&gl=IL&ceid=IL:en",
}

# ══════════════════════════════════════════════════════════════════════════════
# INTERNATIONAL SOURCES — 40 outlets
# ══════════════════════════════════════════════════════════════════════════════

INTERNATIONAL_SOURCES_FEEDS: dict[str, str] = {
    # ── Wire Agencies ─────────────────────────────────────────────────────
    "Reuters": "https://www.reutersagency.com/feed/?best-topics=political-general",
    "Associated Press": "https://rsshub.app/apnews/topics/world-news",
    "AFP (Agence France-Presse)": "https://www.france24.com/en/middle-east/rss",

    # ── BBC ───────────────────────────────────────────────────────────────
    "BBC News": "https://feeds.bbci.co.uk/news/rss.xml",
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "BBC Middle East": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",

    # ── United States ─────────────────────────────────────────────────────
    "CNN World": "http://rss.cnn.com/rss/edition_world.rss",
    "CNN Middle East": "http://rss.cnn.com/rss/edition_meast.rss",
    "NPR News": "https://feeds.npr.org/1001/rss.xml",
    "NPR World": "https://feeds.npr.org/1004/rss.xml",
    "New York Times World": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "New York Times Middle East": "https://rss.nytimes.com/services/xml/rss/nyt/MiddleEast.xml",
    "Washington Post World": "https://feeds.washingtonpost.com/rss/world",
    "Wall Street Journal World": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    "PBS NewsHour": "https://www.pbs.org/newshour/feeds/rss/world",
    "Axios": "https://api.axios.com/feed/",
    "The Atlantic": "https://www.theatlantic.com/feed/all/",
    "Foreign Policy": "https://foreignpolicy.com/feed/",
    "Foreign Affairs": "https://www.foreignaffairs.com/rss.xml",

    # ── United Kingdom ────────────────────────────────────────────────────
    "The Guardian World": "https://www.theguardian.com/world/rss",
    "The Guardian Middle East": "https://www.theguardian.com/world/middleeast/rss",
    "The Telegraph World": "https://www.telegraph.co.uk/news/world/rss.xml",
    "The Independent": "https://www.independent.co.uk/news/world/rss",
    "Financial Times": "https://www.ft.com/world?format=rss",
    "The Economist": "https://www.economist.com/middle-east-and-africa/rss.xml",
    "Sky News": "https://feeds.skynews.com/feeds/rss/world.xml",

    # ── Europe ────────────────────────────────────────────────────────────
    "Euronews": "https://www.euronews.com/rss?level=theme&name=news",
    "Deutsche Welle (DW)": "https://rss.dw.com/rdf/rss-en-world",
    "France24 English": "https://www.france24.com/en/rss",
    "France24 Middle East": "https://www.france24.com/en/middle-east/rss",
    "The Local (Sweden)": "https://feeds.thelocal.com/rss/se",
    "POLITICO Europe": "https://www.politico.eu/feed/",
    "Irish Times World": "https://www.irishtimes.com/cmlink/the-irish-times-world-rss-1.1346858",

    # ── Asia-Pacific ──────────────────────────────────────────────────────
    "The Straits Times": "https://www.straitstimes.com/news/world/rss.xml",
    "South China Morning Post": "https://www.scmp.com/rss/5/feed",
    "NHK World Japan": "https://www3.nhk.or.jp/nhkworld/en/news/feeds/",

    # ── Americas (non-US) ─────────────────────────────────────────────────
    "Globe and Mail (Canada)": "https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/world/",
    "Sydney Morning Herald": "https://www.smh.com.au/rss/world.xml",

    # ── Supplementary aggregator ──────────────────────────────────────────
    "Google News World": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    "Google News Business": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB",
}

# ══════════════════════════════════════════════════════════════════════════════
# ARABIC & REGIONAL SOURCES — 30 outlets
# ══════════════════════════════════════════════════════════════════════════════

ARABIC_SOURCES_FEEDS: dict[str, str] = {
    # ── Pan-Arab Major Broadcasters ───────────────────────────────────────
    "Al Jazeera English": "https://www.aljazeera.com/xml/rss/all.xml",
    "Al Jazeera Arabic": "https://www.aljazeera.net/aje/rss/all.xml",
    "BBC Arabic": "https://feeds.bbci.co.uk/arabic/rss.xml",
    "Al Arabiya English": "https://english.alarabiya.net/rss.xml",
    "Al Arabiya Arabic": "https://www.alarabiya.net/feed.xml",
    "Sky News Arabia": "https://www.skynewsarabia.com/rss",
    "Arab News": "https://www.arabnews.com/rss.xml",
    "Middle East Eye": "https://www.middleeasteye.net/rss",
    "Middle East Monitor": "https://www.middleeastmonitor.com/feed/",

    # ── Palestinian Sources ───────────────────────────────────────────────
    "WAFA (Palestinian News Agency)": "https://english.wafa.ps/rss.xml",
    "Ma'an News": "https://www.maannews.net/rss/all",
    "Palestine Chronicle": "https://www.palestinechronicle.com/feed/",

    # ── Gulf Sources ──────────────────────────────────────────────────────
    "Gulf News": "https://gulfnews.com/rss/world",
    "Khaleej Times": "https://www.khaleejtimes.com/rss",
    "The National (UAE)": "https://www.thenationalnews.com/rss/world.xml",
    "Saudi Gazette": "https://saudigazette.com.sa/rss.xml",

    # ── Egyptian Sources ──────────────────────────────────────────────────
    "Ahram Online": "https://english.ahram.org.eg/rss.xml",
    "Egypt Independent": "https://www.egyptindependent.com/feed/",
    "Daily News Egypt": "https://www.dailynewsegypt.com/feed/",

    # ── Jordanian / Lebanese ──────────────────────────────────────────────
    "Roya News (Jordan)": "https://en.royanews.tv/rss",
    "Jordan Times": "https://www.jordantimes.com/rss.xml",
    "Daily Star (Lebanon)": "https://www.dailystar.com.lb/rss.ashx",
    "L'Orient Today (Lebanon)": "https://today.lorientlejour.com/rss",
    "Naharnet (Lebanon)": "https://www.naharnet.com/rss.xml",

    # ── Turkish Regional ──────────────────────────────────────────────────
    "Anadolu Agency": "https://www.aa.com.tr/en/rss/default?cat=world",
    "TRT World": "https://www.trtworld.com/rss",
    "Daily Sabah": "https://www.dailysabah.com/rssFeed/mideast",
    "Hürriyet Daily News": "https://www.hurriyetdailynews.com/rss",

    # ── North African ─────────────────────────────────────────────────────
    "Morocco World News": "https://www.moroccoworldnews.com/feed/",
    "The North Africa Journal": "https://north-africa.com/feed/",

    # ── Supplementary aggregator ──────────────────────────────────────────
    "Google News Arabic": "https://news.google.com/rss?hl=ar&gl=SA&ceid=SA:ar",
}

# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY-BASED RSS FEEDS (topic-specific supplementary feeds)
# ══════════════════════════════════════════════════════════════════════════════

RSS_FEEDS: dict[str, str] = {
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

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE REGISTRY — Full metadata for every source
# Each entry: url, country, language, bias, credibility, category
# ══════════════════════════════════════════════════════════════════════════════

SOURCE_REGISTRY: dict[str, dict] = {
    # ── ISRAELI SOURCES (30) ──────────────────────────────────────────────
    "Haaretz": {
        "url": "https://www.haaretz.com",
        "country": "Israel", "language": "Hebrew/English",
        "bias": "left", "credibility": 0.85, "category": "general",
    },
    "Haaretz English": {
        "url": "https://www.haaretz.com",
        "country": "Israel", "language": "English",
        "bias": "left", "credibility": 0.85, "category": "general",
    },
    "Times of Israel": {
        "url": "https://www.timesofisrael.com",
        "country": "Israel", "language": "English",
        "bias": "center", "credibility": 0.82, "category": "general",
    },
    "Jerusalem Post": {
        "url": "https://www.jpost.com",
        "country": "Israel", "language": "English",
        "bias": "center-right", "credibility": 0.78, "category": "general",
    },
    "Ynet News": {
        "url": "https://www.ynetnews.com",
        "country": "Israel", "language": "English",
        "bias": "center", "credibility": 0.75, "category": "general",
    },
    "Ynet Hebrew": {
        "url": "https://www.ynet.co.il",
        "country": "Israel", "language": "Hebrew",
        "bias": "center", "credibility": 0.75, "category": "general",
    },
    "Kan News": {
        "url": "https://www.kan.org.il",
        "country": "Israel", "language": "Hebrew",
        "bias": "center", "credibility": 0.88, "category": "public_broadcast",
    },
    "Israel Hayom": {
        "url": "https://www.israelhayom.com",
        "country": "Israel", "language": "English/Hebrew",
        "bias": "right", "credibility": 0.68, "category": "general",
    },
    "Israel Hayom Hebrew": {
        "url": "https://www.israelhayom.co.il",
        "country": "Israel", "language": "Hebrew",
        "bias": "right", "credibility": 0.68, "category": "general",
    },
    "Arutz Sheva": {
        "url": "https://www.israelnationalnews.com",
        "country": "Israel", "language": "English/Hebrew",
        "bias": "right", "credibility": 0.62, "category": "general",
    },
    "Channel 12 (Mako)": {
        "url": "https://www.mako.co.il",
        "country": "Israel", "language": "Hebrew",
        "bias": "center", "credibility": 0.82, "category": "broadcast",
    },
    "Channel 13 (Reshet)": {
        "url": "https://13tv.co.il",
        "country": "Israel", "language": "Hebrew",
        "bias": "center", "credibility": 0.80, "category": "broadcast",
    },
    "i24 News": {
        "url": "https://www.i24news.tv",
        "country": "Israel", "language": "English/French/Arabic",
        "bias": "center", "credibility": 0.78, "category": "broadcast",
    },
    "Walla News": {
        "url": "https://www.walla.co.il",
        "country": "Israel", "language": "Hebrew",
        "bias": "center", "credibility": 0.74, "category": "general",
    },
    "Maariv": {
        "url": "https://www.maariv.co.il",
        "country": "Israel", "language": "Hebrew",
        "bias": "center-right", "credibility": 0.72, "category": "general",
    },
    "Nrg (Maariv Online)": {
        "url": "https://www.nrg.co.il",
        "country": "Israel", "language": "Hebrew",
        "bias": "center-right", "credibility": 0.70, "category": "general",
    },
    "Globes": {
        "url": "https://www.globes.co.il",
        "country": "Israel", "language": "Hebrew/English",
        "bias": "center", "credibility": 0.80, "category": "business",
    },
    "TheMarker": {
        "url": "https://www.themarker.com",
        "country": "Israel", "language": "Hebrew",
        "bias": "center-left", "credibility": 0.82, "category": "business",
    },
    "CTech (Calcalist)": {
        "url": "https://www.calcalistech.com",
        "country": "Israel", "language": "English",
        "bias": "center", "credibility": 0.78, "category": "tech",
    },
    "Geektime": {
        "url": "https://www.geektime.co.il",
        "country": "Israel", "language": "Hebrew",
        "bias": "center", "credibility": 0.72, "category": "tech",
    },
    "Calcalist": {
        "url": "https://www.calcalist.co.il",
        "country": "Israel", "language": "Hebrew",
        "bias": "center", "credibility": 0.78, "category": "business",
    },
    "The Algemeiner": {
        "url": "https://www.algemeiner.com",
        "country": "Israel/US", "language": "English",
        "bias": "right", "credibility": 0.65, "category": "general",
    },
    "Jewish Press": {
        "url": "https://www.jewishpress.com",
        "country": "Israel/US", "language": "English",
        "bias": "right", "credibility": 0.60, "category": "general",
    },
    "Sport5": {
        "url": "https://www.sport5.co.il",
        "country": "Israel", "language": "Hebrew",
        "bias": "center", "credibility": 0.72, "category": "sport",
    },
    "One (Sport)": {
        "url": "https://www.one.co.il",
        "country": "Israel", "language": "Hebrew",
        "bias": "center", "credibility": 0.70, "category": "sport",
    },
    "Israel Democracy Institute": {
        "url": "https://en.idi.org.il",
        "country": "Israel", "language": "English/Hebrew",
        "bias": "center", "credibility": 0.92, "category": "think_tank",
    },
    "+972 Magazine": {
        "url": "https://www.972mag.com",
        "country": "Israel", "language": "English",
        "bias": "left", "credibility": 0.70, "category": "analysis",
    },
    "Local Call (Sikha Mekomit)": {
        "url": "https://www.local-call.com",
        "country": "Israel", "language": "Hebrew",
        "bias": "left", "credibility": 0.68, "category": "analysis",
    },
    "Israel Policy Forum": {
        "url": "https://israelpolicyforum.org",
        "country": "Israel/US", "language": "English",
        "bias": "center-left", "credibility": 0.82, "category": "think_tank",
    },

    # ── INTERNATIONAL SOURCES (40) ────────────────────────────────────────
    "Reuters": {
        "url": "https://www.reuters.com",
        "country": "UK", "language": "English",
        "bias": "center", "credibility": 0.95, "category": "wire_agency",
    },
    "Associated Press": {
        "url": "https://apnews.com",
        "country": "US", "language": "English",
        "bias": "center", "credibility": 0.95, "category": "wire_agency",
    },
    "AFP (Agence France-Presse)": {
        "url": "https://www.france24.com",
        "country": "France", "language": "English/French",
        "bias": "center", "credibility": 0.90, "category": "wire_agency",
    },
    "BBC News": {
        "url": "https://www.bbc.com",
        "country": "UK", "language": "English",
        "bias": "center", "credibility": 0.90, "category": "public_broadcast",
    },
    "BBC World": {
        "url": "https://www.bbc.com/news/world",
        "country": "UK", "language": "English",
        "bias": "center", "credibility": 0.90, "category": "public_broadcast",
    },
    "BBC Middle East": {
        "url": "https://www.bbc.com/news/world/middle_east",
        "country": "UK", "language": "English",
        "bias": "center", "credibility": 0.90, "category": "public_broadcast",
    },
    "CNN World": {
        "url": "https://www.cnn.com",
        "country": "US", "language": "English",
        "bias": "center-left", "credibility": 0.78, "category": "broadcast",
    },
    "CNN Middle East": {
        "url": "https://www.cnn.com/middle-east",
        "country": "US", "language": "English",
        "bias": "center-left", "credibility": 0.78, "category": "broadcast",
    },
    "NPR News": {
        "url": "https://www.npr.org",
        "country": "US", "language": "English",
        "bias": "center-left", "credibility": 0.85, "category": "public_broadcast",
    },
    "NPR World": {
        "url": "https://www.npr.org/sections/world",
        "country": "US", "language": "English",
        "bias": "center-left", "credibility": 0.85, "category": "public_broadcast",
    },
    "New York Times World": {
        "url": "https://www.nytimes.com/section/world",
        "country": "US", "language": "English",
        "bias": "center-left", "credibility": 0.88, "category": "general",
    },
    "New York Times Middle East": {
        "url": "https://www.nytimes.com/section/world/middleeast",
        "country": "US", "language": "English",
        "bias": "center-left", "credibility": 0.88, "category": "general",
    },
    "Washington Post World": {
        "url": "https://www.washingtonpost.com/world/",
        "country": "US", "language": "English",
        "bias": "center-left", "credibility": 0.86, "category": "general",
    },
    "Wall Street Journal World": {
        "url": "https://www.wsj.com/world",
        "country": "US", "language": "English",
        "bias": "center-right", "credibility": 0.88, "category": "business",
    },
    "PBS NewsHour": {
        "url": "https://www.pbs.org/newshour",
        "country": "US", "language": "English",
        "bias": "center", "credibility": 0.88, "category": "public_broadcast",
    },
    "Axios": {
        "url": "https://www.axios.com",
        "country": "US", "language": "English",
        "bias": "center", "credibility": 0.82, "category": "analysis",
    },
    "The Atlantic": {
        "url": "https://www.theatlantic.com",
        "country": "US", "language": "English",
        "bias": "center-left", "credibility": 0.84, "category": "analysis",
    },
    "Foreign Policy": {
        "url": "https://foreignpolicy.com",
        "country": "US", "language": "English",
        "bias": "center", "credibility": 0.88, "category": "analysis",
    },
    "Foreign Affairs": {
        "url": "https://www.foreignaffairs.com",
        "country": "US", "language": "English",
        "bias": "center", "credibility": 0.92, "category": "think_tank",
    },
    "The Guardian World": {
        "url": "https://www.theguardian.com/world",
        "country": "UK", "language": "English",
        "bias": "center-left", "credibility": 0.82, "category": "general",
    },
    "The Guardian Middle East": {
        "url": "https://www.theguardian.com/world/middleeast",
        "country": "UK", "language": "English",
        "bias": "center-left", "credibility": 0.82, "category": "general",
    },
    "The Telegraph World": {
        "url": "https://www.telegraph.co.uk",
        "country": "UK", "language": "English",
        "bias": "center-right", "credibility": 0.78, "category": "general",
    },
    "The Independent": {
        "url": "https://www.independent.co.uk",
        "country": "UK", "language": "English",
        "bias": "center-left", "credibility": 0.76, "category": "general",
    },
    "Financial Times": {
        "url": "https://www.ft.com",
        "country": "UK", "language": "English",
        "bias": "center", "credibility": 0.90, "category": "business",
    },
    "The Economist": {
        "url": "https://www.economist.com",
        "country": "UK", "language": "English",
        "bias": "center", "credibility": 0.90, "category": "analysis",
    },
    "Sky News": {
        "url": "https://news.sky.com",
        "country": "UK", "language": "English",
        "bias": "center", "credibility": 0.78, "category": "broadcast",
    },
    "Euronews": {
        "url": "https://www.euronews.com",
        "country": "France", "language": "English/Multi",
        "bias": "center", "credibility": 0.78, "category": "broadcast",
    },
    "Deutsche Welle (DW)": {
        "url": "https://www.dw.com",
        "country": "Germany", "language": "English/German",
        "bias": "center", "credibility": 0.85, "category": "public_broadcast",
    },
    "France24 English": {
        "url": "https://www.france24.com/en",
        "country": "France", "language": "English",
        "bias": "center", "credibility": 0.82, "category": "public_broadcast",
    },
    "France24 Middle East": {
        "url": "https://www.france24.com/en/middle-east",
        "country": "France", "language": "English",
        "bias": "center", "credibility": 0.82, "category": "public_broadcast",
    },
    "The Local (Sweden)": {
        "url": "https://www.thelocal.se",
        "country": "Sweden", "language": "English",
        "bias": "center", "credibility": 0.72, "category": "general",
    },
    "POLITICO Europe": {
        "url": "https://www.politico.eu",
        "country": "EU", "language": "English",
        "bias": "center", "credibility": 0.84, "category": "analysis",
    },
    "Irish Times World": {
        "url": "https://www.irishtimes.com",
        "country": "Ireland", "language": "English",
        "bias": "center", "credibility": 0.80, "category": "general",
    },
    "The Straits Times": {
        "url": "https://www.straitstimes.com",
        "country": "Singapore", "language": "English",
        "bias": "center", "credibility": 0.80, "category": "general",
    },
    "South China Morning Post": {
        "url": "https://www.scmp.com",
        "country": "Hong Kong", "language": "English",
        "bias": "center", "credibility": 0.78, "category": "general",
    },
    "NHK World Japan": {
        "url": "https://www3.nhk.or.jp/nhkworld",
        "country": "Japan", "language": "English",
        "bias": "center", "credibility": 0.85, "category": "public_broadcast",
    },
    "Globe and Mail (Canada)": {
        "url": "https://www.theglobeandmail.com",
        "country": "Canada", "language": "English",
        "bias": "center", "credibility": 0.82, "category": "general",
    },
    "Sydney Morning Herald": {
        "url": "https://www.smh.com.au",
        "country": "Australia", "language": "English",
        "bias": "center", "credibility": 0.80, "category": "general",
    },

    # ── ARABIC & REGIONAL SOURCES (30) ────────────────────────────────────
    "Al Jazeera English": {
        "url": "https://www.aljazeera.com",
        "country": "Qatar", "language": "English",
        "bias": "center-left", "credibility": 0.75, "category": "broadcast",
    },
    "Al Jazeera Arabic": {
        "url": "https://www.aljazeera.net",
        "country": "Qatar", "language": "Arabic",
        "bias": "center-left", "credibility": 0.72, "category": "broadcast",
    },
    "BBC Arabic": {
        "url": "https://www.bbc.com/arabic",
        "country": "UK", "language": "Arabic",
        "bias": "center", "credibility": 0.88, "category": "public_broadcast",
    },
    "Al Arabiya English": {
        "url": "https://english.alarabiya.net",
        "country": "Saudi Arabia", "language": "English",
        "bias": "center-right", "credibility": 0.74, "category": "broadcast",
    },
    "Al Arabiya Arabic": {
        "url": "https://www.alarabiya.net",
        "country": "Saudi Arabia", "language": "Arabic",
        "bias": "center-right", "credibility": 0.72, "category": "broadcast",
    },
    "Sky News Arabia": {
        "url": "https://www.skynewsarabia.com",
        "country": "UAE", "language": "Arabic",
        "bias": "center-right", "credibility": 0.72, "category": "broadcast",
    },
    "Arab News": {
        "url": "https://www.arabnews.com",
        "country": "Saudi Arabia", "language": "English",
        "bias": "center-right", "credibility": 0.72, "category": "general",
    },
    "Middle East Eye": {
        "url": "https://www.middleeasteye.net",
        "country": "UK", "language": "English",
        "bias": "center-left", "credibility": 0.72, "category": "analysis",
    },
    "Middle East Monitor": {
        "url": "https://www.middleeastmonitor.com",
        "country": "UK", "language": "English",
        "bias": "left", "credibility": 0.65, "category": "analysis",
    },
    "WAFA (Palestinian News Agency)": {
        "url": "https://english.wafa.ps",
        "country": "Palestine", "language": "English/Arabic",
        "bias": "left", "credibility": 0.55, "category": "government",
    },
    "Ma'an News": {
        "url": "https://www.maannews.net",
        "country": "Palestine", "language": "English/Arabic",
        "bias": "center-left", "credibility": 0.60, "category": "general",
    },
    "Palestine Chronicle": {
        "url": "https://www.palestinechronicle.com",
        "country": "Palestine", "language": "English",
        "bias": "left", "credibility": 0.55, "category": "analysis",
    },
    "Gulf News": {
        "url": "https://gulfnews.com",
        "country": "UAE", "language": "English",
        "bias": "center-right", "credibility": 0.72, "category": "general",
    },
    "Khaleej Times": {
        "url": "https://www.khaleejtimes.com",
        "country": "UAE", "language": "English",
        "bias": "center", "credibility": 0.72, "category": "general",
    },
    "The National (UAE)": {
        "url": "https://www.thenationalnews.com",
        "country": "UAE", "language": "English",
        "bias": "center-right", "credibility": 0.75, "category": "general",
    },
    "Saudi Gazette": {
        "url": "https://saudigazette.com.sa",
        "country": "Saudi Arabia", "language": "English",
        "bias": "center-right", "credibility": 0.65, "category": "general",
    },
    "Ahram Online": {
        "url": "https://english.ahram.org.eg",
        "country": "Egypt", "language": "English",
        "bias": "center", "credibility": 0.70, "category": "general",
    },
    "Egypt Independent": {
        "url": "https://www.egyptindependent.com",
        "country": "Egypt", "language": "English",
        "bias": "center", "credibility": 0.68, "category": "general",
    },
    "Daily News Egypt": {
        "url": "https://www.dailynewsegypt.com",
        "country": "Egypt", "language": "English",
        "bias": "center", "credibility": 0.65, "category": "general",
    },
    "Roya News (Jordan)": {
        "url": "https://en.royanews.tv",
        "country": "Jordan", "language": "English/Arabic",
        "bias": "center", "credibility": 0.70, "category": "broadcast",
    },
    "Jordan Times": {
        "url": "https://www.jordantimes.com",
        "country": "Jordan", "language": "English",
        "bias": "center", "credibility": 0.72, "category": "general",
    },
    "Daily Star (Lebanon)": {
        "url": "https://www.dailystar.com.lb",
        "country": "Lebanon", "language": "English",
        "bias": "center", "credibility": 0.68, "category": "general",
    },
    "L'Orient Today (Lebanon)": {
        "url": "https://today.lorientlejour.com",
        "country": "Lebanon", "language": "English",
        "bias": "center", "credibility": 0.75, "category": "general",
    },
    "Naharnet (Lebanon)": {
        "url": "https://www.naharnet.com",
        "country": "Lebanon", "language": "English",
        "bias": "center", "credibility": 0.65, "category": "general",
    },
    "Anadolu Agency": {
        "url": "https://www.aa.com.tr",
        "country": "Turkey", "language": "English/Turkish",
        "bias": "center-right", "credibility": 0.68, "category": "wire_agency",
    },
    "TRT World": {
        "url": "https://www.trtworld.com",
        "country": "Turkey", "language": "English",
        "bias": "center-right", "credibility": 0.68, "category": "public_broadcast",
    },
    "Daily Sabah": {
        "url": "https://www.dailysabah.com",
        "country": "Turkey", "language": "English",
        "bias": "right", "credibility": 0.60, "category": "general",
    },
    "Hürriyet Daily News": {
        "url": "https://www.hurriyetdailynews.com",
        "country": "Turkey", "language": "English",
        "bias": "center", "credibility": 0.70, "category": "general",
    },
    "Morocco World News": {
        "url": "https://www.moroccoworldnews.com",
        "country": "Morocco", "language": "English",
        "bias": "center", "credibility": 0.65, "category": "general",
    },
    "The North Africa Journal": {
        "url": "https://north-africa.com",
        "country": "North Africa", "language": "English",
        "bias": "center", "credibility": 0.60, "category": "analysis",
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

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

# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

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
    """Get metadata for a source. Falls back to defaults if unknown."""
    return SOURCE_REGISTRY.get(source_name, {
        "url": "",
        "country": "Unknown",
        "language": "Unknown",
        "bias": "unknown",
        "credibility": 0.5,
        "category": "unknown"
    })


# ── Source Ownership & Funding Transparency ───────────────────────────────────
# Static data about who owns, funds, and controls each source.
# Transparency score: 0.0 (opaque) – 1.0 (fully transparent).
# This helps users evaluate potential conflicts of interest.

SOURCE_OWNERSHIP_DATA: dict[str, dict] = {
    # ── Israeli Sources ───────────────────────────────────────────────────
    "Haaretz": {
        "ownership": "Haaretz Group (Schocken family, ~25% + DuMont Schauberg)",
        "funding_model": "Subscription + advertising",
        "notable_affiliations": "Center-left editorial line, owned by Schocken family since 1937",
        "transparency_score": 0.8,
        "press_freedom_note": "Considered Israel's newspaper of record for liberal readership",
    },
    "Times of Israel": {
        "ownership": "Times of Israel (founded by Seth Klarman backing)",
        "funding_model": "Advertising + sponsored content + blogs",
        "notable_affiliations": "Founded by David Horovitz (ex-Jerusalem Post editor)",
        "transparency_score": 0.7,
        "press_freedom_note": "English-language, broadly centrist with opinion diversity",
    },
    "Jerusalem Post": {
        "ownership": "Eli Azur (acquired 2014)",
        "funding_model": "Subscription + advertising + events",
        "notable_affiliations": "Shifted rightward under Azur ownership",
        "transparency_score": 0.6,
        "press_freedom_note": "Oldest English-language daily in Israel, center-right editorial",
    },
    "Ynet News": {
        "ownership": "Yedioth Ahronoth Group",
        "funding_model": "Advertising (free online)",
        "notable_affiliations": "Part of Yedioth Ahronoth media empire",
        "transparency_score": 0.7,
        "press_freedom_note": "Israel's most-visited news site",
    },
    "Kan News": {
        "ownership": "Israeli Public Broadcasting Corporation (state-funded)",
        "funding_model": "Government budget (public broadcaster)",
        "notable_affiliations": "Replaced IBA in 2017, mandated editorial independence",
        "transparency_score": 0.85,
        "press_freedom_note": "Public broadcaster with legal mandate for balanced coverage",
    },
    "Israel Hayom": {
        "ownership": "Miriam Adelson (Adelson family)",
        "funding_model": "Free distribution (advertising + owner subsidy)",
        "notable_affiliations": "Associated with Likud / PM Netanyahu, known as 'Bibiton'",
        "transparency_score": 0.4,
        "press_freedom_note": "Free daily with highest circulation, criticized for pro-Netanyahu bias",
    },
    "Arutz Sheva": {
        "ownership": "Arutz Sheva (settler media network)",
        "funding_model": "Donations + advertising",
        "notable_affiliations": "Religious Zionist movement, settler community oriented",
        "transparency_score": 0.5,
        "press_freedom_note": "National-religious perspective, significant online following",
    },
    "Channel 12 (Mako)": {
        "ownership": "Keshet Broadcasting (publicly traded)",
        "funding_model": "Advertising + streaming subscriptions",
        "notable_affiliations": "Israel's most-watched TV channel",
        "transparency_score": 0.75,
        "press_freedom_note": "Commercial broadcaster, mainstream audience",
    },
    "Channel 13 (Reshet)": {
        "ownership": "Reshet Media (Len Blavatnik / Access Industries)",
        "funding_model": "Advertising",
        "notable_affiliations": "Owned by Ukrainian-British billionaire Blavatnik",
        "transparency_score": 0.6,
        "press_freedom_note": "Second-largest commercial broadcaster",
    },
    "i24 News": {
        "ownership": "Patrick Drahi (Altice Group)",
        "funding_model": "Advertising + cable/satellite distribution",
        "notable_affiliations": "International focus, French-Israeli billionaire Drahi",
        "transparency_score": 0.6,
        "press_freedom_note": "Multilingual broadcaster targeting international audience",
    },
    "Walla News": {
        "ownership": "Bezeq (formerly Shaul Elovitch, now Searchlight Capital)",
        "funding_model": "Advertising",
        "notable_affiliations": "Previously implicated in Netanyahu Case 4000",
        "transparency_score": 0.5,
        "press_freedom_note": "Major portal, editorial independence questioned during Elovitch era",
    },
    "Globes": {
        "ownership": "Globes Group (Fishman family)",
        "funding_model": "Subscription + advertising",
        "notable_affiliations": "Business-focused, economically liberal",
        "transparency_score": 0.7,
        "press_freedom_note": "Leading business daily",
    },
    "TheMarker": {
        "ownership": "Haaretz Group",
        "funding_model": "Subscription + advertising",
        "notable_affiliations": "Part of Haaretz Group, economic investigative journalism",
        "transparency_score": 0.8,
        "press_freedom_note": "Israel's leading economic newspaper",
    },
    "+972 Magazine": {
        "ownership": "Independent nonprofit",
        "funding_model": "Donations + grants (NIF, European foundations)",
        "notable_affiliations": "Israeli-Palestinian journalist collective",
        "transparency_score": 0.8,
        "press_freedom_note": "Progressive independent journalism, critical of occupation",
    },

    # ── International Wire Agencies ───────────────────────────────────────
    "Reuters": {
        "ownership": "Thomson Reuters Corporation",
        "funding_model": "Subscription (financial terminals) + licensing",
        "notable_affiliations": "Largest international wire agency",
        "transparency_score": 0.9,
        "press_freedom_note": "Global gold standard for factual reporting",
    },
    "Associated Press": {
        "ownership": "Nonprofit cooperative (member newspapers)",
        "funding_model": "Licensing + member fees",
        "notable_affiliations": "Nonprofit, member-owned cooperative",
        "transparency_score": 0.95,
        "press_freedom_note": "Founded 1846, nonprofit wire agency, highest factual reporting standards",
    },
    "BBC News": {
        "ownership": "BBC (UK public broadcaster)",
        "funding_model": "UK licence fee (public funding)",
        "notable_affiliations": "UK government charter, mandated impartiality",
        "transparency_score": 0.9,
        "press_freedom_note": "World's largest public broadcaster, strict impartiality guidelines",
    },

    # ── US Sources ────────────────────────────────────────────────────────
    "CNN World": {
        "ownership": "Warner Bros. Discovery",
        "funding_model": "Advertising + cable subscription",
        "notable_affiliations": "Part of WBD media conglomerate",
        "transparency_score": 0.7,
        "press_freedom_note": "24-hour cable news, center-left editorial perspective",
    },
    "New York Times World": {
        "ownership": "The New York Times Company (Sulzberger family)",
        "funding_model": "Subscription + advertising",
        "notable_affiliations": "Family-controlled since 1896",
        "transparency_score": 0.85,
        "press_freedom_note": "Newspaper of record, Pulitzer Prize leader",
    },
    "Washington Post World": {
        "ownership": "Jeff Bezos (Nash Holdings)",
        "funding_model": "Subscription + advertising",
        "notable_affiliations": "Owned by Amazon founder since 2013",
        "transparency_score": 0.75,
        "press_freedom_note": "Major US broadsheet, known for investigative journalism",
    },

    # ── Arabic & Regional Sources ─────────────────────────────────────────
    "Al Jazeera English": {
        "ownership": "Qatar Foundation / Government of Qatar",
        "funding_model": "Qatar state funding",
        "notable_affiliations": "Qatari government funded, editorial independence debated",
        "transparency_score": 0.5,
        "press_freedom_note": "State-funded, criticized for Qatar bias but praised for ME coverage",
    },
    "Al Arabiya English": {
        "ownership": "MBC Group (Saudi Arabia)",
        "funding_model": "Advertising + Saudi state support",
        "notable_affiliations": "Saudi-funded, counter to Al Jazeera editorial line",
        "transparency_score": 0.4,
        "press_freedom_note": "Saudi-oriented perspective on Middle East affairs",
    },
    "Middle East Eye": {
        "ownership": "Middle East Eye Ltd (UK-based)",
        "funding_model": "Donations + advertising",
        "notable_affiliations": "Founded by former Guardian journalist, Qatar-linked funding alleged",
        "transparency_score": 0.5,
        "press_freedom_note": "Pro-Palestinian perspective, investigative journalism",
    },
    "Anadolu Agency": {
        "ownership": "Turkish government (state-run)",
        "funding_model": "Turkish state funding",
        "notable_affiliations": "Turkish state news agency, government editorial control",
        "transparency_score": 0.3,
        "press_freedom_note": "State-run, follows Turkish government editorial line",
    },
    "TRT World": {
        "ownership": "Turkish Radio and Television Corporation (state-run)",
        "funding_model": "Turkish state funding",
        "notable_affiliations": "Turkish government broadcaster",
        "transparency_score": 0.3,
        "press_freedom_note": "State broadcaster, reflects Turkish government positions",
    },
}


def get_source_ownership(source_name: str) -> dict:
    """Get ownership and funding transparency info for a source."""
    data = SOURCE_OWNERSHIP_DATA.get(source_name)
    if data:
        return {"source_name": source_name, **data}
    return {
        "source_name": source_name,
        "ownership": "Unknown",
        "funding_model": "Unknown",
        "notable_affiliations": "No data available",
        "transparency_score": 0.0,
        "press_freedom_note": "Ownership data not yet collected for this source.",
    }


def get_source_count() -> dict:
    """Return a summary of source counts by region."""
    return {
        "israeli": len(ISRAELI_SOURCES_FEEDS),
        "international": len(INTERNATIONAL_SOURCES_FEEDS),
        "arabic_regional": len(ARABIC_SOURCES_FEEDS),
        "category_supplementary": len(RSS_FEEDS),
        "total_feeds": len(get_all_feeds()),
        "total_registry": len(SOURCE_REGISTRY),
        "sources_with_ownership_data": len(SOURCE_OWNERSHIP_DATA),
    }

