import asyncio
import httpx
import csv
from datetime import datetime, timedelta

async def find_passed():
    url = "https://production.oknesset.org/pipelines/data/bills/kns_bill/kns_bill.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        head_resp = await client.head(url, headers=headers)
        content_length = int(head_resp.headers.get("content-length", 0))
        
        # Read last 3 MB to be thorough
        chunk_size = 3 * 1024 * 1024
        range_start = max(0, content_length - int(chunk_size))
        headers["Range"] = f"bytes={range_start}-{content_length}"
        
        resp = await client.get(url, headers=headers)
        text = resp.content.decode("utf-8", errors="replace")
        lines = text.splitlines()
        if len(lines) > 1:
            lines = lines[1:]
            
        headers_header = {"User-Agent": "Mozilla/5.0", "Range": "bytes=0-2000"}
        header_resp = await client.get(url, headers=headers_header)
        header_text = header_resp.content.decode("utf-8", errors="replace")
        header_line = header_text.splitlines()[0]
        
        csv_data = [header_line] + lines
        reader = csv.DictReader(csv_data)
        
        cutoff_30d = datetime(2026, 5, 23)
        
        status_counts = {}
        recent_passed = []
        
        for b in reader:
            lu_str = b.get("LastUpdatedDate") or ""
            if not lu_str:
                continue
            try:
                dt_part = lu_str.split("T")[0]
                dt = datetime.strptime(dt_part, "%Y-%m-%d")
            except Exception:
                continue
                
            status_id = b.get("StatusID") or "none"
            sub_type_desc = b.get("SubTypeDesc") or ""
            
            if dt >= cutoff_30d:
                status_counts[status_id] = status_counts.get(status_id, 0) + 1
                
            if status_id in ("120", "162"):
                recent_passed.append((dt, b))
                
        print("Status ID counts for bills updated in the last 30 days (since May 23, 2026):")
        for sid, cnt in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  StatusID {sid} -> Count: {cnt}")
            
        print(f"\nTotal passed/enacted bills in chunk: {len(recent_passed)}")
        recent_passed.sort(key=lambda x: x[0], reverse=True)
        print("Most recent 5 passed bills in chunk:")
        for dt, b in recent_passed[:5]:
            print(f"  Date: {b.get('LastUpdatedDate')} | BillID: {b.get('BillID')} | StatusID: {b.get('StatusID')} | Name: {b.get('Name')[:80]}")

asyncio.run(find_passed())
