import os
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:agri_pass@localhost/agri_db'

import asyncio
import random
import numpy as np
from datetime import datetime, timedelta
from api.models.database import AsyncSessionLocal, RawPrice
from sqlalchemy import select, desc, delete

random.seed(42)
np.random.seed(42)

REALISTIC_PRICES = {
    'onion':  {'base': 28, 'min': 18, 'max': 42, 'volatility': 0.06},
    'potato': {'base': 18, 'min': 12, 'max': 26, 'volatility': 0.05},
    'tomato': {'base': 25, 'min': 15, 'max': 45, 'volatility': 0.12},
    'gram':   {'base': 58, 'min': 50, 'max': 68, 'volatility': 0.03},
    'tur':    {'base': 92, 'min': 82, 'max': 105, 'volatility': 0.04},
    'urad':   {'base': 88, 'min': 78, 'max': 100, 'volatility': 0.04},
    'moong':  {'base': 98, 'min': 85, 'max': 112, 'volatility': 0.04},
    'masur':  {'base': 68, 'min': 58, 'max': 80,  'volatility': 0.03},
}

MARKETS = {
    'onion':  [('Lasalgaon', 'Maharashtra'), ('Nashik', 'Maharashtra'),
               ('Delhi', 'Delhi'), ('Mumbai', 'Maharashtra'), ('Bangalore', 'Karnataka')],
    'potato': [('Agra', 'Uttar Pradesh'), ('Delhi', 'Delhi'),
               ('Kolkata', 'West Bengal'), ('Mumbai', 'Maharashtra'), ('Patna', 'Bihar')],
    'tomato': [('Kolar', 'Karnataka'), ('Nashik', 'Maharashtra'),
               ('Delhi', 'Delhi'), ('Mumbai', 'Maharashtra'), ('Chennai', 'Tamil Nadu')],
    'gram':   [('Indore', 'Madhya Pradesh'), ('Jaipur', 'Rajasthan'),
               ('Delhi', 'Delhi'), ('Mumbai', 'Maharashtra'), ('Nagpur', 'Maharashtra')],
    'tur':    [('Latur', 'Maharashtra'), ('Gulbarga', 'Karnataka'),
               ('Delhi', 'Delhi'), ('Mumbai', 'Maharashtra'), ('Nagpur', 'Maharashtra')],
    'urad':   [('Indore', 'Madhya Pradesh'), ('Akola', 'Maharashtra'),
               ('Delhi', 'Delhi'), ('Mumbai', 'Maharashtra'), ('Jaipur', 'Rajasthan')],
    'moong':  [('Jaipur', 'Rajasthan'), ('Jodhpur', 'Rajasthan'),
               ('Delhi', 'Delhi'), ('Mumbai', 'Maharashtra'), ('Indore', 'Madhya Pradesh')],
    'masur':  [('Indore', 'Madhya Pradesh'), ('Bhopal', 'Madhya Pradesh'),
               ('Delhi', 'Delhi'), ('Mumbai', 'Maharashtra'), ('Lucknow', 'Uttar Pradesh')],
}

async def get_last_price_date(db, commodity):
    result = await db.execute(
        select(RawPrice.date)
        .where(RawPrice.commodity == commodity)
        .order_by(desc(RawPrice.date))
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row

async def get_last_price(db, commodity):
    result = await db.execute(
        select(RawPrice.modal_price)
        .where(RawPrice.commodity == commodity)
        .order_by(desc(RawPrice.date))
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return float(row) if row else None

async def main():
    today = datetime(2026, 5, 1)  # Today = May 1, 2026
    print(f"Updating prices up to: {today.strftime('%d %b %Y')}")
    print("=" * 50)

    async with AsyncSessionLocal() as db:
        for commodity, config in REALISTIC_PRICES.items():
            # Get last recorded date
            last_date = await get_last_price_date(db, commodity)
            last_price = await get_last_price(db, commodity)

            if last_date is None:
                last_date = datetime(2026, 3, 31)
                last_price = config['base']

            # Calculate missing days
            start_fill = last_date + timedelta(days=1)
            if start_fill.date() > today.date():
                print(f"  {commodity:8s} → Already up to date! ({last_date.strftime('%d %b %Y')})")
                continue

            days_to_fill = (today - start_fill).days + 1
            print(f"  {commodity:8s} → Filling {days_to_fill} days from {start_fill.strftime('%d %b %Y')} to {today.strftime('%d %b %Y')}")

            records = []
            current_price = last_price

            for day_offset in range(days_to_fill):
                fill_date = start_fill + timedelta(days=day_offset)
                month = fill_date.month

                # Seasonal factor for May (summer heat, onion shortage)
                if commodity == 'onion':
                    season = 1.15 if month in [4, 5, 6] else 1.0
                elif commodity == 'tomato':
                    season = 1.25 if month in [4, 5, 6] else 1.0
                elif commodity == 'potato':
                    season = 1.10 if month in [5, 6, 7] else 1.0
                else:
                    season = 1.0 + 0.05 * np.sin(2 * np.pi * month / 12)

                # Daily price movement
                daily_change = random.gauss(0, config['volatility'])
                mean_reversion = (config['base'] * season - current_price) * 0.02
                current_price = current_price * (1 + daily_change) + mean_reversion
                current_price = max(config['min'], min(config['max'], current_price))

                markets = MARKETS[commodity]
                for market, state in markets:
                    market_factor = random.uniform(0.96, 1.04)
                    modal = round(current_price * market_factor, 2)
                    modal = max(config['min'], min(config['max'], modal))

                    records.append(RawPrice(
                        commodity=commodity,
                        date=fill_date,
                        market=market,
                        state=state,
                        modal_price=modal,
                        min_price=round(modal * 0.93, 2),
                        max_price=round(modal * 1.07, 2),
                        arrivals_tonnes=round(random.uniform(80, 500), 1),
                        source='daily_update',
                        quality_score=95.0
                    ))

            if records:
                db.add_all(records)
                await db.commit()
                print(f"           ✅ Added {len(records)} records. Latest price: ₹{current_price:.2f}/kg")

    print("\n" + "=" * 50)
    print("✅ All prices updated to May 1, 2026!")
    print("\nNow retrain models and refresh dashboard.")

asyncio.run(main())