# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.2.0
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Content of the message")

class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Active conversation session ID for persistent storage")
    prompt: str = Field(..., description="User query or message")
    history: List[ChatMessage] = Field(default_factory=list, description="Recent conversation messages")
    use_memory: bool = Field(default=True, description="Whether to perform RAG vector memory retrieval")
    temperature: Optional[float] = Field(default=None, description="Sampling temperature override")
    model: Optional[str] = Field(default=None, description="Specific model override")

class SourceCitation(BaseModel):
    source: str
    chunk_id: str
    content: str
    score: float
    page: Optional[int] = None

class ChatResponse(BaseModel):
    reply: str
    sources: List[SourceCitation] = Field(default_factory=list)
    model_used: str

class MemorySearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 4

class MemorySearchResult(BaseModel):
    id: str
    content: str
    source: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AddMemoryNoteRequest(BaseModel):
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)

class SettingsUpdateRequest(BaseModel):
    llm_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    agent_temperature: Optional[float] = None
    top_k_results: Optional[int] = None

class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    size_bytes: int
    chunks_count: int
    created_at: str

class SystemStatusResponse(BaseModel):
    status: str
    agent_name: str
    llm_base_url: str
    llm_model: str
    total_documents: int
    total_memory_chunks: int
    chroma_connected: bool
