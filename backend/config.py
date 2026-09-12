import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Server Ports
    WEB_PORT: int = 3000
    BACKEND_PORT: int = 8000

    # Remote / Local LLM Server (OpenAI-compatible)
    LLM_BASE_URL: str = "http://192.168.9.10:11434/v1"
    LLM_API_KEY: str = "not-needed"
    LLM_MODEL: str = "llama3.3"

    # Agent Persona & Behavior
    AGENT_NAME: str = "Company Data Intelligence Agent"
    AGENT_TEMPERATURE: float = 0.3
    MAX_CONTEXT_TOKENS: int = 8192

    # Vector Memory & Ingestion (RAG)
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    CHUNKING_SIZE: int = 800
    CHUNKING_OVERLAP: int = 150
    TOP_K_RESULTS: int = 4

    # Storage Paths
    DATA_DIR: str = "/app/data"
    DOCUMENTS_DIR: str = "/app/data/documents"
    CHROMA_DIR: str = "/app/data/chroma_db"
    UPLOADS_DIR: str = "/app/data/uploads"

    class Config:
        env_file = ".env"
        extra = "allow"

    def setup_directories(self):
        """Ensures storage directories exist on the host or inside container."""
        base_path = Path(self.DATA_DIR)
        if not base_path.exists() and not str(base_path).startswith("/app"):
            # Local fallback for non-docker execution
            self.DATA_DIR = "./data"
            self.DOCUMENTS_DIR = "./data/documents"
            self.CHROMA_DIR = "./data/chroma_db"
            self.UPLOADS_DIR = "./data/uploads"

        os.makedirs(self.DOCUMENTS_DIR, exist_ok=True)
        os.makedirs(self.CHROMA_DIR, exist_ok=True)
        os.makedirs(self.UPLOADS_DIR, exist_ok=True)

settings = Settings()
settings.setup_directories()
