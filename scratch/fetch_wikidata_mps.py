import httpx
import json

async def test_wikidata():
    url = "https://query.wikidata.org/sparql"
    # Query all entities with Knesset member ID (P9770) and image (P18)
    query = """
    SELECT ?knesset_id ?image WHERE {
      ?member wdt:P9770 ?knesset_id.
      ?member wdt:P18 ?image.
    }
    """
    headers = {
        "User-Agent": "TalmicahelApp/1.0 (contact@example.com)",
        "Accept": "application/sparql-results+json"
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30) as client:
        resp = await client.post(url, data={"query": query})
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", {}).get("bindings", [])
            print(f"Total members found on Wikidata with Knesset ID: {len(results)}")
            # Show top 10 with image
            with_img = [r for r in results if "image" in r]
            print(f"Total results: {len(results)}")
            for r in results[:15]:
                kid = r["knesset_id"]["value"]
                img = r["image"]["value"]
                print(f"ID: {kid} | Image: {img}")
        else:
            print(resp.text[:500])

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_wikidata())
