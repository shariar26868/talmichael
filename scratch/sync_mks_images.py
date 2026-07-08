import asyncio
import httpx
from urllib.parse import unquote
from app.core.database import init_db, get_db, close_db

async def sync_images():
    await init_db()
    db = get_db()

    print("Fetching Wikidata mapping for Knesset IDs...")
    url = "https://query.wikidata.org/sparql"
    query = """
    SELECT ?knesset_id ?image WHERE {
      ?member wdt:P9770 ?knesset_id.
      ?member wdt:P18 ?image.
    }
    """
    headers = {
        "User-Agent": "TalmicahelApp/1.0 (contact@example.com)",
        "Accept": "application/sparql-results+json"
    }
    
    wikidata_map = {}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30) as client:
        resp = await client.post(url, data={"query": query})
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", {}).get("bindings", [])
            for r in results:
                kid_str = r["knesset_id"]["value"]
                img_url = r["image"]["value"]
                
                # Extract filename from http://commons.wikimedia.org/wiki/Special:FilePath/...
                if "Special:FilePath/" in img_url:
                    filename = img_url.split("Special:FilePath/")[-1]
                    # We can use the https version of Special:FilePath which redirects beautifully
                    clean_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename}"
                    try:
                        # Store numeric ID if possible
                        kid = int(kid_str)
                    except ValueError:
                        kid = kid_str
                    wikidata_map[kid] = clean_url
            print(f"Loaded {len(wikidata_map)} Knesset member images from Wikidata.")
        else:
            print(f"Error fetching from Wikidata: {resp.status_code}")
            print(resp.text[:500])
            await close_db()
            return

    # Now update database
    cursor = db.mps.find({})
    mps = await cursor.to_list(length=1000)
    print(f"Found {len(mps)} MPs in local database.")
    
    updated_count = 0
    for m in mps:
        kid = m.get("knesset_id")
        # Try both integer and string matches
        img_url = wikidata_map.get(kid)
        if not img_url and isinstance(kid, str) and kid.isdigit():
            img_url = wikidata_map.get(int(kid))
        
        if img_url:
            # Let's update the MP's photo_url in DB
            await db.mps.update_one(
                {"_id": m["_id"]},
                {"$set": {"photo_url": img_url}}
            )
            updated_count += 1
            print(f"Updated {m.get('name')} (ID: {kid}) with photo: {img_url}")
        else:
            # If no wikidata image, let's keep or check if it's currently a placeholder
            curr_photo = m.get("photo_url")
            if not curr_photo or "placeholder" in curr_photo:
                # We can construct the official knesset one just in case the client can load it
                official_url = f"https://main.knesset.gov.il/static/images/mk/MK_{kid}.jpg"
                # Wait, let's see if we should set it
                # For now let's leave it or set it so client can try to load it
                pass

    print(f"Successfully synced {updated_count} MP photos in the database.")
    await close_db()

if __name__ == "__main__":
    asyncio.run(sync_images())
