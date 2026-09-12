# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.2.0
from fastapi import APIRouter, HTTPException
from config import settings
from models.schemas import SettingsUpdateRequest
from agent.core_agent import CompanyAIAgent

router = APIRouter(prefix="/api/settings", tags=["Settings & Connectivity"])

_agent_instance = None

def get_agent() -> CompanyAIAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = CompanyAIAgent()
    return _agent_instance

@router.get("")
async def get_settings():
    """
    Returns the active configuration and LLM connection parameters.
    """
    return {
        "agent_name": settings.AGENT_NAME,
        "llm_base_url": settings.LLM_BASE_URL,
        "llm_model": settings.LLM_MODEL,
        "agent_temperature": settings.AGENT_TEMPERATURE,
        "embedding_model": settings.EMBEDDING_MODEL,
        "top_k_results": settings.TOP_K_RESULTS,
        "web_port": settings.WEB_PORT,
        "backend_port": settings.BACKEND_PORT
    }

@router.post("")
async def update_settings(req: SettingsUpdateRequest):
    """
    Dynamically updates LLM connection and agent parameters without restarting container.
    """
    agent = get_agent()
    
    if req.llm_base_url is not None:
        settings.LLM_BASE_URL = req.llm_base_url
    if req.llm_api_key is not None:
        settings.LLM_API_KEY = req.llm_api_key
    if req.llm_model is not None:
        settings.LLM_MODEL = req.llm_model
    if req.agent_temperature is not None:
        settings.AGENT_TEMPERATURE = req.agent_temperature
    if req.top_k_results is not None:
        settings.TOP_K_RESULTS = req.top_k_results

    # Refresh client connection
    agent.refresh_client()

    return {
        "success": True,
        "message": "Settings updated successfully.",
        "settings": {
            "llm_base_url": settings.LLM_BASE_URL,
            "llm_model": settings.LLM_MODEL,
            "agent_temperature": settings.AGENT_TEMPERATURE,
            "top_k_results": settings.TOP_K_RESULTS
        }
    }

@router.post("/test-connection")
async def test_llm_server_connection():
    """
    Tests connectivity to the remote LLM server and lists available models.
    """
    agent = get_agent()
    result = await agent.test_llm_connection()
    return result
