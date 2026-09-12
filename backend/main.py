# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 2.0.0
# ==============================================================================

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from memory.vector_store import VectorMemoryStore
from memory.chat_session_store import ChatSessionStore
from memory.user_store import UserStore
from routers import (
    chat_router,
    documents_router,
    memory_router,
    settings_router,
    auth_router,
    sessions_router,
    users_router,
    dashboard_router,
    models_mgmt_router
)
from models.schemas import SystemStatusResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("myagent.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle initialization for vector store and persistent databases."""
    logger.info(f"Starting {settings.AGENT_NAME} v2.0.0 on port {settings.WEB_PORT}...")
    
    # Warm up ChromaDB
    try:
        store = VectorMemoryStore()
        stats = store.get_stats()
        logger.info(f"Vector memory active. Total indexed chunks: {stats.get('total_chunks', 0)}")
    except Exception as e:
        logger.error(f"Vector store warmup error: {e}")

    # Warm up SQLite chat & user databases
    try:
        db = await ChatSessionStore.get_db()
        await db.close()
        u_db = await UserStore.get_db()
        await u_db.close()
        logger.info(f"Databases initialized at {settings.SESSION_DB_PATH}")
    except Exception as e:
        logger.error(f"SQLite DB initialization error: {e}")

    yield
    logger.info("Shutting down MyAgent services...")

app = FastAPI(
    title="MyAgent - Enterprise AI Agent Platform",
    description="Enterprise AI Agent with Vector Memory, Admin Suite, and Universal Branding",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for Web UI access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all enterprise routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(dashboard_router)
app.include_router(models_mgmt_router)
app.include_router(sessions_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(memory_router)
app.include_router(settings_router)

@app.get("/api/version")
async def get_version():
    """Returns official project version and branding information."""
    return {
        "version": "2.0.0",
        "company": "IT support BD",
        "company_url": "https://itsupport.com.bd",
        "author": "Arif",
        "author_url": "https://arifmahmud.com/",
        "web_port": settings.WEB_PORT,
        "copyright": "Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/)"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint for Docker container monitoring."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "service": "myagent-backend",
        "web_port": settings.WEB_PORT
    }

@app.get("/api/status", response_model=SystemStatusResponse)
async def system_status():
    """Returns high-level system status and memory statistics."""
    store = VectorMemoryStore()
    stats = store.get_stats()
    
    import os
    from pathlib import Path
    docs_dir = Path(settings.DOCUMENTS_DIR)
    doc_count = len(list(docs_dir.glob("*_*"))) if docs_dir.exists() else 0

    return SystemStatusResponse(
        status="running",
        agent_name=settings.AGENT_NAME,
        llm_base_url=settings.LLM_BASE_URL,
        llm_model=settings.LLM_MODEL,
        total_documents=doc_count,
        total_memory_chunks=stats.get("total_chunks", 0),
        chroma_connected=True
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.BACKEND_PORT, reload=True)
