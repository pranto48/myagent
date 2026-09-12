# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 2.2.0
# ==============================================================================

import uuid
import time
import aiosqlite
from typing import List, Dict, Any, Optional
from config import settings

class UserStore:
    """Manages persistent enterprise users and roles in SQLite."""

    @classmethod
    async def get_db(cls):
        db = await aiosqlite.connect(settings.SESSION_DB_PATH)
        db.row_factory = aiosqlite.Row
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'Member',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Seed default admin if not exists
        cursor = await db.execute("SELECT id FROM users WHERE username = ?", (settings.ADMIN_USERNAME,))
        row = await cursor.fetchone()
        if not row:
            admin_id = f"user_{uuid.uuid4().hex[:8]}"
            await db.execute(
                "INSERT INTO users (id, username, password, role, status) VALUES (?, ?, ?, ?, ?)",
                (admin_id, settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD, "Admin", "active")
            )
        await db.commit()
        return db

    @classmethod
    async def list_users(cls) -> List[Dict[str, Any]]:
        db = await cls.get_db()
        try:
            cursor = await db.execute("SELECT id, username, role, status, created_at FROM users ORDER BY created_at ASC")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            await db.close()

    @classmethod
    async def get_user(cls, username: str) -> Optional[Dict[str, Any]]:
        db = await cls.get_db()
        try:
            cursor = await db.execute("SELECT id, username, password, role, status FROM users WHERE username = ?", (username,))
            row = await cursor.fetchone()
            return dict(row) if row else None
        finally:
            await db.close()

    @classmethod
    async def create_user(cls, username: str, password: str, role: str = "Member") -> Dict[str, Any]:
        db = await cls.get_db()
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            await db.execute(
                "INSERT INTO users (id, username, password, role, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, password, role, "active", now)
            )
            await db.commit()
            return {"id": user_id, "username": username, "role": role, "status": "active", "created_at": now}
        finally:
            await db.close()

    @classmethod
    async def update_password(cls, user_id: str, new_password: str) -> bool:
        db = await cls.get_db()
        try:
            await db.execute("UPDATE users SET password = ? WHERE id = ?", (new_password, user_id))
            await db.commit()
            return True
        finally:
            await db.close()

    @classmethod
    async def delete_user(cls, user_id: str) -> bool:
        db = await cls.get_db()
        try:
            # Prevent deleting default admin
            cursor = await db.execute("SELECT username FROM users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()
            if row and row["username"] == settings.ADMIN_USERNAME:
                return False
            await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
            await db.commit()
            return True
        finally:
            await db.close()
