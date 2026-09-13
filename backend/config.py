# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.2.0
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Server Ports
    WEB_PORT: int = 3399
    BACKEND_PORT: int = 8000

    # Admin Authentication Credentials
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "Aa987654"
    JWT_SECRET: str = "company-secret-jwt-token-key-3399-2026"
    JWT_EXPIRATION_HOURS: int = 72

    # Remote / Local LLM Server (OpenAI-compatible)
    LLM_BASE_URL: str = "http://192.168.20.10:1234/v1"
    LLM_API_KEY: str = "sk-lm-itvN1hr4:n8gt8iapM8Slt3NqjlHk"
    LLM_MODEL: str = "gemma-4-e2b-it-qat"

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
    SESSION_DB_PATH: str = "/app/data/chat_history.db"
    AUDIT_DB_PATH: str = "/app/data/security_audit.db"

    # Enterprise Data Security & Compliance Settings
    SECURITY_ENCRYPTION_KEY: str = "it-support-bd-secure-aes256-master-key-2026"
    DLP_ENABLED: bool = True
    DLP_MASK_CREDIT_CARDS: bool = True
    DLP_MASK_API_KEYS: bool = True
    DLP_MASK_EMAILS: bool = True
    DLP_MASK_PHONES: bool = True
    FIREWALL_ENABLED: bool = True
    AUDIT_LOG_ENABLED: bool = True
    RATE_LIMIT_ENABLED: bool = True

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
            self.SESSION_DB_PATH = "./data/chat_history.db"
            self.AUDIT_DB_PATH = "./data/security_audit.db"

        os.makedirs(self.DOCUMENTS_DIR, exist_ok=True)
        os.makedirs(self.CHROMA_DIR, exist_ok=True)
        os.makedirs(self.UPLOADS_DIR, exist_ok=True)

settings = Settings()

settings.setup_directories()
