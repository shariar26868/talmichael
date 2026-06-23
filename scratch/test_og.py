import httpx
import asyncio
import re


async def check_og():
    url = "https://www.aljazeera.com/sports/2026/6/23/algeria-jordan-score-fifa-world-cup-2026-mahrez-gouiri-benbouali-alrashdan"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=headers) as c:
        r = await c.get(url)
        html = r.text
        # Search broader
        og_matches = re.findall(r'og:image[^>]*content=["\']([^"\']+)["\']|content=["\']([^"\']+)["\'][^>]*og:image', html[:20000])
        print("OG image matches:", og_matches[:5])
        # Also check for data-src or srcset patterns
        img_match = re.search(r'<img[^>]+src=["\']([^"\']*cdn[^"\']+)["\']', html[:20000])
        print("CDN img:", img_match.group(1) if img_match else "NOT FOUND")
        # Check response status
        print("Status:", r.status_code)
        print("Content-length:", len(html))
        # Check first 500 chars of HTML
        print("HTML snippet:", html[:500])


asyncio.run(check_og())
