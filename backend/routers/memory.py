# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.2.0
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from memory.vector_store import VectorMemoryStore
from models.schemas import MemorySearchRequest, MemorySearchResult, AddMemoryNoteRequest

router = APIRouter(prefix="/api/memory", tags=["Vector Memory"])

class UpdateChunkRequest(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None

@router.get("/chunks")
async def list_chunks(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    query: Optional[str] = None,
    source: Optional[str] = None
):
    """
    Returns stored memory chunks with pagination, search query, and source filter for Admin UI.
    Allows admins to inspect, search, and verify indexed knowledge.
    """
    store = VectorMemoryStore()
    return store.list_chunks(limit=limit, offset=offset, query=query, source_filter=source)

@router.get("/chunks/{chunk_id}")
async def get_chunk(chunk_id: str):
    """Fetches a specific memory chunk by its unique ID."""
    store = VectorMemoryStore()
    chunk = store.get_chunk(chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail="Memory chunk not found.")
    return chunk

@router.put("/chunks/{chunk_id}")
async def update_chunk(chunk_id: str, req: UpdateChunkRequest):
    """
    Enables admin to correct wrong saved data in vector memory.
    Updates the text content and automatically regenerates vector embeddings and FTS index.
    """
    if not req.content or not req.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty.")

    store = VectorMemoryStore()
    success = store.update_chunk(chunk_id=chunk_id, new_content=req.content.strip(), metadata=req.metadata)
    if not success:
        raise HTTPException(status_code=404, detail="Failed to update chunk. Item not found or update error.")

    return {
        "success": True,
        "message": f"সফলভাবে মেমোরি চাঙ্ক '{chunk_id}' আপডেট ও নতুন এমবেডিং সম্পন্ন হয়েছে।",
        "chunk": store.get_chunk(chunk_id)
    }

@router.delete("/chunks/{chunk_id}")
async def delete_chunk(chunk_id: str):
    """
    Enables admin to permanently delete an inaccurate or obsolete memory chunk.
    """
    store = VectorMemoryStore()
    success = store.delete_chunk(chunk_id)
    if not success:
        raise HTTPException(status_code=404, detail="Failed to delete chunk.")
    return {"success": True, "message": f"মেমোরি চাঙ্ক '{chunk_id}' সফলভাবে মুছে ফেলা হয়েছে।"}

@router.post("/search", response_model=List[MemorySearchResult])
async def search_memory(req: MemorySearchRequest):
    """
    Directly queries vector memory to inspect company knowledge base retrieval.
    """
    store = VectorMemoryStore()
    hits = store.super_fast_search(query=req.query, top_k=req.top_k)
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

@router.post("/notes")
@router.post("/note")
async def add_memory_note(req: AddMemoryNoteRequest):
    """
    Adds a custom manual knowledge note or verified company policy directly to memory.
    """
    title_str = str(req.title or "").strip()
    content_str = str(req.content or "").strip()
    if not title_str or not content_str:
        raise HTTPException(status_code=400, detail="শিরোনাম এবং বিবরণ উভয়ই প্রদান করা আবশ্যক।")

    if "????" in title_str or "????" in content_str or (content_str.count("?") > 5 and content_str.count("?") / max(len(content_str), 1) > 0.15):
        raise HTTPException(status_code=400, detail="নোটের শিরোনাম বা তথ্যে ত্রুটিপূর্ণ অক্ষরের প্রশ্নচিহ্ন ('????') সনাক্ত হয়েছে। অনুগ্রহ করে সঠিক UTF-8 টেক্সট প্রদান করুন।")

    store = VectorMemoryStore()
    try:
        note_id = store.add_note(title=title_str, content=content_str, tags=req.tags)
        return {
            "success": True,
            "note_id": note_id,
            "message": f"সফলভাবে কোম্পানি তথ্য নোট '{title_str}' মেমোরিতে সংরক্ষিত হয়েছে।"
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.get("/stats")
async def get_memory_stats():
    """
    Returns memory statistics including chunk count, cache status, and active embedding model.
    """
    store = VectorMemoryStore()
    return store.get_stats()
