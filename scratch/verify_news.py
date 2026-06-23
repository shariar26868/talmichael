import asyncio
import os
import sys

# Ensure stdout handles UTF-8 for Hebrew printing
sys.stdout.reconfigure(encoding='utf-8')

from app.core.database import init_db, close_db
from app.services.news_service import fetch_news

async def verify():
    print("Initializing Database...")
    await init_db()
    
    print("\nFetching general news with AI analysis...")
    try:
        # Fetching international category with 2 articles, pro tier, and with_analysis=True
        news_response = await fetch_news(
            category="international",
            limit=2,
            israeli_only=False,
            use_cache=False,
            with_analysis=True,
            user_tier="pro"
        )
        
        print(f"Fetched {len(news_response.articles)} articles.")
        for idx, article in enumerate(news_response.articles, 1):
            print(f"\n--- Article {idx} ---")
            print(f"Title: {article.title}")
            print(f"Source: {article.source}")
            print(f"Link: {article.link}")
            print(f"Sentiment: {article.sentiment}")
            print(f"Bias Leaning: {article.bias}")
            print(f"Bias Score: {article.bias_score}")
            print(f"Bias Category: {article.bias_category}")
            print(f"Credibility Score: {article.credibility_score}")
            print(f"Hebrew Summary: {article.summary_hebrew}")
            print(f"Topics: {article.topics}")
            print(f"Claims: {article.claims}")
            print(f"Factual Points: {article.factual_points}")
            print(f"Bias Explanation: {article.bias_explanation}")
            
    except Exception as e:
        print(f"Error occurred during verification: {e}")
        import traceback
        traceback.print_exc()
        
    await close_db()

if __name__ == "__main__":
    asyncio.run(verify())
