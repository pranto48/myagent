# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 2.2.0
# ==============================================================================

import time
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from config import settings
from agent.core_agent import CompanyAIAgent

router = APIRouter(prefix="/api/models", tags=["AI Model Management"])

_agent_instance = None
def get_agent() -> CompanyAIAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = CompanyAIAgent()
    return _agent_instance

class SwitchModelReq(BaseModel):
    model: str
    temperature: Optional[float] = None

class TestConnectionReq(BaseModel):
    url: Optional[str] = None
    key: Optional[str] = None

@router.get("")
async def get_models_overview():
    """Lists current AI model configuration and available models from LLM server."""
    agent = get_agent()
    conn_res = await agent.test_llm_connection()
    return {
        "active_model": settings.LLM_MODEL,
        "base_url": settings.LLM_BASE_URL,
        "temperature": settings.AGENT_TEMPERATURE,
        "available_models": conn_res.get("models_available", []),
        "connected": conn_res.get("success", False)
    }

@router.post("/ping")
async def ping_llm_server(req: Optional[TestConnectionReq] = None):
    """Measures live round-trip latency to the external LLM server in milliseconds."""
    target_url = (req.url if req and req.url else settings.LLM_BASE_URL).rstrip("/")
    if not target_url.endswith("/v1") and "/v1" not in target_url:
        endpoint = f"{target_url}/v1/models"
    else:
        endpoint = f"{target_url}/models"

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            res = await client.get(endpoint)
            latency = round((time.time() - start) * 1000, 1)
            models = []
            if res.status_code == 200:
                try:
                    data = res.json()
                    models = [m["id"] for m in data.get("data", [])]
                except Exception:
                    pass
            return {
                "success": res.status_code in [200, 401],
                "latency_ms": latency,
                "status_code": res.status_code,
                "models_count": len(models),
                "models": models[:10]
            }
    except Exception as e:
        return {
            "success": False,
            "latency_ms": 0,
            "error": str(e)
        }

@router.post("/active")
async def switch_active_model(req: SwitchModelReq):
    """Switches the active LLM model and sampling temperature."""
    settings.LLM_MODEL = req.model
    if req.temperature is not None:
        settings.AGENT_TEMPERATURE = req.temperature
    get_agent().refresh_client()
    return {
        "success": True,
        "active_model": settings.LLM_MODEL,
        "temperature": settings.AGENT_TEMPERATURE
    }
