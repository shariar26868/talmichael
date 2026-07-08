import httpx
import asyncio

async def test():
    url = "https://query.wikidata.org/sparql"
    query = """
    SELECT ?knesset_id ?image ?name_he ?name_en WHERE {
      ?member wdt:P9770 ?knesset_id.
      ?member wdt:P18 ?image.
      OPTIONAL {
        ?member rdfs:label ?name_he.
        FILTER(LANG(?name_he) = "he")
      }
      OPTIONAL {
        ?member rdfs:label ?name_en.
        FILTER(LANG(?name_en) = "en")
      }
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
            results = resp.json().get("results", {}).get("bindings", [])
            print(f"Total Knesset members with images: {len(results)}")
            for r in results[:10]:
                he = r.get("name_he", {}).get("value", "")
                en = r.get("name_en", {}).get("value", "")
                img = r["image"]["value"]
                print(f"Hebrew: {he} | English: {en} | Image: {img}")
        else:
            print(resp.text[:500])

if __name__ == "__main__":
    asyncio.run(test())
