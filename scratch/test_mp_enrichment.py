import asyncio
import json
from datetime import datetime
from app.core.database import init_db, get_db, close_db
from app.services.blocs_service import get_mp_full_profile

def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def safe_print(data):
    print(json.dumps(data, indent=2, ensure_ascii=False, default=datetime_serializer))

async def test():
    await init_db()
    db = get_db()
    
    # Let's find David Bitan's MP doc to get his ID
    mp = await db.mps.find_one({"name": "David Bitan"})
    if not mp:
        mp = await db.mps.find_one({"name_hebrew": "דוד ביטן"})
        
    if mp:
        mp_id = str(mp.get("_id"))
        print(f"Testing get_mp_full_profile for {mp.get('name')} (ID: {mp_id})")
        profile = await get_mp_full_profile(mp_id)
        if profile:
            safe_print(profile)
        else:
            print("Failed to get profile.")
    else:
        print("David Bitan not found in DB")
        
    await close_db()

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(test())
