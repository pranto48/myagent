# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 2.0.0
# ==============================================================================

"""
Autonomous Agent Tools Definition for Reasoning over Company Data, Big Data, and Web.
"""

from typing import Dict, Any, List
import httpx
from memory.vector_store import VectorMemoryStore

class AgentTools:
    """Toolbox accessible by the Company AI Agent."""

    @staticmethod
    def query_company_memory(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Tool to retrieve semantic matches from company vector memory."""
        store = VectorMemoryStore()
        return store.search_memory(query=query, top_k=top_k)

    @staticmethod
    async def web_search(query: str) -> str:
        """Autonomous live web search tool using DuckDuckGo Instant Answers."""
        try:
            url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    abstract = data.get("AbstractText", "")
                    if abstract:
                        return f"[Web Search Result]: {abstract}"
                    related = [t.get("Text", "") for t in data.get("RelatedTopics", []) if "Text" in t]
                    if related:
                        return f"[Web Search Result]: {related[0]}"
            return f"No direct web answer found for '{query}'."
        except Exception as e:
            return f"Web search service error: {str(e)}"

    @staticmethod
    def calculate(expression: str) -> str:
        """Safely evaluates basic mathematical calculations for financial/numerical company reports."""
        import math
        allowed_names = {
            "sum": sum,
            "max": max,
            "min": min,
            "abs": abs,
            "round": round,
            "math": math
        }
        try:
            code = compile(expression, "<string>", "eval")
            for name in code.co_names:
                if name not in allowed_names:
                    raise NameError(f"Use of {name} not allowed in calculator")
            return str(eval(code, {"__builtins__": {}}, allowed_names))
        except Exception as e:
            return f"Calculation error: {str(e)}"
