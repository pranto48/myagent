# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.0.0
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from memory.chat_session_store import ChatSessionStore
from routers.auth import get_current_admin

router = APIRouter(prefix="/api/sessions", tags=["Chat Sessions"])

class CreateSessionRequest(BaseModel):
    title: Optional[str] = "নতুন চ্যাট"

class RenameSessionRequest(BaseModel):
    title: str

@router.get("")
async def list_sessions():
    """Returns list of all stored conversation sessions."""
    return await ChatSessionStore.list_sessions()

@router.post("")
async def create_session(req: CreateSessionRequest):
    """Creates a new chat session."""
    return await ChatSessionStore.create_session(title=req.title or "নতুন চ্যাট")

@router.get("/{session_id}")
async def get_session(session_id: str):
    """Retrieves all chat messages for a specific session."""
    messages = await ChatSessionStore.get_session_messages(session_id)
    return {"session_id": session_id, "messages": messages}

@router.put("/{session_id}")
async def rename_session(session_id: str, req: RenameSessionRequest):
    """Renames an existing session."""
    success = await ChatSessionStore.rename_session(session_id, req.title)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "session_id": session_id, "title": req.title}

@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Deletes a session and its message history."""
    success = await ChatSessionStore.delete_session(session_id)
    return {"success": success, "message": "Session deleted successfully"}
