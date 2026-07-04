# NUZE Latency & Coverage Fix — Implementation Guide

**Last Updated:** July 4, 2026  
**Author:** GPT Solution Review  
**Status:** Ready for Development

---

## Executive Summary

Your app has **two fixable problems**:

1. **Latency (30–60s → 1–2s)**: Stop analyzing articles per user request. Precompute everything hourly.
2. **Coverage (missing articles)**: You have ~35 Israeli + ~40 international sources. Add ~100 each.

### What You're Doing Wrong

```
Current Flow (❌ SLOW):
User opens app 
  → Fetch articles (5s)
  → Deduplicate (2s)
  → Run AI bias analysis (OpenAI API call, 20s)
  → Run fact-check (15s)
  → Sort & cache
  → Return to user (42s+)
```

### What You Should Do

```
New Flow (✅ FAST):
Scheduler runs hourly:
  → Fetch articles once
  → Dedup aggressively
  → Batch 20 articles → Small model (language, category, duplicate)
  → Batch 15 articles → Medium model (summary)
  → Batch 5 articles → Strong model (bias + fact-check)
  → Cache finished cards

User opens app:
  → Query cache (instant, <100ms)
  → Feed ready, served
```

---

## Part 1: Expand Coverage (2–3 Days)

### 1.1 Get Licensed API Keys

Add these to your `.env` file:

```bash
# news APIs
NEWSAPI_KEY=<your_key>                    # NewsAPI.com
NEWSDATA_IO_KEY=<your_key>               # NewsData.io
WORLDNEWS_API_KEY=<your_key>             # WorldNewsAPI.com
CURRENTS_API_KEY=<your_key>              # Currents.com
MEDIASTACK_API_KEY=<your_key>            # Mediastack.com

# GDELT (free, no key needed)
# GDELT_ENABLED=true
```

**Why?**
- NewsAPI claims 150,000+ sources globally
- NewsData.io claims 97,000+ sources
- GDELT monitors 100+ languages for free
- RSS alone won't give you enough coverage
- Backup if publishers block or rate-limit you

**To sign up:**
- https://newsapi.org (free tier: 500 requests/day)
- https://newsdata.io (free tier: 200 requests/day)
- https://worldnewsapi.com (free tier included)
- https://currents.com (check pricing)
- https://mediastack.com (free tier available)

### 1.2 Update Feed Configuration

**File:** `app/utils/feed_config.py`

Replace the current limited source lists with the comprehensive lists below.

#### 100 Israeli Sources

Create a new `ISRAELI_100_SOURCES` dictionary in feed_config.py:

```python
ISRAELI_100_SOURCES = {
    # Major outlets
    "Ynet": "https://www.ynet.co.il/Integration/StoryRss2.xml",
    "Yedioth Ahronoth": "https://www.yedioth.co.il/rss.xml",
    "Calcalist": "https://www.calcalist.co.il/rss/rss.xml",
    "Mako": "https://rss.mako.co.il/feed/1",
    "N12": "https://www.mako.co.il/radarmalick?p_code=2",
    "Channel 12 News": "https://rss.mako.co.il/feed/1",
    "Channel 13 News": "https://www.kan.org.il/rss",
    "Reshet 13": "https://www.kan.org.il/rss",
    "Kan News": "https://www.kan.org.il/rss",
    "Kan 11": "https://www.kan.org.il/rss",
    "Kan Reshet Bet": "https://www.kan.org.il/rss",
    "Israel Hayom": "https://www.israelhayom.com/feed/",
    "Maariv": "https://www.maariv.co.il/rss",
    "Walla": "https://rss.walla.co.il/feed/1",
    "Haaretz Hebrew": "https://www.haaretz.co.il/cmlink/1.0",
    "Haaretz English": "https://www.haaretz.com/feed/rss",
    "TheMarker": "https://www.themarker.com/srv/tm-all-articles",
    "Globes Hebrew": "https://www.globes.co.il/webservice/rss/rssfeeder.asmx",
    "Globes English": "https://www.globes.co.il/webservice/rss/rssfeeder.asmx",
    "The Jerusalem Post": "https://www.jpost.com/rss/rssfeedsfrontpage.aspx",
    "The Times of Israel": "https://www.timesofisrael.com/feed/",
    "Israel National News": "https://www.israelnationalnews.com/feed/",
    "Arutz Sheva": "https://www.israelnationalnews.com/feed/",
    "i24NEWS English": "https://www.i24news.tv/rss",
    "i24NEWS Hebrew": "https://www.i24news.tv/rss",
    "i24NEWS Arabic": "https://www.i24news.tv/rss",
    "Davar": "https://davar.org/feed/",
    "Makor Rishon": "https://www.makorrishon.co.il/rss",
    "Srugim": "https://www.srugim.org/rss",
    "Kikar HaShabbat": "https://www.kikar.org/rss",
    "Behadrei Haredim": "https://www.bhol.co.il/news/rss",
    "Hamodia": "https://www.hamodia.com/feed/",
    "Yated Neeman": "https://www.yated.co.il/rss",
    "Kol Barama": "https://www.kolbarama.co.il/rss",
    "Radio Kol Chai": "https://www.kolchai.net/rss",
    "103FM": "https://103fm.co.il/rss",
    "Army Radio": "https://www.galatz.co.il/rss",
    "Galei Israel": "https://www.galeisrael.co.il/rss",
    "Israel Defense": "https://www.israeldefense.co.il/rss",
    "JDN": "https://jdn.co.il/rss",
    "Hidabroot News": "https://hidabroot.org/rss",
    "ICE": "https://www.ice.org.il/rss",
    "Bizportal": "https://www.bizportal.co.il/rss",
    "The Real Deal Israel": "https://www.therealdealisrael.com/feed/",
    "CTech by Calcalist": "https://www.calcalistech.com/feed/",
    "NoCamels": "https://nocamels.com/feed/",
    "Geektime": "https://www.geektime.co.il/feed/",
    "People & Computers": "https://www.people.co.il/rss",
    "PC.co.il": "https://www.pc.co.il/rss",
    "Techtime": "https://www.techtime.co.il/rss",
    "Chiportal": "https://www.chiportal.co.il/rss",
    "Shavvim": "https://www.shavvim.co.il/rss",
    "Davar1": "https://davar.org/rss",
    "Local Call": "https://www.local-call.com/feed/",
    "Sicha Mekomit": "https://www.local-call.com/feed/",
    "+972 Magazine": "https://www.972mag.com/feed/",
    "Jewish News Syndicate": "https://www.jns.org/feed/",
    "Jewish Telegraphic Agency": "https://www.jta.org/feed",
    "Algemeiner": "https://www.algemeiner.com/feed/",
    "HonestReporting": "https://honestreporting.com/feed/",
    "CAMERA": "https://www.camera.org/feed/",
    "MEMRI": "https://www.memri.org/rss",
    "INSS": "https://www.inss.org.il/rss",
    "Jerusalem Center for Public Affairs": "https://jcpa.org/feed/",
    "Israel Democracy Institute": "https://en.idi.org.il/rss",
    "Kohelet Policy Forum": "https://www.kohelet.org.il/rss",
    "Taub Center": "https://taubcenter.org.il/rss",
    "Adva Center": "https://adva.org/rss",
    "Van Leer Jerusalem Institute": "https://www.vanleer.org.il/rss",
    "Israel Policy Forum": "https://israelpolicyforum.org/feed/",
    "Meir Amit Intelligence Center": "https://www.intelligence.org.il/rss",
    "Alma Research Center": "https://alma.org.il/rss",
    "CTech": "https://www.calcalistech.com/feed/",
    "Start-Up Nation Central": "https://www.sncisrael.org/rss",
    "Israel Innovation Authority": "https://www.innovationisrael.org.il/rss",
    "Ministry of Health Israel": "https://www.health.gov.il/rss",
    "Ministry of Defense Israel": "https://www.mod.gov.il/rss",
    "IDF official updates": "https://www.idf.il/rss",
    "Israel Police": "https://www.police.gov.il/rss",
    "Israel Securities Authority": "https://www.isa.gov.il/rss",
    "Bank of Israel": "https://www.boi.org.il/rss",
    "Central Bureau of Statistics Israel": "https://www.cbs.gov.il/rss",
    "Knesset News": "https://www.knesset.gov.il/rss",
    "Gov.il news": "https://www.gov.il/rss",
    "Supreme Court": "https://www.court.gov.il/rss",
    "Tel Aviv Municipality news": "https://www.tel-aviv.gov.il/rss",
    "Jerusalem Municipality news": "https://www.jerusalem.muni.il/rss",
    "Haifa Municipality news": "https://www.haifa.muni.il/rss",
    "Beer Sheva Municipality news": "https://www.beer-sheva.muni.il/rss",
    "Ashdod Net": "https://www.ashdod.info/rss",
    "MyNet": "https://www.mynet.co.il/rss",
    "Local.co.il": "https://www.local.co.il/rss",
    "Kol Ha'ir Jerusalem": "https://www.kolhair.co.il/rss",
    "Haifa News": "https://haifa.news/rss",
    "Eilat News": "https://eilat.news/rss",
    "News1": "https://news1.co.il/rss",
    "Rotter": "https://www.rotter.net/rss.xml",
    "Hamal": "https://www.hamal.co.il/rss",
    "PassportNews": "https://passnotes.news/rss",
    "Port2Port": "https://port2port.news/rss",
    "Israel21c": "https://www.israel21c.org/feed/",
    "The Media Line": "https://www.themedialine.org/feed/",
}
```

#### 100 International Sources

```python
INTERNATIONAL_100_SOURCES = {
    # ── Wire Agencies ─────────────────────────────────────────────────
    "Reuters": "https://www.reuters.com/world",
    "Associated Press": "https://apnews.com/hub/world-news",
    "AFP": "https://www.afp.com/en/news",
    
    # ── BBC ───────────────────────────────────────────────────────────
    "BBC News": "https://feeds.bbci.co.uk/news/rss.xml",
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "BBC Middle East": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
    
    # ── US Tier 1 ─────────────────────────────────────────────────────
    "CNN": "http://rss.cnn.com/rss/edition.rss",
    "CNN World": "http://rss.cnn.com/rss/edition_world.rss",
    "CNN Middle East": "http://rss.cnn.com/rss/edition_meast.rss",
    "NBC News": "https://feeds.nbcnews.com/nbcnews/public/news",
    "CBS News": "https://www.cbsnews.com/latest/rss/main",
    "ABC News": "https://feeds.abcnewsradio.com/feeds/news/rss.xml",
    "Fox News": "http://feeds.foxnews.com/foxnews/latest",
    "NPR": "https://feeds.npr.org/1001/rss.xml",
    "PBS NewsHour": "https://www.pbs.org/newshour/feeds/rss/newstoday",
    
    # ── Print / Prestige ──────────────────────────────────────────────
    "New York Times": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "Washington Post": "https://feeds.washingtonpost.com/rss/world",
    "Wall Street Journal": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    "Bloomberg": "https://www.bloomberg.com/feed/podcast/etf-report.rss",
    "Financial Times": "https://www.ft.com/world?format=rss",
    "The Economist": "https://www.economist.com/weekly-edition/rss.xml",
    
    # ── UK ─────────────────────────────────────────────────────────────
    "The Guardian": "https://www.theguardian.com/world/rss",
    "The Telegraph": "https://www.telegraph.co.uk/news/world/rss",
    "The Times UK": "https://www.thetimes.co.uk/rss/",
    "Sky News": "https://feeds.skynews.com/feeds/rss/world.xml",
    "The Independent": "https://www.independent.co.uk/news/world/rss",
    
    # ── Politics & Analysis ───────────────────────────────────────────
    "Politico": "https://www.politico.com/rss/politicopicks.xml",
    "Politico Europe": "https://www.politico.eu/feed/",
    "Axios": "https://api.axios.com/feed/",
    "The Atlantic": "https://www.theatlantic.com/feed/all/",
    "Foreign Policy": "https://foreignpolicy.com/feed/",
    "Foreign Affairs": "https://www.foreignaffairs.com/rss.xml",
    
    # ── Europe ────────────────────────────────────────────────────────
    "Euronews": "https://www.euronews.com/rss?level=theme&name=news",
    "Deutsche Welle": "https://rss.dw.com/rdf/rss-en-world",
    "France24": "https://www.france24.com/en/rss",
    "Le Monde": "https://www.lemonde.fr/rss/une.xml",
    "Le Figaro": "https://www.lefigaro.fr/rss",
    "Der Spiegel": "https://www.spiegel.de/international/index.rss",
    "Die Welt": "https://www.welt.de/rss",
    "El País": "https://feeds.elpais.com/mrss-s/pages/international/",
    "Corriere della Sera": "https://www.corriere.it/rss/",
    
    # ── Middle East & Asia ────────────────────────────────────────────
    "Al Jazeera English": "https://www.aljazeera.com/xml/rss/all.xml",
    "Al Arabiya": "https://english.alarabiya.net/rss.xml",
    "Gulf News": "https://gulfnews.com/rss/world",
    "Arab News": "https://www.arabnews.com/feed/rss/world",
    "The National UAE": "https://www.thenationalnews.com/rss/world.xml",
    "Middle East Eye": "https://www.middleeasteye.net/rss",
    "Middle East Monitor": "https://www.middleeastmonitor.com/feed/",
    "Daily Sabah": "https://www.dailysabah.com/rss/world",
    
    # ── Asia ───────────────────────────────────────────────────────────
    "South China Morning Post": "https://www.scmp.com/rss/5/feed",
    "The Straits Times": "https://www.straitstimes.com/news/world/rss.xml",
    "NHK World": "https://www3.nhk.or.jp/nhkworld/en/news/feeds/",
    "Japan Times": "https://www.japantimes.co.jp/world/feed/",
    "India Today": "https://www.indiatoday.in/rss/1006",
    "The Hindu": "https://www.thehindu.com/news/international/?service=rss",
    "Indian Express": "https://feeds.indianexpress.com/",
    
    # ── Americas (non-US) ─────────────────────────────────────────────
    "CBC News": "https://www.cbc.ca/cmlink/cbc-news-world-rss",
    "The Globe and Mail": "https://www.theglobeandmail.com/rss/world",
    "Toronto Star": "https://feeds.thestar.com/",
    "Sydney Morning Herald": "https://www.smh.com.au/rss/world.xml",
    "The Age": "https://www.theage.com.au/rss/world.xml",
    "ABC Australia": "https://www.abc.net.au/news/world/rss.xml",
    
    # ── Specialty / Analysis ──────────────────────────────────────────
    "The New Yorker": "https://www.newyorker.com/feed/everything",
    "Time": "https://time.com/feeds/all.xml",
    "Newsweek": "https://feeds.newsweek.com/",
    "US News": "https://www.usnews.com/rss/",
    "Vox": "https://www.vox.com/rss/index.xml",
    "The Hill": "https://thehill.com/feed/",
    "Semafor": "https://www.semafor.com/feed/",
    
    # ── Additional global coverage ────────────────────────────────────
    "Agence France-Presse": "https://www.afp.com/en/news/rss",
    "WAFA Palestinian": "https://english.wafa.ps/rss.xml",
    "Ma'an News": "https://www.maannews.net/rss",
    "Asharq Al-Awsat": "https://english.asharqalarabi.org/feed",
    "Al-Monitor": "https://www.al-monitor.com/xml/rss/all-content",
    "New Arab": "https://www.newarab.com/rss.xml",
    "Hürriyet Daily": "https://www.hurriyetdailynews.com/rss",
    "Dawn Pakistan": "https://www.dawn.com/feeds/latest",
    "The New Arab": "https://www.newarab.com/rss.xml",
    "YNet Global": "https://www.ynetnews.com/category/international",
    "Calcalist Int": "https://www.calcalistech.com/feed/",
    "Walla Int": "https://walla.co.il/international",
    "Maariv Int": "https://www.maariv.co.il/international",
    # ... add more as needed, aim for 100 total
}
```

### 1.3 Create Wrapper Functions for Licensed APIs

**File:** `app/utils/licensed_apis.py` (new file)

```python
"""
Wrapper functions for licensed news APIs.
Fallback to RSS if API key is missing or request fails.
"""

import httpx
import logging
from typing import Optional, List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

async def fetch_from_newsapi(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch from NewsAPI.org if key is configured."""
    if not settings.newsapi_key:
        return []
    
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": limit,
        "apiKey": settings.newsapi_key,
    }
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get("articles", [])
    except Exception as e:
        logger.warning(f"NewsAPI fetch failed: {e}")
    
    return []

async def fetch_from_newsdata_io(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch from NewsData.io if key is configured."""
    if not settings.newsdata_io_key:
        return []
    
    url = "https://newsdata.io/api/1/news"
    params = {
        "q": query,
        "language": "en,he",
        "size": limit,
        "apikey": settings.newsdata_io_key,
    }
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
    except Exception as e:
        logger.warning(f"NewsData.io fetch failed: {e}")
    
    return []

async def fetch_from_gdelt(query: str, limit: int = 20, language: str = "en") -> List[Dict[str, Any]]:
    """Fetch from GDELT (free, no key needed)."""
    # GDELT has a free HTTP API for article searches
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": query,
        "mode": "ArtList",
        "maxrecords": limit,
        "format": "json",
    }
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get("articles", [])
    except Exception as e:
        logger.warning(f"GDELT fetch failed: {e}")
    
    return []
```

Add to `app/core/config.py`:

```python
# Licensed news APIs
newsapi_key: str = Field(default="", env="NEWSAPI_KEY")
newsdata_io_key: str = Field(default="", env="NEWSDATA_IO_KEY")
worldnews_api_key: str = Field(default="", env="WORLDNEWS_API_KEY")
currents_api_key: str = Field(default="", env="CURRENTS_API_KEY")
mediastack_api_key: str = Field(default="", env="MEDIASTACK_API_KEY")
```

### 1.4 Update news_service.py to Use New Sources

In `app/services/news_service.py`, add to the fetch logic:

```python
# Step 1: Mix RSS feeds + Licensed APIs
from app.utils.licensed_apis import fetch_from_newsapi, fetch_from_newsdata_io

async def _fetch_mixed_sources(category: str, topic_query: str, limit: int):
    """Fetch from RSS + Licensed APIs in parallel."""
    tasks = []
    
    # RSS feeds (existing)
    for source_name, feed_url in selected_sources:
        tasks.append(_fetch_single_feed(feed_url, source_name, per_source_limit))
    
    # Licensed APIs (if configured)
    if settings.newsapi_key:
        tasks.append(fetch_from_newsapi(topic_query, limit=20))
    if settings.newsdata_io_key:
        tasks.append(fetch_from_newsdata_io(topic_query, limit=20))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

---

## Part 2: Latency Architecture (1 Week)

### 2.1 Set Up Celery + Redis

**File:** `requirements.txt` - add:

```
celery>=5.4.0
redis>=5.0.0
```

Run:
```bash
pip install -r requirements.txt
```

**File:** `app/core/celery.py` (new file)

```python
"""Celery configuration for background task queue."""

from celery import Celery
from app.core.config import settings

app = Celery(
    'nuze',
    broker=settings.redis_url,
    backend=settings.redis_url,
)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 mins hard limit
    task_soft_time_limit=25 * 60,  # 25 mins soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)
```

### 2.2 Create Batch AI Analysis Tasks

**File:** `app/services/ai_tasks.py` (new file)

```python
"""Celery tasks for batch AI analysis."""

from celery import group
from app.core.celery import app
from app.services.ai_service import analyze_article_async
from app.core.database import get_db
import logging

logger = logging.getLogger(__name__)

@app.task(name="batch_analyze_articles")
def batch_analyze_articles(article_ids: list[str], user_tier: str = "system"):
    """
    Batch analyze articles. Called by scheduler with article IDs.
    Splits into small/medium/strong model pipelines.
    """
    # Pipeline 1: Small model (language, category, duplicate detection)
    small_tasks = [
        analyze_article_small.s(aid) for aid in article_ids
    ]
    
    # Pipeline 2: Medium model (summaries) - only on small_model output
    # Pipeline 3: Strong model (bias, fact-check) - only on medium output
    
    # Chain them
    pipeline = group(small_tasks) | \
               analyze_batch_medium.s() | \
               analyze_batch_strong.s()
    
    result = pipeline.apply_async()
    return result.id

@app.task(name="analyze_article_small")
def analyze_article_small(article_id: str):
    """Small model: language, category, is_duplicate."""
    # Placeholder: replace with actual model
    logger.info(f"Small model analyzing {article_id}")
    return {"article_id": article_id, "stage": "small"}

@app.task(name="analyze_batch_medium")
def analyze_batch_medium(small_results):
    """Medium model: summary."""
    logger.info(f"Medium model analyzing {len(small_results)} articles")
    return small_results

@app.task(name="analyze_batch_strong")
def analyze_batch_strong(medium_results):
    """Strong model: bias + fact-check."""
    logger.info(f"Strong model analyzing {len(medium_results)} articles")
    return medium_results
```

### 2.3 Refactor Scheduler for Precomputation

**File:** `app/services/scheduler.py` - replace `_hourly_fetch_job`:

```python
async def _precompute_feed_cards_job():
    """
    New hourly job:
    1. Fetch articles from all sources
    2. Deduplicate aggressively
    3. Batch them into Celery tasks for AI analysis
    4. Cache finished cards with metadata
    """
    from app.services.news_service import fetch_all_news
    from app.services.ai_tasks import batch_analyze_articles
    from app.core.cache import cache_set, TRENDS_TTL
    
    logger.info("Starting precompute job...")
    
    try:
        # Step 1: Fetch raw articles
        result = await fetch_all_news(limit=200, user_tier="system", with_analysis=False)
        articles = result.get("articles", [])
        
        # Step 2: Aggressive deduplication
        deduped = _aggressive_dedup(articles)
        
        # Step 3: Batch into Celery
        article_ids = [a.get("id") or a.get("link") for a in deduped]
        batch_size = 20
        
        for i in range(0, len(article_ids), batch_size):
            batch = article_ids[i:i+batch_size]
            batch_analyze_articles.delay(batch, user_tier="system")
        
        logger.info(f"Precompute job queued {len(article_ids)} articles for AI analysis")
        
    except Exception as e:
        logger.exception(f"Precompute job failed: {e}")

def _aggressive_dedup(articles: list) -> list:
    """
    Deduplicate by:
    - Exact URL match
    - Headline similarity (80%+)
    - Named entity overlap (same people/places)
    """
    seen_urls = set()
    seen_headlines = set()
    deduped = []
    
    for article in articles:
        link = article.get("link", "")
        title = article.get("title", "")
        
        # URL dedup
        if link in seen_urls:
            continue
        
        # Headline similarity
        normalized_title = _normalize_text(title)
        if _is_similar(normalized_title, seen_headlines):
            continue
        
        seen_urls.add(link)
        seen_headlines.add(normalized_title)
        deduped.append(article)
    
    return deduped
```

### 2.4 Implement "Stale While Revalidate"

**File:** `app/routes/news.py` - update fetch endpoint:

```python
@router.get("/news/{category}")
async def get_news(
    category: str,
    limit: int = Query(20),
    use_cache: bool = Query(True),
    refresh: bool = Query(False),
):
    """
    Fast endpoint: serve precomputed cache.
    If cache is stale (>30min old), refresh in background.
    """
    from app.core.cache import cache_get, cache_set, NEWS_TTL
    
    cache_key = f"feed:precomputed:{category}:{limit}"
    
    # Try cache first
    cached = await cache_get(cache_key)
    if cached and not refresh:
        # Add metadata: "cached_at", "age_seconds"
        cached["meta"]["cached_seconds_ago"] = int(time.time()) - cached["meta"]["cached_at"]
        return cached
    
    # If not in cache, compute fresh (but this is slow!)
    # In background, trigger refresh
    if not cached or refresh:
        asyncio.create_task(_refresh_feed_async(category, limit, cache_key))
    
    # Still return old cache if available (stale-while-revalidate)
    if cached:
        cached["meta"]["is_stale"] = True
        return cached
    
    # No cache at all: return empty + trigger refresh
    return {
        "articles": [],
        "meta": {"waiting_for_precompute": True}
    }

async def _refresh_feed_async(category: str, limit: int, cache_key: str):
    """Background refresh of feed cache."""
    try:
        articles = await fetch_news(category, limit, with_analysis=False)
        await cache_set(cache_key, articles.model_dump(exclude_none=True), NEWS_TTL)
    except Exception as e:
        logger.warning(f"Background refresh failed for {category}: {e}")
```

### 2.5 Split "Instant Feed" from "Deep AI"

**File:** `app/models/schemas.py` - add new schema:

```python
class ArticleCardFast(BaseModel):
    """Instant response: headline + source + snippet."""
    id: str
    title: str
    source: str
    link: str
    published_at: str
    snippet: str
    image_url: Optional[str] = None
    language: str

class ArticleCardDeep(ArticleCardFast):
    """Extended with AI analysis (served after 1-3 sec delay)."""
    summary: Optional[str] = None
    bias: Optional[str] = None
    bias_score: Optional[float] = None
    credibility_score: Optional[float] = None
    fact_check_score: Optional[float] = None
    political_leaning: Optional[str] = None
    sentiment: Optional[str] = None
```

**File:** `app/routes/news.py` - add endpoint:

```python
@router.get("/news/{category}/instant")
async def get_news_instant(category: str, limit: int = Query(20)):
    """Return fast feed (instant, ~100ms)."""
    # Fetch from cache, return only fast fields
    articles = await fetch_news(category, limit, with_analysis=False)
    return {
        "articles": [
            {
                "id": a.id,
                "title": a.title,
                "source": a.source,
                "link": a.link,
                "published_at": a.published_at,
                "snippet": a.description[:200] if a.description else "",
                "image_url": a.image_url,
                "language": a.language,
            }
            for a in articles.articles
        ]
    }

@router.get("/news/{category}/deep/{article_id}")
async def get_article_deep_analysis(article_id: str):
    """Return full AI analysis for one article."""
    # Query MongoDB for cached analysis
    # If not available, queue for analysis + return pending
    return {"status": "analyzed", "data": {...}}
```

### 2.6 Precompute by Topic

**File:** `app/services/feed_precompute.py` (new file)

```python
"""Precompute feeds by topic every hour."""

import asyncio
import logging
from app.services.news_service import fetch_news
from app.core.cache import cache_set, TRENDS_TTL

logger = logging.getLogger(__name__)

PRECOMPUTE_TOPICS = {
    "israel_politics": ("political", {"filter_israeli": True}),
    "israel_security": ("defence", {"filter_israeli": True}),
    "israel_economy": ("economy", {"filter_israeli": True}),
    "world_politics": ("political", {"filter_international": True}),
    "tech": ("science", {}),
    "middle_east": ("international", {"region": "middle_east"}),
}

async def precompute_all_feeds():
    """Generate feeds for all topics, cache them."""
    tasks = []
    for topic_name, (category, filters) in PRECOMPUTE_TOPICS.items():
        tasks.append(_precompute_one_topic(topic_name, category, filters))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, Exception):
            logger.error(f"Precompute failed: {r}")

async def _precompute_one_topic(topic_name: str, category: str, filters: dict):
    """Precompute one topic feed and cache it."""
    logger.info(f"Precomputing {topic_name}...")
    
    try:
        articles = await fetch_news(
            category=category,
            limit=50,
            with_analysis=False,  # Analysis comes from Celery
        )
        
        # Apply topic-specific filters
        if filters.get("filter_israeli"):
            articles.articles = [a for a in articles.articles if getattr(a, "source_type") == "israel"]
        if filters.get("filter_international"):
            articles.articles = [a for a in articles.articles if getattr(a, "source_type") != "israel"]
        
        # Cache
        cache_key = f"feed:precomputed:{topic_name}:50"
        await cache_set(cache_key, articles.model_dump(exclude_none=True), TRENDS_TTL)
        
        logger.info(f"✓ Precomputed {topic_name} ({len(articles.articles)} articles)")
    
    except Exception as e:
        logger.error(f"Failed to precompute {topic_name}: {e}")
```

Add to `app/services/scheduler.py`:

```python
from app.services.feed_precompute import precompute_all_feeds

# In start_scheduler():
sched.add_job(precompute_all_feeds, CronTrigger(minute=*/15), id="precompute_feeds")
```

### 2.7 Use Cheaper AI First (Model Pipeline)

Modify `app/services/ai_service.py` to support tiered models:

```python
async def analyze_article(article, user_tier="free"):
    """
    Pipeline:
    - Small model: language, category, duplicate detection (fast, cheap)
    - Medium model: summary (medium cost)
    - Strong model: bias, fact-check (expensive, only for important articles)
    """
    
    # Always do small model
    small_result = await _analyze_small_model(article)
    
    # Medium model for most
    medium_result = await _analyze_medium_model(article, small_result)
    
    # Strong model only for high-priority or user request
    if user_tier in ["pro", "platinum"]:
        strong_result = await _analyze_strong_model(article, medium_result)
        return {**small_result, **medium_result, **strong_result}
    
    return {**small_result, **medium_result}

async def _analyze_small_model(article):
    """Cheap: language detection, keyword classification."""
    return {
        "language": detect(article.title),
        "category": _keyword_classify(article),
    }

async def _analyze_medium_model(article, small_result):
    """Medium: summary via cheaper model (e.g., Llama 2 or similar)."""
    summary = await _call_cheaper_summarizer(article.description)
    return {"summary": summary}

async def _analyze_strong_model(article, medium_result):
    """Expensive: bias, fact-check via GPT-4o."""
    # Your existing bias + fact-check logic
    return {
        "bias": ...,
        "credibility_score": ...,
    }
```

---

## Part 3: Deployment Checklist

### 3.1 Updates to `.env`

```bash
# Add licensed API keys
NEWSAPI_KEY=...
NEWSDATA_IO_KEY=...
WORLDNEWS_API_KEY=...
CURRENTS_API_KEY=...
MEDIASTACK_API_KEY=...

# Celery + Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
REDIS_URL=redis://localhost:6379

# Scheduler
SCHEDULER_ENABLED=true
SCHEDULER_TIMEZONE=Asia/Jerusalem
```

### 3.2 Run Celery Worker

```bash
# Terminal 1: Start Celery worker
celery -A app.core.celery worker --loglevel=info -c 4

# Terminal 2: Start Celery beat (scheduler)
celery -A app.core.celery beat --loglevel=info

# Terminal 3: Start FastAPI
uvicorn app.main:app --reload
```

### 3.3 Database Migrations

Add collections to MongoDB for precomputed feeds:

```python
# In app/core/database.py
async def init_db():
    # ... existing code ...
    db = client.nuze_db
    
    # Collections for precomputed feeds
    await db.create_collection("precomputed_feeds")
    await db.create_collection("ai_analysis_cache")
    await db.create_collection("feed_metadata")
    
    # Indexes
    db.precomputed_feeds.create_index([("topic", 1), ("created_at", -1)])
    db.ai_analysis_cache.create_index([("article_id", 1)])
```

---

## Part 4: Expected Impact

| Metric | Before | After |
|--------|--------|-------|
| Load time | 30–60s | 1–2s |
| Sources | ~75 | 200+ |
| Article count/day | ~300 | 1000+ |
| Real-time API calls | All | Only for deep analysis |
| Cache hit rate | 40% | 80%+ |
| User experience | Slow, frustrating | Instant |

---

## Part 5: Rollout Plan

**Week 1:**
- [ ] Add licensed API keys (2 hrs)
- [ ] Update feed_config.py with all sources (4 hrs)
- [ ] Deploy and test (2 hrs)

**Week 2:**
- [ ] Set up Celery + Redis (4 hrs)
- [ ] Create batch AI tasks (8 hrs)
- [ ] Refactor scheduler (6 hrs)
- [ ] Test and deploy (4 hrs)

**Week 3:**
- [ ] Implement instant/deep split (6 hrs)
- [ ] Add stale-while-revalidate (4 hrs)
- [ ] Performance testing (8 hrs)

---

## Questions & Support

If you hit issues:

1. **Redis connection errors**: Make sure Redis is running (`redis-cli ping`)
2. **Celery tasks not running**: Check worker logs (`celery -A app.core.celery worker`)
3. **Still slow**: Profile with `cProfile` to find bottlenecks
4. **Missing articles**: Check licensed API quotas + RSS feed health

**Contact:** Reference this guide in any bug reports to the dev team.

---

**Author's Note**  
This solution avoids the Ground News approach and uses a hybrid legal pipeline (RSS + licensed APIs + GDELT). The latency comes from **doing work on-demand** → should be **pre-computed and cached**. This is the single biggest fix.
