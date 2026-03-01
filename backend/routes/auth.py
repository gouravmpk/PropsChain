"""
Authentication Routes
---------------------
POST /auth/register  — create account
POST /auth/login     — get JWT token
GET  /auth/me        — current user info
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt

from config.database import users_collection

router = APIRouter(prefix="/auth", tags=["Auth"])

# ── Config ────────────────────────────────────────────────────────────────────
SECRET_KEY = "propchain-secret-key-opsai-hackathon-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Pydantic models ───────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    phone: str
    aadhaar: str


class UserLogin(BaseModel):
    email: str
    password: str


# ── Helpers ───────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _safe_user(user: dict) -> dict:
    """Strip sensitive and MongoDB-specific fields."""
    return {k: v for k, v in user.items() if k not in ("password", "_id")}


async def get_current_user_from_token(authorization: Optional[str]) -> Optional[dict]:
    """Decode JWT and return user from DB. Returns None if token is missing/invalid."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            return None
        user = await users_collection.find_one({"email": email})
        return user
    except JWTError:
        return None


# ── Routes ────────────────────────────────────────────────────────────────────
@router.post(
    "/register",
    summary="Create a new PropChain account",
)
async def register(user: UserRegister):
    existing = await users_collection.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    doc = {
        "id": str(uuid.uuid4()),
        "name": user.name,
        "email": user.email,
        "password": hash_password(user.password),
        "phone": user.phone,
        "aadhaar": user.aadhaar,
        "created_at": datetime.utcnow().isoformat(),
        "kyc_verified": False,
        "wallet_balance": 1000000,
    }
    await users_collection.insert_one(doc)
    token = create_access_token({"sub": user.email})
    return {"token": token, "user": _safe_user(doc)}


@router.post(
    "/login",
    summary="Login and receive JWT access token",
)
async def login(creds: UserLogin):
    user = await users_collection.find_one({"email": creds.email})
    if not user or not verify_password(creds.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": creds.email})
    return {"token": token, "user": _safe_user(user)}


@router.get(
    "/me",
    summary="Get current authenticated user",
)
async def me(authorization: Optional[str] = Header(default=None)):
    user = await get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return _safe_user(user)
