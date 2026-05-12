
import httpx
import xml.etree.ElementTree as ET

RSS_FEEDS = {
    "social":    "https://news.google.com/rss/search?q=Israel+social&hl=en-IL&gl=IL&ceid=IL:en",
    "economics": "https://news.google.com/rss/search?q=Israel+economics&hl=en-IL&gl=IL&ceid=IL:en",
    "security":  "https://news.google.com/rss/search?q=Israel+security&hl=en-IL&gl=IL&ceid=IL:en",
    "education": "https://news.google.com/rss/search?q=Israel+education&hl=en-IL&gl=IL&ceid=IL:en",
    "political": "https://news.google.com/rss/search?q=Israel+political+knesset&hl=en-IL&gl=IL&ceid=IL:en",
    "positive":  "https://news.google.com/rss/search?q=Israel+positive+news&hl=en-IL&gl=IL&ceid=IL:en",
    "world":     "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pWVXlnQVAB?hl=en-IL&gl=IL&ceid=IL:en",
}

async def test_sources():
    all_sources = set()
    async with httpx.AsyncClient(timeout=10.0) as client:
        for cat, url in RSS_FEEDS.items():
            print(f"Fetching {cat}...")
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            root = ET.fromstring(resp.text)
            for item in root.findall(".//item"):
                source = item.find("source")
                if source is not None:
                    all_sources.add(source.text)
    
    print("\n--- Unique Sources ---")
    for s in sorted(list(all_sources)):
        print(s)

import asyncio
asyncio.run(test_sources())
