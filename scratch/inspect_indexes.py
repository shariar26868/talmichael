import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def inspect():
    url = "mongodb+srv://smtnayem:smtnayemproject@cluster0.p87lrd6.mongodb.net/talmichael530?appName=Cluster0"
    client = AsyncIOMotorClient(url)
    db = client["talmichael530"]
    
    collections = await db.list_collection_names()
    print(f"Collections: {collections}")
    
    for coll_name in sorted(collections):
        coll = db[coll_name]
        try:
            indexes = []
            async for index in coll.list_indexes():
                indexes.append(index)
            print(f"\nCollection: {coll_name}")
            for idx in indexes:
                print(f"  Name: {idx.get('name')} | Key: {idx.get('key')} | Unique: {idx.get('unique', False)}")
        except Exception as e:
            print(f"Error reading indexes for {coll_name}: {e}")
            
    client.close()

asyncio.run(inspect())
