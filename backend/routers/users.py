# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 2.0.0
# ==============================================================================

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from memory.user_store import UserStore
from routers.auth import get_current_admin

router = APIRouter(prefix="/api/users", tags=["User Management"])

class CreateUserReq(BaseModel):
    username: str
    password: str
    role: Optional[str] = "Member"

class UpdatePasswordReq(BaseModel):
    new_password: str

@router.get("")
async def list_users():
    """Lists all registered company users and their roles."""
    return await UserStore.list_users()

@router.post("")
async def create_user(req: CreateUserReq):
    """Creates a new company user with specified role."""
    existing = await UserStore.get_user(req.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists.")
    return await UserStore.create_user(req.username, req.password, req.role)

@router.put("/{user_id}/password")
async def update_user_password(user_id: str, req: UpdatePasswordReq):
    """Updates the password of a user."""
    success = await UserStore.update_password(user_id, req.new_password)
    if not success:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"success": True, "message": "Password updated successfully."}

@router.delete("/{user_id}")
async def delete_user(user_id: str):
    """Deletes a company user account."""
    success = await UserStore.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot delete default admin user or user not found.")
    return {"success": True, "message": "User deleted successfully."}
