import os
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:agri_pass@localhost/agri_db'

import asyncio
import random
from datetime import datetime, timedelta
from api.models.database import AsyncSessionLocal, RawPrice
from sqlalchemy import delete

async def main():
    async with AsyncSessionLocal() as db:
        await db.execute(delete(RawPrice))
        await db.commit()
        print('Old data deleted...')

        commodities = ['onion', 'potato', 'tomato', 'gram', 'tur', 'urad', 'moong', 'masur']
        markets = ['Delhi', 'Mumbai', 'Chennai', 'Bangalore', 'Hyderabad']
        base_prices = {
            'onion': 25, 'potato': 15, 'tomato': 30, 'gram': 55,
            'tur': 70, 'urad': 65, 'moong': 75, 'masur': 50
        }

        records = []
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        for commodity in commodities:
            base = base_prices[commodity]
            for days_ago in range(365, 0, -1):
                date = today - timedelta(days=days_ago)
                price = base + random.uniform(-5, 5) + (days_ago % 30) * 0.1
                record = RawPrice(
                    commodity=commodity,
                    date=date,
                    market=random.choice(markets),
                    state='Maharashtra',
                    modal_price=round(price, 2),
                    min_price=round(price - 2, 2),
                    max_price=round(price + 2, 2),
                    arrivals_tonnes=random.uniform(100, 500),
                    source='demo_data',
                    quality_score=90.0
                )
                records.append(record)

        db.add_all(records)
        await db.commit()
        print(f'Added {len(records)} records up to today {today.strftime("%d %b %Y")}!')

asyncio.run(main())