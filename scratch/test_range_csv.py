import asyncio
import httpx
import csv
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

async def test():
    url = "https://production.oknesset.org/pipelines/data/committees/kns_committeesession/kns_committeesession.csv"
    
    # Let's check size first
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.head(url)
        content_length = int(resp.headers.get("content-length", 0))
        print(f"Content length: {content_length}")
        
        # Download last 3MB of the CSV
        chunk_size = 3 * 1024 * 1024
        start_byte = max(0, content_length - chunk_size)
        headers = {"Range": f"bytes={start_byte}-{content_length}"}
        
        print(f"Downloading range: {start_byte} to {content_length}...")
        resp2 = await client.get(url, headers=headers)
        print(f"Range download status: {resp2.status_code}")
        
        content = resp2.text
        # Split by lines, skip the first line because it might be partial/cut off
        lines = content.splitlines()[1:]
        
        # We need the fieldnames. Let's request the first 10KB to get the header line
        header_headers = {"Range": "bytes=0-10000"}
        resp_header = await client.get(url, headers=header_headers)
        header_line = resp_header.text.splitlines()[0]
        fieldnames = csv.reader([header_line]).__next__()
        
        print("CSV Fieldnames:", fieldnames)
        
        # Parse the partial lines using DictReader and fieldnames
        reader = csv.DictReader(lines, fieldnames=fieldnames)
        
        sessions = []
        for row in reader:
            knum = row.get("KnessetNum")
            # If the row is partially formed, or KnessetNum is not correct, skip
            if knum in ("25", "26"):
                sessions.append(row)
                
        print(f"Parsed {len(sessions)} sessions from the end of the file.")
        
        # Sort and print
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
        
        print("\nTop 15 most recent/upcoming committee sessions from end of CSV:")
        for dt, s in valid_sessions[:15]:
            print(f"Date: {dt} | Committee: {s.get('committee_name')} | Location: {s.get('Location')}")
            print(f"  Topics: {s.get('topics')}")
            print(f"  URL: {s.get('SessionUrl')}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test())
