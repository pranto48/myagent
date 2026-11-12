# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.5.0
"""
Zero-AI-Leak Sealed Device Credential Vault for MyAgent MCP Server.

Security Guarantee:
1. Router/Switch/Firewall/Server credentials are encrypted at rest with AES-256-GCM
   (`security.crypto.DataCrypto`) inside a dedicated isolated SQLite table
   (`mcp_sealed_device_vault`) that is NEVER indexed by ChromaDB or project memory.
2. AI models and external MCP clients NEVER receive plaintext usernames, passwords,
   or enable/API secrets from list/get/verify tools or MCP resources.
3. `verify_device_with_sealed_credential()` decrypts credentials strictly inside
   transient Python backend memory to test HTTP/HTTPS/RouterOS/TCP connectivity,
   discards secrets immediately, and returns only operational pass/fail telemetry.
4. Plaintext reveal is restricted exclusively to Human Admin Web Panel sessions
   (`get_current_admin` + explicit `X-Human-Admin-Reveal: true` header) and audited.
"""

import asyncio
import json
import logging
import os
import re
import socket
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import aiosqlite
import httpx

from config import settings
from security.audit import SecurityAuditStore
from security.crypto import DataCrypto

logger = logging.getLogger("myagent.mcp.sealed_vault")

_MASKED_SECRET = "•••••••• [AI-SEALED]"
SEALED_VAULT_DB_PATH = os.path.join(settings.DATA_DIR, "sealed_vault.db")


def _mask_username(username: str) -> str:
    """Returns a non-reversible masked hint for AI/UI displays (never full username)."""
    raw = (username or "").strip()
    if not raw:
        return "—"
    if len(raw) <= 2:
        return "*" * len(raw)
    if len(raw) <= 4:
        return f"{raw[0]}{'*' * (len(raw) - 1)}"
    return f"{raw[:2]}{'*' * min(6, len(raw) - 3)}{raw[-1]}"


def _default_port_for_protocol(protocol: str) -> int:
    proto = (protocol or "http").strip().lower()
    mapping = {
        "http": 80,
        "https": 443,
        "ssh": 22,
        "telnet": 23,
        "ftp": 21,
        "smb": 445,
        "rdp": 3389,
        "winbox": 8291,
        "routeros_api": 8728,
        "routeros_rest": 443,
        "snmp": 161,
    }
    return mapping.get(proto, 80)


def _normalize_host(raw_host: str) -> str:
    val = (raw_host or "").strip()
    if "://" in val:
        parsed = urlparse(val)
        val = parsed.hostname or val
    return val.split("/")[0].split(":")[0].strip()


class SealedDeviceVault:
    """Isolated AES-256-GCM Device Credential Store enforcing Zero-AI-Leak boundaries."""

    _table_ready: bool = False

    @classmethod
    async def _ensure_table(cls):
        if cls._table_ready:
            return
        os.makedirs(os.path.dirname(SEALED_VAULT_DB_PATH), exist_ok=True)
        async with aiosqlite.connect(SEALED_VAULT_DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS mcp_sealed_device_vault (
                    id TEXT PRIMARY KEY,
                    device_name TEXT NOT NULL,
                    device_type TEXT NOT NULL DEFAULT 'router',
                    host TEXT NOT NULL,
                    port INTEGER NOT NULL DEFAULT 80,
                    protocol TEXT NOT NULL DEFAULT 'http',
                    username_enc TEXT NOT NULL,
                    password_enc TEXT NOT NULL,
                    enable_secret_enc TEXT DEFAULT '',
                    username_hint TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    created_by TEXT DEFAULT 'admin',
                    last_verified_at TEXT DEFAULT '',
                    last_verify_status TEXT DEFAULT 'UNVERIFIED',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_sealed_vault_host ON mcp_sealed_device_vault(host)"
            )
            await db.commit()
        cls._table_ready = True

    @classmethod
    def _to_ai_safe_record(cls, row: Dict[str, Any]) -> Dict[str, Any]:
        """Strips ALL encrypted/plaintext secrets and returns AI-safe redacted metadata."""
        return {
            "id": row["id"],
            "device_name": row["device_name"],
            "device_type": row["device_type"],
            "host": row["host"],
            "port": row["port"],
            "protocol": row["protocol"],
            "username_masked": row.get("username_hint") or "***",
            "password_masked": _MASKED_SECRET,
            "has_enable_secret": bool(row.get("enable_secret_enc")),
            "enable_secret_masked": _MASKED_SECRET if row.get("enable_secret_enc") else "",
            "notes": row.get("notes") or "",
            "ai_access": "DENIED (Zero-AI-Leak AES-256-GCM Sealed)",
            "last_verified_at": row.get("last_verified_at") or "",
            "last_verify_status": row.get("last_verify_status") or "UNVERIFIED",
            "created_by": row.get("created_by") or "admin",
            "created_at": row.get("created_at") or "",
            "updated_at": row.get("updated_at") or "",
        }

    @classmethod
    async def save_device_credential(
        cls,
        device_name: str,
        host: str,
        username: str,
        password: str,
        device_type: str = "router",
        protocol: str = "http",
        port: Optional[int] = None,
        enable_secret: str = "",
        notes: str = "",
        created_by: str = "admin",
    ) -> Dict[str, Any]:
        """Encrypts and stores or updates a network device login in the AI-sealed vault."""
        await cls._ensure_table()

        clean_host = _normalize_host(host)
        if not clean_host:
            raise ValueError("Device IP or hostname is required.")
        clean_user = (username or "").strip()
        clean_pass = password or ""
        if not clean_user or not clean_pass:
            raise ValueError("Both username and password are required to seal device credentials.")

        clean_proto = (protocol or "http").strip().lower()
        resolved_port = int(port) if port else _default_port_for_protocol(clean_proto)
        clean_name = (device_name or "").strip() or f"{device_type.title()} ({clean_host})"
        clean_type = (device_type or "router").strip().lower()

        crypto = DataCrypto()
        user_enc = crypto.encrypt_text(clean_user)
        pass_enc = crypto.encrypt_text(clean_pass)
        secret_enc = crypto.encrypt_text(enable_secret) if enable_secret else ""
        hint = _mask_username(clean_user)
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        async with aiosqlite.connect(SEALED_VAULT_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id FROM mcp_sealed_device_vault WHERE host = ? AND protocol = ? AND port = ? LIMIT 1",
                (clean_host, clean_proto, resolved_port),
            ) as cur:
                existing = await cur.fetchone()

            if existing:
                vault_id = existing["id"]
                await db.execute(
                    """
                    UPDATE mcp_sealed_device_vault
                    SET device_name = ?, device_type = ?, username_enc = ?, password_enc = ?,
                        enable_secret_enc = ?, username_hint = ?, notes = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (clean_name, clean_type, user_enc, pass_enc, secret_enc, hint, notes or "", now, vault_id),
                )
            else:
                vault_id = f"vault_{uuid.uuid4().hex[:8]}"
                await db.execute(
                    """
                    INSERT INTO mcp_sealed_device_vault (
                        id, device_name, device_type, host, port, protocol,
                        username_enc, password_enc, enable_secret_enc, username_hint,
                        notes, created_by, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        vault_id, clean_name, clean_type, clean_host, resolved_port, clean_proto,
                        user_enc, pass_enc, secret_enc, hint, notes or "", created_by, now, now,
                    ),
                )
            await db.commit()

            async with db.execute("SELECT * FROM mcp_sealed_device_vault WHERE id = ?", (vault_id,)) as cur:
                saved = dict(await cur.fetchone())

        await SecurityAuditStore().log_event(
            action="SEALED_VAULT_SAVE",
            username=created_by,
            user_role="admin",
            resource=f"{clean_name} ({clean_host}:{resolved_port})",
            severity="INFO",
            details={"vault_id": vault_id, "protocol": clean_proto, "device_type": clean_type},
        )
        return cls._to_ai_safe_record(saved)

    @classmethod
    async def list_devices_safe(cls, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns ONLY AI-safe masked inventory metadata (NEVER returns plaintext secrets)."""
        await cls._ensure_table()
        async with aiosqlite.connect(SEALED_VAULT_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            sql = "SELECT * FROM mcp_sealed_device_vault"
            params: List[Any] = []
            if query and query.strip():
                like_q = f"%{query.strip()}%"
                sql += " WHERE device_name LIKE ? OR host LIKE ? OR device_type LIKE ? OR protocol LIKE ? OR notes LIKE ?"
                params.extend([like_q, like_q, like_q, like_q, like_q])
            sql += " ORDER BY updated_at DESC"
            async with db.execute(sql, params) as cur:
                rows = [dict(r) for r in await cur.fetchall()]
        return [cls._to_ai_safe_record(r) for r in rows]

    @classmethod
    async def _find_raw_device(cls, identifier: str) -> Optional[Dict[str, Any]]:
        await cls._ensure_table()
        ident = (identifier or "").strip()
        if not ident:
            return None
        async with aiosqlite.connect(SEALED_VAULT_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM mcp_sealed_device_vault
                WHERE id = ? OR LOWER(host) = LOWER(?) OR LOWER(device_name) LIKE LOWER(?)
                ORDER BY updated_at DESC LIMIT 1
                """,
                (ident, ident, f"%{ident}%"),
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    @classmethod
    async def delete_device(cls, vault_id: str, actor: str = "admin") -> bool:
        await cls._ensure_table()
        async with aiosqlite.connect(SEALED_VAULT_DB_PATH) as db:
            res = await db.execute("DELETE FROM mcp_sealed_device_vault WHERE id = ?", (vault_id,))
            await db.commit()
            deleted = res.rowcount > 0
        if deleted:
            await SecurityAuditStore().log_event(
                action="SEALED_VAULT_DELETE",
                username=actor,
                user_role="admin",
                resource=vault_id,
                severity="WARNING",
            )
        return deleted

    @classmethod
    async def human_admin_reveal(cls, vault_id: str, actor: str = "admin", client_ip: str = "127.0.0.1") -> Optional[Dict[str, Any]]:
        """
        HUMAN-ADMIN ONLY: Decrypts and reveals device credentials for authenticated Web Panel admins.
        MUST NEVER be called from AgentTools, MCP tools/call, resources/read, or LLM pipelines.
        """
        await cls._ensure_table()
        async with aiosqlite.connect(SEALED_VAULT_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM mcp_sealed_device_vault WHERE id = ?", (vault_id,)) as cur:
                row = await cur.fetchone()
                if not row:
                    return None
                rec = dict(row)

        crypto = DataCrypto()
        username_plain = crypto.decrypt_text(rec["username_enc"])
        password_plain = crypto.decrypt_text(rec["password_enc"])
        enable_plain = crypto.decrypt_text(rec["enable_secret_enc"]) if rec.get("enable_secret_enc") else ""

        await SecurityAuditStore().log_event(
            action="SEALED_VAULT_HUMAN_REVEAL",
            username=actor,
            user_role="admin",
            resource=f"{rec['device_name']} ({rec['host']})",
            severity="WARNING",
            ip_address=client_ip,
            details={"vault_id": vault_id},
        )
        return {
            "id": rec["id"],
            "device_name": rec["device_name"],
            "device_type": rec["device_type"],
            "host": rec["host"],
            "port": rec["port"],
            "protocol": rec["protocol"],
            "username": username_plain,
            "password": password_plain,
            "enable_secret": enable_plain,
            "notes": rec.get("notes") or "",
        }

    @classmethod
    async def verify_device_with_sealed_credential(cls, device_or_host: str) -> Dict[str, Any]:
        """
        Blind MCP Proxy Verification:
        Decrypts credentials ONLY transiently in backend memory to test reachability / auth
        against the target router/server, immediately wipes locals, and returns ONLY sanitized status.
        """
        raw = await cls._find_raw_device(device_or_host)
        if not raw:
            return {"found": False, "message": f"No sealed device matching '{device_or_host}' found in vault."}

        crypto = DataCrypto()
        username = crypto.decrypt_text(raw["username_enc"])
        password = crypto.decrypt_text(raw["password_enc"])

        host = raw["host"]
        port = int(raw["port"])
        proto = (raw["protocol"] or "http").lower()
        t0 = time.perf_counter()

        verify_status = "UNREACHABLE"
        detail_msg = ""
        http_status: Optional[int] = None
        reachable = False

        try:
            if proto in ("http", "https", "routeros_rest"):
                scheme = "https" if proto in ("https", "routeros_rest") or port in (443, 8443) else "http"
                base_url = f"{scheme}://{host}:{port}"
                probe_path = "/rest/system/resource" if proto == "routeros_rest" else "/"
                async with httpx.AsyncClient(timeout=5.0, verify=False, follow_redirects=True) as client:
                    resp = await client.get(f"{base_url}{probe_path}", auth=(username, password))
                    reachable = True
                    http_status = resp.status_code
                    srv = resp.headers.get("server", "")
                    if resp.status_code in (200, 204):
                        verify_status = "ONLINE_AUTH_OK"
                        detail_msg = f"HTTP {resp.status_code} authenticated response ({srv or 'web UI'})."
                    elif resp.status_code in (401, 403):
                        verify_status = "ONLINE_AUTH_REJECTED"
                        detail_msg = f"Host reachable (HTTP {resp.status_code}), credentials/method not accepted by basic auth ({srv or 'web UI'})."
                    else:
                        verify_status = f"ONLINE_HTTP_{resp.status_code}"
                        detail_msg = f"Host reachable; responded HTTP {resp.status_code}."
            else:
                # Safe non-HTTP protocol probe (SSH/Winbox/RDP/RouterOS API): verify TCP socket & optional banner
                conn = asyncio.open_connection(host, port)
                reader, writer = await asyncio.wait_for(conn, timeout=4.0)
                reachable = True
                banner = ""
                try:
                    chunk = await asyncio.wait_for(reader.read(128), timeout=1.0)
                    banner = chunk.decode("utf-8", errors="replace").strip()
                except Exception:
                    pass
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
                verify_status = "PORT_OPEN_SEALED"
                detail_msg = f"TCP port {port}/{proto.upper()} open" + (f" (banner: {banner[:60]})" if banner else "")
        except Exception as exc:
            verify_status = "UNREACHABLE"
            detail_msg = f"Connection failed to {host}:{port}: {type(exc).__name__}"
        finally:
            # Wipe transient secret variables from frame immediately
            del username
            del password

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(SEALED_VAULT_DB_PATH) as db:
            await db.execute(
                "UPDATE mcp_sealed_device_vault SET last_verified_at = ?, last_verify_status = ? WHERE id = ?",
                (now, verify_status, raw["id"]),
            )
            await db.commit()

        return {
            "found": True,
            "vault_id": raw["id"],
            "device_name": raw["device_name"],
            "host": host,
            "port": port,
            "protocol": proto,
            "reachable": reachable,
            "http_status": http_status,
            "verify_status": verify_status,
            "latency_ms": latency_ms,
            "detail": detail_msg,
            "ai_access": "DENIED (Credentials never returned to AI model)",
        }

    @classmethod
    async def intercept_and_seal_message(cls, message: str, actor: str = "chat_user") -> Optional[Dict[str, Any]]:
        """
        Zero-AI-Leak Message Interceptor:
        Detects when a user inputs router/switch/server login credentials in Chat or Telegram,
        immediately seals them into the AES-256-GCM vault BEFORE any LLM prompt or chat history
        storage sees them, and returns a redacted message + vault confirmation receipt.
        """
        text = (message or "").strip()
        if not text:
            return None

        # Form 1: Explicit slash command `/save-router <host> <username> <password> [device_name]`
        slash_m = re.match(
            r"^/save[-_](?:router|device)\s+([A-Za-z0-9.\-_]+)\s+(\S+)\s+(\S+)(?:\s+(.+))?$",
            text,
            flags=re.IGNORECASE,
        )
        if slash_m:
            host, user, pwd, dname = slash_m.groups()
            saved = await cls.save_device_credential(
                device_name=(dname or f"Router ({host})").strip(),
                host=host,
                username=user,
                password=pwd,
                device_type="router",
                created_by=actor,
            )
            return {
                "intercepted": True,
                "saved": saved,
                "redacted_prompt": f"[AI-SEALED CREDENTIAL STORED -> {saved['id']} | {saved['device_name']} ({saved['host']}) | Credentials Redacted]",
            }

        # Form 2: Natural language router/device credential drop containing host/IP + user + pass
        low = text.lower()
        has_device_ctx = any(
            k in low
            for k in (
                "router", "mikrotik", "cisco", "switch", "firewall", "modem", "ont",
                "nas", "gateway", "login", "credential", "রাউটার", "লগইন", "পাসওয়ার্ড", "পাসওয়ার্ড",
            )
        )
        if not has_device_ctx:
            return None

        host_m = re.search(
            r"(?:(?:ip|host|server|router|gateway)\s*[:=]\s*|\b)((?:\d{1,3}\.){3}\d{1,3})\b",
            text,
            flags=re.IGNORECASE,
        )
        user_m = re.search(
            r"(?:username|user|usr)\s*(?:[:=]\s*|\s+(?:is\s+)?)[\"']?([^\s,\"']+)[\"']?",
            text,
            flags=re.IGNORECASE,
        )
        pass_m = re.search(
            r"(?:password|passwd|pwd|secret)\s*(?:[:=]\s*|\s+(?:is\s+)?)[\"']?([^\s,\"']+)[\"']?",
            text,
            flags=re.IGNORECASE,
        )

        if not (host_m and user_m and pass_m):
            return None

        host = host_m.group(1)
        user = user_m.group(1)
        pwd = pass_m.group(1)
        if user.lower() in ("and", "is", "are", "for", "with") or pwd.lower() in ("and", "is", "are", "for", "with"):
            return None

        proto = "https" if "https" in low else ("ssh" if "ssh" in low else ("winbox" if "winbox" in low else "http"))
        port_m = re.search(r"port\s*[:=]\s*(\d{2,5})", text, flags=re.IGNORECASE)
        port = int(port_m.group(1)) if port_m else _default_port_for_protocol(proto)

        saved = await cls.save_device_credential(
            device_name=f"Router ({host})",
            host=host,
            username=user,
            password=pwd,
            device_type="router",
            protocol=proto,
            port=port,
            notes="Captured via Zero-AI-Leak Chat Interceptor",
            created_by=actor,
        )

        redacted_msg = text
        redacted_msg = redacted_msg.replace(pwd, "[AI-SEALED_PASSWORD]")
        redacted_msg = redacted_msg.replace(user, "[AI-SEALED_USER]")
        return {
            "intercepted": True,
            "saved": saved,
            "redacted_prompt": redacted_msg,
        }
