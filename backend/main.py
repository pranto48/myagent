import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from memory.vector_store import VectorMemoryStore
from routers import chat_router, documents_router, memory_router, settings_router
from models.schemas import SystemStatusResponse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("myagent.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for warming up the agent memory store."""
    logger.info(f"Starting {settings.AGENT_NAME}...")
    # Initialize ChromaDB and pre-load embedding model
    try:
        store = VectorMemoryStore()
        stats = store.get_stats()
        logger.info(f"Vector memory active. Total indexed chunks: {stats.get('total_chunks', 0)}")
    except Exception as e:
        logger.error(f"Vector store warmup error: {e}")
    yield
    logger.info("Shutting down MyAgent services...")

app = FastAPI(
    title="MyAgent - Company AI Agent Platform",
    description="Enterprise AI Agent with Persistent Vector Memory and External LLM Connectivity",
    version="1.0.0",
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

# Register routers
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(memory_router)
app.include_router(settings_router)

@app.get("/api/health")
async def health_check():
    """Health check endpoint for Docker container monitoring."""
    return {"status": "healthy", "service": "myagent-backend"}

@app.get("/api/status", response_model=SystemStatusResponse)
async def system_status():
    """Returns high-level system status and memory statistics."""
    store = VectorMemoryStore()
    stats = store.get_stats()
    
    # Calculate document counts
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
