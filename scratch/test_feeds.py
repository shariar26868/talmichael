import asyncio
import httpx
import xml.etree.ElementTree as ET

google_news_fallbacks = {
    "Israel Hayom Hebrew (via Google News)": "https://news.google.com/rss/search?q=site:israelhayom.co.il&hl=he&gl=IL&ceid=IL:he",
    "Israel Hayom English (via Google News)": "https://news.google.com/rss/search?q=site:israelhayom.com&hl=en&gl=IL&ceid=IL:en",
    "Maariv (via Google News)": "https://news.google.com/rss/search?q=site:maariv.co.il&hl=he&gl=IL&ceid=IL:he",
    "Calcalist (via Google News)": "https://news.google.com/rss/search?q=site:calcalist.co.il&hl=he&gl=IL&ceid=IL:he",
    "Haaretz Hebrew (via Google News)": "https://news.google.com/rss/search?q=site:haaretz.co.il&hl=he&gl=IL&ceid=IL:he",
    "Haaretz English (via Google News)": "https://news.google.com/rss/search?q=site:haaretz.com&hl=en&gl=IL&ceid=IL:en",
    "Arutz Sheva (via Google News)": "https://news.google.com/rss/search?q=site:israelnationalnews.com&hl=en&gl=IL&ceid=IL:en",
    "i24 News (via Google News)": "https://news.google.com/rss/search?q=site:i24news.tv&hl=en&gl=IL&ceid=IL:en",
    "Sport5 (via Google News)": "https://news.google.com/rss/search?q=site:sport5.co.il&hl=he&gl=IL&ceid=IL:he",
    "One Sport (via Google News)": "https://news.google.com/rss/search?q=site:one.co.il&hl=he&gl=IL&ceid=IL:he",
    "CTech Calcalist (via Google News)": "https://news.google.com/rss/search?q=site:calcalistech.com&hl=en&gl=IL&ceid=IL:en",
    "Channel 13 Reshet (via Google News)": "https://news.google.com/rss/search?q=site:13tv.co.il&hl=he&gl=IL&ceid=IL:he",
}

async def test_url(name, url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            print(f"[{name}] Status: {resp.status_code}")
            resp.raise_for_status()
            
            try:
                root = ET.fromstring(resp.content)
                items = root.findall(".//item")
                print(f"  -> SUCCESS! Parsed XML. Found {len(items)} items.")
                if len(items) > 0:
                    first_item_title = items[0].findtext("title", "")
                    first_item_link = items[0].findtext("link", "")
                    print(f"     First Title: {first_item_title}")
                    print(f"     First Link: {first_item_link}")
            except Exception as pe:
                print(f"  -> XML Parse Error: {pe}")
    except Exception as e:
        print(f"  -> Request Error: {e}")

async def main():
    for name, url in google_news_fallbacks.items():
        await test_url(name, url)

asyncio.run(main())
