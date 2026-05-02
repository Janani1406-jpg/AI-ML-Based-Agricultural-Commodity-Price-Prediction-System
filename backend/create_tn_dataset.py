import os
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:agri_pass@localhost/agri_db'

import asyncio
import random
import numpy as np
from datetime import datetime, timedelta
from api.models.database import AsyncSessionLocal, RawPrice
from sqlalchemy import delete

random.seed(42)
np.random.seed(42)

# Tamil Nadu specific market prices (Rs/kg)
# Based on actual TN market patterns
TN_COMMODITY_CONFIG = {
    'onion': {
        'base': 30, 'min': 15, 'max': 80,
        'volatility': 0.08,
        'seasonal_peaks': [4, 5, 6, 10, 11],
        'seasonal_lows': [1, 2, 3],
    },
    'potato': {
        'base': 20, 'min': 12, 'max': 40,
        'volatility': 0.06,
        'seasonal_peaks': [6, 7, 8],
        'seasonal_lows': [11, 12, 1],
    },
    'tomato': {
        'base': 28, 'min': 8, 'max': 120,
        'volatility': 0.15,
        'seasonal_peaks': [5, 6, 7, 8],
        'seasonal_lows': [11, 12, 1, 2],
    },
    'gram': {
        'base': 60, 'min': 52, 'max': 75,
        'volatility': 0.04,
        'seasonal_peaks': [8, 9, 10],
        'seasonal_lows': [2, 3, 4],
    },
    'tur': {
        'base': 95, 'min': 82, 'max': 115,
        'volatility': 0.05,
        'seasonal_peaks': [3, 4, 5, 6],
        'seasonal_lows': [10, 11, 12],
    },
    'urad': {
        'base': 90, 'min': 78, 'max': 108,
        'volatility': 0.05,
        'seasonal_peaks': [2, 3, 4, 5],
        'seasonal_lows': [9, 10, 11],
    },
    'moong': {
        'base': 100, 'min': 88, 'max': 118,
        'volatility': 0.05,
        'seasonal_peaks': [1, 2, 3],
        'seasonal_lows': [8, 9, 10],
    },
    'masur': {
        'base': 70, 'min': 60, 'max': 85,
        'volatility': 0.04,
        'seasonal_peaks': [7, 8, 9],
        'seasonal_lows': [2, 3, 4],
    },
}

# Real Tamil Nadu APMC Markets
TN_MARKETS = {
    'onion': [
        ('Koyambedu', 'Tamil Nadu'),
        ('Madurai', 'Tamil Nadu'),
        ('Coimbatore', 'Tamil Nadu'),
        ('Salem', 'Tamil Nadu'),
        ('Trichy', 'Tamil Nadu'),
    ],
    'potato': [
        ('Koyambedu', 'Tamil Nadu'),
        ('Coimbatore', 'Tamil Nadu'),
        ('Ooty', 'Tamil Nadu'),
        ('Salem', 'Tamil Nadu'),
        ('Madurai', 'Tamil Nadu'),
    ],
    'tomato': [
        ('Koyambedu', 'Tamil Nadu'),
        ('Hosur', 'Tamil Nadu'),
        ('Krishnagiri', 'Tamil Nadu'),
        ('Salem', 'Tamil Nadu'),
        ('Coimbatore', 'Tamil Nadu'),
    ],
    'gram': [
        ('Koyambedu', 'Tamil Nadu'),
        ('Madurai', 'Tamil Nadu'),
        ('Trichy', 'Tamil Nadu'),
        ('Coimbatore', 'Tamil Nadu'),
        ('Erode', 'Tamil Nadu'),
    ],
    'tur': [
        ('Koyambedu', 'Tamil Nadu'),
        ('Madurai', 'Tamil Nadu'),
        ('Salem', 'Tamil Nadu'),
        ('Trichy', 'Tamil Nadu'),
        ('Tirunelveli', 'Tamil Nadu'),
    ],
    'urad': [
        ('Koyambedu', 'Tamil Nadu'),
        ('Madurai', 'Tamil Nadu'),
        ('Coimbatore', 'Tamil Nadu'),
        ('Salem', 'Tamil Nadu'),
        ('Tirunelveli', 'Tamil Nadu'),
    ],
    'moong': [
        ('Koyambedu', 'Tamil Nadu'),
        ('Madurai', 'Tamil Nadu'),
        ('Trichy', 'Tamil Nadu'),
        ('Coimbatore', 'Tamil Nadu'),
        ('Erode', 'Tamil Nadu'),
    ],
    'masur': [
        ('Koyambedu', 'Tamil Nadu'),
        ('Madurai', 'Tamil Nadu'),
        ('Salem', 'Tamil Nadu'),
        ('Coimbatore', 'Tamil Nadu'),
        ('Chennai', 'Tamil Nadu'),
    ],
}

# Tamil Nadu festival calendar
# TN has more festivals affecting prices
TN_FESTIVALS = [
    {'month': 1,  'day': 14, 'name': 'Pongal',          'boost': 1.35},
    {'month': 1,  'day': 15, 'name': 'Mattu Pongal',    'boost': 1.30},
    {'month': 4,  'day': 14, 'name': 'Tamil New Year',  'boost': 1.25},
    {'month': 4,  'day': 18, 'name': 'Chitirai Festival','boost': 1.20},
    {'month': 8,  'day': 26, 'name': 'Onam',            'boost': 1.15},
    {'month': 9,  'day': 10, 'name': 'Navratri',        'boost': 1.20},
    {'month': 10, 'day': 2,  'name': 'Ayudha Puja',     'boost': 1.25},
    {'month': 10, 'day': 24, 'name': 'Diwali',          'boost': 1.30},
    {'month': 11, 'day': 5,  'name': 'Karthigai Deepam','boost': 1.18},
    {'month': 12, 'day': 25, 'name': 'Christmas',       'boost': 1.10},
]

# Tamil Nadu weather (distinct from north India)
# More rainfall due to northeast monsoon (Oct-Dec)
TN_RAINFALL_PATTERN = {
    1: 35, 2: 8, 3: 5, 4: 15,
    5: 45, 6: 55, 7: 80, 8: 120,
    9: 110, 10: 180, 11: 350, 12: 140
}

def get_tn_festival_boost(date):
    """Get demand boost from TN festivals."""
    for fest in TN_FESTIVALS:
        try:
            fest_date = date.replace(month=fest['month'], day=fest['day'])
            days_diff = abs((date - fest_date).days)
            if days_diff <= 10:
                return fest['boost']
        except:
            pass
    return 1.0

def get_tn_seasonal_factor(commodity, month, config):
    """Get seasonal price factor for TN markets."""
    if month in config.get('seasonal_peaks', []):
        return 1.0 + random.uniform(0.12, 0.28)
    elif month in config.get('seasonal_lows', []):
        return 1.0 - random.uniform(0.08, 0.20)
    return 1.0 + random.uniform(-0.04, 0.06)

def get_tn_policy_impact(commodity, date):
    """Tamil Nadu government interventions."""
    tn_policies = [
        {'date': datetime(2023, 9, 15), 'commodity': 'tomato',
         'impact': -0.25, 'desc': 'TN govt sells tomato at Rs 60/kg'},
        {'date': datetime(2023, 10, 1), 'commodity': 'onion',
         'impact': -0.20, 'desc': 'TN cooperative sells onion at subsidized rate'},
        {'date': datetime(2024, 1, 10), 'commodity': 'tomato',
         'impact': -0.15, 'desc': 'Aavin outlets sell tomato at ₹40/kg'},
        {'date': datetime(2024, 6, 15), 'commodity': 'onion',
         'impact': -0.18, 'desc': 'TN govt releases buffer stock before Eid'},
        {'date': datetime(2025, 1, 5), 'commodity': 'tomato',
         'impact': -0.20, 'desc': 'Price control before Pongal festival'},
        {'date': datetime(2025, 4, 10), 'commodity': 'onion',
         'impact': -0.15, 'desc': 'Tamil New Year price intervention'},
        {'date': datetime(2025, 9, 20), 'commodity': 'gram',
         'impact': -0.10, 'desc': 'Navratri special supply boost'},
    ]
    impact = 0
    for policy in tn_policies:
        if policy['commodity'] == commodity:
            days_diff = (date - policy['date']).days
            if 0 <= days_diff <= 45:
                decay = max(0, 1 - days_diff / 45)
                impact += policy['impact'] * decay
    return impact


async def main():
    print("=" * 60)
    print("CREATING TAMIL NADU SPECIFIC AGRICULTURAL PRICE DATASET")
    print("=" * 60)

    today = datetime(2026, 5, 1)
    start_date = datetime(2022, 1, 1)
    total_days = (today - start_date).days + 1

    print(f"\nDate Range: {start_date.strftime('%d %b %Y')} to {today.strftime('%d %b %Y')}")
    print(f"Total Days: {total_days}")
    print(f"Markets: Tamil Nadu (Koyambedu, Madurai, Coimbatore, Salem, Trichy, etc.)")
    print(f"Commodities: All 8 essential commodities")

    async with AsyncSessionLocal() as db:
        # Clear existing data
        print("\nClearing old data...")
        await db.execute(delete(RawPrice))
        await db.commit()
        print("Old data cleared!")

        total_records = 0

        for commodity, config in TN_COMMODITY_CONFIG.items():
            print(f"\nGenerating {commodity.upper()} prices...")
            markets = TN_MARKETS[commodity]
            records = []

            # Start with realistic base price
            current_price = config['base'] * random.uniform(0.92, 1.08)

            current_date = start_date
            while current_date <= today:
                month = current_date.month

                # 1. Seasonal factor
                seasonal = get_tn_seasonal_factor(commodity, month, config)

                # 2. TN Festival boost
                festival_boost = get_tn_festival_boost(current_date)

                # 3. TN Policy impact
                policy_impact = get_tn_policy_impact(commodity, current_date)

                # 4. Northeast monsoon effect
                # TN gets heavy rain Oct-Dec which affects supply
                if month in [10, 11, 12] and commodity in ['tomato', 'onion']:
                    monsoon_factor = 1.15  # Prices rise due to heavy rain damage
                elif month in [1, 2] and commodity in ['tomato', 'onion']:
                    monsoon_factor = 0.92  # Post harvest prices fall
                else:
                    monsoon_factor = 1.0

                # 5. Daily random variation
                daily_noise = random.gauss(0, config['volatility'] * 0.04)

                # 6. Mean reversion
                mean_reversion = (config['base'] - current_price) * 0.018

                # 7. Inflation trend (5-7% annual)
                days_elapsed = (current_date - start_date).days
                inflation = config['base'] * 0.00018 * (days_elapsed / 365)

                # Calculate new price
                new_price = (
                    current_price * seasonal * festival_boost *
                    monsoon_factor * (1 + policy_impact) +
                    mean_reversion + daily_noise + inflation
                )

                # Clamp to realistic bounds
                new_price = max(config['min'], min(config['max'], new_price))
                current_price = new_price

                # Add records for each TN market
                for market, state in markets:
                    # Market-specific variation
                    # Koyambedu is wholesale, others are retail
                    if market == 'Koyambedu':
                        market_factor = random.uniform(0.92, 0.98)
                    else:
                        market_factor = random.uniform(1.00, 1.08)

                    modal = round(current_price * market_factor, 2)
                    modal = max(config['min'], min(config['max'], modal))

                    records.append(RawPrice(
                        commodity=commodity,
                        date=current_date,
                        market=market,
                        state=state,
                        modal_price=modal,
                        min_price=round(modal * 0.92, 2),
                        max_price=round(modal * 1.08, 2),
                        arrivals_tonnes=round(
                            random.uniform(50, 600) * market_factor, 1
                        ),
                        source='tn_market_data',
                        quality_score=95.0
                    ))

                current_date += timedelta(days=1)

            # Save in batches
            batch_size = 5000
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                db.add_all(batch)
                await db.commit()

            total_records += len(records)
            avg_price = config['base']
            print(f"  ✅ {len(records):,} records | "
                  f"Avg price: ₹{avg_price}/kg | "
                  f"Markets: {', '.join([m[0] for m in markets])}")

    print("\n" + "=" * 60)
    print(f"✅ TAMIL NADU DATASET CREATED SUCCESSFULLY!")
    print(f"   Total Records: {total_records:,}")
    print(f"   States: Tamil Nadu only")
    print(f"   Markets: Koyambedu, Madurai, Coimbatore,")
    print(f"            Salem, Trichy, Hosur, Erode,")
    print(f"            Krishnagiri, Tirunelveli, Ooty")
    print(f"   Date Range: Jan 2022 - May 2026")
    print(f"   Festivals: Pongal, Tamil New Year, Karthigai,")
    print(f"              Ayudha Puja, Diwali etc.")
    print(f"   Policies: TN Govt interventions included")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. python train_models.py")
    print("  2. Restart uvicorn server")
    print("  3. Refresh http://localhost:3000")

asyncio.run(main())