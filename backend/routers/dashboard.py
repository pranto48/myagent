# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 3.0.0
# ==============================================================================

import os
import time
import sqlite3
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, Depends
from config import settings
from memory.vector_store import VectorMemoryStore
from memory.chat_session_store import ChatSessionStore
from memory.user_store import UserStore
from routers.auth import get_optional_current_user

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
    """Returns comprehensive KPI analytics for the Enterprise Admin Dashboard."""
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
        for f in docs_dir.glob("*"):
            if f.is_file() and not f.name.startswith("."):
                total_docs += 1
                ext = f.suffix.lower()
                if ext == ".pdf":
                    type_counts["pdf"] += 1
                elif ext in [".xlsx", ".xls", ".csv"]:
                    type_counts["excel"] += 1
                elif ext in [".docx", ".doc"]:
                    type_counts["word"] += 1
                elif ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
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
        "version": "3.0.0",
        "web_port": settings.WEB_PORT,
        "kpi": {
            "total_documents": total_docs,
            "total_chunks": v_stats.get("total_chunks", 0),
            "total_sessions": len(sessions),
            "total_users": len(users),
            "total_storage_bytes": total_storage,
            "docs_size_bytes": docs_size,
            "chroma_size_bytes": chroma_size
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


@router.get("/analytics")
async def get_analytics_data(current_user: dict = Depends(get_optional_current_user)):
    """
    Returns time-series analytics data for Chart.js rendering:
    - 7-day chat activity
    - Memory growth trend (last 30 days approximation)
    - Document type distribution
    - Top document sources
    """
    store = VectorMemoryStore()
    v_stats = store.get_stats()

    # 7-day chat activity from session store
    sessions = await ChatSessionStore.list_sessions()
    daily_activity = {}
    for i in range(7):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_activity[day] = 0

    for sess in sessions:
        created = sess.get("created_at", "")
        if created:
            try:
                day_key = created[:10]
                if day_key in daily_activity:
                    daily_activity[day_key] += 1
            except Exception:
                pass

    # Sort by date ascending
    sorted_days = sorted(daily_activity.keys())
    chat_labels = [datetime.strptime(d, "%Y-%m-%d").strftime("%d %b") for d in sorted_days]
    chat_data = [daily_activity[d] for d in sorted_days]

    # Document distribution
    docs_dir = Path(settings.DOCUMENTS_DIR)
    type_counts = {"PDF": 0, "Excel/CSV": 0, "Word": 0, "Image": 0, "Text/Other": 0}
    recent_docs = []

    if docs_dir.exists():
        all_files = sorted(docs_dir.glob("*"), key=lambda f: f.stat().st_mtime if f.is_file() else 0, reverse=True)
        for f in all_files:
            if f.is_file() and not f.name.startswith("."):
                ext = f.suffix.lower()
                size_kb = round(f.stat().st_size / 1024, 1)
                if ext == ".pdf":
                    type_counts["PDF"] += 1
                elif ext in [".xlsx", ".xls", ".csv"]:
                    type_counts["Excel/CSV"] += 1
                elif ext in [".docx", ".doc"]:
                    type_counts["Word"] += 1
                elif ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                    type_counts["Image"] += 1
                else:
                    type_counts["Text/Other"] += 1

                if len(recent_docs) < 5:
                    recent_docs.append({
                        "name": f.name,
                        "size_kb": size_kb,
                        "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                    })

    # Memory growth simulation (chunks over time based on doc count)
    total_chunks = v_stats.get("total_chunks", 0)
    memory_labels = [f"Week {i+1}" for i in range(4)]
    # Approximate historical growth
    memory_data = [
        max(0, int(total_chunks * 0.25)),
        max(0, int(total_chunks * 0.5)),
        max(0, int(total_chunks * 0.75)),
        total_chunks
    ]

    return {
        "chat_activity": {
            "labels": chat_labels,
            "data": chat_data,
            "total_sessions": len(sessions)
        },
        "document_distribution": {
            "labels": list(type_counts.keys()),
            "data": list(type_counts.values()),
            "total": sum(type_counts.values())
        },
        "memory_growth": {
            "labels": memory_labels,
            "data": memory_data,
            "total_chunks": total_chunks
        },
        "recent_documents": recent_docs,
        "system_health": {
            "embedding_model": settings.EMBEDDING_MODEL,
            "llm_model": settings.LLM_MODEL,
            "agent_name": settings.AGENT_NAME
        }
    }


@router.get("/activity-log")
async def get_activity_log(limit: int = 50, current_user: dict = Depends(get_optional_current_user)):
    """
    Returns recent agent activity log from the security audit database.
    Shows: user queries, document uploads, memory saves, security events.
    """
    audit_db_path = os.path.join(settings.DATA_DIR, "audit.db")
    activities = []

    if os.path.exists(audit_db_path):
        try:
            conn = sqlite3.connect(audit_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, action, username, user_role, resource, severity, details
                FROM audit_log
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                details_str = row["details"] or "{}"
                try:
                    import json
                    details = json.loads(details_str)
                except Exception:
                    details = {}

                activities.append({
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "action": row["action"],
                    "username": row["username"],
                    "role": row["user_role"],
                    "resource": row["resource"],
                    "severity": row["severity"],
                    "details": details
                })
        except Exception as e:
            pass  # Return empty list if audit DB not ready

    # Also include recent sessions as activity
    if len(activities) < 10:
        sessions = await ChatSessionStore.list_sessions()
        for sess in sessions[:20]:
            activities.append({
                "id": sess.get("id", ""),
                "timestamp": sess.get("created_at", ""),
                "action": "CHAT_SESSION",
                "username": sess.get("user", "admin"),
                "role": "admin",
                "resource": "chat",
                "severity": "INFO",
                "details": {"session_id": sess.get("id", ""), "title": sess.get("title", "New Chat")}
            })

    # Sort by timestamp desc
    activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return {
        "activities": activities[:limit],
        "total": len(activities)
    }


@router.get("/top-documents")
async def get_top_documents(current_user: dict = Depends(get_optional_current_user)):
    """Returns most recently added and most relevant documents for the dashboard."""
    docs_dir = Path(settings.DOCUMENTS_DIR)
    uploads_dir = Path(settings.UPLOADS_DIR)

    docs = []
    seen_names = set()

    for search_dir in [docs_dir, uploads_dir]:
        if search_dir.exists():
            for f in sorted(search_dir.glob("*"), key=lambda x: x.stat().st_mtime if x.is_file() else 0, reverse=True):
                if f.is_file() and not f.name.startswith("."):
                    base_name = "_".join(f.name.split("_")[1:]) if "_" in f.name else f.name
                    if base_name in seen_names:
                        continue
                    seen_names.add(base_name)

                    ext = f.suffix.lower()
                    file_type = "document"
                    if ext == ".pdf":
                        file_type = "pdf"
                    elif ext in [".xlsx", ".xls", ".csv"]:
                        file_type = "excel"
                    elif ext in [".docx", ".doc"]:
                        file_type = "word"
                    elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
                        file_type = "image"
                    elif ext == ".txt":
                        file_type = "note"

                    docs.append({
                        "doc_id": f.stem.split("_")[0] if "_" in f.stem else f.stem,
                        "filename": base_name,
                        "file_type": file_type,
                        "size_bytes": f.stat().st_size,
                        "size_kb": round(f.stat().st_size / 1024, 1),
                        "modified_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                        "path": str(f)
                    })

                    if len(docs) >= 20:
                        break

    return {
        "documents": docs,
        "total": len(docs)
    }
