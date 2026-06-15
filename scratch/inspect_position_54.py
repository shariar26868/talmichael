import csv
import httpx
import asyncio

def safe_str(val):
    if val is None:
        return "None"
    return str(val).encode('ascii', errors='backslashreplace').decode('ascii')

async def check():
    url = "https://production.oknesset.org/pipelines/data/members/kns_persontoposition/kns_persontoposition.csv"
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(url)
        pos = list(csv.DictReader(resp.text.splitlines()))
        
        count = 0
        for row in pos:
            if row.get("KnessetNum") == "25" and row.get("PositionID") == "54":
                count += 1
                if count <= 5:
                    print(f"Row {count}: PersonID: {safe_str(row.get('PersonID'))} | PositionID: {safe_str(row.get('PositionID'))} | FactionID: {safe_str(row.get('FactionID'))} | FactionName: {safe_str(row.get('FactionName'))} | DutyDesc: {safe_str(row.get('DutyDesc'))}")
        print(f"Total Knesset 25 Position 54 rows: {count}")

import asyncio
asyncio.run(check())
