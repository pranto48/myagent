# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.1.0
from fastapi import APIRouter, HTTPException, Depends, Body, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from memory.chat_session_store import ChatSessionStore
from routers.auth import get_current_admin, get_current_user, get_optional_current_user

router = APIRouter(prefix="/api/sessions", tags=["Chat Sessions"])

class CreateSessionRequest(BaseModel):
    title: Optional[str] = "নতুন চ্যাট"
    model_name: Optional[str] = "gemini-3.7-flash"
    source: Optional[str] = "webchat"

class RenameSessionRequest(BaseModel):
    title: str

class PruneSessionsRequest(BaseModel):
    days: Optional[int] = 30
    empty_only: Optional[bool] = False

class ArchiveSessionRequest(BaseModel):
    is_archived: bool

@router.get("")
async def list_sessions(
    q: str = Query(""),
    include_archived: bool = Query(True),
    limit: int = Query(100, ge=1, le=300),
):
    """Returns list of stored conversation sessions with counts, snippets, and optional search filtering."""
    return await ChatSessionStore.list_sessions(q=q, include_archived=include_archived, limit=limit)

@router.get("/overview")
async def get_sessions_overview(user=Depends(get_current_user)):
    """Returns telemetry overview for Sessions view matching connected platforms and recent sessions."""
    return await ChatSessionStore.get_sessions_overview()

@router.get("/history/messages")
async def search_chat_message_history(
    q: str = Query(""),
    session_id: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(60, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(get_optional_current_user),
):
    """Searches full Chat AI conversation message history across all sessions."""
    data = await ChatSessionStore.search_messages(
        q=q,
        session_id=session_id,
        role=role,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return {"success": True, **data}

@router.post("")
async def create_session(req: CreateSessionRequest):
    """Creates a new chat session."""
    return await ChatSessionStore.create_session(
        title=req.title or "নতুন চ্যাট",
        model_name=req.model_name or "gemini-3.7-flash",
        source=req.source or "webchat",
    )

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
    """Retrieves all chat messages and metadata for a specific session."""
    sess = await ChatSessionStore.get_session_with_messages(session_id)
    if sess:
        return {"session_id": session_id, "session": sess, "messages": sess.get("messages", [])}
    messages = await ChatSessionStore.get_session_messages(session_id)
    return {"session_id": session_id, "session": None, "messages": messages}

@router.get("/{session_id}/export")
async def export_session(session_id: str, user=Depends(get_optional_current_user)):
    """Exports full metadata and conversation transcript for a session."""
    sess = await ChatSessionStore.get_session_with_messages(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "session": sess}

@router.delete("/{session_id}/messages/{message_id}")
async def delete_session_message(
    session_id: str,
    message_id: int,
    user=Depends(get_optional_current_user),
):
    """Deletes a single message from a chat session."""
    deleted = await ChatSessionStore.delete_message(session_id, message_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"success": True, "session_id": session_id, "deleted_message_id": message_id}

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

