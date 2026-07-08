import asyncio
import httpx
import csv
import sys

sys.stdout.reconfigure(encoding='utf-8')

async def test():
    # Use streaming to only get the first 50 lines (so it's super fast)
    url = "https://production.oknesset.org/pipelines/data/committees/kns_committeesession/kns_committeesession.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        async with client.stream("GET", url, headers=headers) as response:
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                return
            
            lines = []
            async for line in response.aiter_lines():
                lines.append(line)
                if len(lines) >= 10:
                    break
            
            decoded_lines = [l for l in lines]
            reader = csv.DictReader(decoded_lines)
            print("Columns:", reader.fieldnames)
            print("\nFirst row sample:")
            for row in reader:
                print(dict(row))
                break

if __name__ == "__main__":
    asyncio.run(test())
