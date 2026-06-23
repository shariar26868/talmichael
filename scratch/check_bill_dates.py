import asyncio
from datetime import datetime, timedelta
from app.core.database import init_db, get_db, close_db

async def main():
    await init_db()
    db = get_db()
    
    # Check all statuses
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    cursor = db.knesset_bills.aggregate(pipeline)
    print("--- Status counts in DB ---")
    async for doc in cursor:
        print(f"  Status: {doc['_id']} -> Count: {doc['count']}")
        
    # Check max and min last_updated dates
    cursor = db.knesset_bills.find({}, {"last_updated": 1}).sort("last_updated", -1).limit(5)
    print("\n--- Top 5 most recent bills last_updated ---")
    async for doc in cursor:
        print(f"  Bill ID: {doc.get('bill_id')} -> last_updated: {doc.get('last_updated')}")
        
    await close_db()

if __name__ == "__main__":
    asyncio.run(main())
