# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.2.0
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from memory.vector_store import VectorMemoryStore
from memory.chat_session_store import ChatSessionStore
from models.schemas import MemorySearchRequest, MemorySearchResult, AddMemoryNoteRequest

router = APIRouter(prefix="/api/memory", tags=["Vector Memory"])

class UpdateChunkRequest(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None

class PurgeMemoryRequest(BaseModel):
    purge_type: str = "nuclear"  # "nuclear", "vectors_only", "chat_only"
    auto_backup: bool = True
    confirmation_code: str

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

@router.post("/optimize")
async def optimize_vector_store():
    """
    Executes deep vector store optimization:
    1. Reclaims orphaned chunks and deduplicates indexes.
    2. Merges and optimizes SQLite FTS5 inverted search index.
    3. Performs SQLite VACUUM to reclaim disk pages and defragment database storage.
    4. Flushes LRU caches to free memory.
    """
    try:
        store = VectorMemoryStore()
        result = store.optimize_memory_store()
        return {
            "success": True,
            "message": "ভেক্টর ডাটাবেস ও FTS5 সার্চ ইনডেক্স সফলভাবে অপ্টিমাইজ ও ডিফ্র্যাগমেন্ট করা হয়েছে।",
            "optimization": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"মেমোরি অপ্টিমাইজেশন ব্যর্থ হয়েছে: {str(e)}")

@router.post("/purge")
async def purge_agent_memory(req: PurgeMemoryRequest):
    """
    Cognitive 200IQ Multi-Tier Agent Memory Purge & Reset:
    - Tier 1: 'nuclear' - Purges all vectors, documents, FTS5 index, and all chat sessions.
    - Tier 2: 'vectors_only' - Purges all vector memories, documents, and FTS5 index (preserves chat history).
    - Tier 3: 'chat_only' - Purges all chat sessions and conversation history (preserves vector knowledge base).
    Requires safety confirmation code 'DELETE' or 'মুছে ফেলুন'.
    """
    valid_codes = ["DELETE", "PURGE", "CONFIRM_DELETE", "মুছে ফেলুন"]
    if req.confirmation_code.strip().upper() not in [c.upper() for c in valid_codes]:
        raise HTTPException(
            status_code=400,
            detail="নিরাপত্তা নিশ্চিতকরণ কোডটি মেলেনি। মেমোরি মুছতে হলে সঠিকভাবে 'DELETE' টাইপ করুন।"
        )

    store = VectorMemoryStore()
    results: Dict[str, Any] = {
        "success": True,
        "purge_type": req.purge_type,
        "auto_backup": req.auto_backup
    }

    # 1. Vector Knowledge Base & Document Purge
    if req.purge_type in ["nuclear", "vectors_only"]:
        vec_res = store.purge_all_vector_memory(preserve_backup=req.auto_backup)
        results["vector_memory"] = vec_res

    # 2. Chat Sessions Purge
    if req.purge_type in ["nuclear", "chat_only"]:
        chat_res = await ChatSessionStore.purge_all_sessions()
        results["chat_sessions"] = chat_res

    # Message summary
    if req.purge_type == "nuclear":
        results["message"] = "এজেন্টের সমস্ত ভেক্টর নলেজবেস, ডকুমেন্টস এবং চ্যাট হিস্ট্রি সম্পূর্ণভাবে মুছে ক্লিন ফ্যাক্টরি রিসেট করা হয়েছে।"
    elif req.purge_type == "vectors_only":
        results["message"] = "এজেন্টের সমস্ত ভেক্টর নলেজবেস ও সংরক্ষিত ডকুমেন্টস সফলভাবে মুছে ফ্রেশ বেসলাইনে অপ্টিমাইজ করা হয়েছে।"
    else:
        results["message"] = "এজেন্টের সমস্ত কনভারসেশন ও চ্যাট ডায়ালগ সেশন সফলভাবে মুছে নতুন চ্যাট সেশন শুরু করা হয়েছে।"

    return results

@router.get("/health")
async def get_memory_health():
    """
    Returns real-time 200IQ cognitive memory health diagnostics, storage footprint, and performance metrics.
    """
    store = VectorMemoryStore()
    telemetry = store.get_memory_health_telemetry()
    
    try:
        db = await ChatSessionStore.get_db()
        try:
            cur = await db.execute("SELECT COUNT(*) FROM sessions")
            telemetry["total_chat_sessions"] = (await cur.fetchone())[0]
            cur = await db.execute("SELECT COUNT(*) FROM messages")
            telemetry["total_chat_messages"] = (await cur.fetchone())[0]
        finally:
            await db.close()
    except Exception:
        telemetry["total_chat_sessions"] = 0
        telemetry["total_chat_messages"] = 0

    return telemetry


