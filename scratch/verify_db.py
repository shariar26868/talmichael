import asyncio
from app.core.database import init_db, get_db, close_db

async def check():
    await init_db()
    db = get_db()
    parties = await db.parties.find({}, {"_id": 0, "name": 1, "wing": 1, "seats": 1, "leader": 1}).sort("seats", -1).to_list(20)
    print("=== PARTIES ===")
    for p in parties:
        name = p.get("name", "?")
        wing = p.get("wing", "?")
        seats = p.get("seats", 0)
        leader = p.get("leader", "N/A")
        print(f"  {name[:30]:30s} | {wing:22s} | seats={seats:3d} | {leader}")

    total_mps = await db.mps.count_documents({"is_active": True})
    named_mps = await db.mps.count_documents({"is_active": True, "name": {"$not": {"$regex": "^MK-"}}})
    total_bills = await db.knesset_bills.count_documents({})
    print(f"\n=== COUNTS ===")
    print(f"  Active MPs: {total_mps}")
    print(f"  MPs with English names: {named_mps}")
    print(f"  Bills (Knesset 25): {total_bills}")

    # Sample bill
    bill = await db.knesset_bills.find_one({}, {"_id": 0, "bill_id": 1, "name": 1, "status": 1, "source": 1})
    if bill:
        print(f"\n=== SAMPLE BILL ===")
        print(f"  ID: {bill.get('bill_id')} | status: {bill.get('status')} | source: {bill.get('source')}")
        print(f"  Name (Hebrew): {repr(bill.get('name', ''))[:80]}")

    await close_db()

asyncio.run(check())
