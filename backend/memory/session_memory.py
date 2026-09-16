# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.0.0
import time
from typing import List, Dict, Any, Optional

class SessionMemoryManager:
    """In-memory cache for recent active conversations and conversation context."""

    _sessions: Dict[str, List[Dict[str, str]]] = {}
    _last_active: Dict[str, float] = {}

    @classmethod
    def get_history(cls, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Retrieves recent turns for the specified session."""
        history = cls._sessions.get(session_id, [])
        return history[-limit:]

    @classmethod
    def add_turn(cls, session_id: str, role: str, content: str):
        """Records a chat turn in session memory."""
        if session_id not in cls._sessions:
            cls._sessions[session_id] = []
        cls._sessions[session_id].append({"role": role, "content": content})
        cls._last_active[session_id] = time.time()

        # Clean old sessions if list grows too large (> 50 messages per session)
        if len(cls._sessions[session_id]) > 50:
            cls._sessions[session_id] = cls._sessions[session_id][-30:]

    @classmethod
    def clear_session(cls, session_id: str):
        """Resets the chat context for a session."""
        if session_id in cls._sessions:
            del cls._sessions[session_id]
        if session_id in cls._last_active:
            del cls._last_active[session_id]
