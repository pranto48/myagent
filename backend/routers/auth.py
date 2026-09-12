# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.0.0
import time
import jwt
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
from config import settings

router = APIRouter(prefix="/api/auth", tags=["Admin Authentication"])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    expires_in: int

def create_access_token(username: str) -> str:
    """Generates signed JWT token for admin session."""
    expire_seconds = settings.JWT_EXPIRATION_HOURS * 3600
    payload = {
        "sub": username,
        "role": "admin",
        "iat": int(time.time()),
        "exp": int(time.time()) + expire_seconds
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def verify_token(token: str) -> dict:
    """Decodes and validates JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please log in again.")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authorization token.")

def get_current_admin(authorization: Optional[str] = Header(None)) -> dict:
    """Security dependency ensuring caller is authenticated."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format. Expected 'Bearer <token>'")
    token = parts[1]
    return verify_token(token)

@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Validates admin credentials and issues a JWT token.
    Default Admin: admin / Aa987654
    """
    if credentials.username != settings.ADMIN_USERNAME or credentials.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = create_access_token(credentials.username)
    return LoginResponse(
        access_token=token,
        username=credentials.username,
        expires_in=settings.JWT_EXPIRATION_HOURS * 3600
    )

@router.get("/verify")
async def verify_auth(admin: dict = Depends(get_current_admin)):
    """
    Validates whether active session token is still valid.
    """
    return {
        "authenticated": True,
        "username": admin.get("sub", "admin"),
        "role": admin.get("role", "admin")
    }
