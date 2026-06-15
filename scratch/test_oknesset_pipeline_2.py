import httpx

async def test_pipeline():
    domains = ["https://oknesset.org", "https://datadump.oknesset.org", "https://production.oknesset.org"]
    paths = [
        "pipelines/data/bills/kns_bill/kns_bill.csv",
        "pipelines/data/knesset/kns_faction/kns_faction.csv",
        "pipelines/data/members/kns_person/kns_person.csv",
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for domain in domains:
            for path in paths:
                url = f"{domain}/{path}"
                print(f"Testing URL: {url}")
                try:
                    headers = {"User-Agent": "Mozilla/5.0", "Range": "bytes=0-200"}
                    resp = await client.get(url, headers=headers)
                    print(f"Status: {resp.status_code}")
                    if resp.status_code in (200, 206):
                        print(f"Success! Snippet: {resp.text[:100]}")
                        return # Stop at first working configuration!
                except Exception as e:
                    print(f"Error: {e}")

import asyncio
asyncio.run(test_pipeline())
