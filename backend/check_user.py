import os
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:agri_pass@localhost/agri_db'

import asyncio
from api.models.database import AsyncSessionLocal, User
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        for u in users:
            print(f"Username: {u.username}, Role: {u.role}, Active: {u.is_active}")

asyncio.run(main())