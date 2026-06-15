import httpx

async def explore():
    urls = {
        "kns_bill": "https://production.oknesset.org/pipelines/data/bills/kns_bill/kns_bill.csv",
        "kns_faction": "https://production.oknesset.org/pipelines/data/knesset/kns_faction/kns_faction.csv",
        "kns_person": "https://production.oknesset.org/pipelines/data/members/kns_person/kns_person.csv",
        "kns_position": "https://production.oknesset.org/pipelines/data/members/kns_position/kns_position.csv",
        "kns_persontoposition": "https://production.oknesset.org/pipelines/data/members/kns_persontoposition/kns_persontoposition.csv",
    }
    
    output_lines = []
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for name, url in urls.items():
            output_lines.append(f"\n--- Checking {name} URL: {url} ---")
            try:
                headers = {"User-Agent": "Mozilla/5.0", "Range": "bytes=0-4000"}
                resp = await client.get(url, headers=headers)
                output_lines.append(f"Status: {resp.status_code}")
                if resp.status_code in (200, 206):
                    # Decode as utf-8
                    text = resp.content.decode('utf-8', errors='replace')
                    lines = text.split("\n")
                    output_lines.append("First lines:")
                    for i, line in enumerate(lines[:10]):
                        output_lines.append(f"  Line {i+1}: {line.strip()}")
                else:
                    output_lines.append(f"Failed: {resp.status_code}")
            except Exception as e:
                output_lines.append(f"Error: {e}")
                
    with open("scratch/explore_output.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print("Done! Check scratch/explore_output.txt")

import asyncio
asyncio.run(explore())
