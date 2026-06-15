import httpx

async def test_pipeline():
    urls = {
        "kns_member": "https://production.oknesset.org/pipelines/data/members/kns_member.csv",
        "kns_faction": "https://production.oknesset.org/pipelines/data/knesset/kns_faction.csv",
        "kns_bill": "https://production.oknesset.org/pipelines/data/bills/kns_bill.csv",
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, url in urls.items():
            print(f"Testing {name} URL: {url}")
            try:
                headers = {"User-Agent": "Mozilla/5.0", "Range": "bytes=0-500"}
                resp = await client.get(url, headers=headers)
                print(f"Status: {resp.status_code}")
                if resp.status_code in (200, 206):
                    print(f"Success! Content snippet: {resp.text[:200]}")
                else:
                    print(f"Failed with text: {resp.text[:200]}")
            except Exception as e:
                print(f"Error fetching {name}: {e}")

import asyncio
asyncio.run(test_pipeline())
