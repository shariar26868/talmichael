import asyncio
import sys
from app.core.database import init_db, get_db, close_db

# Force utf-8 encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

async def inspect():
    await init_db()
    db = get_db()
    
    print("=== Parties Collection ===")
    cursor = db.parties.find({}, {"_id": 0})
    parties = await cursor.to_list(length=100)
    for p in parties:
        name = p.get('name')
        name_he = p.get('name_hebrew')
        print(f"Party: {name} (Hebrew Name length: {len(name_he) if name_he else 0})")
        print(f"  Seats: {p.get('seats')}")
        print(f"  Bloc: {p.get('bloc')}")
        print(f"  Leader: {p.get('leader')}")
        print(f"  Wikipedia: {p.get('wikipedia_url')}")
        print(f"  Badge Tooltip: {p.get('verification_badge', {}).get('tooltip') if p.get('verification_badge') else None}")
        print("-" * 40)
        
    await close_db()

if __name__ == "__main__":
    asyncio.run(inspect())
