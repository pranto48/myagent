# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 2.0.0
# ==============================================================================

import os
import time
import httpx
from pathlib import Path
from fastapi import APIRouter
from config import settings
from memory.vector_store import VectorMemoryStore
from memory.chat_session_store import ChatSessionStore
from memory.user_store import UserStore

router = APIRouter(prefix="/api/dashboard", tags=["Admin Dashboard"])

def get_directory_size(path_str: str) -> int:
    total = 0
    p = Path(path_str)
    if p.exists():
        for f in p.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    return total

@router.get("/stats")
async def get_dashboard_stats():
    """Returns comprehensive analytics for the Enterprise Admin Dashboard."""
    store = VectorMemoryStore()
    v_stats = store.get_stats()
    
    # Storage calculations
    docs_size = get_directory_size(settings.DOCUMENTS_DIR)
    chroma_size = get_directory_size(settings.CHROMA_DIR)
    db_size = os.path.getsize(settings.SESSION_DB_PATH) if os.path.exists(settings.SESSION_DB_PATH) else 0
    total_storage = docs_size + chroma_size + db_size

    # Document counts by type
    docs_dir = Path(settings.DOCUMENTS_DIR)
    type_counts = {"pdf": 0, "excel": 0, "word": 0, "image": 0, "text": 0}
    total_docs = 0

    if docs_dir.exists():
        for f in docs_dir.glob("*_*"):
            if f.is_file() and not f.name.startswith("."):
                total_docs += 1
                ext = f.suffix.lower()
                if ext == ".pdf":
                    type_counts["pdf"] += 1
                elif ext in [".xlsx", ".xls"]:
                    type_counts["excel"] += 1
                elif ext in [".docx", ".doc"]:
                    type_counts["word"] += 1
                elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
                    type_counts["image"] += 1
                else:
                    type_counts["text"] += 1

    # Database counts
    sessions = await ChatSessionStore.list_sessions()
    users = await UserStore.list_users()

    # Ping LLM Server
    ping_ms = 0
    llm_connected = False
    start_time = time.time()
    try:
        base_url = settings.LLM_BASE_URL.rstrip("/")
        if not base_url.endswith("/v1") and "/v1" not in base_url:
            test_url = f"{base_url}/v1/models"
        else:
            test_url = f"{base_url}/models"

        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(test_url)
            if res.status_code in [200, 401]:
                llm_connected = True
                ping_ms = round((time.time() - start_time) * 1000, 1)
    except Exception:
        llm_connected = False

    return {
        "version": "2.0.0",
        "web_port": settings.WEB_PORT,
        "kpi": {
            "total_documents": total_docs,
            "total_chunks": v_stats.get("total_chunks", 0),
            "total_sessions": len(sessions),
            "total_users": len(users),
            "total_storage_bytes": total_storage
        },
        "document_distribution": type_counts,
        "llm_status": {
            "url": settings.LLM_BASE_URL,
            "active_model": settings.LLM_MODEL,
            "connected": llm_connected,
            "latency_ms": ping_ms
        },
        "system": {
            "copyright": "Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/)",
            "embedding_model": settings.EMBEDDING_MODEL
        }
    }
