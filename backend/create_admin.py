import os
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:agri_pass@localhost/agri_db'

import asyncio
from api.models.database import AsyncSessionLocal, User, RoleEnum
from api.routes.auth import hash_password

async def main():
    async with AsyncSessionLocal() as db:
        user = User(
            username='admin',
            email='admin@gov.in',
            hashed_password=hash_password('Admin@123'),
            role=RoleEnum.ADMIN
        )
        db.add(user)
        await db.commit()
        print('Admin user created successfully!')

asyncio.run(main())