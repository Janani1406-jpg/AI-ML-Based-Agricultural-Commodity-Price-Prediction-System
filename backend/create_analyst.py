import os
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:agri_pass@localhost/agri_db'

import asyncio
from api.models.database import AsyncSessionLocal, User, RoleEnum
from api.routes.auth import hash_password

async def main():
    async with AsyncSessionLocal() as db:
        # Create analyst user
        analyst = User(
            username='analyst1',
            email='analyst1@gov.in',
            hashed_password=hash_password('Analyst@123'),
            role=RoleEnum.ANALYST
        )
        db.add(analyst)

        # Create viewer user
        viewer = User(
            username='viewer1',
            email='viewer1@gov.in',
            hashed_password=hash_password('Viewer@123'),
            role=RoleEnum.VIEWER
        )
        db.add(viewer)

        await db.commit()
        print('Analyst and Viewer users created!')

asyncio.run(main())