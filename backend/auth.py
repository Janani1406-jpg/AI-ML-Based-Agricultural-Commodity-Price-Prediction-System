"""
Authentication Routes + JWT Utilities
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import os

from api.models.database import get_db, User, RoleEnum

router = APIRouter()
security = HTTPBearer()

SECRET_KEY = os.getenv("JWT_SECRET", "agri-super-secret-key-2024-government-system!!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(data: dict, expires_delta: timedelta) -> str:
    payload = {**data, "exp": datetime.utcnow() + expires_delta}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(user: User) -> str:
    return create_token(
        {"sub": str(user.id), "username": user.username, "role": user.role},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def create_refresh_token(user: User) -> str:
    return create_token(
        {"sub": str(user.id), "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(401, "Invalid or expired token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")
    return user


# ── LOGIN ──────────────────────────────────────────────────────────────────────

@router.post("/login")
async def login(req: dict, db: AsyncSession = Depends(get_db)):
    username = req.get("username")
    password = req.get("password")

    if not username or not password:
        raise HTTPException(422, "Username and password required")

    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    if not user.is_active:
        raise HTTPException(403, "Account is deactivated")

    user.last_login = datetime.utcnow()
    await db.commit()

    return {
        "access_token": create_access_token(user),
        "refresh_token": create_refresh_token(user),
        "token_type": "bearer",
        "expires_in": 3600,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": str(user.role.value),
            "is_active": user.is_active,
            "created_at": str(user.created_at)
        }
    }


# ── REFRESH TOKEN ──────────────────────────────────────────────────────────────

@router.post("/refresh")
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        if payload.get("type") != "refresh":
            raise HTTPException(401, "Invalid refresh token")
        user_id = int(payload["sub"])
    except JWTError:
        raise HTTPException(401, "Invalid or expired refresh token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")

    return {
        "access_token": create_access_token(user),
        "token_type": "bearer"
    }


# ── CREATE USER ────────────────────────────────────────────────────────────────

@router.post("/users")
async def create_user(
    req: dict,
    db: AsyncSession = Depends(get_db)
):
    username = req.get("username", "").strip()
    email = req.get("email", "").strip()
    password = req.get("password", "")
    role = req.get("role", "viewer")

    # Validation
    if not username:
        raise HTTPException(400, "Username is required")
    if not email:
        raise HTTPException(400, "Email is required")
    if not password or len(password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    # Check valid role
    valid_roles = ["admin", "analyst", "viewer"]
    if role not in valid_roles:
        role = "viewer"

    # Check if username already exists
    existing = await db.execute(
        select(User).where(User.username == username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Username '{username}' already exists")

    # Check if email already exists
    existing_email = await db.execute(
        select(User).where(User.email == email)
    )
    if existing_email.scalar_one_or_none():
        raise HTTPException(400, f"Email '{email}' already registered")

    # Create user
    new_user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role=RoleEnum(role),
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {
        "id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "role": new_user.role.value,
        "is_active": new_user.is_active,
        "message": f"User '{username}' created successfully!"
    }


# ── LIST USERS ─────────────────────────────────────────────────────────────────

@router.get("/users-list")
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(User).order_by(User.id))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role.value,
            "is_active": u.is_active,
            "last_login": str(u.last_login) if u.last_login else None,
            "created_at": str(u.created_at),
        }
        for u in users
    ]


# ── TOGGLE USER STATUS ─────────────────────────────────────────────────────────

@router.put("/users/{user_id}/toggle")
async def toggle_user(
    user_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = payload.get("is_active", not user.is_active)
    await db.commit()
    return {"success": True, "is_active": user.is_active}