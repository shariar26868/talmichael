import csv
import httpx
import asyncio

def safe_str(val):
    if val is None:
        return "None"
    return str(val).encode('ascii', errors='backslashreplace').decode('ascii')

async def debug_csv():
    urls = {
        "english_names": "https://production.oknesset.org/pipelines/data/members/member_english_names/member_english_names.csv",
        "individuals": "https://production.oknesset.org/pipelines/data/members/mk_individual/mk_individual.csv",
        "positions": "https://production.oknesset.org/pipelines/data/members/kns_persontoposition/kns_persontoposition.csv",
        "factions": "https://production.oknesset.org/pipelines/data/knesset/kns_faction/kns_faction.csv",
    }
    
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        # Factions
        resp = await client.get(urls["factions"])
        factions = list(csv.DictReader(resp.text.splitlines()))
        print("--- Faction keys: ---")
        print(factions[0].keys())
        print("Sample factions (Knesset 25):")
        for f in factions:
            if f.get("KnessetNum") == "25":
                print(f"  Id: {safe_str(f.get('Id'))} | Name: {safe_str(f.get('Name'))}")

        # English Names
        resp = await client.get(urls["english_names"])
        eng = list(csv.DictReader(resp.text.splitlines()))
        print("\n--- English Names keys: ---")
        print(eng[0].keys())
        print("Sample English Names:")
        for row in eng[:5]:
            print(f"  mk_individual_id: {safe_str(row.get('mk_individual_id'))} | NameEng: {safe_str(row.get('NameEng'))}")

        # Individuals
        resp = await client.get(urls["individuals"])
        ind = list(csv.DictReader(resp.text.splitlines()))
        print("\n--- Individuals keys: ---")
        print(ind[0].keys())
        print("Sample Individuals:")
        for row in ind[:5]:
            print(f"  PersonID: {safe_str(row.get('PersonID'))} | mk_individual_id: {safe_str(row.get('mk_individual_id'))} | LastName: {safe_str(row.get('LastName'))}")

        # Positions
        resp = await client.get(urls["positions"])
        pos = list(csv.DictReader(resp.text.splitlines()))
        print("\n--- Positions keys: ---")
        print(pos[0].keys())
        print("Sample Positions (Knesset 25, Position 43):")
        count = 0
        for row in pos:
            if row.get("KnessetNum") == "25" and row.get("PositionID") == "43":
                count += 1
                if count <= 5:
                    print(f"  PersonID: {safe_str(row.get('PersonID'))} | FactionID: {safe_str(row.get('FactionID'))} | FactionName: {safe_str(row.get('FactionName'))}")
        print(f"Total Knesset 25 Position 43 rows: {count}")

import asyncio
asyncio.run(debug_csv())
