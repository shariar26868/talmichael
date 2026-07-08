import httpx

async def main():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = "https://main.knesset.gov.il/apps/mklobby/main/current-knesset-mks/all-current-mks"
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10) as client:
            resp = await client.get(url)
            print(f"Status: {resp.status_code}")
            print(f"Content-type: {resp.headers.get('content-type')}")
            print(f"Preview: {resp.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
