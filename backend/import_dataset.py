import os
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:agri_pass@localhost/agri_db'

import asyncio
import pandas as pd
from datetime import datetime
from api.models.database import AsyncSessionLocal, RawPrice
from sqlalchemy import delete, text

async def main():
    print("Loading dataset...")
    df = pd.read_csv('agri_prices_dataset.csv')
    print(f"Loaded {len(df):,} records")
    print(f"Commodities: {df['commodity'].unique()}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")

    async with AsyncSessionLocal() as db:
        # Clear old data
        print("\nClearing old price data...")
        await db.execute(delete(RawPrice))
        await db.commit()
        print("Old data cleared!")

        # Import in batches of 1000
        print("\nImporting new data...")
        batch = []
        total = 0

        for _, row in df.iterrows():
            try:
                record = RawPrice(
                    commodity=str(row['commodity']).lower().strip(),
                    date=pd.to_datetime(row['date']),
                    market=str(row['market']),
                    state=str(row['state']),
                    modal_price=float(row['modal_price_rs_per_kg']),
                    min_price=float(row['min_price_rs_per_kg']),
                    max_price=float(row['max_price_rs_per_kg']),
                    arrivals_tonnes=float(row['arrivals_tonnes']),
                    source='agri_dataset',
                    quality_score=95.0
                )
                batch.append(record)

                if len(batch) >= 1000:
                    db.add_all(batch)
                    await db.commit()
                    total += len(batch)
                    batch = []
                    print(f"  Imported {total:,} records so far...")

            except Exception as e:
                print(f"  Row error: {e}")
                continue

        # Save remaining records
        if batch:
            db.add_all(batch)
            await db.commit()
            total += len(batch)

        print(f"\n✅ Successfully imported {total:,} records!")

asyncio.run(main())