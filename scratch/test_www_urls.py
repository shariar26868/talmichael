import httpx

async def main():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    # Test Aryeh Deri (ID 2291)
    urls = [
        "https://www.knesset.gov.il/mk/images/members/2291.jpg",
        "https://www.knesset.gov.il/mk/images/members/DeriArie_2291.jpg",
        "http://www.knesset.gov.il/mk/images/members/DeriArie_2291.jpg",
        "https://www.knesset.gov.il/mk/images/members/ArieDeri_2291.jpg",
        "https://main.knesset.gov.il/static/images/mk/DeriArie_2291.jpg",
    ]
    for url in urls:
        try:
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=5) as client:
                resp = await client.head(url)
                print(f"URL: {url} -> Status: {resp.status_code}")
        except Exception as e:
            print(f"URL: {url} -> Error: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
