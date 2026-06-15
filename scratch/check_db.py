import asyncio
from app.core.database import init_db, get_db, close_db

def safe_str(val):
    if val is None:
        return "None"
    return str(val).encode('ascii', errors='backslashreplace').decode('ascii')

async def check():
    await init_db()
    db = get_db()
    
    print("--- Parties in DB ---")
    cursor = db.parties.find()
    async for party in cursor:
        print(f"Name: {safe_str(party.get('name'))} | Seats: {party.get('seats')} | Wing: {safe_str(party.get('wing'))} | Leader: {safe_str(party.get('leader'))}")
        
    print("\n--- MPs Analysis ---")
    total = await db.mps.count_documents({})
    print(f"Total MPs: {total}")
    
    unnamed = await db.mps.count_documents({"name": {"$regex": "^MP-"}})
    named = total - unnamed
    print(f"Named MPs: {named} | Unnamed MPs (fallback): {unnamed}")
    
    print("\n--- Sample of Named MPs ---")
    cursor = db.mps.find({"name": {"$not": {"$regex": "^MP-"}}}).limit(10)
    async for mp in cursor:
        print(f"  Name: {safe_str(mp.get('name'))} | Hebrew: {safe_str(mp.get('name_hebrew'))} | Party: {safe_str(mp.get('party_name'))} | Role: {safe_str(mp.get('role'))}")
        
    await close_db()

if __name__ == "__main__":
    asyncio.run(check())
