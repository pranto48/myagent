# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.0.0
import time
import jwt
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
from config import settings
from security.rate_limiter import RateLimiter
from security.audit import SecurityAuditStore

router = APIRouter(prefix="/api/auth", tags=["Admin Authentication"])
audit_store = SecurityAuditStore()

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str = "admin"
    expires_in: int

def create_access_token(username: str, role: str = "admin") -> str:
    """Generates signed JWT token for session."""
    expire_seconds = settings.JWT_EXPIRATION_HOURS * 3600
    payload = {
        "sub": username,
        "role": role,
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

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Security dependency ensuring caller is authenticated."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format. Expected 'Bearer <token>'")
    token = parts[1]
    return verify_token(token)

def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Ensures caller has admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required.")
    return current_user

def get_optional_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Returns authenticated user if valid token present, otherwise default guest viewer."""
    if not authorization:
        return {"sub": "guest", "role": "viewer"}
    try:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return verify_token(parts[1])
    except Exception:
        pass
    return {"sub": "guest", "role": "viewer"}

@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest, request: Request):
    """
    Validates admin credentials with brute-force protection and security audit logging.
    Default Admin: admin / Aa987654
    """
    client_ip = request.client.host if request.client else "127.0.0.1"

    # 1. Rate limiter / brute force check
    allowed, retry_after = RateLimiter.check_rate_limit(f"ip:{client_ip}", max_limit=10, window_seconds=60)
    if not allowed:
        await audit_store.log_event(
            action="RATE_LIMIT_LOCKOUT",
            username=credentials.username,
            resource="login",
            severity="CRITICAL",
            ip_address=client_ip,
            details={"retry_after": retry_after}
        )
        raise HTTPException(status_code=429, detail=f"Too many attempts. Locked out for {retry_after} seconds.")

    # 2. Credential verification (default admin credentials)
    is_valid = (credentials.username == settings.ADMIN_USERNAME and credentials.password == settings.ADMIN_PASSWORD)
    
    if not is_valid:
        # Check if database user exists
        from memory.user_store import UserStore
        db_user = await UserStore.get_user_by_username(credentials.username)
        if db_user and UserStore.verify_password(credentials.password, db_user.get("password_hash", "")):
            is_valid = True
            user_role = db_user.get("role", "analyst")
        else:
            user_role = "unknown"

    if not is_valid:
        lockout = RateLimiter.record_auth_failure(client_ip)
        await audit_store.log_event(
            action="LOGIN_FAILED",
            username=credentials.username,
            user_role=user_role,
            resource="login",
            severity="WARNING" if not lockout else "CRITICAL",
            ip_address=client_ip,
            details={"lockout_triggered": lockout}
        )
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # Successful login
    role = "admin" if credentials.username == settings.ADMIN_USERNAME else user_role
    RateLimiter.reset(client_ip)
    
    await audit_store.log_event(
        action="LOGIN_SUCCESS",
        username=credentials.username,
        user_role=role,
        resource="login",
        severity="INFO",
        ip_address=client_ip
    )

    token = create_access_token(credentials.username, role=role)
    return LoginResponse(
        access_token=token,
        username=credentials.username,
        role=role,
        expires_in=settings.JWT_EXPIRATION_HOURS * 3600
    )

@router.get("/verify")
async def verify_auth(user: dict = Depends(get_current_user)):
    """
    Validates whether active session token is still valid.
    """
    return {
        "authenticated": True,
        "username": user.get("sub", "admin"),
        "role": user.get("role", "admin")
    }
