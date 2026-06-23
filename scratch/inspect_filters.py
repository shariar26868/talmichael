import asyncio
import sys

# Ensure stdout handles UTF-8 for Hebrew printing
sys.stdout.reconfigure(encoding='utf-8')

from app.services.news_service import _fetch_single_feed
from app.utils.filters import is_opinion, is_blocked_source, is_israeli_source, is_negative

async def test():
    # Fetch from Ynet Hebrew
    url = "https://www.ynet.co.il/Integration/StoryRss2.xml"
    print(f"Fetching from Ynet Hebrew: {url}...")
    articles = await _fetch_single_feed(url, "Ynet Hebrew", 5)
    print(f"Fetched {len(articles)} articles.")
    
    for idx, a in enumerate(articles, 1):
        print(f"\n--- Article {idx} ---")
        print(f"Title: {a.title}")
        print(f"Source: {a.source}")
        print(f"Source URL: {a.source_url}")
        
        opinion = is_opinion(a.title, a.description)
        blocked = is_blocked_source(a.source, a.source_url)
        israeli = is_israeli_source(a.source, a.source_url)
        neg = is_negative(a.title, a.description)
        
        print(f"Filters evaluation:")
        print(f"  is_opinion: {opinion}")
        print(f"  is_blocked_source: {blocked}")
        print(f"  is_israeli_source: {israeli}")
        print(f"  is_negative: {neg}")

if __name__ == "__main__":
    asyncio.run(test())
