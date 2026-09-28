# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.0.0
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
                model_name TEXT DEFAULT 'solar-pro4:free',
                is_archived INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Safe migration for existing tables
        try:
            await db.execute("ALTER TABLE sessions ADD COLUMN model_name TEXT DEFAULT 'solar-pro4:free'")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE sessions ADD COLUMN is_archived INTEGER DEFAULT 0")
        except Exception:
            pass

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

    @classmethod
    async def purge_all_sessions(cls) -> Dict[str, Any]:
        """
        Nuclear Chat Session Purge:
        1. Deletes all chat messages and sessions.
        2. Executes VACUUM on SQLite database to defragment storage.
        3. Initializes a fresh initial conversation session.
        """
        db = await cls.get_db()
        try:
            cursor = await db.execute("SELECT COUNT(*) FROM messages")
            msg_count = (await cursor.fetchone())[0]
            cursor = await db.execute("SELECT COUNT(*) FROM sessions")
            sess_count = (await cursor.fetchone())[0]

            await db.execute("DELETE FROM messages")
            await db.execute("DELETE FROM sessions")
            await db.commit()
            await db.execute("VACUUM")
            await db.commit()

            # Create clean initial session
            new_session = await cls.create_session(title="নতুন চ্যাট")
            return {
                "success": True,
                "purged_sessions": sess_count,
                "purged_messages": msg_count,
                "new_session_id": new_session["id"]
            }
        finally:
            await db.close()

    @classmethod
    async def get_sessions_overview(cls) -> Dict[str, Any]:
        """Returns deep telemetry overview matching Hermes Sessions dashboard."""
        db = await cls.get_db()
        try:
            # 1. Total sessions
            c = await db.execute("SELECT COUNT(*) FROM sessions")
            total = (await c.fetchone())[0]

            # 2. Archived sessions
            c = await db.execute("SELECT COUNT(*) FROM sessions WHERE is_archived = 1")
            archived = (await c.fetchone())[0]
            active_in_store = total - archived

            # 3. Total messages
            c = await db.execute("SELECT COUNT(*) FROM messages")
            total_msgs = (await c.fetchone())[0]

            # 4. Recent sessions with message count and snippet
            query = """
                SELECT 
                    s.id, 
                    s.title, 
                    s.model_name, 
                    s.is_archived, 
                    s.created_at, 
                    s.updated_at,
                    COUNT(m.id) as msg_count,
                    (SELECT content FROM messages WHERE session_id = s.id ORDER BY id ASC LIMIT 1) as first_snippet,
                    (SELECT content FROM messages WHERE session_id = s.id ORDER BY id DESC LIMIT 1) as last_snippet
                FROM sessions s
                LEFT JOIN messages m ON s.id = m.session_id
                GROUP BY s.id
                ORDER BY s.updated_at DESC
                LIMIT 50
            """
            cursor = await db.execute(query)
            rows = await cursor.fetchall()

            sessions_list = []
            for r in rows:
                row_dict = dict(r)
                # Compute human readable relative time
                snippet = row_dict.get("last_snippet") or row_dict.get("first_snippet") or "নতুন চ্যাট সেশন..."
                if len(snippet) > 80:
                    snippet = snippet[:80] + "..."
                
                model = row_dict.get("model_name") or "solar-pro4:free"
                sessions_list.append({
                    "id": row_dict["id"],
                    "title": row_dict["title"],
                    "model": model,
                    "is_archived": bool(row_dict.get("is_archived", 0)),
                    "msg_count": row_dict.get("msg_count", 0),
                    "snippet": snippet,
                    "created_at": row_dict["created_at"],
                    "updated_at": row_dict["updated_at"],
                    "source": "api_server"
                })

            # Connected Platforms
            connected_platforms = [
                {
                    "name": "api_server",
                    "status": "Connected",
                    "last_update": "Active now",
                    "type": "core"
                },
                {
                    "name": "webchat_ui",
                    "status": "Connected",
                    "last_update": "Active now",
                    "type": "web"
                },
                {
                    "name": "cli_agent",
                    "status": "Connected",
                    "last_update": "1h ago",
                    "type": "cli"
                }
            ]

            return {
                "success": True,
                "total": total,
                "active_in_store": active_in_store,
                "archived": archived,
                "messages": total_msgs,
                "sources": len(connected_platforms),
                "connected_platforms": connected_platforms,
                "recent_sessions": sessions_list
            }
        finally:
            await db.close()

    @classmethod
    async def prune_old_sessions(cls, days: int = 30, empty_only: bool = False) -> Dict[str, Any]:
        """Prunes empty sessions or sessions older than specified days."""
        db = await cls.get_db()
        try:
            if empty_only:
                # Delete sessions with 0 messages
                c = await db.execute("""
                    DELETE FROM sessions 
                    WHERE id NOT IN (SELECT DISTINCT session_id FROM messages)
                """)
                deleted = c.rowcount
            else:
                # Delete sessions older than X days
                c = await db.execute("""
                    DELETE FROM sessions 
                    WHERE datetime(updated_at) < datetime('now', '-' || ? || ' days')
                """, (days,))
                deleted = c.rowcount

            await db.commit()
            return {"success": True, "pruned_count": deleted}
        finally:
            await db.close()

    @classmethod
    async def toggle_archive_session(cls, session_id: str, is_archived: bool) -> bool:
        """Toggles archive status for a session."""
        db = await cls.get_db()
        try:
            await db.execute(
                "UPDATE sessions SET is_archived = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (1 if is_archived else 0, session_id)
            )
            await db.commit()
            return True
        finally:
            await db.close()


