# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.1.0
import os
import json
import uuid
import time
import aiosqlite
from typing import List, Dict, Any, Optional
from config import settings

class ChatSessionStore:
    """Manages persistent multi-session chat history using SQLite."""

    _instance = None

    @classmethod
    async def get_db(cls):
        """Returns connection to the SQLite database and ensures schema exists."""
        db = await aiosqlite.connect(settings.SESSION_DB_PATH)
        db.row_factory = aiosqlite.Row
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)
        await db.commit()
        return db

    @classmethod
    async def create_session(cls, title: str = "নতুন চ্যাট") -> Dict[str, Any]:
        """Creates a new persistent conversation session."""
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        db = await cls.get_db()
        try:
            await db.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, title, now, now)
            )
            await db.commit()
            return {"id": session_id, "title": title, "created_at": now, "updated_at": now}
        finally:
            await db.close()

    @classmethod
    async def list_sessions(cls) -> List[Dict[str, Any]]:
        """Lists all conversation sessions ordered by most recently updated."""
        db = await cls.get_db()
        try:
            cursor = await db.execute(
                "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            await db.close()

    @classmethod
    async def get_session_messages(cls, session_id: str) -> List[Dict[str, Any]]:
        """Returns all messages belonging to a conversation session."""
        db = await cls.get_db()
        try:
            cursor = await db.execute(
                "SELECT id, role, content, sources, created_at FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,)
            )
            rows = await cursor.fetchall()
            messages = []
            for r in rows:
                item = dict(r)
                if item.get("sources"):
                    try:
                        item["sources"] = json.loads(item["sources"])
                    except Exception:
                        item["sources"] = []
                else:
                    item["sources"] = []
                messages.append(item)
            return messages
        finally:
            await db.close()

    @classmethod
    async def add_message(cls, session_id: str, role: str, content: str, sources: Optional[List[Any]] = None):
        """Appends a user or assistant message to the session."""
        db = await cls.get_db()
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        sources_json = json.dumps(sources) if sources else None
        try:
            # Check if session exists; if not, create it
            cursor = await db.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
            exists = await cursor.fetchone()
            if not exists:
                # Generate title from first 30 chars of user prompt
                title = content[:35] + "..." if len(content) > 35 else content
                await db.execute(
                    "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (session_id, title, now, now)
                )

            await db.execute(
                "INSERT INTO messages (session_id, role, content, sources, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, sources_json, now)
            )
            await db.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id)
            )
            await db.commit()
        finally:
            await db.close()

    @classmethod
    async def rename_session(cls, session_id: str, new_title: str) -> bool:
        """Renames a conversation session title."""
        db = await cls.get_db()
        try:
            await db.execute(
                "UPDATE sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_title, session_id)
            )
            await db.commit()
            return True
        finally:
            await db.close()

    @classmethod
    async def delete_session(cls, session_id: str) -> bool:
        """Deletes a session and its associated messages."""
        db = await cls.get_db()
        try:
            await db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await db.commit()
            return True
        finally:
            await db.close()
