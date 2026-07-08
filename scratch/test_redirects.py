import httpx
import asyncio

async def test_mks():
    headers = {"User-Agent": "Mozilla/5.0"}
    ids = [2291, 99999]
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=5) as client:
        for pid in ids:
            url = f"https://oknesset.org/static/img/members/{pid}.jpg"
            resp = await client.get(url)
            print(f"ID {pid}: {url}")
            print(f"  Status: {resp.status_code}")
            print(f"  Content-Length: {len(resp.content)}")
            print(f"  Content-Type: {resp.headers.get('content-type')}")
            print(f"  Final URL: {resp.url}")

if __name__ == "__main__":
    asyncio.run(test_mks())
