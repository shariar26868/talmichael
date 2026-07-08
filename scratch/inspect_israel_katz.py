import httpx
import asyncio

async def test():
    # Israel Katz on Wikidata is Q983215
    url = "https://www.wikidata.org/wiki/Special:EntityData/Q983215.json"
    headers = {"User-Agent": "TalmicahelApp/1.0 (contact@example.com)"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10) as client:
        resp = await client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            entity = data.get("entities", {}).get("Q983215", {})
            claims = entity.get("claims", {})
            print("Claims keys:")
            # Print all property keys and their values
            for prop_id, prop_claims in claims.items():
                for claim in prop_claims:
                    mainsnak = claim.get("mainsnak", {})
                    datavalue = mainsnak.get("datavalue", {})
                    value = datavalue.get("value")
                    val_str = str(value)
                    if len(val_str) < 100:
                        print(f"Prop: {prop_id} | Value: {val_str}")
        else:
            print(f"Error: {resp.status_code}")

if __name__ == "__main__":
    asyncio.run(test())
