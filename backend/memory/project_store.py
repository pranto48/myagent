# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.1.0
import os
import json
import time
import uuid
import aiosqlite
import logging
from typing import List, Dict, Any, Optional
from config import settings

logger = logging.getLogger("myagent.memory.project_store")

class ProjectMemoryStore:
    """
    Manages persistent per-project information, architecture blueprints,
    and hierarchical memory indexing (Project -> Category -> Context -> Key) in SQLite.
    """

    _initialized = False

    @classmethod
    async def get_db(cls):
        """Connects to persistent SQLite database and ensures project memory schema exists."""
        db = await aiosqlite.connect(settings.SESSION_DB_PATH)
        db.row_factory = aiosqlite.Row

        # Table 1: Registered Projects & Architecture Blueprints
        await db.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                display_name TEXT,
                description TEXT,
                tech_stack TEXT,
                architecture_blueprint TEXT,
                urls TEXT,
                env_summary TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT,
                updated_at TEXT
            )
        """)

        # Table 2: Hierarchical Project Memories
        await db.execute("""
            CREATE TABLE IF NOT EXISTS project_memories (
                id TEXT PRIMARY KEY,
                project_name TEXT NOT NULL,
                key TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                context TEXT DEFAULT 'production',
                title TEXT,
                content TEXT NOT NULL,
                tags TEXT,
                security_level TEXT DEFAULT 'INTERNAL',
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(project_name, key)
            )
        """)

        await db.execute("CREATE INDEX IF NOT EXISTS idx_pm_proj ON project_memories(project_name)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_pm_cat ON project_memories(project_name, category)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_pm_key ON project_memories(project_name, key)")

        await db.commit()

        if not cls._initialized:
            await cls._seed_defaults(db)
            cls._initialized = True

        return db

    @classmethod
    async def _seed_defaults(cls, db: aiosqlite.Connection):
        """Seeds default project metadata for MyAgent and key projects if not present."""
        async with db.execute("SELECT COUNT(*) as cnt FROM projects") as cursor:
            row = await cursor.fetchone()
            if row and row["cnt"] > 0:
                return

        now = time.strftime("%Y-%m-%d %H:%M:%S")

        default_projects = [
            {
                "id": "prj_myagent",
                "name": "myagent",
                "display_name": "MyAgent — Enterprise Autonomous AI Platform",
                "description": "Enterprise AI Agent platform with MCP Server, Hybrid Vector Memory, Autonomous Subagents, and Multi-Model AI.",
                "tech_stack": json.dumps({
                    "frontend": "HTML5, Vanilla ES6 JavaScript, CSS3, Nginx Reverse Proxy",
                    "backend": "FastAPI, Python 3.11, Uvicorn, Pydantic v2",
                    "databases": "SQLite (FTS5), ChromaDB (Vector Store)",
                    "models": "OpenRouter Multi-Provider, OxionAI, LM Studio, OpenAI-compatible",
                    "protocols": "Model Context Protocol (MCP 2024-11-05 SSE/JSON-RPC), OpenAPI 3.1",
                    "containers": ["myagent-web (Port 3399)", "myagent-backend (Port 8008 -> 8000)"]
                }, ensure_ascii=False),
                "architecture_blueprint": (
                    "MyAgent Architecture Blueprint:\n"
                    "1. Frontend Web UI (Port 3399) served by Nginx, routing /api/* to FastAPI backend container.\n"
                    "2. Core Agent Engine with Tool Calling, ReAct loop, and dynamic OpenRouter / Local LLM provider.\n"
                    "3. Model Context Protocol (MCP) Server exposing tools via SSE (/api/mcp/server/sse) and JSON-RPC (/api/mcp/server/rpc).\n"
                    "4. Network Ping Sub-Agent testing host connectivity, latency, packet loss, and TCP port status.\n"
                    "5. Per-Project Memory Vault storing credentials, architectural blueprints, and key facts.\n"
                    "6. Persistent Data volume mapped to /app/data on host for chat_history.db and chroma_db."
                ),
                "urls": json.dumps({
                    "live_url": "http://192.168.9.9:3399",
                    "repo_url": "https://github.com/pranto48/myagent.git",
                    "docs_url": "http://192.168.9.9:3399/docs"
                }),
                "env_summary": "WEB_PORT=3399, BACKEND_PORT=8000, LLM_PROVIDER=openrouter/default, OPENROUTER_API_KEY",
                "status": "active",
                "created_at": now,
                "updated_at": now
            },
            {
                "id": "prj_48_otnarp",
                "name": "48_otnarp",
                "display_name": "48 Otnarp Production Hub",
                "description": "Core enterprise operations, automation, and project infrastructure.",
                "tech_stack": json.dumps({"stack": "Web & Cloud Services", "database": "PostgreSQL / SQLite"}, ensure_ascii=False),
                "architecture_blueprint": "Central management and deployment infrastructure.",
                "urls": json.dumps({"status": "active"}),
                "env_summary": "Production keys and cloud credentials.",
                "status": "active",
                "created_at": now,
                "updated_at": now
            },
            {
                "id": "prj_ampshop",
                "name": "ampshop",
                "display_name": "AmpShop E-Commerce Platform",
                "description": "E-Commerce multi-vendor shopping and inventory system.",
                "tech_stack": json.dumps({"stack": "Node.js / React / Python", "database": "MySQL / PostgreSQL"}, ensure_ascii=False),
                "architecture_blueprint": "E-commerce store with user cart, checkout, payment gateway, and admin portal.",
                "urls": json.dumps({"environment": "production"}),
                "env_summary": "Database connection and merchant payment keys.",
                "status": "active",
                "created_at": now,
                "updated_at": now
            }
        ]

        for p in default_projects:
            await db.execute("""
                INSERT OR IGNORE INTO projects (
                    id, name, display_name, description, tech_stack,
                    architecture_blueprint, urls, env_summary, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p["id"], p["name"], p["display_name"], p["description"], p["tech_stack"],
                p["architecture_blueprint"], p["urls"], p["env_summary"], p["status"], p["created_at"], p["updated_at"]
            ))

        # Seed initial memories for myagent
        default_memories = [
            {
                "id": "mem_myagent_ports",
                "project_name": "myagent",
                "key": "container_ports",
                "category": "deployment",
                "context": "production",
                "title": "MyAgent Container Ports & Network",
                "content": "Web Nginx container runs on port 3399 (http://192.168.9.9:3399). Backend FastAPI runs inside container on port 8000 and mapped to host port 8008.",
                "tags": json.dumps(["ports", "network", "docker", "nginx"]),
                "security_level": "INTERNAL"
            },
            {
                "id": "mem_myagent_mcp",
                "project_name": "myagent",
                "key": "mcp_server_endpoints",
                "category": "architecture",
                "context": "production",
                "title": "MyAgent MCP Server Endpoints",
                "content": "SSE Endpoint: http://192.168.9.9:3399/api/mcp/server/sse\nHTTP JSON-RPC: http://192.168.9.9:3399/api/mcp/server/rpc\nMessages: http://192.168.9.9:3399/api/mcp/server/messages\nProtocol: MCP 2024-11-05",
                "tags": json.dumps(["mcp", "sse", "rpc", "protocol"]),
                "security_level": "INTERNAL"
            },
            {
                "id": "mem_myagent_ssh",
                "project_name": "myagent",
                "key": "deploy_ssh_credentials",
                "category": "credentials",
                "context": "production",
                "title": "Remote Deployment SSH Target",
                "content": "Remote Host: 192.168.9.9, Port: 22, User: it, Deploy Directory: /home/it/myagent.",
                "tags": json.dumps(["ssh", "deploy", "server", "credentials"]),
                "security_level": "CONFIDENTIAL"
            }
        ]

        for m in default_memories:
            await db.execute("""
                INSERT OR IGNORE INTO project_memories (
                    id, project_name, key, category, context, title, content, tags, security_level, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                m["id"], m["project_name"], m["key"], m["category"], m["context"],
                m["title"], m["content"], m["tags"], m["security_level"], now, now
            ))

        await db.commit()

    @classmethod
    async def save_project_info(
        cls,
        name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        tech_stack: Optional[Any] = None,
        architecture_blueprint: Optional[str] = None,
        urls: Optional[Any] = None,
        env_summary: Optional[str] = None,
        status: str = "active"
    ) -> Dict[str, Any]:
        """Creates or updates high-level project metadata and architecture blueprint."""
        clean_name = name.strip().lower()
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        tech_stack_str = json.dumps(tech_stack) if isinstance(tech_stack, (dict, list)) else (tech_stack or "")
        urls_str = json.dumps(urls) if isinstance(urls, (dict, list)) else (urls or "")

        db = await cls.get_db()
        try:
            # Check if project exists
            async with db.execute("SELECT id FROM projects WHERE name = ?", (clean_name,)) as cursor:
                existing = await cursor.fetchone()

            if existing:
                project_id = existing["id"]
                await db.execute("""
                    UPDATE projects SET
                        display_name = COALESCE(?, display_name),
                        description = COALESCE(?, description),
                        tech_stack = CASE WHEN ? != '' THEN ? ELSE tech_stack END,
                        architecture_blueprint = CASE WHEN ? != '' THEN ? ELSE architecture_blueprint END,
                        urls = CASE WHEN ? != '' THEN ? ELSE urls END,
                        env_summary = CASE WHEN ? != '' THEN ? ELSE env_summary END,
                        status = ?,
                        updated_at = ?
                    WHERE name = ?
                """, (
                    display_name, description, tech_stack_str, tech_stack_str,
                    architecture_blueprint or "", architecture_blueprint or "",
                    urls_str, urls_str, env_summary or "", env_summary or "",
                    status, now, clean_name
                ))
            else:
                project_id = f"prj_{clean_name}_{uuid.uuid4().hex[:6]}"
                await db.execute("""
                    INSERT INTO projects (
                        id, name, display_name, description, tech_stack,
                        architecture_blueprint, urls, env_summary, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    project_id, clean_name, display_name or clean_name, description or "",
                    tech_stack_str, architecture_blueprint or "", urls_str, env_summary or "",
                    status, now, now
                ))

            await db.commit()
            return await cls.get_project_info(clean_name)
        finally:
            await db.close()

    @classmethod
    async def get_project_info(cls, name: str) -> Optional[Dict[str, Any]]:
        """Retrieves project details, architecture blueprint, and memory counts."""
        clean_name = name.strip().lower()
        db = await cls.get_db()
        try:
            async with db.execute("SELECT * FROM projects WHERE name = ?", (clean_name,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                data = dict(row)

            # Count total memories
            async with db.execute("SELECT COUNT(*) as cnt FROM project_memories WHERE project_name = ?", (clean_name,)) as m_cur:
                m_row = await m_cur.fetchone()
                data["memories_count"] = m_row["cnt"] if m_row else 0

            # Parse JSON fields if valid
            for json_field in ("tech_stack", "urls"):
                if data.get(json_field):
                    try:
                        data[json_field] = json.loads(data[json_field])
                    except Exception:
                        pass

            return data
        finally:
            await db.close()

    @classmethod
    async def list_projects(cls) -> List[Dict[str, Any]]:
        """Lists all registered projects with their memory count and status."""
        db = await cls.get_db()
        try:
            query = """
                SELECT p.*, COUNT(m.id) as memories_count
                FROM projects p
                LEFT JOIN project_memories m ON p.name = m.project_name
                GROUP BY p.id
                ORDER BY p.updated_at DESC
            """
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()
                results = []
                for r in rows:
                    item = dict(r)
                    for jf in ("tech_stack", "urls"):
                        if item.get(jf):
                            try:
                                item[jf] = json.loads(item[jf])
                            except Exception:
                                pass
                    results.append(item)
                return results
        finally:
            await db.close()

    @classmethod
    async def save_memory(
        cls,
        project_name: str,
        key: str,
        content: str,
        title: Optional[str] = None,
        category: str = "general",
        context: str = "production",
        tags: Optional[List[str]] = None,
        security_level: str = "INTERNAL"
    ) -> Dict[str, Any]:
        """
        Saves or updates a project memory record using strict hierarchical indexing:
        Tag Level 1 (Project) -> Tag Level 2 (Category) -> Tag Level 3 (Context) -> Key.
        Also indexes a chunk into hybrid vector memory for semantic RAG search.
        """
        clean_proj = project_name.strip().lower()
        clean_key = key.strip().lower()
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        tags_list = tags if isinstance(tags, list) else ([t.strip() for t in str(tags or "").split(",") if t.strip()])
        # Auto-append hierarchical tags
        for t in [clean_proj, category, context]:
            if t and t not in tags_list:
                tags_list.append(t)

        tags_str = json.dumps(tags_list, ensure_ascii=False)
        resolved_title = title or f"[{clean_proj.upper()}] {clean_key.replace('_', ' ').title()}"

        db = await cls.get_db()
        try:
            # Ensure parent project exists
            async with db.execute("SELECT id FROM projects WHERE name = ?", (clean_proj,)) as cursor:
                if not await cursor.fetchone():
                    p_id = f"prj_{clean_proj}_{uuid.uuid4().hex[:6]}"
                    await db.execute("""
                        INSERT INTO projects (id, name, display_name, description, status, created_at, updated_at)
                        VALUES (?, ?, ?, ?, 'active', ?, ?)
                    """, (p_id, clean_proj, clean_proj.title(), f"Auto-created project for {clean_proj}", now, now))

            # UPSERT memory
            mem_id = f"mem_{clean_proj}_{clean_key}"
            await db.execute("""
                INSERT INTO project_memories (
                    id, project_name, key, category, context, title, content, tags, security_level, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_name, key) DO UPDATE SET
                    category = excluded.category,
                    context = excluded.context,
                    title = excluded.title,
                    content = excluded.content,
                    tags = excluded.tags,
                    security_level = excluded.security_level,
                    updated_at = excluded.updated_at
            """, (
                mem_id, clean_proj, clean_key, category, context,
                resolved_title, content, tags_str, security_level, now, now
            ))
            await db.commit()

            # Also index into hybrid Vector Store if available
            try:
                from memory.vector_store import VectorStore
                store = VectorStore()
                store.add_note(
                    title=resolved_title,
                    content=f"Project: {clean_proj}\nKey: {clean_key}\nCategory: {category}\nContext: {context}\n\n{content}",
                    category=category,
                    tags=tags_list,
                    security_level=security_level
                )
            except Exception as ve:
                logger.warning(f"Could not index project memory into vector store: {ve}")

            return {
                "success": True,
                "project": clean_proj,
                "key": clean_key,
                "title": resolved_title,
                "category": category,
                "context": context,
                "tags": tags_list,
                "security_level": security_level,
                "updated_at": now
            }
        finally:
            await db.close()

    @classmethod
    async def get_memory(cls, project_name: str, key: str) -> Optional[Dict[str, Any]]:
        """Direct ultra-fast retrieval (<1ms) of a project memory by project and exact key."""
        clean_proj = project_name.strip().lower()
        clean_key = key.strip().lower()

        db = await cls.get_db()
        try:
            async with db.execute("""
                SELECT * FROM project_memories WHERE project_name = ? AND key = ?
            """, (clean_proj, clean_key)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                data = dict(row)
                if data.get("tags"):
                    try:
                        data["tags"] = json.loads(data["tags"])
                    except Exception:
                        pass
                return data
        finally:
            await db.close()

    @classmethod
    async def search_memories(
        cls,
        project_name: Optional[str] = None,
        category: Optional[str] = None,
        context: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Filters project memories by project, category, context, and text search."""
        db = await cls.get_db()
        try:
            sql = "SELECT * FROM project_memories WHERE 1=1"
            params = []

            if project_name:
                sql += " AND project_name = ?"
                params.append(project_name.strip().lower())
            if category:
                sql += " AND category = ?"
                params.append(category.strip().lower())
            if context:
                sql += " AND context = ?"
                params.append(context.strip().lower())
            if query:
                sql += " AND (title LIKE ? OR content LIKE ? OR key LIKE ? OR tags LIKE ?)"
                pattern = f"%{query.strip()}%"
                params.extend([pattern, pattern, pattern, pattern])

            sql += " ORDER BY updated_at DESC LIMIT ?"
            params.append(int(limit))

            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                results = []
                for r in rows:
                    item = dict(r)
                    if item.get("tags"):
                        try:
                            item["tags"] = json.loads(item["tags"])
                        except Exception:
                            pass
                    results.append(item)
                return results
        finally:
            await db.close()

    @classmethod
    async def delete_memory(cls, project_name: str, key: str) -> bool:
        """Deletes a specific memory record."""
        clean_proj = project_name.strip().lower()
        clean_key = key.strip().lower()

        db = await cls.get_db()
        try:
            cursor = await db.execute("""
                DELETE FROM project_memories WHERE project_name = ? AND key = ?
            """, (clean_proj, clean_key))
            await db.commit()
            return cursor.rowcount > 0
        finally:
            await db.close()

    @classmethod
    async def delete_project(cls, project_name: str) -> bool:
        """Deletes a project and all its associated memories."""
        clean_proj = project_name.strip().lower()
        db = await cls.get_db()
        try:
            await db.execute("DELETE FROM project_memories WHERE project_name = ?", (clean_proj,))
            cursor = await db.execute("DELETE FROM projects WHERE name = ?", (clean_proj,))
            await db.commit()
            return cursor.rowcount > 0
        finally:
            await db.close()
