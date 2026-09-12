"""
Agent Tools Definition for Autonomous Reasoning over Company Data.
"""

from typing import Dict, Any, List
from memory.vector_store import VectorMemoryStore

class AgentTools:
    """Toolbox accessible by the Company AI Agent."""

    @staticmethod
    def query_company_memory(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Tool to retrieve semantic matches from company vector memory."""
        store = VectorMemoryStore()
        return store.search_memory(query=query, top_k=top_k)

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
            # Clean string for numbers and arithmetic operators
            code = compile(expression, "<string>", "eval")
            for name in code.co_names:
                if name not in allowed_names:
                    raise NameError(f"Use of {name} not allowed in calculator")
            return str(eval(code, {"__builtins__": {}}, allowed_names))
        except Exception as e:
            return f"Calculation error: {str(e)}"
