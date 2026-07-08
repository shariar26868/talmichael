import asyncio
import sys
from app.core.database import init_db, get_db, close_db

sys.stdout.reconfigure(encoding='utf-8')

async def inspect():
    await init_db()
    db = get_db()
    
    print("=== MPs Collection ===")
    cursor = db.mps.find({}).limit(5)
    mps = await cursor.to_list(length=5)
    for m in mps:
        print(f"Name: {m.get('name')} | Hebrew: {m.get('name_hebrew')}")
        print(f"  Party: {m.get('party_name')} | ID: {m.get('knesset_id')}")
        print(f"  Photo URL: {m.get('photo_url')}")
        print(f"  Bio: {m.get('bio')}")
        print(f"  Career history: {m.get('career_history')}")
        print("-" * 50)
        
    await close_db()

if __name__ == "__main__":
    asyncio.run(inspect())
