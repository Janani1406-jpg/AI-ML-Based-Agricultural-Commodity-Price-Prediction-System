import os
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:agri_pass@localhost/agri_db'

import asyncio
import random
from datetime import datetime, timedelta
from api.models.database import AsyncSessionLocal, RawPrice

async def main():
    async with AsyncSessionLocal() as db:
        commodities = ['onion', 'potato', 'tomato', 'gram', 'tur', 'urad', 'moong', 'masur']
        markets = ['Delhi', 'Mumbai', 'Chennai', 'Bangalore', 'Hyderabad']
        
        base_prices = {
            'onion': 25, 'potato': 15, 'tomato': 30, 'gram': 55,
            'tur': 70, 'urad': 65, 'moong': 75, 'masur': 50
        }
        
        records = []
        for commodity in commodities:
            base = base_prices[commodity]
            for days_ago in range(365, 0, -1):
                date = datetime.utcnow() - timedelta(days=days_ago)
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
        print(f'Added {len(records)} price records!')

asyncio.run(main())