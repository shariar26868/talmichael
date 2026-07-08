import pandas as pd
import httpx
import io
import sys

sys.stdout.reconfigure(encoding='utf-8')

async def test_csv():
    url = "https://production.oknesset.org/pipelines/data/members/mk_individual/mk_individual.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30) as client:
        resp = await client.get(url)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            df = pd.read_csv(io.StringIO(resp.text))
            print("Columns:", df.columns.tolist())
            print(df[['mk_individual_id', 'PersonID', 'mk_individual_photo', 'mk_individual_name_eng']].head(10))
            # Find rows where photo is not null
            with_photo = df[df['mk_individual_photo'].notna()]
            print(f"Total rows: {len(df)}, Rows with photo: {len(with_photo)}")
            if len(with_photo) > 0:
                print(with_photo[['mk_individual_name_eng', 'mk_individual_photo']].head(10))
        else:
            print(resp.text[:500])

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_csv())
