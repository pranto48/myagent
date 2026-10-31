# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.1.0
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

    # Remote / Local LLM Server (OxionAI, OpenAI-compatible, LM Studio)
    LLM_BASE_URL: str = "https://oxionai.com/v1"
    LLM_API_KEY: str = "cc_o6cFXoXcIp9XGvQlBUBqG3qp0QmgXgb7WZeR3hwFnV6R4I3R"
    LLM_MODEL: str = "gemini-3.7-flash"
    LLM_VERIFY_SSL: bool = False

    # OpenRouter Frontier Multi-Provider AI Settings
    LLM_PROVIDER: str = "default"  # "default" (OxionAI / local) or "openrouter"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "deepseek/deepseek-r1"
    OPENROUTER_SITE_URL: str = "http://192.168.9.9:3399"
    OPENROUTER_APP_NAME: str = "MyAgent Enterprise" 

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
    BACKUPS_DIR: str = "/app/data/backups"
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
            self.BACKUPS_DIR = "./data/backups"
            self.SESSION_DB_PATH = "./data/chat_history.db"
            self.AUDIT_DB_PATH = "./data/security_audit.db"

        os.makedirs(self.DOCUMENTS_DIR, exist_ok=True)
        os.makedirs(self.CHROMA_DIR, exist_ok=True)
        os.makedirs(self.UPLOADS_DIR, exist_ok=True)
        os.makedirs(self.BACKUPS_DIR, exist_ok=True)

settings = Settings()

settings.setup_directories()
