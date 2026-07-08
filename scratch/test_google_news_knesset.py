import asyncio
import httpx
from app.utils.rss_parser import parse_rss
import sys

sys.stdout.reconfigure(encoding='utf-8')

async def test():
    # Hebrew Knesset Spokesperson RSS via Google News (safe from geo-block)
    url_he = "https://news.google.com/rss/search?q=site:knesset.gov.il+דוברות+OR+דובר+OR+הודעות&hl=he&gl=IL&ceid=IL:he"
    
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url_he, headers=headers)
        print(f"Hebrew status: {resp.status_code}")
        if resp.status_code == 200:
            articles = parse_rss(resp.text, limit=20)
            print(f"Found {len(articles.articles)} Hebrew announcements.")
            for art in articles.articles[:10]:
                print(f"Title: {art.title}")
                print(f"  Link: {art.link}")
                print(f"  Published: {art.pub_date}")
                print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test())
