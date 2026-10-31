# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 3.2.0
# AI Model & Multi-Provider Management (Local/OxionAI & OpenRouter Frontier)
# ==============================================================================

import os
import time
import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from config import settings
from agent.core_agent import CompanyAIAgent, get_shared_agent
from agent.openrouter_client import OpenRouterService, FEATURED_OPENROUTER_MODELS
from routers.auth import get_optional_current_user

router = APIRouter(prefix="/api/models", tags=["AI Model Management"])

get_agent = get_shared_agent

class SwitchModelReq(BaseModel):
    model: str
    temperature: Optional[float] = None
    provider: Optional[str] = None

class TestConnectionReq(BaseModel):
    url: Optional[str] = None
    key: Optional[str] = None

class OpenRouterConfigPayload(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    set_as_active: bool = False

class OpenRouterTestPromptReq(BaseModel):
    model: Optional[str] = "deepseek/deepseek-r1"
    prompt: Optional[str] = "Say hello in Bengali and explain what OpenRouter model you are running on."

def _mask_key(k: str) -> str:
    if not k:
        return ""
    if len(k) <= 8:
        return "••••••••"
    return k[:6] + "••••••••" + k[-4:]

@router.get("")
async def get_models_overview():
    """Lists current AI model configuration, providers, and available models from LLM server."""
    agent = get_agent()
    conn_res = await agent.test_llm_connection()
    
    or_configured = OpenRouterService.is_configured()
    or_key = OpenRouterService.get_api_key()
    
    return {
        "active_model": settings.LLM_MODEL,
        "base_url": settings.LLM_BASE_URL,
        "temperature": settings.AGENT_TEMPERATURE,
        "available_models": conn_res.get("models_available", []),
        "connected": conn_res.get("success", False),
        # Multi-provider states
        "active_provider": getattr(settings, "LLM_PROVIDER", "default"),
        "openrouter": {
            "configured": or_configured,
            "key_masked": _mask_key(or_key),
            "active_model": getattr(settings, "OPENROUTER_MODEL", "deepseek/deepseek-r1"),
            "featured_models": FEATURED_OPENROUTER_MODELS
        }
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
    headers = {}
    api_key = (req.key if req and req.key else settings.LLM_API_KEY) or ""
    if api_key and api_key != "not-needed":
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        verify_ssl = getattr(settings, "LLM_VERIFY_SSL", False)
        async with httpx.AsyncClient(verify=verify_ssl, timeout=5.0) as client:
            res = await client.get(endpoint, headers=headers)
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
                "models": models[:15]
            }
    except Exception as e:
        return {
            "success": False,
            "latency_ms": 0,
            "error": str(e)
        }

@router.post("/active")
async def switch_active_model(req: SwitchModelReq):
    """Switches the active LLM model, sampling temperature, and optional provider."""
    settings.LLM_MODEL = req.model
    if req.temperature is not None:
        settings.AGENT_TEMPERATURE = req.temperature
    if req.provider is not None:
        settings.LLM_PROVIDER = req.provider
    elif "/" in req.model:
        settings.LLM_PROVIDER = "openrouter"
        settings.OPENROUTER_MODEL = req.model
        
    get_agent().refresh_client()
    return {
        "success": True,
        "active_model": settings.LLM_MODEL,
        "temperature": settings.AGENT_TEMPERATURE,
        "active_provider": getattr(settings, "LLM_PROVIDER", "default")
    }

# ==============================================================================
# OpenRouter Dedicated Management Endpoints
# ==============================================================================

@router.get("/openrouter/status")
async def get_openrouter_status(user=Depends(get_optional_current_user)):
    """Inspects OpenRouter connectivity, credit telemetry, and featured models."""
    key = OpenRouterService.get_api_key()
    verification = await OpenRouterService.verify_key(key)
    
    return {
        "success": True,
        "configured": OpenRouterService.is_configured(),
        "key_masked": _mask_key(key),
        "active_model": getattr(settings, "OPENROUTER_MODEL", "deepseek/deepseek-r1"),
        "is_active_provider": getattr(settings, "LLM_PROVIDER", "default") == "openrouter",
        "verification": verification,
        "featured_models": FEATURED_OPENROUTER_MODELS
    }

@router.post("/openrouter/config")
async def configure_openrouter(payload: OpenRouterConfigPayload, user=Depends(get_optional_current_user)):
    """Saves OpenRouter API Key, model selection, or switches active provider."""
    if payload.api_key is not None:
        clean_key = payload.api_key.strip()
        settings.OPENROUTER_API_KEY = clean_key
        # Update .env if present
        env_path = "/home/it/myagent/.env" if os.path.exists("/home/it/myagent/.env") else ".env"
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    env_lines = f.readlines()
                found = False
                new_lines = []
                for line in env_lines:
                    if line.startswith("OPENROUTER_API_KEY="):
                        new_lines.append(f"OPENROUTER_API_KEY={clean_key}\n")
                        found = True
                    else:
                        new_lines.append(line)
                if not found:
                    new_lines.append(f"OPENROUTER_API_KEY={clean_key}\n")
                with open(env_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
            except Exception as e:
                pass

    if payload.model:
        settings.OPENROUTER_MODEL = payload.model
        if payload.set_as_active or payload.provider == "openrouter":
            settings.LLM_MODEL = payload.model

    if payload.provider:
        settings.LLM_PROVIDER = payload.provider
    elif payload.set_as_active:
        settings.LLM_PROVIDER = "openrouter"

    get_agent().refresh_client()

    verification = await OpenRouterService.verify_key(settings.OPENROUTER_API_KEY)
    return {
        "success": True,
        "message": "OpenRouter configuration updated successfully.",
        "configured": OpenRouterService.is_configured(),
        "key_masked": _mask_key(settings.OPENROUTER_API_KEY),
        "active_model": settings.LLM_MODEL,
        "openrouter_model": getattr(settings, "OPENROUTER_MODEL", "deepseek/deepseek-r1"),
        "active_provider": getattr(settings, "LLM_PROVIDER", "default"),
        "verification": verification
    }

@router.get("/openrouter/catalog")
async def get_openrouter_catalog(user=Depends(get_optional_current_user)):
    """Fetches live catalog from OpenRouter API with fallbacks."""
    live_models = await OpenRouterService.fetch_live_catalog()
    if live_models:
        formatted = []
        for m in live_models[:50]:
            formatted.append({
                "id": m.get("id"),
                "name": m.get("name", m.get("id")),
                "context_length": m.get("context_length", 32000),
                "pricing": m.get("pricing", {}),
                "description": m.get("description", "")
            })
        return {"success": True, "source": "live", "count": len(formatted), "models": formatted}
    
    return {
        "success": True,
        "source": "featured_fallback",
        "count": len(FEATURED_OPENROUTER_MODELS),
        "models": FEATURED_OPENROUTER_MODELS
    }

@router.post("/openrouter/test")
async def test_openrouter_generation(req: OpenRouterTestPromptReq, user=Depends(get_optional_current_user)):
    """Executes a live test prompt against OpenRouter to verify generation and latency."""
    if not OpenRouterService.is_configured():
        raise HTTPException(status_code=400, detail="OpenRouter API key is not configured.")

    client = OpenRouterService.get_client()
    target_model = req.model or getattr(settings, "OPENROUTER_MODEL", "deepseek/deepseek-r1")

    start_time = time.time()
    try:
        response = await client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "system", "content": "You are a concise enterprise AI test responder. Answer accurately in 1-2 sentences."},
                {"role": "user", "content": req.prompt or "Hello, test."}
            ],
            temperature=0.3,
            max_tokens=256
        )
        elapsed_ms = round((time.time() - start_time) * 1000, 1)
        reply = response.choices[0].message.content if response.choices else ""
        return {
            "success": True,
            "model_tested": target_model,
            "latency_ms": elapsed_ms,
            "reply": reply,
            "usage": dict(response.usage) if hasattr(response, "usage") and response.usage else {}
        }
    except Exception as e:
        elapsed_ms = round((time.time() - start_time) * 1000, 1)
        return {
            "success": False,
            "model_tested": target_model,
            "latency_ms": elapsed_ms,
            "error": str(e)
        }
