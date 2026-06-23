import asyncio
import sys

# Ensure stdout handles UTF-8 for Hebrew printing
sys.stdout.reconfigure(encoding='utf-8')

from app.core.database import init_db, close_db
from app.services.news_service import fetch_all_news

async def verify():
    print("Initializing Database...")
    await init_db()
    
    print("\nFetching all categories...")
    try:
        res = await fetch_all_news(limit=10, user_tier="pro", with_analysis=False)
        print("\n=== FETCH RESULTS ===")
        print(f"Total returned articles: {res.get('total')}")
        print(f"Metadata: {res.get('meta')}")
        articles = res.get("articles", [])
        print(f"Number of articles: {len(articles)}")
        for idx, article in enumerate(articles[:5], 1):
            print(f"  {idx}. Source: {article.get('source')} | Title: {article.get('title')}")
    except Exception as e:
        print(f"Error during verify_all_news: {e}")
        import traceback
        traceback.print_exc()
        
    await close_db()

if __name__ == "__main__":
    asyncio.run(verify())
