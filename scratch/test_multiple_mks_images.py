import httpx
import asyncio

async def test_mks():
    headers = {"User-Agent": "Mozilla/5.0"}
    # Some current/recent Knesset member IDs
    ids = [2291, 30749, 30601, 30765, 30770, 138, 200, 210, 99999]
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=5) as client:
        for pid in ids:
            url = f"https://oknesset.org/static/img/members/{pid}.jpg"
            resp = await client.head(url)
            print(f"ID {pid}: {url} -> Status {resp.status_code}")

if __name__ == "__main__":
    asyncio.run(test_mks())
