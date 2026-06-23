import asyncio
import sys

# Ensure stdout handles UTF-8 for Hebrew printing
sys.stdout.reconfigure(encoding='utf-8')

from app.core.database import init_db, close_db
from app.services.news_service import fetch_news

async def test():
    await init_db()
    
    print("Fetching political news...")
    res = await fetch_news(
        category="political",
        limit=10,
        israeli_only=True,
        use_cache=False, # Bypass cache
        with_analysis=False,
    )
    print(f"Total articles: {res.total}")
    for idx, a in enumerate(res.articles, 1):
        print(f"  {idx}. Source: {a.source} | Title: {a.title}")
        
    await close_db()

if __name__ == "__main__":
    asyncio.run(test())
