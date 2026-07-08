import httpx
import asyncio

async def test():
    url = "https://query.wikidata.org/sparql"
    # Simple query
    query = "SELECT * WHERE { wd:Q42 rdfs:label ?label. FILTER(LANG(?label) = 'en') }"
    headers = {
        "User-Agent": "TalmicahelApp/1.0 (contact@example.com)",
        "Accept": "application/sparql-results+json"
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10) as client:
        try:
            resp = await client.get(url, params={"query": query})
            print(f"GET status: {resp.status_code}")
            if resp.status_code == 200:
                print(resp.json())
        except Exception as e:
            print(f"GET error: {e}")

        try:
            resp = await client.post(url, data={"query": query})
            print(f"POST status: {resp.status_code}")
            if resp.status_code == 200:
                print(resp.json())
        except Exception as e:
            print(f"POST error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
