# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.2.0
import os
import json
import time
import uuid
import aiosqlite
import logging
from typing import List, Dict, Any, Optional
from config import settings

logger = logging.getLogger("myagent.mcp.store")

class MCPStore:
    """Manages persistent MCP server registrations in SQLite."""

    _initialized = False

    @classmethod
    async def get_db(cls):
        db = await aiosqlite.connect(settings.SESSION_DB_PATH)
        db.row_factory = aiosqlite.Row
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mcp_servers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                transport TEXT NOT NULL DEFAULT 'sse',
                command TEXT,
                args TEXT,
                url TEXT,
                env TEXT,
                is_enabled INTEGER DEFAULT 1,
                last_ping_ms REAL DEFAULT -1,
                status TEXT DEFAULT 'configured',
                tools_cache TEXT DEFAULT '[]',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        await db.commit()

        if not cls._initialized:
            await cls._seed_defaults(db)
            cls._initialized = True

        return db

    @classmethod
    async def _seed_defaults(cls, db: aiosqlite.Connection):
        """Seeds standard open-source MCP server templates if table is empty."""
        async with db.execute("SELECT COUNT(*) as cnt FROM mcp_servers") as cursor:
            row = await cursor.fetchone()
            if row and row["cnt"] > 0:
                return

        now = time.strftime("%Y-%m-%d %H:%M:%S")
        templates = [
            {
                "id": "mcp-filesystem",
                "name": "Local FileSystem MCP",
                "transport": "stdio",
                "command": "python3",
                "args": json.dumps(["-c", "import sys; print('MCP FileSystem Ready')"]),
                "url": "",
                "env": json.dumps({"BASE_PATH": "/app/data"}),
                "is_enabled": 1,
                "status": "ready",
                "tools_cache": json.dumps([
                    {
                        "name": "fs_read_dir",
                        "description": "Read directory tree from container data volume",
                        "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}}
                    }
                ]),
                "created_at": now,
                "updated_at": now
            },
            {
                "id": "mcp-sqlite",
                "name": "SQLite Analytics MCP",
                "transport": "stdio",
                "command": "python3",
                "args": json.dumps(["-c", "import sys; print('MCP SQLite Server Ready')"]),
                "url": "",
                "env": json.dumps({"DB_PATH": "/app/data/chat_history.db"}),
                "is_enabled": 1,
                "status": "ready",
                "tools_cache": json.dumps([
                    {
                        "name": "sqlite_schema_dump",
                        "description": "Inspect all tables and schemas in internal SQLite database",
                        "inputSchema": {"type": "object", "properties": {}}
                    }
                ]),
                "created_at": now,
                "updated_at": now
            },
            {
                "id": "mcp-web-fetch",
                "name": "Web & HTML Fetcher MCP",
                "transport": "sse",
                "command": "",
                "args": "[]",
                "url": "http://127.0.0.1:8000/api/mcp/mock-sse",
                "env": "{}",
                "is_enabled": 1,
                "status": "ready",
                "tools_cache": json.dumps([
                    {
                        "name": "fetch_article_markdown",
                        "description": "Fetch remote web article and convert to clean markdown format",
                        "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}
                    }
                ]),
                "created_at": now,
                "updated_at": now
            }
        ]

        for t in templates:
            await db.execute("""
                INSERT INTO mcp_servers (id, name, transport, command, args, url, env, is_enabled, status, tools_cache, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                t["id"], t["name"], t["transport"], t["command"], t["args"], t["url"],
                t["env"], t["is_enabled"], t["status"], t["tools_cache"], t["created_at"], t["updated_at"]
            ))
        await db.commit()
        logger.info("Default Open Source MCP Server templates seeded successfully.")

    @classmethod
    async def list_servers(cls) -> List[Dict[str, Any]]:
        db = await cls.get_db()
        try:
            async with db.execute("SELECT * FROM mcp_servers ORDER BY created_at ASC") as cursor:
                rows = await cursor.fetchall()
                result = []
                for r in rows:
                    item = dict(r)
                    item["args"] = json.loads(item.get("args") or "[]")
                    item["env"] = json.loads(item.get("env") or "{}")
                    item["tools_cache"] = json.loads(item.get("tools_cache") or "[]")
                    item["is_enabled"] = bool(item.get("is_enabled", 1))
                    result.append(item)
                return result
        finally:
            await db.close()

    @classmethod
    async def get_server(cls, server_id: str) -> Optional[Dict[str, Any]]:
        db = await cls.get_db()
        try:
            async with db.execute("SELECT * FROM mcp_servers WHERE id = ?", (server_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                item = dict(row)
                item["args"] = json.loads(item.get("args") or "[]")
                item["env"] = json.loads(item.get("env") or "{}")
                item["tools_cache"] = json.loads(item.get("tools_cache") or "[]")
                item["is_enabled"] = bool(item.get("is_enabled", 1))
                return item
        finally:
            await db.close()

    @classmethod
    async def add_server(
        cls,
        name: str,
        transport: str = "sse",
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        url: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        is_enabled: bool = True
    ) -> Dict[str, Any]:
        db = await cls.get_db()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        server_id = f"mcp_{uuid.uuid4().hex[:8]}"

        try:
            await db.execute("""
                INSERT INTO mcp_servers (id, name, transport, command, args, url, env, is_enabled, status, tools_cache, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'configured', '[]', ?, ?)
            """, (
                server_id,
                name,
                transport.lower(),
                command or "",
                json.dumps(args or []),
                url or "",
                json.dumps(env or {}),
                1 if is_enabled else 0,
                now,
                now
            ))
            await db.commit()
        finally:
            await db.close()

        return await cls.get_server(server_id)

    @classmethod
    async def update_server(
        cls,
        server_id: str,
        name: Optional[str] = None,
        transport: Optional[str] = None,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        url: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        is_enabled: Optional[bool] = None,
        status: Optional[str] = None,
        last_ping_ms: Optional[float] = None,
        tools_cache: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Dict[str, Any]]:
        existing = await cls.get_server(server_id)
        if not existing:
            return None

        db = await cls.get_db()
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            await db.execute("""
                UPDATE mcp_servers
                SET name = COALESCE(?, name),
                    transport = COALESCE(?, transport),
                    command = COALESCE(?, command),
                    args = COALESCE(?, args),
                    url = COALESCE(?, url),
                    env = COALESCE(?, env),
                    is_enabled = COALESCE(?, is_enabled),
                    status = COALESCE(?, status),
                    last_ping_ms = COALESCE(?, last_ping_ms),
                    tools_cache = COALESCE(?, tools_cache),
                    updated_at = ?
                WHERE id = ?
            """, (
                name,
                transport.lower() if transport else None,
                command,
                json.dumps(args) if args is not None else None,
                url,
                json.dumps(env) if env is not None else None,
                (1 if is_enabled else 0) if is_enabled is not None else None,
                status,
                last_ping_ms,
                json.dumps(tools_cache) if tools_cache is not None else None,
                now,
                server_id
            ))
            await db.commit()
        finally:
            await db.close()

        return await cls.get_server(server_id)

    @classmethod
    async def delete_server(cls, server_id: str) -> bool:
        db = await cls.get_db()
        try:
            res = await db.execute("DELETE FROM mcp_servers WHERE id = ?", (server_id,))
            await db.commit()
            return res.rowcount > 0
        finally:
            await db.close()
