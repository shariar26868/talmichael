import pandas as pd
import asyncio
from app.services.political_service import _fetch_oknesset_csv, OKNESSET_INDIVIDUALS_URL, OKNESSET_PERSONS_URL

import sys
sys.stdout.reconfigure(encoding='utf-8')

async def inspect():
    print("Fetching individuals...")
    ind = await _fetch_oknesset_csv(OKNESSET_INDIVIDUALS_URL)
    if ind:
        df = pd.DataFrame(ind)
        print("Individuals columns:", df.columns.tolist())
        print("First 5 individuals:")
        for idx, row in df.head(5).iterrows():
            print(f"Name: {row.get('mk_individual_name')} | Eng: {row.get('mk_individual_name_eng')} | PersonID: {row.get('PersonID')} | mk_individual_id: {row.get('mk_individual_id')}")
        
    print("\nFetching persons...")
    pers = await _fetch_oknesset_csv(OKNESSET_PERSONS_URL)
    if pers:
        df2 = pd.DataFrame(pers)
        print("Persons columns:", df2.columns.tolist())
        print("First person row:")
        print(df2.iloc[0].to_dict())

if __name__ == "__main__":
    asyncio.run(inspect())
