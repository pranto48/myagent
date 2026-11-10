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
        try:
            await db.execute("ALTER TABLE sessions ADD COLUMN source TEXT DEFAULT 'webchat'")
        except Exception:
            pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                model_name TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)
        try:
            await db.execute("ALTER TABLE messages ADD COLUMN model_name TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id, id)")
        except Exception:
            pass
        await db.commit()
        return db

    @classmethod
    async def create_session(
        cls,
        title: str = "নতুন চ্যাট",
        model_name: str = "gemini-3.7-flash",
        source: str = "webchat",
    ) -> Dict[str, Any]:
        """Creates a new persistent conversation session."""
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        db = await cls.get_db()
        try:
            await db.execute(
                "INSERT INTO sessions (id, title, model_name, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, title, model_name, source, now, now)
            )
            await db.commit()
            return {
                "id": session_id,
                "title": title,
                "model_name": model_name,
                "source": source,
                "is_archived": 0,
                "msg_count": 0,
                "created_at": now,
                "updated_at": now,
            }
        finally:
            await db.close()

    @classmethod
    async def list_sessions(
        cls,
        q: str = "",
        include_archived: bool = True,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Lists conversation sessions with message counts, snippet, and optional search filtering."""
        db = await cls.get_db()
        try:
            clauses = ["1=1"]
            params: List[Any] = []
            if not include_archived:
                clauses.append("COALESCE(s.is_archived, 0) = 0")
            clean_q = (q or "").strip()
            if clean_q:
                like_q = f"%{clean_q}%"
                clauses.append(
                    "(s.title LIKE ? OR s.id LIKE ? OR EXISTS ("
                    "SELECT 1 FROM messages m2 WHERE m2.session_id = s.id AND m2.content LIKE ?))"
                )
                params.extend([like_q, like_q, like_q])
            params.append(max(1, min(int(limit or 100), 300)))

            sql = f"""
                SELECT
                    s.id,
                    s.title,
                    COALESCE(s.model_name, 'gemini-3.7-flash') AS model_name,
                    COALESCE(s.is_archived, 0) AS is_archived,
                    COALESCE(s.source, CASE WHEN s.id LIKE 'session_daily%' THEN 'automation' ELSE 'webchat' END) AS source,
                    s.created_at,
                    s.updated_at,
                    COUNT(m.id) AS msg_count,
                    (SELECT content FROM messages WHERE session_id = s.id ORDER BY id DESC LIMIT 1) AS last_snippet
                FROM sessions s
                LEFT JOIN messages m ON s.id = m.session_id
                WHERE {' AND '.join(clauses)}
                GROUP BY s.id
                ORDER BY s.updated_at DESC
                LIMIT ?
            """
            cursor = await db.execute(sql, tuple(params))
            rows = await cursor.fetchall()
            out = []
            for row in rows:
                d = dict(row)
                snip = (d.get("last_snippet") or "").strip()
                d["last_snippet"] = (snip[:140] + "...") if len(snip) > 140 else snip
                d["is_archived"] = bool(d.get("is_archived", 0))
                out.append(d)
            return out
        finally:
            await db.close()

    @classmethod
    async def get_session_messages(cls, session_id: str) -> List[Dict[str, Any]]:
        """Returns all messages belonging to a conversation session."""
        db = await cls.get_db()
        try:
            cursor = await db.execute(
                "SELECT id, session_id, role, content, sources, COALESCE(model_name, '') AS model_name, created_at FROM messages WHERE session_id = ? ORDER BY id ASC",
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
    async def get_session_with_messages(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """Returns full session metadata plus all messages for detailed inspection or export."""
        db = await cls.get_db()
        try:
            cur = await db.execute(
                """
                SELECT id, title, COALESCE(model_name, 'gemini-3.7-flash') AS model_name,
                       COALESCE(is_archived, 0) AS is_archived,
                       COALESCE(source, CASE WHEN id LIKE 'session_daily%' THEN 'automation' ELSE 'webchat' END) AS source,
                       created_at, updated_at
                FROM sessions WHERE id = ?
                """,
                (session_id,)
            )
            row = await cur.fetchone()
            if not row:
                return None
            sess = dict(row)
            sess["is_archived"] = bool(sess.get("is_archived", 0))
        finally:
            await db.close()
        sess["messages"] = await cls.get_session_messages(session_id)
        sess["msg_count"] = len(sess["messages"])
        return sess

    @classmethod
    async def add_message(
        cls,
        session_id: str,
        role: str,
        content: str,
        sources: Optional[List[Any]] = None,
        model_name: Optional[str] = None,
        source: Optional[str] = None,
    ):
        """Appends a user or assistant message to the session."""
        db = await cls.get_db()
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        sources_json = json.dumps(sources) if sources else None
        inferred_source = source or ("automation" if str(session_id).startswith("session_daily") else "webchat")
        try:
            # Check if session exists; if not, create it
            cursor = await db.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
            exists = await cursor.fetchone()
            if not exists:
                title = content[:35] + "..." if len(content) > 35 else content
                await db.execute(
                    "INSERT INTO sessions (id, title, model_name, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (session_id, title, model_name or "gemini-3.7-flash", inferred_source, now, now)
                )

            await db.execute(
                "INSERT INTO messages (session_id, role, content, sources, model_name, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, role, content, sources_json, (model_name or ""), now)
            )
            if model_name:
                await db.execute(
                    "UPDATE sessions SET updated_at = ?, model_name = ? WHERE id = ?",
                    (now, model_name, session_id)
                )
            else:
                await db.execute(
                    "UPDATE sessions SET updated_at = ? WHERE id = ?",
                    (now, session_id)
                )
            await db.commit()
        finally:
            await db.close()

    @classmethod
    async def search_messages(
        cls,
        q: str = "",
        session_id: Optional[str] = None,
        role: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 60,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Searches across all Chat AI messages and sessions with filtering & pagination."""
        db = await cls.get_db()
        try:
            clauses = ["1=1"]
            params: List[Any] = []
            clean_q = (q or "").strip()
            if clean_q:
                like_q = f"%{clean_q}%"
                clauses.append("(m.content LIKE ? OR s.title LIKE ?)")
                params.extend([like_q, like_q])
            if session_id:
                clauses.append("m.session_id = ?")
                params.append(session_id)
            if role and role.lower() in ("user", "assistant", "system"):
                clauses.append("LOWER(m.role) = ?")
                params.append(role.lower())
            if date_from:
                clauses.append("date(m.created_at) >= date(?)")
                params.append(date_from)
            if date_to:
                clauses.append("date(m.created_at) <= date(?)")
                params.append(date_to)

            where_sql = " AND ".join(clauses)
            cnt_cur = await db.execute(
                f"SELECT COUNT(*) FROM messages m JOIN sessions s ON m.session_id = s.id WHERE {where_sql}",
                tuple(params)
            )
            total = int((await cnt_cur.fetchone())[0])

            safe_limit = max(1, min(int(limit or 60), 200))
            safe_offset = max(0, int(offset or 0))
            query_sql = f"""
                SELECT
                    m.id,
                    m.session_id,
                    m.role,
                    m.content,
                    m.sources,
                    COALESCE(NULLIF(m.model_name, ''), s.model_name, 'gemini-3.7-flash') AS model_name,
                    m.created_at,
                    s.title AS session_title,
                    COALESCE(s.source, CASE WHEN s.id LIKE 'session_daily%' THEN 'automation' ELSE 'webchat' END) AS session_source,
                    COALESCE(s.is_archived, 0) AS is_archived
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE {where_sql}
                ORDER BY m.created_at DESC, m.id DESC
                LIMIT ? OFFSET ?
            """
            cur = await db.execute(query_sql, tuple(params + [safe_limit, safe_offset]))
            rows = await cur.fetchall()
            items = []
            for r in rows:
                d = dict(r)
                if d.get("sources"):
                    try:
                        d["sources"] = json.loads(d["sources"])
                    except Exception:
                        d["sources"] = []
                else:
                    d["sources"] = []
                d["is_archived"] = bool(d.get("is_archived", 0))
                items.append(d)
            return {"total": total, "items": items, "limit": safe_limit, "offset": safe_offset}
        finally:
            await db.close()

    @classmethod
    async def delete_message(cls, session_id: str, message_id: int) -> bool:
        """Deletes a single message from a chat session."""
        db = await cls.get_db()
        try:
            cur = await db.execute(
                "DELETE FROM messages WHERE id = ? AND session_id = ?",
                (int(message_id), session_id)
            )
            await db.commit()
            return (cur.rowcount or 0) > 0
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
        """Returns deep telemetry overview for the Sessions dashboard."""
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


