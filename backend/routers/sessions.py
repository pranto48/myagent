# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.1.0
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from memory.chat_session_store import ChatSessionStore
from routers.auth import get_current_admin, get_current_user

router = APIRouter(prefix="/api/sessions", tags=["Chat Sessions"])

class CreateSessionRequest(BaseModel):
    title: Optional[str] = "নতুন চ্যাট"

class RenameSessionRequest(BaseModel):
    title: str

class PruneSessionsRequest(BaseModel):
    days: Optional[int] = 30
    empty_only: Optional[bool] = False

class ArchiveSessionRequest(BaseModel):
    is_archived: bool

@router.get("")
async def list_sessions():
    """Returns list of all stored conversation sessions."""
    return await ChatSessionStore.list_sessions()

@router.get("/overview")
async def get_sessions_overview(user=Depends(get_current_user)):
    """Returns telemetry overview for Sessions view matching connected platforms and recent sessions."""
    return await ChatSessionStore.get_sessions_overview()

@router.post("")
async def create_session(req: CreateSessionRequest):
    """Creates a new chat session."""
    return await ChatSessionStore.create_session(title=req.title or "নতুন চ্যাট")

@router.post("/prune")
async def prune_sessions(req: PruneSessionsRequest = Body(...), user=Depends(get_current_admin)):
    """Prunes empty or old inactive sessions."""
    return await ChatSessionStore.prune_old_sessions(days=req.days or 30, empty_only=req.empty_only or False)

@router.post("/import")
async def import_sessions(payload: Dict[str, Any] = Body(...), user=Depends(get_current_admin)):
    """Imports sessions from exported JSON file."""
    sessions_data = payload.get("sessions", [])
    imported = 0
    for s in sessions_data:
        title = s.get("title", "Imported Session")
        sess = await ChatSessionStore.create_session(title=title)
        messages = s.get("messages", [])
        for m in messages:
            await ChatSessionStore.add_message(
                session_id=sess["id"],
                role=m.get("role", "user"),
                content=m.get("content", ""),
                sources=m.get("sources")
            )
        imported += 1
    return {"success": True, "imported_count": imported}

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

@router.put("/{session_id}/archive")
async def archive_session(session_id: str, req: ArchiveSessionRequest, user=Depends(get_current_user)):
    """Archives or unarchives an existing session."""
    success = await ChatSessionStore.toggle_archive_session(session_id, req.is_archived)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "session_id": session_id, "is_archived": req.is_archived}

@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Deletes a session and its message history."""
    success = await ChatSessionStore.delete_session(session_id)
    return {"success": success, "message": "Session deleted successfully"}

