import os
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:agri_pass@localhost/agri_db'

import asyncio
from api.models.database import AsyncSessionLocal
from api.services.recommendation_service import RecommendationEngine

async def main():
    async with AsyncSessionLocal() as db:
        engine = RecommendationEngine(db)
        recs = await engine.generate_recommendations()
        print(f"\n✅ Generated {len(recs)} recommendations!\n")
        for r in recs:
            commodity = r.commodity if isinstance(r.commodity, str) else r.commodity.value
            risk = r.risk_level if isinstance(r.risk_level, str) else r.risk_level.value
            print(f"  [{risk.upper():6s}] {commodity:8s} → {r.headline[:60]}")

asyncio.run(main())