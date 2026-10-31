# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 3.2.0
# OpenRouter Frontier AI Model Integration Engine
# ==============================================================================

import os
import json
import logging
import httpx
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI, OpenAI
from config import settings

logger = logging.getLogger("myagent.openrouter")

# Curated catalog of leading OpenRouter models
FEATURED_OPENROUTER_MODELS = [
    {
        "id": "deepseek/deepseek-r1",
        "name": "DeepSeek R1 (Reasoning Master)",
        "provider": "DeepSeek",
        "category": "Reasoning",
        "badge": "Top Reasoning",
        "context_length": 64000,
        "pricing": "ultra-low",
        "description": "State-of-the-art open-weights reasoning model with chain-of-thought problem solving rivaling o1."
    },
    {
        "id": "anthropic/claude-3.5-sonnet",
        "name": "Claude 3.5 Sonnet",
        "provider": "Anthropic",
        "category": "Frontier",
        "badge": "Most Powerful",
        "context_length": 200000,
        "pricing": "standard",
        "description": "Benchmark leader in coding, multi-step agent reasoning, tool use, and enterprise intelligence."
    },
    {
        "id": "openai/gpt-4o",
        "name": "GPT-4o Omnimodal",
        "provider": "OpenAI",
        "category": "Frontier",
        "badge": "Omni Flagship",
        "context_length": 128000,
        "pricing": "standard",
        "description": "OpenAI flagship high-intelligence model with comprehensive coding and tool-calling fidelity."
    },
    {
        "id": "openai/gpt-4o-mini",
        "name": "GPT-4o Mini",
        "provider": "OpenAI",
        "category": "Fast",
        "badge": "Fast & Efficient",
        "context_length": 128000,
        "pricing": "very-low",
        "description": "Sub-second latency, budget-friendly high accuracy model ideal for fast subagent operations."
    },
    {
        "id": "google/gemini-2.0-flash-exp:free",
        "name": "Gemini 2.0 Flash (Free)",
        "provider": "Google",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 1048576,
        "pricing": "free",
        "description": "Next-gen multimodal Gemini 2.0 Flash model available at zero cost on OpenRouter."
    },
    {
        "id": "google/gemini-flash-1.5",
        "name": "Gemini 1.5 Flash",
        "provider": "Google",
        "category": "Fast",
        "badge": "1M Context",
        "context_length": 1000000,
        "pricing": "very-low",
        "description": "Massive 1M token context window with high throughput and instant responsiveness."
    },
    {
        "id": "meta-llama/llama-3.3-70b-instruct",
        "name": "Llama 3.3 70B Instruct",
        "provider": "Meta",
        "category": "Open Weights",
        "badge": "Open SOTA",
        "context_length": 131072,
        "pricing": "low",
        "description": "Meta's flagship open-weights instruction model delivering 405B-class capability in 70B efficiency."
    },
    {
        "id": "deepseek/deepseek-chat",
        "name": "DeepSeek V3 (Chat)",
        "provider": "DeepSeek",
        "category": "General",
        "badge": "Popular",
        "context_length": 64000,
        "pricing": "ultra-low",
        "description": "Ultra fast, cost-effective 671B MoE architecture with exceptional Bengali and English proficiency."
    },
    {
        "id": "mistralai/mistral-large-2407",
        "name": "Mistral Large 2",
        "provider": "Mistral",
        "category": "Frontier",
        "badge": "Enterprise",
        "context_length": 128000,
        "pricing": "standard",
        "description": "European flagship LLM with strong multilingual, mathematical, and coding capabilities."
    },
    {
        "id": "qwen/qwen-2.5-72b-instruct",
        "name": "Qwen 2.5 72B Instruct",
        "provider": "Alibaba",
        "category": "Coding & Math",
        "badge": "Top Coding",
        "context_length": 131072,
        "pricing": "low",
        "description": "SOTA code generation, mathematical reasoning, and complex tool dispatching capabilities."
    }
]

class OpenRouterService:
    """Manages OpenRouter API connectivity, model discovery, and client provisioning."""

    @classmethod
    def get_api_key(cls) -> str:
        key = getattr(settings, "OPENROUTER_API_KEY", "") or os.getenv("OPENROUTER_API_KEY", "")
        return key.strip()

    @classmethod
    def is_configured(cls) -> bool:
        key = cls.get_api_key()
        return bool(key and len(key) > 10 and not key.startswith("your_"))

    @classmethod
    def get_client(cls, custom_key: Optional[str] = None) -> AsyncOpenAI:
        """Creates an AsyncOpenAI client targeting OpenRouter with requisite discovery headers."""
        api_key = custom_key or cls.get_api_key()
        if not api_key:
            api_key = "not-configured"

        headers = {
            "HTTP-Referer": getattr(settings, "OPENROUTER_SITE_URL", "http://192.168.9.9:3399"),
            "X-Title": getattr(settings, "OPENROUTER_APP_NAME", "MyAgent Enterprise Intelligence")
        }

        http_client = httpx.AsyncClient(
            verify=False,
            timeout=httpx.Timeout(90.0, connect=10.0),
            headers=headers
        )

        return AsyncOpenAI(
            base_url=getattr(settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=api_key,
            http_client=http_client
        )

    @classmethod
    def get_sync_client(cls, custom_key: Optional[str] = None) -> OpenAI:
        """Creates a synchronous OpenAI client for ping / connectivity checks."""
        api_key = custom_key or cls.get_api_key()
        if not api_key:
            api_key = "not-configured"

        headers = {
            "HTTP-Referer": getattr(settings, "OPENROUTER_SITE_URL", "http://192.168.9.9:3399"),
            "X-Title": getattr(settings, "OPENROUTER_APP_NAME", "MyAgent Enterprise Intelligence")
        }

        http_client = httpx.Client(
            verify=False,
            timeout=httpx.Timeout(15.0, connect=5.0),
            headers=headers
        )

        return OpenAI(
            base_url=getattr(settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=api_key,
            http_client=http_client
        )

    @classmethod
    async def verify_key(cls, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Validates the OpenRouter key and inspects account credit balance."""
        key = api_key or cls.get_api_key()
        if not key:
            return {
                "valid": False,
                "message": "No OpenRouter API key provided.",
                "configured": False
            }

        headers = {
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": getattr(settings, "OPENROUTER_SITE_URL", "http://192.168.9.9:3399"),
            "X-Title": getattr(settings, "OPENROUTER_APP_NAME", "MyAgent Enterprise Intelligence")
        }

        try:
            async with httpx.AsyncClient(verify=False, timeout=8.0) as client:
                res = await client.get("https://openrouter.ai/api/v1/auth/key", headers=headers)
                if res.status_code == 200:
                    data = res.json().get("data", {})
                    limit = data.get("limit")
                    usage = data.get("usage", 0)
                    is_free = data.get("is_free_tier", False)
                    return {
                        "valid": True,
                        "configured": True,
                        "label": data.get("label", "Default Key"),
                        "limit": limit,
                        "usage": usage,
                        "is_free_tier": is_free,
                        "rate_limit": data.get("rate_limit", {}),
                        "message": "OpenRouter API key is active and verified."
                    }
                else:
                    return {
                        "valid": False,
                        "configured": False,
                        "status_code": res.status_code,
                        "message": f"OpenRouter verification returned HTTP {res.status_code}: {res.text[:120]}"
                    }
        except Exception as e:
            return {
                "valid": False,
                "configured": False,
                "message": f"Connection error verifying OpenRouter key: {str(e)}"
            }

    @classmethod
    async def fetch_live_catalog(cls) -> List[Dict[str, Any]]:
        """Queries OpenRouter /models endpoint for dynamic live catalog."""
        headers = {
            "HTTP-Referer": getattr(settings, "OPENROUTER_SITE_URL", "http://192.168.9.9:3399"),
            "X-Title": getattr(settings, "OPENROUTER_APP_NAME", "MyAgent Enterprise Intelligence")
        }
        api_key = cls.get_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                res = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
                if res.status_code == 200:
                    data = res.json().get("data", [])
                    return data
        except Exception as e:
            logger.warning(f"Failed to fetch live OpenRouter catalog: {e}")
        return []
