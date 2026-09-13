# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 2.2.0
# ==============================================================================

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from memory.vector_store import VectorMemoryStore
from memory.chat_session_store import ChatSessionStore
from memory.user_store import UserStore
from mcp.store import MCPStore
from security.audit import SecurityAuditStore
from routers import (
    chat_router,
    documents_router,
    memory_router,
    settings_router,
    auth_router,
    sessions_router,
    users_router,
    dashboard_router,
    models_mgmt_router,
    mcp_router,
    security_router,
    backup_router
)
from models.schemas import SystemStatusResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("myagent.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle initialization for vector store, persistent databases, and MCP registry."""
    logger.info(f"Starting {settings.AGENT_NAME} v2.2.0 on port {settings.WEB_PORT}...")

    # Warm up ChromaDB and FTS5
    try:
        store = VectorMemoryStore()
        stats = store.get_stats()
        logger.info(f"Hybrid vector memory active. Total indexed chunks: {stats.get('total_chunks', 0)}")
    except Exception as e:
        logger.error(f"Vector store warmup error: {e}")

    # Warm up SQLite chat, user, MCP, and security audit databases
    try:
        db = await ChatSessionStore.get_db()
        await db.close()
        u_db = await UserStore.get_db()
        await u_db.close()
        m_db = await MCPStore.get_db()
        await m_db.close()
        await SecurityAuditStore().init_db()
        logger.info(f"Persistent databases and security audit trail initialized at {settings.SESSION_DB_PATH}")
    except Exception as e:
        logger.error(f"SQLite DB initialization error: {e}")

    yield
    logger.info("Shutting down MyAgent services...")

app = FastAPI(
    title="MyAgent - Enterprise AI Agent Platform",
    description="Enterprise AI Agent with Data Security System, Hybrid Vector Memory, MCP Hub, and Universal Branding",
    version="2.2.0",
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
app.include_router(mcp_router)
app.include_router(security_router)
app.include_router(backup_router)
app.include_router(sessions_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(memory_router)
app.include_router(settings_router)

@app.get("/api/version")
async def get_version():
    """Returns official project version and branding information."""
    return {
        "version": "2.2.0",
        "company": "IT support BD",
        "company_url": "https://itsupport.com.bd",
        "author": "Arif",
        "author_url": "https://arifmahmud.com/",
        "web_port": settings.WEB_PORT,
        "copyright": "Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.2.0"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint for Docker container monitoring."""
    return {
        "status": "healthy",
        "version": "2.2.0",
        "service": "myagent-backend",
        "web_port": settings.WEB_PORT
    }

@app.get("/api/status", response_model=SystemStatusResponse)
async def system_status():
    """Returns high-level system status and memory statistics."""
    store = VectorMemoryStore()
    stats = store.get_stats()

    return SystemStatusResponse(
        status="online",
        agent_name=settings.AGENT_NAME,
        llm_model=settings.LLM_MODEL,
        llm_base_url=settings.LLM_BASE_URL,
        llm_endpoint=settings.LLM_BASE_URL,
        total_documents=stats.get("total_documents", 0),
        total_memory_chunks=stats.get("total_chunks", 0),
        total_indexed_chunks=stats.get("total_chunks", 0),
        chroma_connected=True,
        embedding_model=settings.EMBEDDING_MODEL
    )
