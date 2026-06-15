import csv
import httpx
import asyncio
from datetime import datetime
from bson import ObjectId
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.database import init_db, get_db, close_db

# Verified detailed data for parties in the 25th Knesset
PARTY_ENRICHMENT = {
    "הליכוד": {
        "name": "Likud",
        "wing": "right",
        "leader": "Benjamin Netanyahu",
        "ideology": "National liberalism, conservatism",
        "agenda": "Promotes national security strength, economic deregulation, secular-religious status quo, and strengthening Jewish heritage.",
        "website": "https://www.likud.org.il/"
    },
    "יש עתיד": {
        "name": "Yesh Atid",
        "wing": "center",
        "leader": "Yair Lapid",
        "ideology": "Liberalism, secularism",
        "agenda": "Advocates for middle-class economic relief, anti-corruption reforms, civil marriage options, and regional peace frameworks.",
        "website": "https://www.yeshatid.org.il/"
    },
    "המחנה הממלכתי": {
        "name": "National Unity",
        "wing": "center",
        "leader": "Benny Gantz",
        "ideology": "Liberal Zionism, security centrism",
        "agenda": "Focuses on state stability, consensus building, judicial preservation, and pragmatic security arrangements.",
        "website": "https://www.machane.org.il/"
    },
    "שס": {
        "name": "Shas",
        "wing": "right",
        "leader": "Aryeh Deri",
        "ideology": "Torah values, Sephardic advocacy",
        "agenda": "Focuses on welfare assistance, religious education funding, support for lower-income families, and Sephardic heritage.",
        "website": "https://www.shas.org.il/"
    },
    'ש"ס': {
        "name": "Shas",
        "wing": "right",
        "leader": "Aryeh Deri",
        "ideology": "Torah values, Sephardic advocacy",
        "agenda": "Focuses on welfare assistance, religious education funding, support for lower-income families, and Sephardic heritage.",
        "website": "https://www.shas.org.il/"
    },
    "יהדות התורה": {
        "name": "United Torah Judaism",
        "wing": "right",
        "leader": "Yitzhak Goldknopf",
        "ideology": "Ultra-Orthodox Judaism, Haredi interests",
        "agenda": "Protects Haredi autonomy in education, secures housing and childcare subsidies, and opposes military conscription of yeshiva students.",
        "website": "https://www.degeltorah.org.il/"
    },
    "יהדות התורה והשבת": {
        "name": "United Torah Judaism",
        "wing": "right",
        "leader": "Yitzhak Goldknopf",
        "ideology": "Ultra-Orthodox Judaism, Haredi interests",
        "agenda": "Protects Haredi autonomy in education, secures housing and childcare subsidies, and opposes military conscription of yeshiva students.",
        "website": "https://www.degeltorah.org.il/"
    },
    "הציונות הדתית": {
        "name": "Religious Zionist Party",
        "wing": "right",
        "leader": "Bezalel Smotrich",
        "ideology": "Religious Zionism, ultranationalism",
        "agenda": "Advocates for settlement expansion, judicial restructure, Jewish national identity enforcement, and conservative social policies.",
        "website": "https://www.dati.org.il/"
    },
    "הציונות הדתית בראשות בצלאל סמוטריץ'": {
        "name": "Religious Zionist Party",
        "wing": "right",
        "leader": "Bezalel Smotrich",
        "ideology": "Religious Zionism, ultranationalism",
        "agenda": "Advocates for settlement expansion, judicial restructure, Jewish national identity enforcement, and conservative social policies.",
        "website": "https://www.dati.org.il/"
    },
    "עוצמה יהודית": {
        "name": "Otzma Yehudit",
        "wing": "right",
        "leader": "Itamar Ben-Gvir",
        "ideology": "Jewish ultranationalism, Kahanism",
        "agenda": "Demands strict law enforcement, increased security spending, annexation of the West Bank, and deporting hostile elements.",
        "website": "https://www.ozma-yehudit.org.il/"
    },
    "עוצמה יהודית בראשות איתמר בן גביר": {
        "name": "Otzma Yehudit",
        "wing": "right",
        "leader": "Itamar Ben-Gvir",
        "ideology": "Jewish ultranationalism, Kahanism",
        "agenda": "Demands strict law enforcement, increased security spending, annexation of the West Bank, and deporting hostile elements.",
        "website": "https://www.ozma-yehudit.org.il/"
    },
    "ישראל ביתנו": {
        "name": "Yisrael Beiteinu",
        "wing": "right",
        "leader": "Avigdor Lieberman",
        "ideology": "Secular nationalism, right-wing liberalism",
        "agenda": "Promotes universal draft (including ultra-Orthodox), public transport on Shabbat, free market policies, and security hawkishness.",
        "website": "https://www.beytenu.org.il/"
    },
    "רעמ": {
        "name": "United Arab List (Ra'am)",
        "wing": "center to conservative",
        "leader": "Mansour Abbas",
        "ideology": "Islamism, Arab minority interest advocacy",
        "agenda": "Focuses on developing Arab municipalities, solving crime in Arab sectors, legalizing Negev Bedouin towns, and coalition bargaining.",
        "website": "https://www.raam.org.il/"
    },
    'רע"ם': {
        "name": "United Arab List (Ra'am)",
        "wing": "center to conservative",
        "leader": "Mansour Abbas",
        "ideology": "Islamism, Arab minority interest advocacy",
        "agenda": "Focuses on developing Arab municipalities, solving crime in Arab sectors, legalizing Negev Bedouin towns, and coalition bargaining.",
        "website": "https://www.raam.org.il/"
    },
    "חדש-תעאל": {
        "name": "Hadash-Ta'al",
        "wing": "left",
        "leader": "Ayman Odeh",
        "ideology": "Democratic socialism, Arab-Jewish joint advocacy",
        "agenda": "Advocates for Arab minority civil rights, creation of a Palestinian state alongside Israel, labor protection, and socialist economics.",
        "website": "https://www.hadash.org.il/"
    },
    'חד"ש-תע"ל': {
        "name": "Hadash-Ta'al",
        "wing": "left",
        "leader": "Ayman Odeh",
        "ideology": "Democratic socialism, Arab-Jewish joint advocacy",
        "agenda": "Advocates for Arab minority civil rights, creation of a Palestinian state alongside Israel, labor protection, and socialist economics.",
        "website": "https://www.hadash.org.il/"
    },
    "העבודה": {
        "name": "The Democrats (Labor-Meretz)",
        "wing": "left",
        "leader": "Yair Golan",
        "ideology": "Social democracy, peace advocacy, secularism",
        "agenda": "Promotes welfare-state economics, religious freedom, civil marriage, LGBT equality, and reviving negotiations for a two-state solution.",
        "website": "https://www.havoda.org.il/"
    },
    "מפלגת העבודה הישראלית": {
        "name": "The Democrats (Labor-Meretz)",
        "wing": "left",
        "leader": "Yair Golan",
        "ideology": "Social democracy, peace advocacy, secularism",
        "agenda": "Promotes welfare-state economics, religious freedom, civil marriage, LGBT equality, and reviving negotiations for a two-state solution.",
        "website": "https://www.havoda.org.il/"
    },
    "נעם": {
        "name": "Noam",
        "wing": "right",
        "leader": "Avi Maoz",
        "ideology": "Jewish orthodox conservatism",
        "agenda": "Promotes strict religious family values, opposition to LGBT advocacy in state structures, and Orthodox Jewish education.",
        "website": "https://www.noamparty.org.il/"
    },
    "נעם - בראשות אבי מעוז": {
        "name": "Noam",
        "wing": "right",
        "leader": "Avi Maoz",
        "ideology": "Jewish orthodox conservatism",
        "agenda": "Promotes strict religious family values, opposition to LGBT advocacy in state structures, and Orthodox Jewish education.",
        "website": "https://www.noamparty.org.il/"
    },
    "הימין הממלכתי": {
        "name": "New Hope (United Right)",
        "wing": "right",
        "leader": "Gideon Sa'ar",
        "ideology": "National liberalism, security hawkishness",
        "agenda": "Focuses on governance reforms, judicial balance, West Bank settlement support, and educational advancement.",
        "website": "https://www.tikvahadasha.org.il/"
    }
}

async def fetch_csv_rows(url: str) -> list[dict]:
    print(f"Fetching CSV: {url} ...")
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        decoded_content = resp.content.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(decoded_content.splitlines())
        return list(reader)

async def translate_names_batch(hebrew_names: list[str]) -> dict[str, str]:
    if not settings.openai_api_key or not hebrew_names:
        return {}
    
    print(f"Translating {len(hebrew_names)} Hebrew names to English via OpenAI...")
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    # Batch names in groups of 80 to prevent prompt overflow
    batches = [hebrew_names[i:i+80] for i in range(0, len(hebrew_names), 80)]
    mapping = {}
    
    for i, batch in enumerate(batches):
        prompt = f"""
        Translate this list of Hebrew names of Israeli politicians into standard English transliterated names.
        List: {batch}
        
        Respond only with a JSON object mapping the Hebrew name to the English name. E.g.:
        {{"בנימין נתניהו": "Benjamin Netanyahu"}}
        """
        try:
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            batch_result = json.loads(resp.choices[0].message.content)
            mapping.update(batch_result)
        except Exception as e:
            print(f"Error translating batch {i+1}: {e}")
            
    return mapping

async def sync():
    await init_db()
    db = get_db()
    
    # 1. Fetch Knesset open datasets
    try:
        factions_rows = await fetch_csv_rows("https://production.oknesset.org/pipelines/data/knesset/kns_faction/kns_faction.csv")
        individuals_rows = await fetch_csv_rows("https://production.oknesset.org/pipelines/data/members/mk_individual/mk_individual.csv")
        positions_rows = await fetch_csv_rows("https://production.oknesset.org/pipelines/data/members/kns_persontoposition/kns_persontoposition.csv")
        persons_rows = await fetch_csv_rows("https://production.oknesset.org/pipelines/data/members/kns_person/kns_person.csv")
    except Exception as e:
        print(f"Failed to fetch Open Knesset data: {e}")
        await close_db()
        return

    # 2. Map PersonID -> Hebrew Name from kns_person.csv
    hebrew_names_by_person_id = {}
    for row in persons_rows:
        pid = row.get("PersonID")
        if pid:
            first = row.get("FirstName", "").strip()
            last = row.get("LastName", "").strip()
            hebrew_names_by_person_id[pid] = f"{first} {last}".strip()

    # 3. Process and Sync Parties (Factions) for KnessetNum = 25
    print("\n--- Syncing Parties ---")
    knesset_25_factions = [f for f in factions_rows if f.get("KnessetNum") == "25"]
    print(f"Found {len(knesset_25_factions)} factions in Knesset 25.")
    
    db_parties = {} # faction_id -> MongoDB ObjectId
    faction_name_mapping = {} # FactionName (Hebrew) -> English Name

    for f in knesset_25_factions:
        faction_id = f.get("Id")
        name_heb = f.get("Name", "").strip()
        
        # Determine wing, leader, ideology, website, and English name
        enrich = PARTY_ENRICHMENT.get(name_heb)
        if not enrich:
            # Try normalization/substring matching
            for k, v in PARTY_ENRICHMENT.items():
                if k in name_heb or name_heb in k:
                    enrich = v
                    break
                    
        name_eng = enrich["name"] if enrich else name_heb
        wing = enrich["wing"] if enrich else "unknown"
        leader = enrich["leader"] if enrich else None
        ideology = enrich["ideology"] if enrich else None
        agenda = enrich["agenda"] if enrich else None
        website = enrich["website"] if enrich else None
        
        # Count seats from PositionID 54 (faction membership)
        seats = len({
            p.get("PersonID") for p in positions_rows 
            if p.get("KnessetNum") == "25" and p.get("FactionID") == faction_id and p.get("PositionID") == "54"
        })
        
        party_doc = {
            "name": name_eng,
            "name_hebrew": name_heb,
            "wing": wing,
            "seats": seats or 1,
            "leader": leader,
            "ideology": ideology,
            "agenda": agenda,
            "website": website,
            "updated_at": datetime.utcnow()
        }
        
        # Upsert by unique English name to respect index
        await db.parties.update_one({"name": name_eng}, {"$set": party_doc}, upsert=True)
        stored_party = await db.parties.find_one({"name": name_eng})
        db_parties[faction_id] = stored_party["_id"]
        faction_name_mapping[name_heb] = name_eng
        print(f"Party synced: wing={wing}, seats={party_doc['seats']}")

    # 4. Map PersonID -> FactionID and FactionName using PositionID 54
    person_to_faction = {}
    for pos in positions_rows:
        if pos.get("KnessetNum") == "25" and pos.get("PositionID") == "54":
            person_id = pos.get("PersonID")
            faction_id = pos.get("FactionID")
            faction_name = pos.get("FactionName", "").strip()
            
            # Use current or non-finished position
            finish = pos.get("FinishDate", "").strip()
            is_current = pos.get("IsCurrent", "").lower() == "true"
            if not finish or is_current:
                person_to_faction[person_id] = {
                    "FactionID": faction_id,
                    "FactionName": faction_name
                }

    # 5. Map PersonID -> Photo URL and individual details from mk_individual.csv
    individual_by_person_id = {}
    for ind in individuals_rows:
        pid = ind.get("PersonID")
        if pid:
            individual_by_person_id[pid] = {
                "photo_url": ind.get("mk_individual_photo"),
                "email": ind.get("mk_individual_email"),
                "alt_names": ind.get("altnames")
            }

    # 6. Find all active MKs (PositionID = 43) in Knesset 25
    active_mk_rows = []
    active_person_ids = set()
    for pos in positions_rows:
        if pos.get("KnessetNum") == "25" and pos.get("PositionID") == "43":
            finish = pos.get("FinishDate", "").strip()
            is_current = pos.get("IsCurrent", "").lower() == "true"
            if not finish or is_current:
                pid = pos.get("PersonID")
                if pid not in active_person_ids:
                    active_person_ids.add(pid)
                    active_mk_rows.append(pos)

    print(f"\nFound {len(active_mk_rows)} active Knesset Members (Position 43).")

    # 7. Collect Hebrew names to translate
    names_to_translate = []
    hebrew_name_map = {}
    
    for pos in active_mk_rows:
        pid = pos.get("PersonID")
        name_heb = hebrew_names_by_person_id.get(pid)
        if not name_heb:
            # Fallback
            ind = individual_by_person_id.get(pid, {})
            name_heb = f"{ind.get('first_name_heb','')} {ind.get('last_name_heb','')}".strip()
            
        if not name_heb:
            name_heb = f"MP-{pid}"
            
        hebrew_name_map[pid] = name_heb
        if name_heb and not name_heb.startswith("MP-"):
            names_to_translate.append(name_heb)

    # 8. Call OpenAI translation
    names_to_translate = list(set(names_to_translate))
    translated_names = {}
    try:
        translated_names = await translate_names_batch(names_to_translate)
    except Exception as e:
        print(f"OpenAI name translation failed: {e}")

    # 9. Sync MPs
    synced_mps = 0
    for pos in active_mk_rows:
        pid = pos.get("PersonID")
        name_heb = hebrew_name_map.get(pid, f"MP-{pid}")
        name_eng = translated_names.get(name_heb)
        
        if not name_eng:
            name_eng = f"MP-{pid}"
            
        # Lookup faction from person_to_faction (PositionID 54)
        faction_info = person_to_faction.get(pid) or {}
        faction_id = faction_info.get("FactionID")
        faction_name_heb = faction_info.get("FactionName", "").strip()
        
        party_oid = db_parties.get(faction_id)
        # Fallback by name lookup
        if not party_oid and faction_name_heb:
            for fid, p_oid in db_parties.items():
                party = await db.parties.find_one({"_id": p_oid})
                if party and party.get("name_hebrew") == faction_name_heb:
                    party_oid = p_oid
                    break
                    
        party_name_eng = faction_name_mapping.get(faction_name_heb, faction_name_heb or "Independent")
        
        # Photo URL
        ind = individual_by_person_id.get(pid) or {}
        photo_url = ind.get("photo_url")
        if not photo_url or "placeholder" in photo_url:
            photo_url = f"https://knesset.gov.il/mk/images/members/{pid}.jpg"
            
        mp_doc = {
            "knesset_id": int(pid),
            "name": name_eng,
            "name_hebrew": name_heb,
            "role": pos.get("DutyDesc") or "Member of Knesset",
            "is_active": True,
            "party_name": party_name_eng,
            "party_id": str(party_oid) if party_oid else None,
            "photo_url": photo_url,
            "bio": f"Member of Knesset representing {party_name_eng}.",
            "updated_at": datetime.utcnow()
        }
        
        await db.mps.update_one({"knesset_id": int(pid)}, {"$set": mp_doc}, upsert=True)
        synced_mps += 1

    print(f"Successfully synced {synced_mps} MPs with correct party associations and translated English names.")
    await close_db()

if __name__ == "__main__":
    import json
    asyncio.run(sync())
