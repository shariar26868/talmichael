import os
import pymongo
from dotenv import load_dotenv

load_dotenv()

mongo_url = os.getenv("MONGODB_URL")
print(f"Connecting to MongoDB...")
client = pymongo.MongoClient(mongo_url)

try:
    print("Listing databases...")
    dbs = client.list_database_names()
    print(f"Databases found: {dbs}")
    
    for db_name in dbs:
        db = client[db_name]
        try:
            stats = db.command("dbStats")
            storage_size_mb = stats.get("storageSize", 0) / (1024 * 1024)
            data_size_mb = stats.get("dataSize", 0) / (1024 * 1024)
            print(f"Database: {db_name:20s} | Storage: {storage_size_mb:.2f} MB | Data: {data_size_mb:.2f} MB")
        except Exception as e:
            print(f"Database: {db_name:20s} | Error getting stats: {e}")
            
except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
