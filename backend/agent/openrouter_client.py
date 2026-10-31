# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 3.2.0
# OpenRouter Frontier AI Model & Free Models Integration Engine
# ==============================================================================

import os
import time
import json
import logging
import httpx
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI, OpenAI
from config import settings

logger = logging.getLogger("myagent.openrouter")

# Complete catalog of OpenRouter 100% Free Models (zero token cost)
OPENROUTER_ALL_FREE_MODELS = [
    {
        "id": "openrouter/free",
        "name": "Free Models Auto-Router",
        "provider": "OpenRouter",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 200000,
        "pricing": "free",
        "description": "স্বয়ংক্রিয় রাউটার - প্রম্পট অনুযায়ী বর্তমানে সবচেয়ে ভালো ও দ্রুতগতির ফ্রি মডেলে রুট করে।"
    },
    {
        "id": "google/gemini-2.0-flash-exp:free",
        "name": "Gemini 2.0 Flash (Free)",
        "provider": "Google",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 1048576,
        "pricing": "free",
        "description": "গুগলের পরবর্তী প্রজন্মের ফ্ল্যাশ মডেল - ১০ লাখ কনটেক্সট উইন্ডো, সুপারফাস্ট স্পিড ও কোডিংয়ে দক্ষ।"
    },
    {
        "id": "google/gemini-2.0-pro-exp-02-05:free",
        "name": "Gemini 2.0 Pro Experimental (Free)",
        "provider": "Google",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 2097152,
        "pricing": "free",
        "description": "গুগলের সর্বাধিক শক্তিশালী রিজননিং ও জটিল প্রোগ্রামিং মডেল - ২০ লাখের বেশি কনটেক্সট সাইজ।"
    },
    {
        "id": "deepseek/deepseek-r1:free",
        "name": "DeepSeek R1 Reasoning (Free)",
        "provider": "DeepSeek",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 64000,
        "pricing": "free",
        "description": "ওপেন-ওয়েটসের শীর্ষ রিজননিং মাস্টার - চেইন-অব-থট ম্যাথ ও ডিপ কোডিং সলভিংয়ে OpenAI o1 সমকক্ষ।"
    },
    {
        "id": "deepseek/deepseek-chat:free",
        "name": "DeepSeek V3 Chat (Free)",
        "provider": "DeepSeek",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 64000,
        "pricing": "free",
        "description": "৬৭১ বিলিয়ন প্যারামিটার MoE আর্কিটেকচার - বাংলা ও ইংরেজিতে অত্যন্ত সাবলীল এবং দ্রুতগতির।"
    },
    {
        "id": "meta-llama/llama-3.3-70b-instruct:free",
        "name": "Llama 3.3 70B Instruct (Free)",
        "provider": "Meta",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 131072,
        "pricing": "free",
        "description": "মেটার ফ্ল্যাগশিপ ওপেন মডেল - ৪০৫ বিলিয়নের কোয়ালিটি দেয় ৭০ বিলিয়ন সাইজে, ১৩১কে কনটেক্সট।"
    },
    {
        "id": "qwen/qwen-2.5-coder-32b-instruct:free",
        "name": "Qwen 2.5 Coder 32B (Free)",
        "provider": "Alibaba",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 32768,
        "pricing": "free",
        "description": "আলি巴巴র কোডিং বিশেষজ্ঞ মডেল - এলগরিদম, ডিবাগিং, পাইথন স্ক্রিপ্টিং ও সফটওয়্যার ইঞ্জিনিয়ারিংয়ে সেরা।"
    },
    {
        "id": "mistralai/mistral-small-24b-instruct-2501:free",
        "name": "Mistral Small 24B Instruct (Free)",
        "provider": "Mistral",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 32768,
        "pricing": "free",
        "description": "ইউরোপীয় ফ্রন্টিয়ার AI ল্যাবের আধুনিক ২৪ বিলিয়ন মডেল - উচ্চ কার্যক্ষমতা ও নির্ভরযোগ্য ফলাফল।"
    },
    {
        "id": "google/gemma-4-31b-it:free",
        "name": "Google Gemma 4 31B (Free)",
        "provider": "Google",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 262144,
        "pricing": "free",
        "description": "গুগলের উন্নত ওপেন জেমা ৪ আর্কিটেকচার - ২৬২কে কনটেক্সট সহ নির্ভুল লজিক্যাল রেসপন্স।"
    },
    {
        "id": "google/gemma-4-26b-a4b-it:free",
        "name": "Google Gemma 4 26B A4B (Free)",
        "provider": "Google",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 262144,
        "pricing": "free",
        "description": "গুগল জেমা ৪ ফ্যামিলির অ্যাডাপটিভ মডেল - ফাইল ও ডাটা বিশ্লেষণের জন্য প্রস্তুত।"
    },
    {
        "id": "nvidia/nemotron-3.5-lightning:free",
        "name": "NVIDIA Nemotron 3.5 Lightning (Free)",
        "provider": "NVIDIA",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 1000000,
        "pricing": "free",
        "description": "এনভিডিয়ার আল্ট্রা-ফাস্ট লাইটনিং মডেল - ১০ লাখ কনটেক্সট উইন্ডো সহ দ্রুত এজেন্ট টাস্ক এক্সিকিউশন।"
    },
    {
        "id": "nvidia/nemotron-3.5-super-vl:free",
        "name": "NVIDIA Nemotron 3.5 Super VL (Free)",
        "provider": "NVIDIA",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 1000000,
        "pricing": "free",
        "description": "এনভিডিয়ার ভিশন-ল্যাঙ্গুয়েজ মাল্টিমোডাল মডেল - ছবি, চার্ট ও টেক্সট বিশ্লেষণে সক্ষম।"
    },
    {
        "id": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "name": "NVIDIA Nemotron 3 Ultra (Free)",
        "provider": "NVIDIA",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 1000000,
        "pricing": "free",
        "description": "এনভিডিয়ার বিশাল ৫৫০ বিলিয়ন MoE আর্কিটেকচার - এন্টারপ্রাইজ গ্রেড জটিল কার্যপ্রবাহ সমাধান।"
    },
    {
        "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "name": "NVIDIA Nemotron 3 Nano Omni (Free)",
        "provider": "NVIDIA",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 256000,
        "pricing": "free",
        "description": "এনভিডিয়া ন্যানো ওমনি রিজননিং মডেল - ধাপভিত্তিক যুক্তি ও সিদ্ধান্ত গ্রহণে কার্যকর।"
    },
    {
        "id": "cohere/north-mini-code:free",
        "name": "Cohere North Mini Code (Free)",
        "provider": "Cohere",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 256000,
        "pricing": "free",
        "description": "কোহিয়ারের কোড স্পেশালিস্ট এআই - ২৫৬কে কনটেক্সট সহ সিনট্যাক্স ও কোড পর্যালোচনায় দক্ষ।"
    },
    {
        "id": "liquid/lfm-2.5-2.6b:free",
        "name": "LiquidAI LFM 2.5 2.6B (Free)",
        "provider": "LiquidAI",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 65536,
        "pricing": "free",
        "description": "লিকুইড নিউরাল নেটওয়ার্ক চালিত অতি দ্রুতগতির লাইটওয়েট মডেল।"
    },
    {
        "id": "poolside/laguna-s-2.1:free",
        "name": "Poolside Laguna S 2.1 (Free)",
        "provider": "Poolside",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 262144,
        "pricing": "free",
        "description": "পুলসাইডের বিশেষায়িত প্রোগ্রামিং ও অ্যালগরিদম মডেল - ২৬২কে কনটেক্সট।"
    },
    {
        "id": "thinkingmachines/inkling-small:free",
        "name": "Thinking Machines Inkling Small (Free)",
        "provider": "Thinking Machines",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 1048576,
        "pricing": "free",
        "description": "১০ লাখ কনটেক্সট উইন্ডো সহ সম্পূর্ণ বিনামূল্যে ব্যবহারযোগ্য ওপেনরাউটার মডেল।"
    },
    {
        "id": "dots-studio/dots-3-note-preview:free",
        "name": "Dots Studio Dots 3 Note Preview (Free)",
        "provider": "Dots Studio",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 512000,
        "pricing": "free",
        "description": "ডকুমেন্ট ও নোট সামারাইজেশনে বিশেষ পারদর্শী - ৫১২কে কনটেক্সট উইন্ডো।"
    },
    {
        "id": "microsoft/phi-3-mini-128k-instruct:free",
        "name": "Microsoft Phi-3 Mini 128K (Free)",
        "provider": "Microsoft",
        "category": "Free",
        "badge": "100% Free",
        "context_length": 128000,
        "pricing": "free",
        "description": "মাইক্রোসফটের কম্প্যাক্ট ৩.৮ বিলিয়ন এসওটিএ মডেল - ১২৮কে কনটেক্সট ও দ্রুতগতির ফলাফল।"
    }
]

# Curated catalog of leading OpenRouter Paid / Frontier models
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

# In-memory cache for live free models
_free_models_cache: Dict[str, Any] = {
    "timestamp": 0,
    "models": []
}

class OpenRouterService:
    """Manages OpenRouter API connectivity, model discovery, key verification, and client provisioning."""

    @classmethod
    def get_api_key(cls) -> str:
        """Retrieves active OpenRouter API key from settings, environment, or persistent database."""
        key = getattr(settings, "OPENROUTER_API_KEY", "") or os.getenv("OPENROUTER_API_KEY", "")
        clean_key = str(key).strip().strip('"').strip("'")
        if clean_key.lower().startswith("bearer "):
            clean_key = clean_key[7:].strip()
        return clean_key

    @classmethod
    def is_configured(cls) -> bool:
        """Checks if a valid-looking OpenRouter key is configured."""
        key = cls.get_api_key()
        return bool(key and len(key) >= 15 and not key.startswith("your_"))

    @classmethod
    async def save_api_key(cls, api_key: str):
        """Persists the OpenRouter API key into settings, OS environment, SQLite ops.db, and .env files."""
        clean_key = str(api_key).strip().strip('"').strip("'")
        if clean_key.lower().startswith("bearer "):
            clean_key = clean_key[7:].strip()

        settings.OPENROUTER_API_KEY = clean_key
        os.environ["OPENROUTER_API_KEY"] = clean_key

        # 1. Persist to SQLite ops.db
        try:
            import aiosqlite
            db_path = os.path.join(settings.DATA_DIR, "ops.db") if os.path.exists(settings.DATA_DIR) else "./data/ops.db"
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            async with aiosqlite.connect(db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS ops_system_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TEXT
                    )
                """)
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                await db.execute("""
                    INSERT INTO ops_system_settings (key, value, updated_at)
                    VALUES ('openrouter_api_key', ?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """, (clean_key, now_str))
                await db.commit()
        except Exception as e:
            logger.warning(f"Failed to persist OpenRouter key in SQLite ops.db: {e}")

        # 2. Persist to .env files
        env_paths = [
            os.path.join(settings.DATA_DIR, "../.env"),
            "/home/it/myagent/.env",
            "/app/.env",
            ".env",
            "backend/.env"
        ]
        for ep in env_paths:
            try:
                if os.path.exists(ep):
                    with open(ep, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    found = False
                    new_lines = []
                    for l in lines:
                        if l.startswith("OPENROUTER_API_KEY="):
                            new_lines.append(f"OPENROUTER_API_KEY={clean_key}\n")
                            found = True
                        else:
                            new_lines.append(l)
                    if not found:
                        new_lines.append(f"OPENROUTER_API_KEY={clean_key}\n")
                    with open(ep, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)
            except Exception:
                pass

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
            default_headers=headers,
            http_client=http_client
        )

    @classmethod
    def get_sync_client(cls, custom_key: Optional[str] = None) -> OpenAI:
        """Creates a synchronous OpenAI client for connectivity checks."""
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
            default_headers=headers,
            http_client=http_client
        )

    @classmethod
    async def verify_key(cls, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Validates the OpenRouter key against /auth/key and inspects account credit balance."""
        raw_key = api_key if api_key is not None else cls.get_api_key()
        if not raw_key:
            return {
                "valid": False,
                "configured": False,
                "message": "কোনো OpenRouter API Key প্রদান করা হয়নি (No key provided)."
            }

        # Sanitize key
        key = str(raw_key).strip().strip('"').strip("'")
        if key.lower().startswith("bearer "):
            key = key[7:].strip()

        if len(key) < 15:
            return {
                "valid": False,
                "configured": False,
                "message": "OpenRouter API Key টি অসম্পূর্ণ বা ছোট (সাধারণত 'sk-or-v1-...' দিয়ে শুরু হয়)।"
            }

        headers = {
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": getattr(settings, "OPENROUTER_SITE_URL", "http://192.168.9.9:3399"),
            "X-Title": getattr(settings, "OPENROUTER_APP_NAME", "MyAgent Enterprise Intelligence")
        }

        try:
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                res = await client.get("https://openrouter.ai/api/v1/auth/key", headers=headers)
                if res.status_code == 200:
                    data = res.json().get("data", {})
                    limit = data.get("limit")
                    usage = data.get("usage", 0)
                    is_free = data.get("is_free_tier", False)
                    label = data.get("label", "Default Key")
                    rate_limit = data.get("rate_limit", {})
                    return {
                        "valid": True,
                        "configured": True,
                        "label": label,
                        "limit": limit,
                        "usage": usage,
                        "is_free_tier": is_free,
                        "rate_limit": rate_limit,
                        "message": "OpenRouter API key ভেরিফিকেশন সফল এবং সক্রিয়!"
                    }
                elif res.status_code == 401:
                    err_json = {}
                    try:
                        err_json = res.json().get("error", {})
                    except Exception:
                        pass
                    err_msg = err_json.get("message", "User not found or invalid API key.")
                    return {
                        "valid": False,
                        "configured": False,
                        "status_code": 401,
                        "message": f"ভেরিফিকেশন ব্যর্থ (৪০১ Unauthorized): {err_msg} - অনুগ্রহ করে ওপেনরাউটার থেকে নতুন কী সংগ্রহ করুন।"
                    }
                elif res.status_code == 403:
                    return {
                        "valid": False,
                        "configured": False,
                        "status_code": 403,
                        "message": "অ্যাক্সেস নিষিদ্ধ (৪০৩ Forbidden): অ্যাকাউন্টে ক্রেডিট বা পলিসি সংক্রান্ত সীমাবদ্ধতা রয়েছে।"
                    }
                else:
                    return {
                        "valid": False,
                        "configured": False,
                        "status_code": res.status_code,
                        "message": f"OpenRouter সার্ভার ত্রুটি (HTTP {res.status_code}): {res.text[:120]}"
                    }
        except Exception as e:
            return {
                "valid": False,
                "configured": False,
                "message": f"OpenRouter সার্ভারের সাথে সংযোগ ত্রুটি: {str(e)}"
            }

    @classmethod
    async def get_all_free_models(cls) -> List[Dict[str, Any]]:
        """Returns the full dynamic list of OpenRouter 100% Free models."""
        global _free_models_cache
        now = time.time()
        if _free_models_cache["models"] and (now - _free_models_cache["timestamp"] < 300):
            return _free_models_cache["models"]

        free_dict: Dict[str, Dict[str, Any]] = {m["id"]: dict(m) for m in OPENROUTER_ALL_FREE_MODELS}

        # Dynamically inspect OpenRouter live catalog
        try:
            headers = {
                "HTTP-Referer": getattr(settings, "OPENROUTER_SITE_URL", "http://192.168.9.9:3399"),
                "X-Title": getattr(settings, "OPENROUTER_APP_NAME", "MyAgent Enterprise Intelligence")
            }
            api_key = cls.get_api_key()
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                res = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
                if res.status_code == 200:
                    data = res.json().get("data", [])
                    for m in data:
                        mid = m.get("id", "")
                        pricing = m.get("pricing", {})
                        p_prompt = float(pricing.get("prompt", 0) or 0)
                        p_comp = float(pricing.get("completion", 0) or 0)
                        is_free = (":free" in mid) or (p_prompt == 0 and p_comp == 0)
                        if is_free:
                            if mid not in free_dict:
                                free_dict[mid] = {
                                    "id": mid,
                                    "name": m.get("name", mid),
                                    "provider": mid.split("/")[0].title() if "/" in mid else "OpenRouter",
                                    "category": "Free",
                                    "badge": "100% Free",
                                    "context_length": m.get("context_length", 32768),
                                    "pricing": "free",
                                    "description": m.get("description", "OpenRouter সম্পূর্ণ বিনামূল্যে ব্যবহারযোগ্য মডেল।")
                                }
        except Exception as e:
            logger.warning(f"Error fetching live free models from OpenRouter: {e}")

        all_free = list(free_dict.values())
        _free_models_cache = {
            "timestamp": now,
            "models": all_free
        }
        return all_free

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
