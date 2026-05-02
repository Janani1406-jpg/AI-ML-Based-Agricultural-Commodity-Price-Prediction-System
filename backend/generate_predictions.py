import os
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:agri_pass@localhost/agri_db'

import asyncio
from api.models.database import AsyncSessionLocal
from api.services.prediction_service import PredictionService

COMMODITIES = ['onion', 'potato', 'tomato', 'gram', 'tur', 'urad', 'moong', 'masur']
HORIZONS = [7, 15, 30, 90]

async def main():
    async with AsyncSessionLocal() as db:
        svc = PredictionService(db)
        for commodity in COMMODITIES:
            for horizon in HORIZONS:
                try:
                    pred = await svc.generate_prediction(commodity, horizon, 'baseline')
                    print(f"✅ {commodity:8s} {horizon:2d}d → ₹{pred['predicted_price']:.2f} (conf: {pred['confidence_score']:.0f}%)")
                except Exception as e:
                    print(f"❌ {commodity:8s} {horizon:2d}d → Error: {e}")

asyncio.run(main())