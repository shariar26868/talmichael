import asyncio
import httpx
import traceback
import xml.etree.ElementTree as ET

test_feeds = {
    "Times of Israel": "https://www.timesofisrael.com/feed/",
    "Ynet Hebrew": "https://www.ynet.co.il/Integration/StoryRss2.xml",
    "Ynet News (Google fallback)": "https://news.google.com/rss/search?q=site:ynetnews.com&hl=en&gl=IL&ceid=IL:en",
    "Walla News": "https://rss.walla.co.il/feed/1",
}

async def debug_feed(name, url):
    print(f"\n=================== DEBUGGING: {name} ===================")
    print(f"URL: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml,application/xml,text/xml,application/xhtml+xml,text/html;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    try:
        async with httpx.AsyncClient(timeout=8.0, headers=headers, follow_redirects=True, trust_env=False) as client:
            print("Sending request...")
            resp = await client.get(url)
            print(f"Response status code: {resp.status_code}")
            resp.raise_for_status()
            
            print(f"Response content length: {len(resp.content)} bytes")
            # Try decoding
            try:
                xml_text = resp.content.decode("utf-8")
                print("Successfully decoded as UTF-8.")
            except Exception as de:
                print(f"UTF-8 decode failed: {de}")
                
            # Try parsing
            try:
                root = ET.fromstring(resp.content)
                print("XML parsed successfully!")
                channel = root.find("channel")
                if channel is not None:
                    items = channel.findall("item")
                    print(f"Found {len(items)} items in channel.")
                else:
                    print("No <channel> found in XML.")
            except Exception as pe:
                print("XML parsing failed:")
                traceback.print_exc()
                
    except Exception as e:
        print(f"Exception type: {type(e)}")
        print(f"Exception message: '{str(e)}'")
        print("Full Traceback:")
        traceback.print_exc()

async def main():
    for name, url in test_feeds.items():
        await debug_feed(name, url)

if __name__ == "__main__":
    asyncio.run(main())
