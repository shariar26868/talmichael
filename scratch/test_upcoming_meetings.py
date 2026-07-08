import asyncio
import httpx
import csv
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

async def test():
    url = "https://production.oknesset.org/pipelines/data/committees/kns_committeesession/kns_committeesession.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    sessions = []
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        # Since CSV might be large, let's stream it
        async with client.stream("GET", url, headers=headers) as response:
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                return
            
            lines = []
            count = 0
            async for line in response.aiter_lines():
                lines.append(line)
                count += 1
                # Read first 30,000 lines (which should cover the most recent sessions if it's ordered, or we can read more if needed)
                if count > 50000:
                    break
            
            reader = csv.DictReader(lines)
            for row in reader:
                knum = row.get("KnessetNum")
                if knum in ("25", "26"):
                    sessions.append(row)

    print(f"Found {len(sessions)} Knesset 25/26 sessions in the read chunk.")
    # Parse dates and sort by StartDate desc
    valid_sessions = []
    for s in sessions:
        start_str = s.get("StartDate")
        if start_str:
            try:
                dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
                valid_sessions.append((dt, s))
            except ValueError:
                pass
                
    valid_sessions.sort(key=lambda x: x[0], reverse=True)
    
    print("\nTop 15 most recent/upcoming committee sessions:")
    for dt, s in valid_sessions[:15]:
        print(f"Date: {dt} | Committee: {s.get('committee_name')} | Location: {s.get('Location')}")
        print(f"  Topics: {s.get('topics')}")
        print(f"  URL: {s.get('SessionUrl')}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test())
