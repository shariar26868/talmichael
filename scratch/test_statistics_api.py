# scratch/test_statistics_api.py
"""
Quick integration test for GET /statistics endpoint.
Run: $env:PYTHONIOENCODING="utf-8"; $env:PYTHONPATH="."; python scratch/test_statistics_api.py
"""

import asyncio
import sys
import json
import logging

logging.basicConfig(level=logging.WARNING)

async def test_statistics():
    from app.main import app
    from app.core.database import init_db, close_db, get_db

    await init_db()
    db = get_db()

    # Clean old cache for fresh test
    await db.statistics_cache.delete_many({"key": "israel_social_stats"})

    import httpx
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:

        print("\n" + "="*60)
        print("TEST 1: GET /statistics?use_ai=false (Fallback keyword stats)")
        print("="*60)
        resp = await client.get("/statistics?use_ai=false")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()

        print(f"Headline: {data['headline']}")
        print(f"Summary: {data['summary'][:100]}...")
        print(f"Sections count: {len(data['sections'])}")
        print(f"Top stories count: {len(data['top_positive_stories'])}")
        print(f"Cached: {data['cached']}")

        assert len(data["sections"]) == 3
        assert data["sections"][0]["id"] == "community_volunteering"
        assert data["sections"][1]["id"] == "social_impact_sentiment"
        assert data["sections"][2]["id"] == "sector_highlights"
        assert len(data["sections"][0]["data"]) == 3   # Tech, Youth, Civilian
        assert len(data["sections"][1]["data"]) == 3   # Pos, Neutral, Critical
        assert len(data["sections"][2]["data"]) == 5   # 5 sectors

        # Verify each section's values sum to ~100
        for section in data["sections"]:
            total = sum(d["value"] for d in section["data"])
            print(f"  Section '{section['title']}' — total = {total}%")
            assert 98 <= total <= 102, f"Section values don't sum to ~100: {total}"

        print("PASS: All 3 chart sections returned with correct structure and ~100% sums.")

        print("\n" + "="*60)
        print("TEST 2: GET /statistics (second call — should be cached)")
        print("="*60)
        resp2 = await client.get("/statistics?use_ai=false")
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["cached"] == True
        print(f"Cached: {data2['cached']} ✓")
        print("PASS: Second call returned cached result.")

        print("\n" + "="*60)
        print("TEST 3: GET /statistics?refresh=true (force refresh)")
        print("="*60)
        resp3 = await client.get("/statistics?use_ai=false&refresh=true")
        assert resp3.status_code == 200
        data3 = resp3.json()
        assert data3["cached"] == False
        print(f"Cached: {data3['cached']} ✓  (fresh generation)")
        print("PASS: Refresh=true bypassed cache and regenerated statistics.")

        print("\n" + "="*60)
        print("Full response sample (section 1 data):")
        print("="*60)
        print(json.dumps(data["sections"][0], indent=2))

    await close_db()
    print("\n✅ ALL TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(test_statistics())
