import httpx

async def test_mk_individual():
    url = "https://production.oknesset.org/pipelines/data/members/mk_individual/mk_individual.csv"
    headers = {"User-Agent": "Mozilla/5.0", "Range": "bytes=0-1500"}
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        try:
            resp = await client.get(url, headers=headers)
            print(f"Status: {resp.status_code}")
            if resp.status_code in (200, 206):
                print(f"Success! Snippet:\n{resp.content.decode('utf-8', errors='replace')[:800]}")
            else:
                print("Failed, response status:", resp.status_code)
        except Exception as e:
            print(f"Error: {e}")

import asyncio
asyncio.run(test_mk_individual())
