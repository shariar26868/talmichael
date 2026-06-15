import httpx

async def explore():
    url = "https://production.oknesset.org/pipelines/data/members/mk_individual/mk_individual.csv"
    headers = {"User-Agent": "Mozilla/5.0", "Range": "bytes=0-5000"}
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code in (200, 206):
                text = resp.content.decode('utf-8', errors='replace')
                with open("scratch/explore_mk_individual.txt", "w", encoding="utf-8") as f:
                    f.write(text)
                print("Success! Written to scratch/explore_mk_individual.txt")
            else:
                print(f"Failed with status: {resp.status_code}")
        except Exception as e:
            print(f"Error: {e}")

import asyncio
asyncio.run(explore())
