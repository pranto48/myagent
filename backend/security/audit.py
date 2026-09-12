# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.2.0
import os
import json
import time
import datetime
import aiosqlite
import logging
from typing import List, Dict, Any, Optional
from config import settings

logger = logging.getLogger(__name__)

class SecurityAuditStore:
    """
    Persistent Enterprise Security & Compliance Audit Trail Engine.
    Records all authentication events, access control decisions, DLP triggers,
    prompt injection blocks, and data modifications to SQLite.
    """
    _instance: Optional['SecurityAuditStore'] = None
    _db_path: str = ""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SecurityAuditStore, cls).__new__(cls)
            cls._instance._db_path = settings.AUDIT_DB_PATH
        return cls._instance

    async def init_db(self):
        """Initializes the security audit database table."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS security_audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    iso_time TEXT NOT NULL,
                    action TEXT NOT NULL,
                    username TEXT NOT NULL,
                    user_role TEXT NOT NULL,
                    resource TEXT DEFAULT '',
                    severity TEXT NOT NULL, -- INFO, WARNING, CRITICAL
                    ip_address TEXT DEFAULT '127.0.0.1',
                    details TEXT DEFAULT '{}'
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON security_audit_logs(timestamp DESC)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_audit_severity ON security_audit_logs(severity)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON security_audit_logs(action)")
            await db.commit()

    async def log_event(
        self,
        action: str,
        username: str = "system",
        user_role: str = "guest",
        resource: str = "",
        severity: str = "INFO",
        ip_address: str = "127.0.0.1",
        details: Optional[Dict[str, Any]] = None
    ):
        """Records a new security event into the audit trail."""
        if not settings.AUDIT_LOG_ENABLED:
            return
        
        now = time.time()
        iso_str = datetime.datetime.fromtimestamp(now, tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        details_str = json.dumps(details or {})
        
        try:
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute("""
                    INSERT INTO security_audit_logs
                    (timestamp, iso_time, action, username, user_role, resource, severity, ip_address, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (now, iso_str, action, username, user_role, resource, severity, ip_address, details_str))
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to record security audit log: {e}")

    async def get_audit_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        severity: Optional[str] = None,
        action: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Queries audit logs with pagination and multi-field filtering."""
        query = "SELECT id, timestamp, iso_time, action, username, user_role, resource, severity, ip_address, details FROM security_audit_logs WHERE 1=1"
        count_query = "SELECT COUNT(*) FROM security_audit_logs WHERE 1=1"
        params: List[Any] = []
        count_params: List[Any] = []

        if severity and severity.upper() != "ALL":
            query += " AND severity = ?"
            count_query += " AND severity = ?"
            params.append(severity.upper())
            count_params.append(severity.upper())

        if action and action.upper() != "ALL":
            query += " AND action = ?"
            count_query += " AND action = ?"
            params.append(action.upper())
            count_params.append(action.upper())

        if search:
            query += " AND (username LIKE ? OR resource LIKE ? OR details LIKE ?)"
            count_query += " AND (username LIKE ? OR resource LIKE ? OR details LIKE ?)"
            like_s = f"%{search}%"
            params.extend([like_s, like_s, like_s])
            count_params.extend([like_s, like_s, like_s])

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(count_query, count_params) as cursor:
                row = await cursor.fetchone()
                total = row[0] if row else 0

            logs = []
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    try:
                        parsed_details = json.loads(row[9])
                    except Exception:
                        parsed_details = {}
                    logs.append({
                        "id": row[0],
                        "timestamp": row[1],
                        "iso_time": row[2],
                        "action": row[3],
                        "username": row[4],
                        "user_role": row[5],
                        "resource": row[6],
                        "severity": row[7],
                        "ip_address": row[8],
                        "details": parsed_details
                    })

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "logs": logs
        }

    async def get_security_stats(self) -> Dict[str, Any]:
        """Calculates security telemetry and threat statistics."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM security_audit_logs") as cur:
                total_events = (await cur.fetchone())[0]

            async with db.execute("SELECT COUNT(*) FROM security_audit_logs WHERE action LIKE '%DLP%'") as cur:
                dlp_triggers = (await cur.fetchone())[0]

            async with db.execute("SELECT COUNT(*) FROM security_audit_logs WHERE action LIKE '%FIREWALL%' OR action LIKE '%INJECTION%'") as cur:
                firewall_blocks = (await cur.fetchone())[0]

            async with db.execute("SELECT COUNT(*) FROM security_audit_logs WHERE action = 'LOGIN_FAILED'") as cur:
                failed_logins = (await cur.fetchone())[0]

            async with db.execute("SELECT COUNT(*) FROM security_audit_logs WHERE severity = 'CRITICAL'") as cur:
                critical_threats = (await cur.fetchone())[0]

        return {
            "encryption_algorithm": "AES-256-GCM",
            "encryption_at_rest": True,
            "dlp_engine_active": settings.DLP_ENABLED,
            "firewall_active": settings.FIREWALL_ENABLED,
            "rate_limiter_active": settings.RATE_LIMIT_ENABLED,
            "total_audit_events": total_events,
            "dlp_triggers_count": dlp_triggers,
            "firewall_blocks_count": firewall_blocks,
            "failed_logins_count": failed_logins,
            "critical_threats_count": critical_threats,
            "overall_status": "SECURE" if critical_threats == 0 else "ATTENTION_REQUIRED"
        }
