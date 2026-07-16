import asyncio
import sys
sys.path.insert(0, '.')
from app.utils.licensed_apis import fetch_from_newsdata_io, fetch_from_gdelt, fetch_from_newsapi, get_quota_status

async def test():
    print("=== Testing NewsData.io (politics) ===")
    articles = await fetch_from_newsdata_io("politics", limit=3)
    print(f"Got {len(articles)} articles")
    for a in articles[:2]:
        src = a.get("api_source", "?")
        title = a.get("title", "")[:80]
        print(f"  [{src}] {title}")

    print()
    print("=== Testing GDELT (security) ===")
    articles2 = await fetch_from_gdelt("security", limit=3)
    print(f"Got {len(articles2)} articles")
    for a in articles2[:2]:
        src = a.get("api_source", "?")
        title = a.get("title", "")[:80]
        print(f"  [{src}] {title}")

    print()
    print("=== Testing NewsAPI (economy) ===")
    articles3 = await fetch_from_newsapi("economy", limit=3)
    print(f"Got {len(articles3)} articles")
    for a in articles3[:2]:
        src = a.get("api_source", "?")
        title = a.get("title", "")[:80]
        print(f"  [{src}] {title}")

    print()
    print("=== Quota after tests ===")
    print(get_quota_status())

asyncio.run(test())
