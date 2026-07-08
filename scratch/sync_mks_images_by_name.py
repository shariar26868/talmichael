import asyncio
import httpx
import sys
from app.core.database import init_db, get_db, close_db
from app.services.political_service import _fetch_oknesset_csv, OKNESSET_INDIVIDUALS_URL

sys.stdout.reconfigure(encoding='utf-8')

def normalize_name(name):
    if not name:
        return ""
    name = name.replace("MK", "").replace("Mr.", "").replace("Mrs.", "")
    return "".join(c for c in name if c.isalnum()).lower()

async def sync_images_by_name():
    await init_db()
    db = get_db()

    print("Fetching Open Knesset individuals CSV to build PersonID -> mk_individual_id mapping...")
    individuals_rows = await _fetch_oknesset_csv(OKNESSET_INDIVIDUALS_URL)
    person_to_mk_id = {}
    for ind in individuals_rows:
        pid = ind.get("PersonID")
        mk_id = ind.get("mk_individual_id")
        if pid and mk_id:
            try:
                person_to_mk_id[int(pid)] = int(mk_id)
            except ValueError:
                person_to_mk_id[pid] = mk_id

    print("Fetching Wikidata mapping for Knesset IDs (P9770) and Names...")
    url = "https://query.wikidata.org/sparql"
    query = """
    SELECT ?knesset_id ?image ?name_he ?name_en WHERE {
      ?member wdt:P9770 ?knesset_id.
      ?member wdt:P18 ?image.
      OPTIONAL {
        ?member rdfs:label ?name_he.
        FILTER(LANG(?name_he) = "he")
      }
      OPTIONAL {
        ?member rdfs:label ?name_en.
        FILTER(LANG(?name_en) = "en")
      }
    }
    """
    headers = {
        "User-Agent": "TalmicahelApp/1.0 (contact@example.com)",
        "Accept": "application/sparql-results+json"
    }
    
    wikidata_by_kid = {}
    wikidata_by_name_he = {}
    wikidata_by_name_en = {}
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30) as client:
        resp = await client.post(url, data={"query": query})
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", {}).get("bindings", [])
            for r in results:
                kid_str = r["knesset_id"]["value"]
                img_url = r["image"]["value"]
                name_he = r.get("name_he", {}).get("value", "")
                name_en = r.get("name_en", {}).get("value", "")
                
                if "Special:FilePath/" in img_url:
                    filename = img_url.split("Special:FilePath/")[-1]
                    clean_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename}"
                    try:
                        kid = int(kid_str)
                    except ValueError:
                        kid = kid_str
                        
                    wikidata_by_kid[kid] = clean_url
                    if name_he:
                        wikidata_by_name_he[normalize_name(name_he)] = clean_url
                    if name_en:
                        wikidata_by_name_en[normalize_name(name_en)] = clean_url
            print(f"Loaded {len(wikidata_by_kid)} Knesset member images from Wikidata.")
        else:
            print(f"Error fetching from Wikidata: {resp.status_code}")
            await close_db()
            return

    # Now update database
    cursor = db.mps.find({})
    mps = await cursor.to_list(length=1000)
    print(f"Found {len(mps)} MPs in local database.")
    
    updated_count = 0
    not_found_count = 0
    
    for m in mps:
        pid = m.get("knesset_id")  # PersonID in local DB
        try:
            pid_key = int(pid) if pid is not None else None
        except ValueError:
            pid_key = pid
            
        mk_id = person_to_mk_id.get(pid_key)
        
        # Match strategy 1: By mapped Knesset ID (mk_individual_id)
        img_url = None
        match_type = ""
        if mk_id:
            img_url = wikidata_by_kid.get(mk_id)
            if not img_url and isinstance(mk_id, str) and mk_id.isdigit():
                img_url = wikidata_by_kid.get(int(mk_id))
            if img_url:
                match_type = "knesset_id"
                
        # Match strategy 2: By Hebrew Name
        if not img_url and m.get("name_hebrew"):
            norm_he = normalize_name(m.get("name_hebrew"))
            img_url = wikidata_by_name_he.get(norm_he)
            if img_url:
                match_type = "hebrew_name"
                
        # Match strategy 3: By English Name
        if not img_url and m.get("name"):
            norm_en = normalize_name(m.get("name"))
            img_url = wikidata_by_name_en.get(norm_en)
            if img_url:
                match_type = "english_name"
                
        if img_url:
            await db.mps.update_one(
                {"_id": m["_id"]},
                {"$set": {"photo_url": img_url}}
            )
            updated_count += 1
            print(f"Updated {m.get('name')} | Hebrew: {m.get('name_hebrew')} (Match: {match_type}) -> {img_url}")
        else:
            not_found_count += 1
            print(f"No image found for {m.get('name')} | Hebrew: {m.get('name_hebrew')}")

    print(f"Successfully synced {updated_count} MP photos in the database. {not_found_count} had no photo.")
    await close_db()

if __name__ == "__main__":
    asyncio.run(sync_images_by_name())
