# scratch/test_bills_api.py
"""
Integration test script for Bills API.
Run: $env:PYTHONPATH="."; python scratch/test_bills_api.py
"""

import asyncio
import sys
import json
import logging
from app.main import app
from app.core.database import init_db, close_db, get_db

logging.basicConfig(level=logging.INFO)

async def test_bills_flow():
    # Ensure DB is initialized and seeded
    await init_db()
    db = get_db()
    
    # Clean user votes for clean tests
    await db.user_bill_votes.delete_many({"bill_id": "security-2026"})
    
    # We use ASGI client to directly target the FastAPI application
    import httpx
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        print("\n" + "="*60)
        print("TEST 1: GET /bills (user_tier=free, with_analysis=false)")
        print("="*60)
        resp = await client.get("/bills?user_tier=free&with_analysis=false")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        print(f"Total bills returned: {len(data['bills'])}")
        
        # Verify mockup bills are ordered first
        expected_order = [
            "security-2026", "education-2026", "tax-2026", "tech-2025",
            "energy-2026", "health-2026", "startup-2026"
        ]
        returned_ids = [b["bill_id"] for b in data["bills"][:7]]
        print(f"Top 7 bill IDs: {returned_ids}")
        assert returned_ids == expected_order, "Seeded mockup bills order mismatch!"
        
        # Verify AI analysis is locked
        security_bill = data["bills"][0]
        assert security_bill["explanation"] is None, "Expected explanation to be None"
        assert security_bill["key_provisions"] is None, "Expected key_provisions to be None"
        print("PASS: top 7 ordered correctly, AI analysis fields locked/None.")

        print("\n" + "="*60)
        print("TEST 2: GET /bills (user_tier=free, with_analysis=true)")
        print("="*60)
        resp = await client.get("/bills?user_tier=free&with_analysis=true")
        assert resp.status_code == 200
        data = resp.json()
        security_bill = data["bills"][0]
        print(f"Explanation (free tier): {security_bill['explanation']}")
        assert "Upgrade to PRO" in security_bill["explanation"]
        print("PASS: Lock notice returned correctly on free tier with with_analysis=true.")

        print("\n" + "="*60)
        print("TEST 3: GET /bills (user_tier=pro, with_analysis=true)")
        print("="*60)
        resp = await client.get("/bills?user_tier=pro&with_analysis=true")
        assert resp.status_code == 200
        data = resp.json()
        security_bill = data["bills"][0]
        print(f"Title: {security_bill['title']}")
        print(f"Explanation: {security_bill['explanation']}")
        print(f"Key Provisions: {security_bill['key_provisions']}")
        print(f"Category Tags: {security_bill['category_tags']}")
        
        assert security_bill["explanation"] is not None
        assert len(security_bill["key_provisions"]) > 0
        assert "Security" in security_bill["category_tags"]
        print("PASS: Seeded AI analysis returned successfully for PRO tier.")

        print("\n" + "="*60)
        print("TEST 4: POST /bills/{bill_id}/vote")
        print("="*60)
        # We vote on security-2026 (base: support=7719, oppose=3486, neutral=1245, total=12450)
        payload = {"vote": "support"}
        resp = await client.post("/bills/security-2026/vote?user_id=test_user_1", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        res_data = resp.json()
        print("Vote response:", json.dumps(res_data, indent=2))
        
        assert res_data["bill_id"] == "security-2026"
        assert res_data["your_vote"] == "support"
        # Total votes should be 12450 + 1 = 12451
        assert res_data["public_opinion"]["total_votes"] == 12451
        print("PASS: Vote registered, total votes incremented to 12451.")

        # Overwrite vote: test_user_1 changes vote to 'oppose'
        payload = {"vote": "oppose"}
        resp = await client.post("/bills/security-2026/vote?user_id=test_user_1", json=payload)
        assert resp.status_code == 200
        res_data = resp.json()
        assert res_data["your_vote"] == "oppose"
        assert res_data["public_opinion"]["total_votes"] == 12451  # total remains same
        print("PASS: Vote changed successfully, total votes remains 12451.")

        # Retract vote: test_user_1 removes vote by sending 'none'
        payload = {"vote": "none"}
        resp = await client.post("/bills/security-2026/vote?user_id=test_user_1", json=payload)
        assert resp.status_code == 200
        res_data = resp.json()
        assert res_data["your_vote"] == "none"
        assert res_data["public_opinion"]["total_votes"] == 12450  # total decrements back to base
        print("PASS: Vote retracted successfully, total votes decremented to 12450.")

        # Let's verify voting 'neutral' from another user updates totals
        payload = {"vote": "neutral"}
        resp = await client.post("/bills/security-2026/vote?user_id=test_user_2", json=payload)
        assert resp.status_code == 200
        res_data = resp.json()
        print("Second user vote response:", json.dumps(res_data, indent=2))
        assert res_data["public_opinion"]["total_votes"] == 12451
        print("PASS: Second vote registered, total votes incremented to 12451.")

        # Let's check error handling for invalid vote choices
        payload = {"vote": "invalid_choice"}
        resp = await client.post("/bills/security-2026/vote?user_id=test_user_2", json=payload)
        print("Invalid vote status:", resp.status_code)
        assert resp.status_code == 400
        print("PASS: Invalid vote choice correctly returns 400 Bad Request.")

        # Let's check non-existent bill
        resp = await client.post("/bills/nonexistent-bill/vote", json={"vote": "support"})
        print("Nonexistent bill status:", resp.status_code)
        assert resp.status_code == 404
        print("PASS: Nonexistent bill correctly returns 404 Not Found.")

        print("\n" + "="*60)
        print("TEST 5: GET /bills?days=30 (Date-wise Bills)")
        print("="*60)
        # Filters: days=30 (last 30 days)
        # Should return exactly our mock bills within 30 days: energy-2026, health-2026, startup-2026, security-2026 (seeding date is March 1, 2026 - wait! March 1 is more than 30 days. So only energy, health, startup)
        resp = await client.get("/bills?days=30&user_tier=pro&with_analysis=true")
        assert resp.status_code == 200
        data = resp.json()
        print(f"Total bills in last 30 days: {len(data['bills'])}")
        
        returned_ids = [b["bill_id"] for b in data["bills"]]
        print(f"Returned bill IDs: {returned_ids}")
        
        # Verify exactly the mock bills within 30 days are present
        assert "energy-2026" in returned_ids
        assert "health-2026" in returned_ids
        assert "startup-2026" in returned_ids
        
        # Verify AI analysis is fully populated and not locked
        energy_bill = [b for b in data["bills"] if b["bill_id"] == "energy-2026"][0]
        print(f"Title: {energy_bill['title']}")
        print(f"Explanation: {energy_bill['explanation']}")
        print(f"Provisions: {energy_bill['key_provisions']}")
        assert "mandates the integration of solar and wind" in energy_bill["explanation"]
        assert len(energy_bill["key_provisions"]) == 3
        
        print("PASS: Date-wise filtering for bills works perfectly and returns full AI explanations.")

        print("\n" + "="*60)
        print("TEST 6: GET /bills/{bill_id} (Single Bill Retrieval)")
        print("="*60)
        # 1. Get existing bill with pro tier and analysis
        resp = await client.get("/bills/energy-2026?user_tier=pro&with_analysis=true")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        bill = resp.json()
        print(f"Single Bill ID: {bill['bill_id']} | Title: {bill['title']}")
        assert bill["bill_id"] == "energy-2026"
        assert bill["explanation"] is not None
        assert "mandates the integration of solar and wind" in bill["explanation"]
        
        # 2. Get with free tier and analysis
        resp = await client.get("/bills/energy-2026?user_tier=free&with_analysis=true")
        assert resp.status_code == 200
        bill_free = resp.json()
        assert "Upgrade to PRO" in bill_free["explanation"]
        print("PASS: Locked notice returned correctly on single bill free tier with analysis.")
        
        # 3. Get non-existent bill
        resp = await client.get("/bills/nonexistent-id")
        assert resp.status_code == 404
        print("PASS: Nonexistent single bill correctly returns 404 Not Found.")

    await close_db()

if __name__ == "__main__":
    asyncio.run(test_bills_flow())
