import asyncio
import httpx

async def test():
    url = "https://production.oknesset.org/pipelines/data/committees/kns_committeesession/kns_committeesession.csv"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.head(url)
        print(f"Status: {resp.status_code}")
        print(f"Headers: {dict(resp.headers)}")

if __name__ == "__main__":
    asyncio.run(test())
