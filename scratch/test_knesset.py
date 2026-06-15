import httpx
import json

async def test_knesset():
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    urls = {
        "bills": "https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Bill?$top=5&$format=json",
        "positions": "https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_PersonToPosition?$top=5&$format=json",
        "factions": "https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Faction?$top=5&$format=json",
    }
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        for name, url in urls.items():
            print(f"Testing {name} endpoint...")
            try:
                resp = await client.get(url, headers=headers)
                print(f"Status code: {resp.status_code}")
                if resp.status_code == 200:
                    data = resp.json()
                    value_len = len(data.get("value", []))
                    print(f"Success! Found {value_len} items.")
                    if value_len > 0:
                        print(f"Sample item keys: {list(data['value'][0].keys())}")
                        print(json.dumps(data['value'][0], indent=2, ensure_ascii=False)[:500])
                else:
                    print(f"Failed with text: {resp.text[:200]}")
            except Exception as e:
                print(f"Error for {name}: {type(e).__name__}: {e}")

import asyncio
asyncio.run(test_knesset())
