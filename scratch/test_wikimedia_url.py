import httpx
import asyncio

async def test():
    # Test if Special:FilePath redirects to upload.wikimedia.org
    url = "https://commons.wikimedia.org/wiki/Special:FilePath/Benjamin%20Netanyahu%2C%20February%202023.jpg"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10) as client:
        resp = await client.get(url)
        print(f"Status: {resp.status_code}")
        print(f"Final URL: {resp.url}")
        print(f"Content length: {len(resp.content)}")

if __name__ == "__main__":
    asyncio.run(test())
