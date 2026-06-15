import csv
import httpx
import asyncio

def safe_str(val):
    if val is None:
        return "None"
    return str(val).encode('ascii', errors='backslashreplace').decode('ascii')

async def check_positions():
    url = "https://production.oknesset.org/pipelines/data/members/kns_persontoposition/kns_persontoposition.csv"
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(url)
        pos = list(csv.DictReader(resp.text.splitlines()))
        
        # Analyze unique positions and check where faction is set
        pos_with_faction = {}
        for row in pos:
            if row.get("KnessetNum") == "25":
                faction_id = row.get("FactionID", "").strip()
                pos_id = row.get("PositionID", "").strip()
                pos_desc = row.get("DutyDesc", "").strip()
                if faction_id:
                    if pos_id not in pos_with_faction:
                        pos_with_faction[pos_id] = {"desc": pos_desc, "count": 0}
                    pos_with_faction[pos_id]["count"] += 1
                    
        print("Positions in Knesset 25 that have FactionID set:")
        for pid, info in pos_with_faction.items():
            print(f"  PositionID: {pid} | Desc: {safe_str(info['desc'])} | Rows count: {info['count']}")

import asyncio
asyncio.run(check_positions())
