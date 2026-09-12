# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.0.0
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from memory.vector_store import VectorMemoryStore
from models.schemas import MemorySearchRequest, MemorySearchResult, AddMemoryNoteRequest

router = APIRouter(prefix="/api/memory", tags=["Vector Memory"])

@router.post("/search", response_model=List[MemorySearchResult])
async def search_memory(req: MemorySearchRequest):
    """
    Directly queries vector memory to inspect company knowledge base retrieval.
    """
    store = VectorMemoryStore()
    hits = store.search_memory(query=req.query, top_k=req.top_k)
    return [
        MemorySearchResult(
            id=h["id"],
            content=h["content"],
            source=h["source"],
            score=h["score"],
            metadata=h.get("metadata", {})
        )
        for h in hits
    ]

@router.post("/note")
async def add_memory_note(req: AddMemoryNoteRequest):
    """
    Adds a custom manual knowledge note or policy directly to memory.
    """
    store = VectorMemoryStore()
    note_id = store.add_note(title=req.title, content=req.content, tags=req.tags)
    return {
        "success": True,
        "note_id": note_id,
        "message": f"Saved corporate knowledge note '{req.title}' to persistent vector memory."
    }

@router.get("/stats")
async def get_memory_stats():
    """
    Returns memory statistics including chunk count and active embedding model.
    """
    store = VectorMemoryStore()
    return store.get_stats()
