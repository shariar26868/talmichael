import asyncio
from app.core.database import init_db, get_db, close_db

async def inspect():
    await init_db()
    db = get_db()
    
    print("=== Database Stats ===")
    try:
        db_stats = await db.command("dbStats")
        print(f"Database: {db.name}")
        print(f"  Collections: {db_stats.get('collections')}")
        print(f"  Objects: {db_stats.get('objects')}")
        print(f"  Data Size: {db_stats.get('dataSize') / (1024 * 1024):.2f} MB")
        print(f"  Storage Size: {db_stats.get('storageSize') / (1024 * 1024):.2f} MB")
        print(f"  Index Size: {db_stats.get('indexSize') / (1024 * 1024):.2f} MB")
    except Exception as e:
        print(f"Error getting dbStats: {e}")
        
    print("\n=== Collection Details ===")
    collections = await db.list_collection_names()
    for col in collections:
        try:
            stats = await db.command("collStats", col)
            size = stats.get("size", 0) / (1024 * 1024)
            storage = stats.get("storageSize", 0) / (1024 * 1024)
            count = await db[col].count_documents({})
            print(f"  - {col:25s}: docs={count:6d}, size={size:6.2f}MB, storage={storage:6.2f}MB")
        except Exception as e:
            print(f"  - {col:25s}: Error getting stats: {e}")

    await close_db()

if __name__ == "__main__":
    asyncio.run(inspect())
