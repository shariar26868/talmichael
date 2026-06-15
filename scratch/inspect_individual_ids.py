import csv
import httpx
import asyncio

async def inspect():
    urls = {
        "individuals": "https://production.oknesset.org/pipelines/data/members/mk_individual/mk_individual.csv",
        "positions": "https://production.oknesset.org/pipelines/data/members/kns_persontoposition/kns_persontoposition.csv",
    }
    
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        # Load active Knesset 25 PersonIDs
        resp = await client.get(urls["positions"])
        positions = list(csv.DictReader(resp.text.splitlines()))
        active_person_ids = {
            row.get("PersonID") for row in positions 
            if row.get("KnessetNum") == "25" and row.get("PositionID") == "54"
        }
        
        # Load individuals mapping
        resp = await client.get(urls["individuals"])
        individuals = list(csv.DictReader(resp.text.splitlines()))
        
        mapped_pids = {row.get("PersonID"): row for row in individuals if row.get("PersonID")}
        
        print(f"Total active PersonIDs in Knesset 25: {len(active_person_ids)}")
        print(f"Total mapped PersonIDs in mk_individual.csv: {len(mapped_pids)}")
        
        matching = active_person_ids.intersection(mapped_pids.keys())
        print(f"Overlap matching active Knesset 25 PersonIDs: {len(matching)}")
        
        missing = active_person_ids - mapped_pids.keys()
        print(f"First 10 missing active PersonIDs from Knesset 25: {list(missing)[:10]}")
        
        # Check if they are stored under different columns or names
        # Let's inspect a few rows in individuals that have PersonID set
        print("\nSample mapping entries in mk_individual.csv:")
        count = 0
        for row in individuals:
            pid = row.get("PersonID", "").strip()
            if pid:
                count += 1
                if count <= 5:
                    print(f"  PersonID: {repr(pid)} | mk_individual_id: {repr(row.get('mk_individual_id'))} | NameEng: {repr(row.get('mk_individual_name_eng'))}")

import asyncio
asyncio.run(inspect())
