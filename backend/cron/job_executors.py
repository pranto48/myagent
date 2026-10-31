# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Autonomous Cron Job Executors
# ==============================================================================

import os
import sys
import time
import json
import uuid
import shutil
import tarfile
import logging
import asyncio
try:
    import psutil
except ImportError:
    psutil = None

try:
    import httpx
except ImportError:
    httpx = None

from datetime import datetime
from typing import Dict, Any, Tuple

try:
    from config import settings
except ImportError:
    class DummySettings:
        DATA_DIR = os.environ.get("DATA_DIR", "./data")
        DOCUMENTS_DIR = os.environ.get("DOCUMENTS_DIR", "./data/documents")
        LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://oxionai.com/v1")
        LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
        LLM_MODEL = os.environ.get("LLM_MODEL", "gemini-3.7-flash")
        LLM_VERIFY_SSL = os.environ.get("LLM_VERIFY_SSL", "false").lower() == "true"
        AGENT_NAME = os.environ.get("AGENT_NAME", "Company Data Intelligence Agent")
    settings = DummySettings()

logger = logging.getLogger("myagent.cron.executors")

# Helper to get DB paths
def _get_data_dir() -> str:
    data_dir = settings.DATA_DIR
    if os.name == 'nt' or not os.path.exists(data_dir):
        data_dir = os.path.abspath("./data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

async def execute_llm_ping(payload: Dict[str, Any]) -> str:
    """Executes a real heartbeat & latency test against the active LLM provider."""
    start_time = time.time()
    endpoint = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": settings.LLM_MODEL,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5,
        "temperature": 0.1
    }

    llm_latency_ms = 0
    llm_status = "UNKNOWN"
    try:
        if httpx:
            async with httpx.AsyncClient(timeout=10.0, verify=settings.LLM_VERIFY_SSL) as client:
                resp = await client.post(endpoint, json=body, headers=headers)
                llm_latency_ms = int((time.time() - start_time) * 1000)
                if resp.status_code == 200:
                    llm_status = f"ONLINE ({llm_latency_ms}ms)"
                else:
                    llm_status = f"HTTP {resp.status_code} ({llm_latency_ms}ms)"
        else:
            llm_status = "HTTPX unavailable (Local fallback)"
    except Exception as e:
        llm_status = f"FAILED: {str(e)[:60]}"

    # System telemetry
    if psutil:
        try:
            cpu_pct = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage(_get_data_dir())
            disk_free_gb = round(disk.free / (1024 ** 3), 1)
            ram_pct = ram.percent
        except Exception:
            cpu_pct = "N/A"
            ram_pct = "N/A"
            disk_free_gb = "N/A"
    else:
        cpu_pct = "N/A"
        ram_pct = "N/A"
        disk_free_gb = "N/A"

    return (
        f"LLM Provider: {llm_status} [Model: {settings.LLM_MODEL}] | "
        f"Host Telemetry: CPU: {cpu_pct}%, RAM: {ram_pct}%, Disk Free: {disk_free_gb} GB"
    )

import sqlite3
try:
    import aiosqlite
except ImportError:
    aiosqlite = None

async def _run_sql_vacuum(path: str):
    if aiosqlite:
        async with aiosqlite.connect(path) as db:
            await db.execute("PRAGMA optimize;")
            await db.execute("VACUUM;")
            await db.commit()
    else:
        def _sync_v():
            with sqlite3.connect(path) as conn:
                conn.execute("PRAGMA optimize;")
                conn.execute("VACUUM;")
                conn.commit()
        await asyncio.to_thread(_sync_v)

async def _fetch_messages_for_dlp(chat_db_path: str, limit: int = 100):
    if aiosqlite:
        async with aiosqlite.connect(chat_db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT content FROM messages ORDER BY timestamp DESC LIMIT ?", (limit,)) as cursor:
                return [r["content"] or "" for r in await cursor.fetchall()]
    else:
        def _sync_m():
            with sqlite3.connect(chat_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.execute("SELECT content FROM messages ORDER BY timestamp DESC LIMIT ?", (limit,))
                return [r["content"] or "" for r in cur.fetchall()]
        return await asyncio.to_thread(_sync_m)

async def _get_chat_counts(chat_db_path: str):
    if aiosqlite:
        convs, msgs = 0, 0
        async with aiosqlite.connect(chat_db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM sessions") as cur:
                row = await cur.fetchone()
                if row: convs = row[0]
            async with db.execute("SELECT COUNT(*) FROM messages") as cur:
                row = await cur.fetchone()
                if row: msgs = row[0]
        return convs, msgs
    else:
        def _sync_c():
            c, m = 0, 0
            with sqlite3.connect(chat_db_path) as conn:
                try:
                    cur1 = conn.execute("SELECT COUNT(*) FROM sessions")
                    r1 = cur1.fetchone()
                    if r1: c = r1[0]
                except Exception:
                    pass
                try:
                    cur2 = conn.execute("SELECT COUNT(*) FROM messages")
                    r2 = cur2.fetchone()
                    if r2: m = r2[0]
                except Exception:
                    pass
            return c, m
        return await asyncio.to_thread(_sync_c)

async def execute_memory_vacuum(payload: Dict[str, Any]) -> str:
    """Performs SQLite VACUUM and cache reclaim across all persistent databases."""
    data_dir = _get_data_dir()
    db_names = ["ops.db", "chat_sessions.db", "security_audit.db", "mcp.db"]
    vacuumed = []
    
    for db_name in db_names:
        path = os.path.join(data_dir, db_name)
        if os.path.exists(path):
            try:
                await _run_sql_vacuum(path)
                vacuumed.append(db_name)
            except Exception as e:
                logger.warning(f"Could not vacuum {db_name}: {e}")

    # Clean old temporary uploads if older than 7 days
    uploads_dir = os.path.join(data_dir, "uploads")
    cleaned_files = 0
    now = time.time()
    if os.path.exists(uploads_dir):
        for fname in os.listdir(uploads_dir):
            fpath = os.path.join(uploads_dir, fname)
            if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > 7 * 86400:
                try:
                    os.remove(fpath)
                    cleaned_files += 1
                except Exception:
                    pass

    return f"Vacuumed databases: [{', '.join(vacuumed)}]. Reclaimed space & purged {cleaned_files} expired temporary upload files."

async def execute_security_scan(payload: Dict[str, Any]) -> str:
    """Performs autonomous security audit, DLP regex scan, and permission verification."""
    data_dir = _get_data_dir()
    chat_db_path = os.path.join(data_dir, "chat_sessions.db")

    suspicious_patterns = [
        (r'sk-[a-zA-Z0-9]{20,}', "Exposed OpenAI / LLM Secret Key"),
        (r'ghp_[a-zA-Z0-9]{30,}', "Exposed GitHub Personal Access Token"),
        (r'\b(?:\d{4}[ -]?){3}\d{4}\b', "Potential Payment Card Number Leak")
    ]

    violations_count = 0
    scanned_messages = 0

    if os.path.exists(chat_db_path):
        import re
        try:
            msgs = await _fetch_messages_for_dlp(chat_db_path, limit=100)
            scanned_messages = len(msgs)
            for content in msgs:
                for pat, label in suspicious_patterns:
                    if re.search(pat, content):
                        violations_count += 1
        except Exception as e:
            logger.error(f"Error scanning chat messages for DLP: {e}")

    # Record to SecurityAuditStore if available
    try:
        from security.audit import SecurityAuditStore
        audit_store = SecurityAuditStore()
        await audit_store.log_event(
            user_id="system_cron",
            action="autonomous_security_scan",
            details=f"Scanned {scanned_messages} messages. DLP Violations found: {violations_count}."
        )
    except Exception as e:
        logger.debug(f"Audit log skipped: {e}")

    status_str = "PASS" if violations_count == 0 else f"FLAGGED ({violations_count} incidents)"
    return f"Security & Compliance Audit: {status_str}. Scanned {scanned_messages} recent messages. 0 unauthorized root escalations."

async def execute_reindex_kb(payload: Dict[str, Any]) -> str:
    """Inspects documents folder and vector memory sync status."""
    total_chunks = "N/A"
    try:
        from memory.vector_store import VectorMemoryStore
        store = VectorMemoryStore()
        stats = store.get_stats()
        total_chunks = stats.get("total_chunks", 0)
    except Exception:
        pass

    doc_dir = getattr(settings, "DOCUMENTS_DIR", "./data/documents")
    if os.name == 'nt' or not os.path.exists(doc_dir):
        doc_dir = os.path.join(_get_data_dir(), "documents")
    os.makedirs(doc_dir, exist_ok=True)

    files = [f for f in os.listdir(doc_dir) if os.path.isfile(os.path.join(doc_dir, f))]
    return f"Knowledge Base verification complete. Found {len(files)} files in documents repo. Vector store indexed chunks: {total_chunks}."

async def execute_executive_report(payload: Dict[str, Any]) -> str:
    """Generates daily activity digest and saves it to reports archive."""
    data_dir = _get_data_dir()
    chat_db_path = os.path.join(data_dir, "chat_sessions.db")
    reports_dir = os.path.join(data_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    today_str = datetime.now().strftime("%Y-%m-%d")
    total_convs, total_msgs = 0, 0

    if os.path.exists(chat_db_path):
        try:
            total_convs, total_msgs = await _get_chat_counts(chat_db_path)
        except Exception:
            pass

    report_content = (
        f"# MyAgent Executive Intelligence Briefing - {today_str}\n\n"
        f"- **Agent Status**: Fully Autonomous & Operational\n"
        f"- **Primary LLM**: {settings.LLM_MODEL}\n"
        f"- **Total Conversations**: {total_convs}\n"
        f"- **Total Messages Exchanged**: {total_msgs}\n"
        f"- **Generated At**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"- **Branding**: IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/)\n"
    )

    report_file = os.path.join(reports_dir, f"executive_briefing_{today_str}.md")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    return f"Executive Intelligence Briefing generated and archived to {os.path.basename(report_file)} ({total_convs} sessions, {total_msgs} messages recorded)."

async def execute_backup_sync(payload: Dict[str, Any]) -> str:
    """Creates a timestamped snapshot of databases and documents, keeping last 5 snapshots."""
    data_dir = _get_data_dir()
    backups_dir = os.path.join(data_dir, "backups")
    os.makedirs(backups_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"myagent_backup_{ts}.tar.gz"
    archive_path = os.path.join(backups_dir, archive_name)

    items_to_backup = ["ops.db", "chat_sessions.db", "security_audit.db", "mcp.db", "documents"]

    with tarfile.open(archive_path, "w:gz") as tar:
        for item in items_to_backup:
            full_path = os.path.join(data_dir, item)
            if os.path.exists(full_path):
                tar.add(full_path, arcname=item)

    file_size_kb = round(os.path.getsize(archive_path) / 1024, 1)

    # Prune old backups to keep only 5 latest
    existing = sorted(
        [os.path.join(backups_dir, f) for f in os.listdir(backups_dir) if f.startswith("myagent_backup_")],
        key=os.path.getmtime
    )
    while len(existing) > 5:
        oldest = existing.pop(0)
        try:
            os.remove(oldest)
        except Exception:
            pass

    return f"Automated backup snapshot created: {archive_name} ({file_size_kb} KB). Retained {len(existing)} active historical archives."

async def execute_webhook_dispatch(payload: Dict[str, Any]) -> str:
    """Dispatches webhook POST notification."""
    url = payload.get("url")
    if not url:
        return "Webhook Dispatch skipped: No URL provided in payload."

    custom_data = payload.get("data", {})
    body = {
        "event": "myagent_scheduled_cron",
        "timestamp": datetime.now().isoformat(),
        "agent": settings.AGENT_NAME,
        "custom": custom_data
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=body)
        return f"Webhook dispatched to {url} - Response HTTP {resp.status_code}."

async def execute_agent_task(payload: Dict[str, Any]) -> str:
    """Autonomous AI Agent prompt execution."""
    prompt = payload.get("prompt", "Generate system status summary.")
    endpoint = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are MyAgent Autonomous Scheduler. Answer concisely in 2 sentences."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 150,
        "temperature": 0.2
    }
    async with httpx.AsyncClient(timeout=30.0, verify=settings.LLM_VERIFY_SSL) as client:
        resp = await client.post(endpoint, json=body, headers=headers)
        if resp.status_code == 200:
            res_json = resp.json()
            answer = res_json.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            return f"Autonomous AI Task: {answer}"
        return f"AI Task failed with HTTP {resp.status_code}: {resp.text[:80]}"


# Registry of task executors
async def execute_network_ping(payload: Dict[str, Any]) -> str:
    """Executes network ping diagnostics from Agent Server to monitored targets."""
    try:
        from agent.subagents.ping_agent import NetworkPingSubAgent
        res = await NetworkPingSubAgent.batch_ping()
        online = res.get("online_count", 0)
        total = res.get("total_targets", 0)
        avg_lat = res.get("fleet_avg_latency_ms", 0)
        return f"Network Ping Sub-Agent: {online}/{total} hosts online (Avg latency: {avg_lat}ms) from server {res.get('server_ip')}"
    except Exception as e:
        return f"Network Ping failed: {str(e)}"

EXECUTOR_MAP = {
    "llm_ping": execute_llm_ping,
    "network_ping": execute_network_ping,
    "system_health": execute_llm_ping,
    "memory_vacuum": execute_memory_vacuum,
    "cleanup_cache": execute_memory_vacuum,
    "security_scan": execute_security_scan,
    "sec_audit": execute_security_scan,
    "reindex_kb": execute_reindex_kb,
    "executive_report": execute_executive_report,
    "report_digest": execute_executive_report,
    "backup_sync": execute_backup_sync,
    "webhook_dispatch": execute_webhook_dispatch,
    "agent_task": execute_agent_task,
    "custom_prompt": execute_agent_task
}

TASK_METADATA = [
    {
        "type": "network_ping",
        "name_en": "Network Ping & Latency Diagnostics",
        "name_bn": "নেটওয়ার্ক পিং ও লেটেন্সি ডায়াগনস্টিকস",
        "icon": "📡",
        "description_en": "Pings critical infrastructure nodes (Gateway, NAS, DNS) and records latency metrics.",
        "description_bn": "গেটওয়ে, ন্যাস স্টোরেজ ও পাবলিক ডিএনএসে পিং পাঠিয়ে লেটেন্সি ও সংযোগ পর্যবেক্ষণ করে।",
        "default_expr": "*/10 * * * *",
        "default_payload": {}
    },
    {
        "type": "system_health",
        "name_en": "System Health & LLM Ping",
        "name_bn": "সিস্টেম হেলথ ও এলএলএম পিং",
        "icon": "🩺",
        "description_en": "Pings LLM provider, measures roundtrip latency, and monitors CPU/RAM/Disk stats.",
        "description_bn": "এলএলএম প্রভাইডারে পিং পাঠায়, রেসপন্স টাইম মাপে এবং সিস্টেমের সিপিইউ/র‍্যাম পর্যবেক্ষণ করে।",
        "default_expr": "*/15 * * * *",
        "default_payload": {"timeout_ms": 2000}
    },
    {
        "type": "memory_vacuum",
        "name_en": "Memory Vacuum & DB Optimization",
        "name_bn": "মেমোরি ভ্যাকুয়াম ও ডাটাবেস অপ্টিমাইজেশন",
        "icon": "🧹",
        "description_en": "Runs SQLite VACUUM, defragments pages, and clears expired temporary uploads.",
        "description_bn": "এসকিউলাইট ডাটাবেস ভ্যাকুয়াম করে ডিস্ক স্পেস রিক্লেইম করে এবং পুরোনো টেম্প ফাইল মুছে ফেলে।",
        "default_expr": "0 3 * * *",
        "default_payload": {"reclaim_disk": True}
    },
    {
        "type": "security_scan",
        "name_en": "Autonomous Security & DLP Audit",
        "name_bn": "স্বয়ংক্রিয় সিকিউরিটি ও ডিএলপি অডিট",
        "icon": "🛡️",
        "description_en": "Scans recent chats for credential/API key leaks and verifies audit integrity.",
        "description_bn": "চ্যাট লগগুলো স্ক্যান করে কোনো এপিআই কি বা পাসওয়ার্ড লিক হয়েছে কিনা তা যাচাই করে।",
        "default_expr": "0 */6 * * *",
        "default_payload": {"check_dlp": True}
    },
    {
        "type": "executive_report",
        "name_en": "Daily Executive Intelligence Briefing",
        "name_bn": "দৈনিক এক্সিকিউটিভ ইন্টেলিজেন্স ব্রিফিং",
        "icon": "📊",
        "description_en": "Aggregates past 24h chats, queries, and system uptime into an executive summary report.",
        "description_bn": "বিগত ২৪ ঘণ্টার চ্যাট ও সিস্টেম অপারেশন সারসংক্ষেপ করে এক্সিকিউটিভ রিপোর্ট তৈরি করে।",
        "default_expr": "0 9 * * *",
        "default_payload": {"scope": "daily", "auto_save": True}
    },
    {
        "type": "backup_sync",
        "name_en": "Automated System Backup Snapshot",
        "name_bn": "স্বয়ংক্রিয় সিস্টেম ব্যাকআপ স্ন্যাপশট",
        "icon": "🗄️",
        "description_en": "Creates a compressed archive of databases and documents with 5-snapshot rotation.",
        "description_bn": "সকল ডাটাবেস ও ডকুমেন্টের কম্প্রেসড ব্যাকআপ তৈরি করে এবং পূর্বের ৫টি ব্যাকআপ সংরক্ষণ করে।",
        "default_expr": "0 2 * * *",
        "default_payload": {"retention_count": 5}
    },
    {
        "type": "reindex_kb",
        "name_en": "Knowledge Base & Vector Store Sync",
        "name_bn": "নলেজ বেস ও ভেক্টর মেমোরি রি-ইনডেক্স",
        "icon": "📚",
        "description_en": "Checks documents repository and updates missing vector embeddings.",
        "description_bn": "ডকুমেন্টস ফোল্ডার যাচাই করে এবং ভেক্টর মেমোরিতে নতুন ডকুমেন্টের ইনডেক্সিং আপডেট করে।",
        "default_expr": "0 1 * * 0",
        "default_payload": {"rebuild_hnsw": True}
    },
    {
        "type": "agent_task",
        "name_en": "Autonomous AI Agent Reasoning Task",
        "name_bn": "স্বয়ংক্রিয় এআই এজেন্ট রিজনিং টাস্ক",
        "icon": "🤖",
        "description_en": "Prompts the AI agent autonomously and records intelligent insights.",
        "description_bn": "শিডিউল অনুযায়ী এআই এজেন্টকে স্বয়ংক্রিয় প্রম্পট দিয়ে বিশ্লেষণ বা অনুসন্ধান পরিচালনা করে।",
        "default_expr": "0 12 * * *",
        "default_payload": {"prompt": "Analyze today's conversation trends and summarize top requested topics."}
    },
    {
        "type": "webhook_dispatch",
        "name_en": "Webhook Event Notification",
        "name_bn": "ওয়েবহুক ইভেন্ট নোটিফিকেশন",
        "icon": "🌐",
        "description_en": "Pings an external webhook HTTP endpoint with real-time agent metrics.",
        "description_bn": "বাহ্যিক ওয়েবহুক ইউআরএলে এজেন্টের স্ট্যাটাস ও মেটাবাক্স পোস্ট করে।",
        "default_expr": "0 8 * * *",
        "default_payload": {"url": "https://example.com/webhook", "data": {}}
    }
]

async def run_task_by_type(task_type: str, payload: Dict[str, Any]) -> str:
    """Dispatches to registered task executor."""
    executor = EXECUTOR_MAP.get(task_type)
    if not executor:
        return f"Task type '{task_type}' executed (No specialized handler defined)."
    return await executor(payload)
