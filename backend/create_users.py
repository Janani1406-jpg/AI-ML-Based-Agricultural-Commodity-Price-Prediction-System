import os
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:agri_pass@localhost/agri_db'

import asyncio
from api.models.database import AsyncSessionLocal, User, RoleEnum
from api.routes.auth import hash_password
from sqlalchemy import select, delete

async def main():
    async with AsyncSessionLocal() as db:

        # Delete existing non-admin users to start fresh
        result = await db.execute(select(User))
        all_users = result.scalars().all()
        print("Existing users:")
        for u in all_users:
            print(f"  {u.username} - {u.role} - active:{u.is_active}")

        # Create all users
        users_to_create = [
            {"username": "admin",    "email": "admin@gov.in",    "password": "Admin@123",    "role": RoleEnum.ADMIN},
            {"username": "analyst1", "email": "analyst1@gov.in", "password": "Analyst@123",  "role": RoleEnum.ANALYST},
            {"username": "analyst2", "email": "analyst2@gov.in", "password": "Analyst@123",  "role": RoleEnum.ANALYST},
            {"username": "viewer1",  "email": "viewer1@gov.in",  "password": "Viewer@123",   "role": RoleEnum.VIEWER},
            {"username": "viewer2",  "email": "viewer2@gov.in",  "password": "Viewer@123",   "role": RoleEnum.VIEWER},
        ]

        for u_data in users_to_create:
            # Check if already exists
            existing = await db.execute(
                select(User).where(User.username == u_data["username"])
            )
            existing_user = existing.scalar_one_or_none()

            if existing_user:
                # Update password and make active
                existing_user.hashed_password = hash_password(u_data["password"])
                existing_user.is_active = True
                existing_user.role = u_data["role"]
                print(f"✅ Updated: {u_data['username']}")
            else:
                # Create new
                new_user = User(
                    username=u_data["username"],
                    email=u_data["email"],
                    hashed_password=hash_password(u_data["password"]),
                    role=u_data["role"],
                    is_active=True,
                )
                db.add(new_user)
                print(f"✅ Created: {u_data['username']}")

        await db.commit()
        print("\n✅ All users ready!")
        print("\nLogin credentials:")
        print("┌─────────────┬──────────────┬──────────┐")
        print("│ Username    │ Password     │ Role     │")
        print("├─────────────┼──────────────┼──────────┤")
        print("│ admin       │ Admin@123    │ Admin    │")
        print("│ analyst1    │ Analyst@123  │ Analyst  │")
        print("│ analyst2    │ Analyst@123  │ Analyst  │")
        print("│ viewer1     │ Viewer@123   │ Viewer   │")
        print("│ viewer2     │ Viewer@123   │ Viewer   │")
        print("└─────────────┴──────────────┴──────────┘")

asyncio.run(main())