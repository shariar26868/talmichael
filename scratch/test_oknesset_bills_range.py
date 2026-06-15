import httpx
import csv

async def test_range_bills():
    # 1. Send a HEAD request to get the total content length
    url = "https://production.oknesset.org/pipelines/data/bills/kns_bill/kns_bill.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        try:
            head_resp = await client.head(url, headers=headers)
            content_length = int(head_resp.headers.get("content-length", 0))
            print(f"Total CSV size: {content_length / (1024*1024):.2f} MB")
            
            if content_length == 0:
                print("Could not retrieve content length.")
                return
                
            # 2. Retrieve the last 200 KB
            range_start = max(0, content_length - 200 * 1024)
            headers["Range"] = f"bytes={range_start}-{content_length}"
            
            resp = await client.get(url, headers=headers)
            print(f"Retrieved chunk size: {len(resp.content) / 1024:.2f} KB")
            
            # Since we sliced the file, the first line is incomplete. We skip it.
            text = resp.content.decode("utf-8", errors="replace")
            lines = text.splitlines()
            if len(lines) > 1:
                lines = lines[1:] # discard first partial line
                
            # We also need the header line to parse it as CSV
            # Let's fetch the first 2 KB to get the header line
            headers_header = {"User-Agent": "Mozilla/5.0", "Range": "bytes=0-2000"}
            header_resp = await client.get(url, headers=headers_header)
            header_text = header_resp.content.decode("utf-8", errors="replace")
            header_line = header_text.splitlines()[0]
            print(f"CSV Header:\n  {header_line}")
            
            # Reconstruct CSV data
            csv_data = [header_line] + lines
            reader = csv.DictReader(csv_data)
            
            # Print last 5 bills
            bills = list(reader)
            print(f"Parsed {len(bills)} bill rows from the end of the file.")
            
            print("\nLast 5 bills:")
            for b in bills[-5:]:
                print(f"  BillID: {b.get('BillID')} | KnessetNum: {b.get('KnessetNum')} | Name: {b.get('Name')[:100]} | LastUpdated: {b.get('LastUpdatedDate')}")
                
        except Exception as e:
            print(f"Error: {e}")

import asyncio
asyncio.run(test_range_bills())
