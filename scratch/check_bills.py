import asyncio
from app.core.database import init_db, get_db, close_db

def safe_str(val):
    if val is None:
        return "None"
    return str(val).encode('ascii', errors='backslashreplace').decode('ascii')

async def check():
    await init_db()
    db = get_db()
    
    # Let's find David Bitan
    mp = await db.mps.find_one({"name": "David Bitan"})
    if not mp:
        mp = await db.mps.find_one({"name_hebrew": "דוד ביטן"})
        
    if mp:
        print(f"MP: {mp.get('name')} | Hebrew: {safe_str(mp.get('name_hebrew'))}")
        # Search bills initiated by this MP
        heb_name = mp.get("name_hebrew")
        if heb_name:
            count = await db.knesset_bills.count_documents({"initiator": heb_name})
            print(f"Total initiated bills in DB: {count}")
            passed = await db.knesset_bills.count_documents({"initiator": heb_name, "status": "Enacted – became law"})
            print(f"Passed bills in DB: {passed}")
            
            # Print a few bills
            async for bill in db.knesset_bills.find({"initiator": heb_name}).limit(5):
                print(f"  Bill: {safe_str(bill.get('name'))} | Status: {safe_str(bill.get('status'))}")
    else:
        print("David Bitan not found in DB")
        
    await close_db()

if __name__ == "__main__":
    asyncio.run(check())
