import asyncio
import sys
from app.core.database import init_db, get_db, close_db

sys.stdout.reconfigure(encoding='utf-8')

async def inspect():
    await init_db()
    db = get_db()
    
    print("=== First cached_articles doc (keys) ===")
    doc = await db.cached_articles.find_one({})
    if doc:
        for k, v in doc.items():
            val_preview = str(v)[:80] if v else None
            print(f"  {k}: {val_preview}")
    else:
        print("  NO DOCUMENTS FOUND")
        
    print("\n=== Election-keyword match count ===")
    election_keywords = [
        "election", "vote", "poll", "ballot", "campaign", "candidate",
        "Knesset 2026", "coalition", "opposition", "legislation",
        "Bennett", "Netanyahu", "Lapid", "Gantz", "Lieberman",
        "Eisenkot", "Smotrich", "Ben-Gvir",
    ]
    keyword_regex = "|".join(election_keywords)
    count = await db.cached_articles.count_documents({
        "$or": [
            {"title": {"$regex": keyword_regex, "$options": "i"}},
            {"description": {"$regex": keyword_regex, "$options": "i"}},
        ]
    })
    print(f"  Matched election articles: {count}")
    
    # show one match
    if count > 0:
        sample = await db.cached_articles.find_one({
            "$or": [
                {"title": {"$regex": keyword_regex, "$options": "i"}},
                {"description": {"$regex": keyword_regex, "$options": "i"}},
            ]
        })
        print(f"\n  Sample match title: {sample.get('title')}")
        print(f"  Sample source: {sample.get('source') or sample.get('source_name')}")
        print(f"  Sample pub_date: {sample.get('pub_date')}")
        
    await close_db()

if __name__ == "__main__":
    asyncio.run(inspect())
