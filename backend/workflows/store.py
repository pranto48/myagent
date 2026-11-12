# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 3.3.0
# Workflow Graph Store & Pre-Built Daily Automation Templates
# ==============================================================================

import os
import json
import uuid
import time
import logging
from datetime import datetime, timedelta, timezone, tzinfo
from typing import Dict, Any, List, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

try:
    import aiosqlite
except ImportError:
    aiosqlite = None

try:
    from config import settings
except ImportError:
    class _FallbackSettings:
        DATA_DIR = os.environ.get("DATA_DIR", "./data")
        LLM_MODEL = os.environ.get("LLM_MODEL", "gemini-3.7-flash")
    settings = _FallbackSettings()

from cron.cron_parser import CronExpression

logger = logging.getLogger("myagent.workflows.store")

STATIC_TZ_OFFSETS = {
    "Asia/Dhaka": timedelta(hours=6),
    "Asia/Kolkata": timedelta(hours=5, minutes=30),
    "Asia/Dubai": timedelta(hours=4),
    "Asia/Singapore": timedelta(hours=8),
    "Asia/Tokyo": timedelta(hours=9),
    "UTC": timedelta(hours=0),
    "Europe/London": timedelta(hours=0),
    "America/New_York": timedelta(hours=-5),
}


def _get_tzinfo(tz_name: str = "Asia/Dhaka") -> tzinfo:
    tz_clean = (tz_name or "Asia/Dhaka").strip()
    if ZoneInfo is not None:
        try:
            return ZoneInfo(tz_clean)
        except Exception:
            pass
    offset = STATIC_TZ_OFFSETS.get(tz_clean, timedelta(hours=6))
    return timezone(offset)


def _get_ops_db_path() -> str:
    if os.name == "nt" or not os.path.exists(settings.DATA_DIR):
        os.makedirs("./data", exist_ok=True)
        return os.path.join("./data", "ops.db")
    return os.path.join(settings.DATA_DIR, "ops.db")


def daily_time_to_cron(daily_time: str = "09:00", frequency: str = "daily", weekday: int = 0) -> str:
    """Converts HH:MM & frequency ('daily', 'hourly', 'every_6h', 'weekly', 'every_15m') to 5-field cron."""
    hh, mm = 9, 0
    try:
        parts = (daily_time or "09:00").strip().split(":")
        hh = max(0, min(23, int(parts[0])))
        mm = max(0, min(59, int(parts[1]))) if len(parts) > 1 else 0
    except Exception:
        hh, mm = 9, 0

    freq = (frequency or "daily").lower().strip()
    if freq == "every_15m":
        return "*/15 * * * *"
    if freq == "hourly":
        return f"{mm} * * * *"
    if freq == "every_6h":
        return f"{mm} */6 * * *"
    if freq == "weekly":
        wd = max(0, min(6, int(weekday)))
        return f"{mm} {hh} * * {wd}"
    return f"{mm} {hh} * * *"


def compute_next_run(
    schedule_expr: Optional[str],
    tz_name: str = "Asia/Dhaka",
    trigger_type: str = "daily"
) -> Tuple[Optional[str], Optional[float], str, str]:
    """
    Computes next run timestamp in target timezone AND UTC epoch timestamp for scheduler accuracy.
    Returns (next_run_local_str, next_run_utc_ts, human_en, human_bn).
    """
    ttype = (trigger_type or "daily").lower().strip()
    if ttype in ("manual", "webhook"):
        label_en = "Webhook HTTP Trigger" if ttype == "webhook" else "Manual / MCP Trigger"
        label_bn = "ওয়েবহুক HTTP ট্রিগার" if ttype == "webhook" else "ম্যানুয়াল / MCP ট্রিগার"
        return None, None, label_en, label_bn

    expr = (schedule_expr or "0 9 * * *").strip()
    try:
        cron = CronExpression(expr)
        tz = _get_tzinfo(tz_name)
        now_in_tz = datetime.now(tz).replace(tzinfo=None)
        next_local_naive = cron.get_next_run(now_in_tz)
        next_aware = next_local_naive.replace(tzinfo=tz)
        next_utc_ts = next_aware.timestamp()
        return (
            next_local_naive.strftime("%Y-%m-%d %H:%M:%S"),
            next_utc_ts,
            cron.to_human_en(),
            cron.to_human_bn()
        )
    except Exception as e:
        logger.warning(f"Cron calculation failed for '{expr}': {e}")
        return None, None, expr, expr


def compute_upcoming_runs(
    schedule_expr: Optional[str],
    tz_name: str = "Asia/Dhaka",
    trigger_type: str = "daily",
    count: int = 3
) -> List[str]:
    """Returns upcoming N local run timestamps formatted as YYYY-MM-DD HH:MM."""
    ttype = (trigger_type or "daily").lower().strip()
    if ttype in ("manual", "webhook") or not schedule_expr:
        return []
    try:
        cron = CronExpression(schedule_expr.strip())
        tz = _get_tzinfo(tz_name)
        now_in_tz = datetime.now(tz).replace(tzinfo=None)
        return [dt.strftime("%Y-%m-%d %H:%M") for dt in cron.get_next_runs(count=count, base_time=now_in_tz)]
    except Exception:
        return []


# ==============================================================================
# Node Types Metadata Catalog for Visual Studio Palette
# ==============================================================================
NODE_CATALOG: List[Dict[str, Any]] = [
    {
        "type": "trigger_daily",
        "category": "trigger",
        "icon": "⏰",
        "label_en": "Daily Schedule Trigger",
        "label_bn": "দৈনিক শিডিউল ট্রিগার",
        "color": "#06b6d4",
        "default_config": {"daily_time": "09:00", "timezone": "Asia/Dhaka", "frequency": "daily"}
    },
    {
        "type": "trigger_webhook",
        "category": "trigger",
        "icon": "🌐",
        "label_en": "Webhook Trigger",
        "label_bn": "ওয়েবহুক ট্রিগার",
        "color": "#0ea5e9",
        "default_config": {"method": "POST"}
    },
    {
        "type": "ai_agent",
        "category": "ai",
        "icon": "🧠",
        "label_en": "AI Autonomous Agent",
        "label_bn": "অটোনোমাস এআই এজেন্ট",
        "color": "#a855f7",
        "default_config": {
            "prompt": "Analyze the incoming data and generate an actionable summary:\n{{prev.output}}",
            "system_instruction": "You are an autonomous corporate AI workflow agent. Use tools if live inspection is needed.",
            "model": "",
            "project_name": "",
            "use_memory": True,
            "enable_tools": True,
            "use_mcp": True,
            "fallback_on_error": True,
            "language": "bn",
            "max_turns": 5
        }
    },
    {
        "type": "subagent",
        "category": "ai",
        "icon": "🤖",
        "label_en": "Sub-Agent / Swarm",
        "label_bn": "সাব-এজেন্ট / সোয়ার্ম",
        "color": "#8b5cf6",
        "default_config": {
            "agent_id": "net_ping_subagent",
            "task": "Run diagnostics and summarize findings. Context: {{prev.output}}",
            "model": ""
        }
    },
    {
        "type": "tool_call",
        "category": "action",
        "icon": "🛠️",
        "label_en": "Execute Agent Tool",
        "label_bn": "টুল এক্সিকিউট করুন",
        "color": "#3b82f6",
        "default_config": {
            "tool_name": "system_info",
            "args_json": "{}"
        }
    },
    {
        "type": "mcp_tool",
        "category": "action",
        "icon": "🔌",
        "label_en": "MCP Tool Call",
        "label_bn": "MCP টুল কল (External/Hub)",
        "color": "#6366f1",
        "default_config": {
            "server_id": "",
            "tool_name": "fetch_article_markdown",
            "args_json": "{\"url\": \"https://example.com\"}",
            "fallback_on_error": False
        }
    },
    {
        "type": "python_transform",
        "category": "action",
        "icon": "🐍",
        "label_en": "Python Data Transform",
        "label_bn": "পাইথন ডেটা ট্রান্সফর্ম",
        "color": "#eab308",
        "default_config": {
            "code": "import json\n# Available vars: prev_output, nodes_data, trigger\ntext = str(prev_output or '')\nlines = [l for l in text.splitlines() if l.strip()]\nprint(f'Processed {len(lines)} lines from upstream on {trigger.get(\"date\", \"\")}.')\nprint(text[:1500])"
        }
    },
    {
        "type": "loop_foreach",
        "category": "logic",
        "icon": "🔁",
        "label_en": "ForEach Batch Loop",
        "label_bn": "ব্যাচ লুপ (ForEach)",
        "color": "#6366f1",
        "default_config": {
            "items_text": "192.168.9.1\n192.168.9.5\n192.168.9.9\n8.8.8.8",
            "action_type": "ping",
            "tool_name": "network_port_scan",
            "args_template_json": "{\"target\": \"{{item}}\", \"ports\": [80, 443, 3399]}",
            "http_url": "https://httpbin.org/get?item={{item}}",
            "http_method": "GET"
        }
    },
    {
        "type": "delay_wait",
        "category": "logic",
        "icon": "⏳",
        "label_en": "Delay / Wait Timer",
        "label_bn": "সময় অপেক্ষা (Wait)",
        "color": "#64748b",
        "default_config": {
            "seconds": 3
        }
    },
    {
        "type": "condition",
        "category": "logic",
        "icon": "🔀",
        "label_en": "IF / Else Condition",
        "label_bn": "শর্ত (IF / Else)",
        "color": "#f59e0b",
        "default_config": {
            "target": "{{prev.output}}",
            "operator": "contains",
            "value": "ERROR"
        }
    },
    {
        "type": "http_request",
        "category": "action",
        "icon": "📡",
        "label_en": "HTTP Request",
        "label_bn": "HTTP রিকোয়েস্ট",
        "color": "#0284c7",
        "default_config": {
            "method": "POST",
            "url": "https://httpbin.org/post",
            "headers_json": "{\"Content-Type\": \"application/json\"}",
            "body_json": "{\"workflow\": \"{{workflow.name}}\", \"output\": \"{{prev.output}}\"}"
        }
    },
    {
        "type": "save_report",
        "category": "output",
        "icon": "📄",
        "label_en": "Save Executive Report",
        "label_bn": "AI রিপোর্ট সেভ করুন",
        "color": "#10b981",
        "default_config": {
            "title": "{{workflow.name}} - {{trigger.date}}",
            "report_type": "executive_summary",
            "content": "{{prev.output}}",
            "index_in_memory": True
        }
    },
    {
        "type": "memory_save",
        "category": "output",
        "icon": "💾",
        "label_en": "Save Project Memory",
        "label_bn": "প্রজেক্ট মেমোরিতে সেভ",
        "color": "#14b8a6",
        "default_config": {
            "project_name": "myagent",
            "key": "daily_log_{{trigger.date}}",
            "category": "notes",
            "context": "production",
            "content": "{{prev.output}}",
            "save_to_vector": True
        }
    },
    {
        "type": "notify_channel",
        "category": "output",
        "icon": "📣",
        "label_en": "Notify / Post Digest",
        "label_bn": "চ্যাট ও চ্যানেল নোটিফাই",
        "color": "#ec4899",
        "default_config": {
            "target": "chat_and_channels",
            "session_title": "📅 Daily Automated Agent Reports",
            "title": "⚡ {{workflow.name}} ({{trigger.date}})",
            "message": "{{prev.output}}",
            "custom_webhook_url": "",
            "telegram_chat_id": "",
            "parse_mode": ""
        }
    },
    {
        "type": "merge_combine",
        "category": "logic",
        "icon": "🤝",
        "label_en": "Merge Branches",
        "label_bn": "ব্রাঞ্চ মার্জ (Join)",
        "color": "#14b8a6",
        "default_config": {
            "mode": "markdown_sections",
            "include_empty": False
        }
    },
    {
        "type": "switch_router",
        "category": "logic",
        "icon": "🚦",
        "label_en": "Multi-Way Switch Router",
        "label_bn": "সুইচ রাউটার (৩+ শাখা)",
        "color": "#f97316",
        "default_config": {
            "target": "{{prev.output}}",
            "route1_op": "regex",
            "route1_val": "(CRITICAL|DOWN|100% LOSS|FATAL)",
            "route2_op": "regex",
            "route2_val": "(WARNING|ERROR|SLOW|FAILED)"
        }
    },
    {
        "type": "sub_workflow",
        "category": "action",
        "icon": "🔗",
        "label_en": "Call Sub-Workflow",
        "label_bn": "সাব-ওয়ার্কফ্লো কল করুন",
        "color": "#8b5cf6",
        "default_config": {
            "target_workflow_id": "",
            "payload_json": "{\"upstream\": \"{{prev.output|400}}\"}"
        }
    },
    {
        "type": "knowledge_db_query",
        "category": "action",
        "icon": "🗄️",
        "label_en": "DB SQL & RAG Query",
        "label_bn": "SQLite ও নলেজ সার্চ",
        "color": "#0ea5e9",
        "default_config": {
            "query_mode": "sqlite",
            "db_name": "ops.db",
            "sql_query": "SELECT id, name, last_status, run_count, last_run FROM ops_workflows ORDER BY updated_at DESC LIMIT 10;",
            "rag_query": "daily workflow reports & policies",
            "top_k": 5
        }
    }
]


# ==============================================================================
# Pre-built Production n8n Workflow Templates
# ==============================================================================
WORKFLOW_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "tpl_daily_morning_brief",
        "name": "🌅 দৈনিক সকালের এআই এক্সিকিউটিভ ব্রিফিং ও হেলথ অডিট",
        "description": "প্রতিদিন সকাল ৯:০০টায় স্বয়ংক্রিয়ভাবে সার্ভার পিং, সিস্টেম রিসোর্স চেক, এআই বিশ্লেষণ, কন্ডিশনাল অ্যালার্ট এবং রিপোর্ট ও চ্যাট ডাইজেস্ট তৈরি করে।",
        "icon": "🌅",
        "trigger_type": "daily",
        "schedule_expr": "0 9 * * *",
        "daily_time": "09:00",
        "timezone": "Asia/Dhaka",
        "is_enabled": 1,
        "nodes": [
            {
                "id": "node_1",
                "type": "trigger_daily",
                "title": "দৈনিক সকাল ৯:০০ ট্রিগার",
                "x": 50,
                "y": 150,
                "config": {"daily_time": "09:00", "timezone": "Asia/Dhaka", "frequency": "daily"}
            },
            {
                "id": "node_2",
                "type": "tool_call",
                "title": "সার্ভার রিসোর্স ও হেলথ চেক",
                "x": 320,
                "y": 150,
                "config": {"tool_name": "system_info", "args_json": "{}"}
            },
            {
                "id": "node_3",
                "type": "subagent",
                "title": "নেটওয়ার্ক পিং সাব-এজেন্ট",
                "x": 590,
                "y": 150,
                "config": {
                    "agent_id": "net_ping_subagent",
                    "task": "Run network latency check across all active LAN and DNS targets and report status.",
                    "model": ""
                }
            },
            {
                "id": "node_4",
                "type": "ai_agent",
                "title": "এআই অটোনোমাস ব্রিফিং এনালিস্ট",
                "x": 860,
                "y": 150,
                "config": {
                    "prompt": (
                        "আজকের তারিখ: {{trigger.date}}। নিচের সার্ভার ও নেটওয়ার্ক টেলিমেট্রি এবং কোম্পানি মেমোরি পর্যালোচনা করে একটি সংক্ষিপ্ত দৈনিক এক্সিকিউটিভ ব্রিফিং তৈরি করুন:\n\n"
                        "1. সিস্টেম ইনফো:\n{{nodes.node_2.output}}\n\n"
                        "2. নেটওয়ার্ক পিং রিপোর্ট:\n{{nodes.node_3.output}}\n\n"
                        "সমস্যা থাকলে WARNING বা CRITICAL চিহ্নিত করুন, নাহলে ALL SYSTEMS HEALTHY লিখুন।"
                    ),
                    "system_instruction": "You are the Daily Morning Operations Briefing Agent. Analyze telemetry cleanly and check project memory if helpful.",
                    "model": "",
                    "project_name": "myagent",
                    "use_memory": True,
                    "enable_tools": True,
                    "fallback_on_error": True,
                    "language": "bn",
                    "max_turns": 4
                }
            },
            {
                "id": "node_5",
                "type": "condition",
                "title": "সমস্যা আছে কি না? (IF Alert)",
                "x": 1130,
                "y": 150,
                "config": {
                    "target": "{{prev.output}}",
                    "operator": "regex",
                    "value": "(OFFLINE|CRITICAL|FAILED|ERROR|WARNING)"
                }
            },
            {
                "id": "node_6",
                "type": "notify_channel",
                "title": "অ্যালার্ট চ্যানেল নোটিফিকেশন",
                "x": 1410,
                "y": 60,
                "config": {
                    "target": "chat_and_channels",
                    "session_title": "📅 Daily Automated Agent Reports",
                    "title": "🚨 ALERT: {{workflow.name}} ({{trigger.date}})",
                    "message": "{{nodes.node_4.output}}",
                    "custom_webhook_url": ""
                }
            },
            {
                "id": "node_7",
                "type": "save_report",
                "title": "দৈনিক রিপোর্ট আর্কাইভ",
                "x": 1410,
                "y": 250,
                "config": {
                    "title": "দৈনিক হেলথ ও ব্রিফিং রিপোর্ট - {{trigger.date}}",
                    "report_type": "executive_summary",
                    "content": "{{nodes.node_4.output}}",
                    "index_in_memory": True
                }
            },
            {
                "id": "node_8",
                "type": "notify_channel",
                "title": "চ্যাট ডাইজেস্ট পাঠান",
                "x": 1680,
                "y": 250,
                "config": {
                    "target": "chat_session",
                    "session_title": "📅 Daily Automated Agent Reports",
                    "title": "✅ {{workflow.name}} ({{trigger.date}})",
                    "message": "{{nodes.node_4.output}}",
                    "custom_webhook_url": ""
                }
            }
        ],
        "edges": [
            {"id": "e1", "source": "node_1", "target": "node_2", "condition": ""},
            {"id": "e2", "source": "node_2", "target": "node_3", "condition": ""},
            {"id": "e3", "source": "node_3", "target": "node_4", "condition": ""},
            {"id": "e4", "source": "node_4", "target": "node_5", "condition": ""},
            {"id": "e5", "source": "node_5", "target": "node_6", "condition": "true"},
            {"id": "e6", "source": "node_5", "target": "node_7", "condition": "false"},
            {"id": "e7", "source": "node_7", "target": "node_8", "condition": ""}
        ]
    },
    {
        "id": "tpl_daily_security_audit",
        "name": "🛡️ দৈনিক সিকিউরিটি, পোর্ট স্ক্যান ও DLP অডিট",
        "description": "প্রতিদিন রাত ৩:০০টায় সার্ভার পোর্ট স্ক্যান করে, সিকিউরিটি অডিটর সাব-এজেন্ট চালায় এবং কমপ্লায়েন্স রিপোর্ট সংরক্ষণ করে।",
        "icon": "🛡️",
        "trigger_type": "daily",
        "schedule_expr": "0 3 * * *",
        "daily_time": "03:00",
        "timezone": "Asia/Dhaka",
        "is_enabled": 1,
        "nodes": [
            {
                "id": "node_1",
                "type": "trigger_daily",
                "title": "রাত ৩:০০ দৈনিক অডিট",
                "x": 60,
                "y": 140,
                "config": {"daily_time": "03:00", "timezone": "Asia/Dhaka", "frequency": "daily"}
            },
            {
                "id": "node_2",
                "type": "tool_call",
                "title": "TCP পোর্ট স্ক্যানার (192.168.9.9)",
                "x": 350,
                "y": 140,
                "config": {
                    "tool_name": "network_port_scan",
                    "args_json": "{\"target\": \"127.0.0.1\", \"ports\": [80, 443, 8000, 3399, 22]}"
                }
            },
            {
                "id": "node_3",
                "type": "subagent",
                "title": "সিকিউরিটি ও DLP সাব-এজেন্ট",
                "x": 640,
                "y": 140,
                "config": {
                    "agent_id": "security_auditor_agent",
                    "task": "Review DLP compliance and inspect port scan findings: {{nodes.node_2.output}}",
                    "model": ""
                }
            },
            {
                "id": "node_4",
                "type": "ai_agent",
                "title": "সিকিউরিটি কমপ্লায়েন্স বিশ্লেষক",
                "x": 930,
                "y": 140,
                "config": {
                    "prompt": "নিচের পোর্ট স্ক্যান ও DLP অডিট ফলাফল থেকে দৈনিক সিকিউরিটি রিপোর্ট তৈরি করুন:\n\nপোর্ট স্ক্যান:\n{{nodes.node_2.output}}\n\nDLP অডিট:\n{{nodes.node_3.output}}",
                    "system_instruction": "Analyze security posture concisely with risk rating and recommendations.",
                    "model": "",
                    "project_name": "myagent",
                    "use_memory": False,
                    "enable_tools": False,
                    "fallback_on_error": True,
                    "language": "bn",
                    "max_turns": 3
                }
            },
            {
                "id": "node_5",
                "type": "save_report",
                "title": "সিকিউরিটি রিপোর্ট সেভ",
                "x": 1220,
                "y": 140,
                "config": {
                    "title": "দৈনিক সিকিউরিটি অডিট - {{trigger.date}}",
                    "report_type": "incident_report",
                    "content": "{{prev.output}}",
                    "index_in_memory": True
                }
            }
        ],
        "edges": [
            {"id": "e1", "source": "node_1", "target": "node_2", "condition": ""},
            {"id": "e2", "source": "node_2", "target": "node_3", "condition": ""},
            {"id": "e3", "source": "node_3", "target": "node_4", "condition": ""},
            {"id": "e4", "source": "node_4", "target": "node_5", "condition": ""}
        ]
    },
    {
        "id": "tpl_daily_custom_ai_task",
        "name": "🤖 দৈনিক কাস্টম এআই রিসার্চ ও প্রজেক্ট নোট এজেন্ট",
        "description": "প্রতিদিন নির্দিষ্ট সময়ে আপনার নির্ধারিত নির্দেশনা অনুযায়ী এআই এজেন্ট কাজ করবে, টুল ব্যবহার করবে ও ফলাফল মেমোরি ও চ্যাটে সেভ করবে।",
        "icon": "🤖",
        "trigger_type": "daily",
        "schedule_expr": "0 10 * * *",
        "daily_time": "10:00",
        "timezone": "Asia/Dhaka",
        "is_enabled": 0,
        "nodes": [
            {
                "id": "node_1",
                "type": "trigger_daily",
                "title": "সকাল ১০:০০ দৈনিক ট্রিগার",
                "x": 60,
                "y": 140,
                "config": {"daily_time": "10:00", "timezone": "Asia/Dhaka", "frequency": "daily"}
            },
            {
                "id": "node_2",
                "type": "ai_agent",
                "title": "অটোনোমাস এআই ওয়ার্কার",
                "x": 360,
                "y": 140,
                "config": {
                    "prompt": "আজকের ({{trigger.date}}) সিস্টেম ডাটাবেস স্ট্যাটাস এবং সংরক্ষিত প্রজেক্ট তথ্য রিভিউ করে একটি কার্যকর অ্যাকশন লিস্ট তৈরি করুন।",
                    "system_instruction": "Check sqlite_schema_inspector or project memory tools first, then produce clear daily action items.",
                    "model": "",
                    "project_name": "myagent",
                    "use_memory": True,
                    "enable_tools": True,
                    "fallback_on_error": True,
                    "language": "bn",
                    "max_turns": 5
                }
            },
            {
                "id": "node_3",
                "type": "memory_save",
                "title": "প্রজেক্ট মেমোরি আপডেট",
                "x": 670,
                "y": 140,
                "config": {
                    "project_name": "myagent",
                    "key": "daily_brief_{{trigger.date}}",
                    "category": "notes",
                    "context": "production",
                    "content": "{{prev.output}}",
                    "save_to_vector": True
                }
            },
            {
                "id": "node_4",
                "type": "notify_channel",
                "title": "চ্যাট ডাইজেস্টে পাঠান",
                "x": 980,
                "y": 140,
                "config": {
                    "target": "chat_session",
                    "session_title": "📅 Daily Automated Agent Reports",
                    "title": "🤖 {{workflow.name}} ({{trigger.date}})",
                    "message": "{{nodes.node_2.output}}",
                    "custom_webhook_url": ""
                }
            }
        ],
        "edges": [
            {"id": "e1", "source": "node_1", "target": "node_2", "condition": ""},
            {"id": "e2", "source": "node_2", "target": "node_3", "condition": ""},
            {"id": "e3", "source": "node_3", "target": "node_4", "condition": ""}
        ]
    },
    {
        "id": "tpl_webhook_ai_pipeline",
        "name": "🌐 ওয়েবহুক ট্রিগার্ড অটো এআই প্রসেসর",
        "description": "যেকোনো বাহ্যিক অ্যাপ/স্ক্রিপ্ট থেকে Webhook POST পেলে স্বয়ংক্রিয়ভাবে এআই দিয়ে বিশ্লেষণ করে মেমোরি ও চ্যাটে সেভ করে।",
        "icon": "🌐",
        "trigger_type": "webhook",
        "schedule_expr": "",
        "daily_time": "",
        "timezone": "Asia/Dhaka",
        "is_enabled": 1,
        "nodes": [
            {
                "id": "node_1",
                "type": "trigger_webhook",
                "title": "ইনবাউন্ড ওয়েবহুক রিসিভার",
                "x": 60,
                "y": 140,
                "config": {"method": "POST"}
            },
            {
                "id": "node_2",
                "type": "ai_agent",
                "title": "এআই পেলোড প্রসেসর",
                "x": 370,
                "y": 140,
                "config": {
                    "prompt": "Webhook থেকে প্রাপ্ত নিচের ইভেন্ট/ডেটা বিশ্লেষণ করে সারসংক্ষেপ ও পরবর্তী করণীয় দিন:\n\n{{trigger.payload}}",
                    "system_instruction": "Process incoming webhook events accurately and highlight action items.",
                    "model": "",
                    "project_name": "",
                    "use_memory": True,
                    "enable_tools": True,
                    "fallback_on_error": True,
                    "language": "bn",
                    "max_turns": 4
                }
            },
            {
                "id": "node_3",
                "type": "memory_save",
                "title": "মেমোরিতে সংরক্ষণ",
                "x": 680,
                "y": 140,
                "config": {
                    "project_name": "myagent",
                    "key": "webhook_event_{{trigger.date}}_{{trigger.time}}",
                    "category": "notes",
                    "context": "production",
                    "content": "{{prev.output}}",
                    "save_to_vector": True
                }
            },
            {
                "id": "node_4",
                "type": "notify_channel",
                "title": "চ্যাট ও চ্যানেল নোটিফাই",
                "x": 990,
                "y": 140,
                "config": {
                    "target": "chat_and_channels",
                    "session_title": "📅 Daily Automated Agent Reports",
                    "title": "🌐 Webhook Processed: {{workflow.name}}",
                    "message": "{{nodes.node_2.output}}",
                    "custom_webhook_url": ""
                }
            }
        ],
        "edges": [
            {"id": "e1", "source": "node_1", "target": "node_2", "condition": ""},
            {"id": "e2", "source": "node_2", "target": "node_3", "condition": ""},
            {"id": "e3", "source": "node_3", "target": "node_4", "condition": ""}
        ]
    },
    {
        "id": "tpl_fleet_batch_health_python",
        "name": "🔁 দৈনিক ফ্লিট ব্যাচ পিং ও পাইথন হেলথ স্কোর",
        "description": "প্রতিদিন সকালে সকল সার্ভার আইপিতে ForEach ব্যাচ পিং চালিয়ে Python স্ক্রিপ্টে আপটাইম স্কোর গণনা করে ও সমস্যা হলে সাথে সাথে সতর্ক করে।",
        "icon": "🔁",
        "trigger_type": "daily",
        "schedule_expr": "30 8 * * *",
        "daily_time": "08:30",
        "timezone": "Asia/Dhaka",
        "is_enabled": 0,
        "nodes": [
            {
                "id": "node_1",
                "type": "trigger_daily",
                "title": "সকাল ৮:৩০ ডেইলি ট্রিগার",
                "x": 40,
                "y": 150,
                "config": {"daily_time": "08:30", "timezone": "Asia/Dhaka", "frequency": "daily"}
            },
            {
                "id": "node_2",
                "type": "loop_foreach",
                "title": "ফ্লিট সার্ভার ব্যাচ পিং",
                "x": 320,
                "y": 150,
                "config": {
                    "items_text": "192.168.9.1\n192.168.9.5\n192.168.9.9\n8.8.8.8",
                    "action_type": "ping",
                    "tool_name": "network_port_scan",
                    "args_template_json": "{\"target\": \"{{item}}\"}"
                }
            },
            {
                "id": "node_3",
                "type": "python_transform",
                "title": "Python স্কোর ও রিপোর্ট টেবিল",
                "x": 610,
                "y": 150,
                "config": {
                    "code": "raw = str(prev_output or '')\nlines = [l for l in raw.splitlines() if l.strip()]\nok_cnt = sum(1 for l in lines if 'SUCCESS' in l.upper() or 'ONLINE' in l.upper() or 'TTL=' in l.upper() or 'LOSS=0' in l.upper() or 'MS' in l.upper())\nfail_cnt = sum(1 for l in lines if 'ERROR' in l.upper() or 'FAIL' in l.upper() or 'TIMEOUT' in l.upper() or '100% LOSS' in l.upper())\nstatus_tag = 'ALERT_NEEDED' if fail_cnt > 0 else 'ALL_HEALTHY'\nprint(f'### Fleet Batch Health ({status_tag})')\nprint(f'- Healthy signals: {ok_cnt} | Warnings/Failures: {fail_cnt}')\nprint('\\n' + raw[:2000])"
                }
            },
            {
                "id": "node_4",
                "type": "condition",
                "title": "অ্যালার্ট প্রয়োজন কি না?",
                "x": 900,
                "y": 150,
                "config": {"target": "{{prev.output}}", "operator": "contains", "value": "ALERT_NEEDED"}
            },
            {
                "id": "node_5",
                "type": "notify_channel",
                "title": "🚨 সার্ভার ডাউন অ্যালার্ট",
                "x": 1190,
                "y": 60,
                "config": {
                    "target": "chat_and_channels",
                    "session_title": "📅 Daily Automated Agent Reports",
                    "title": "🚨 Fleet Alert ({{trigger.date}})",
                    "message": "{{nodes.node_3.output}}",
                    "custom_webhook_url": ""
                }
            },
            {
                "id": "node_6",
                "type": "save_report",
                "title": "📄 দৈনিক ফ্লিট রিপোর্ট সেভ",
                "x": 1190,
                "y": 245,
                "config": {
                    "title": "দৈনিক সার্ভার ফ্লিট হেলথ - {{trigger.date}}",
                    "report_type": "executive_summary",
                    "content": "{{nodes.node_3.output}}",
                    "index_in_memory": True
                }
            }
        ],
        "edges": [
            {"id": "e1", "source": "node_1", "target": "node_2", "condition": ""},
            {"id": "e2", "source": "node_2", "target": "node_3", "condition": ""},
            {"id": "e3", "source": "node_3", "target": "node_4", "condition": ""},
            {"id": "e4", "source": "node_4", "target": "node_5", "condition": "true"},
            {"id": "e5", "source": "node_4", "target": "node_6", "condition": "false"}
        ]
    },
    {
        "id": "tpl_daily_knowledge_digest",
        "name": "📊 দৈনিক ডাটাবেস, মেমোরি ও সিস্টেম ইনসাইট ডাইজেস্ট",
        "description": "প্রতিদিন বিকাল ৫:০০টায় SQLite স্কিমা ও প্রজেক্ট মেমোরি বিশ্লেষণ করে এআই অ্যাকশন প্ল্যান ও এক্সিকিউটিভ রিপোর্ট তৈরি করে।",
        "icon": "📊",
        "trigger_type": "daily",
        "schedule_expr": "0 17 * * *",
        "daily_time": "17:00",
        "timezone": "Asia/Dhaka",
        "is_enabled": 0,
        "nodes": [
            {
                "id": "node_1",
                "type": "trigger_daily",
                "title": "বিকাল ৫:০০ দৈনিক ট্রিগার",
                "x": 40,
                "y": 150,
                "config": {"daily_time": "17:00", "timezone": "Asia/Dhaka", "frequency": "daily"}
            },
            {
                "id": "node_2",
                "type": "tool_call",
                "title": "SQLite ও সিস্টেম ইনফো",
                "x": 320,
                "y": 150,
                "config": {"tool_name": "system_info", "args_json": "{}"}
            },
            {
                "id": "node_3",
                "type": "ai_agent",
                "title": "🧠 প্রজেক্ট ইনসাইট এনালিস্ট",
                "x": 610,
                "y": 150,
                "config": {
                    "prompt": "আজকের ({{trigger.date}}) সিস্টেম অবস্থা ও সংরক্ষিত প্রজেক্ট মেমোরি মিলিয়ে দিনের সারসংক্ষেপ ও আগামীকালের জন্য ৩টি মূল অগ্রাধিকার তালিকা তৈরি করুন।\n\nসিস্টেম ডেটা:\n{{nodes.node_2.output}}",
                    "system_instruction": "Summarize cleanly in Bangla with bullet points and action items.",
                    "model": "",
                    "project_name": "myagent",
                    "use_memory": True,
                    "enable_tools": True,
                    "fallback_on_error": True,
                    "language": "bn",
                    "max_turns": 4,
                    "fallback_on_error": True
                }
            },
            {
                "id": "node_4",
                "type": "save_report",
                "title": "📄 দৈনিক ডাইজেস্ট রিপোর্ট",
                "x": 910,
                "y": 150,
                "config": {
                    "title": "দৈনিক প্রজেক্ট ও সিস্টেম ডাইজেস্ট - {{trigger.date}}",
                    "report_type": "executive_summary",
                    "content": "{{nodes.node_3.output}}",
                    "index_in_memory": True
                }
            },
            {
                "id": "node_5",
                "type": "notify_channel",
                "title": "📣 চ্যাটে পাঠান",
                "x": 1200,
                "y": 150,
                "config": {
                    "target": "chat_session",
                    "session_title": "📅 Daily Automated Agent Reports",
                    "title": "📊 ইভনিং ডাইজেস্ট ({{trigger.date}})",
                    "message": "{{nodes.node_3.output}}",
                    "custom_webhook_url": ""
                }
            }
        ],
        "edges": [
            {"id": "e1", "source": "node_1", "target": "node_2", "condition": ""},
            {"id": "e2", "source": "node_2", "target": "node_3", "condition": ""},
            {"id": "e3", "source": "node_3", "target": "node_4", "condition": ""},
            {"id": "e4", "source": "node_4", "target": "node_5", "condition": ""}
        ]
    },
    {
        "id": "tpl_parallel_merge_ops_center",
        "name": "⚡ প্যারালাল পিং + SQLite + পোর্ট -> Merge & 3-Way Switch",
        "description": "ট্রিগার থেকে একসাথে ৩টি প্যারালাল অডিট চালিয়ে Merge নোডে একত্রিত করে এবং Switch Router দিয়ে Critical/Warning/OK অনুযায়ী আলাদা অ্যাকশন নেয়।",
        "icon": "⚡",
        "trigger_type": "daily",
        "schedule_expr": "0 8 * * *",
        "daily_time": "08:00",
        "timezone": "Asia/Dhaka",
        "is_enabled": 0,
        "nodes": [
            {
                "id": "node_1",
                "type": "trigger_daily",
                "title": "সকাল ৮:০০ প্যারালাল ট্রিগার",
                "x": 40,
                "y": 175,
                "config": {"daily_time": "08:00", "timezone": "Asia/Dhaka", "frequency": "daily"}
            },
            {
                "id": "node_2",
                "type": "loop_foreach",
                "title": "🔁 প্যারালাল ১: ফ্লিট পিং",
                "x": 320,
                "y": 50,
                "config": {"items_text": "192.168.9.1\n192.168.9.5\n192.168.9.9\n8.8.8.8", "action_type": "ping"}
            },
            {
                "id": "node_3",
                "type": "knowledge_db_query",
                "title": "🗄️ প্যারালাল ২: DB হেলথ কোয়েরি",
                "x": 320,
                "y": 180,
                "config": {
                    "query_mode": "sqlite",
                    "db_name": "ops.db",
                    "sql_query": "SELECT name, last_status, run_count, last_run FROM ops_workflows ORDER BY updated_at DESC LIMIT 6;"
                }
            },
            {
                "id": "node_4",
                "type": "tool_call",
                "title": "🛠️ প্যারালাল ৩: সিস্টেম ইনফো",
                "x": 320,
                "y": 310,
                "config": {"tool_name": "system_info", "args_json": "{}"}
            },
            {
                "id": "node_5",
                "type": "merge_combine",
                "title": "🤝 ৩-ব্রাঞ্চ মার্জ",
                "x": 620,
                "y": 175,
                "config": {"mode": "markdown_sections", "include_empty": False}
            },
            {
                "id": "node_6",
                "type": "switch_router",
                "title": "🚦 সিভিয়ারিটি সুইচ রাউটার",
                "x": 900,
                "y": 175,
                "config": {
                    "target": "{{prev.output}}",
                    "route1_op": "regex",
                    "route1_val": "(CRITICAL|100% LOSS|FATAL)",
                    "route2_op": "regex",
                    "route2_val": "(WARNING|OFFLINE|ERROR|FAILED)"
                }
            },
            {
                "id": "node_7",
                "type": "notify_channel",
                "title": "🚨 Route 1: জরুরি অ্যালার্ট",
                "x": 1200,
                "y": 45,
                "config": {
                    "target": "chat_and_channels",
                    "session_title": "📅 Daily Automated Agent Reports",
                    "title": "🚨 CRITICAL: Ops Center ({{trigger.date}})",
                    "message": "{{nodes.node_5.output}}"
                }
            },
            {
                "id": "node_8",
                "type": "save_report",
                "title": "⚠️ Route 2: সতর্কতা রিপোর্ট",
                "x": 1200,
                "y": 175,
                "config": {
                    "title": "Warning Ops Summary - {{trigger.date}}",
                    "report_type": "incident_report",
                    "content": "{{nodes.node_5.output}}",
                    "index_in_memory": True
                }
            },
            {
                "id": "node_9",
                "type": "save_report",
                "title": "✅ Default: হেলদি রিপোর্ট আর্কাইভ",
                "x": 1200,
                "y": 305,
                "config": {
                    "title": "Daily Green Ops Digest - {{trigger.date}}",
                    "report_type": "executive_summary",
                    "content": "{{nodes.node_5.output}}",
                    "index_in_memory": True
                }
            }
        ],
        "edges": [
            {"id": "e1", "source": "node_1", "target": "node_2", "condition": ""},
            {"id": "e2", "source": "node_1", "target": "node_3", "condition": ""},
            {"id": "e3", "source": "node_1", "target": "node_4", "condition": ""},
            {"id": "e4", "source": "node_2", "target": "node_5", "condition": ""},
            {"id": "e5", "source": "node_3", "target": "node_5", "condition": ""},
            {"id": "e6", "source": "node_4", "target": "node_5", "condition": ""},
            {"id": "e7", "source": "node_5", "target": "node_6", "condition": ""},
            {"id": "e8", "source": "node_6", "target": "node_7", "condition": "route_1"},
            {"id": "e9", "source": "node_6", "target": "node_8", "condition": "route_2"},
            {"id": "e10", "source": "node_6", "target": "node_9", "condition": "default"}
        ]
    }
]


class WorkflowStore:
    """SQLite persistence layer for n8n-style workflows and run execution histories inside ops.db."""

    @classmethod
    async def get_db(cls):
        path = _get_ops_db_path()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        db = await aiosqlite.connect(path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL;")
        return db

    @classmethod
    async def init_tables_and_seed(cls):
        db = await cls.get_db()
        try:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ops_workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    icon TEXT DEFAULT '⚡',
                    trigger_type TEXT DEFAULT 'daily',
                    schedule_expr TEXT DEFAULT '0 9 * * *',
                    daily_time TEXT DEFAULT '09:00',
                    timezone TEXT DEFAULT 'Asia/Dhaka',
                    nodes_json TEXT NOT NULL,
                    edges_json TEXT NOT NULL,
                    is_enabled INTEGER DEFAULT 1,
                    webhook_secret TEXT DEFAULT '',
                    last_run TEXT,
                    next_run TEXT,
                    next_run_ts REAL,
                    last_status TEXT DEFAULT 'IDLE',
                    run_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ops_workflow_runs (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    workflow_name TEXT,
                    trigger_source TEXT DEFAULT 'manual',
                    status TEXT DEFAULT 'RUNNING',
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    duration_ms INTEGER DEFAULT 0,
                    node_results_json TEXT DEFAULT '[]',
                    final_output TEXT DEFAULT '',
                    error_message TEXT DEFAULT ''
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_wf_runs_wfid ON ops_workflow_runs(workflow_id, started_at DESC)")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ops_workflow_secrets (
                    key TEXT PRIMARY KEY,
                    value_enc TEXT NOT NULL,
                    is_secret INTEGER DEFAULT 1,
                    description TEXT DEFAULT '',
                    updated_at TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ops_workflow_versions (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    version_num INTEGER NOT NULL,
                    name TEXT,
                    schedule_expr TEXT DEFAULT '',
                    daily_time TEXT DEFAULT '09:00',
                    timezone TEXT DEFAULT 'Asia/Dhaka',
                    nodes_json TEXT NOT NULL,
                    edges_json TEXT NOT NULL,
                    saved_at TEXT NOT NULL
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_wf_versions_wfid ON ops_workflow_versions(workflow_id, version_num DESC)")
            await cls._ensure_telegram_tables(db)
            await db.commit()

            # Seed prebuilt daily workflows if table is empty
            async with db.execute("SELECT COUNT(*) as cnt FROM ops_workflows") as cur:
                row = await cur.fetchone()
                cnt = row["cnt"] if row else 0

            if cnt == 0:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for tpl in WORKFLOW_TEMPLATES[:3]:
                    wf_id = f"wf_{tpl['id'].replace('tpl_', '')}"
                    is_en = int(tpl.get("is_enabled", 1))
                    next_str, next_ts, _, _ = compute_next_run(
                        tpl.get("schedule_expr"),
                        tpl.get("timezone", "Asia/Dhaka"),
                        tpl.get("trigger_type", "daily")
                    ) if is_en else (None, None, "", "")
                    wh_secret = f"whsec_{uuid.uuid4().hex[:16]}"
                    await db.execute("""
                        INSERT INTO ops_workflows (
                            id, name, description, icon, trigger_type, schedule_expr,
                            daily_time, timezone, nodes_json, edges_json, is_enabled,
                            webhook_secret, next_run, next_run_ts, last_status,
                            run_count, success_count, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'IDLE', 0, 0, ?, ?)
                    """, (
                        wf_id,
                        tpl["name"],
                        tpl["description"],
                        tpl.get("icon", "⚡"),
                        tpl.get("trigger_type", "daily"),
                        tpl.get("schedule_expr", ""),
                        tpl.get("daily_time", "09:00"),
                        tpl.get("timezone", "Asia/Dhaka"),
                        json.dumps(tpl["nodes"], ensure_ascii=False),
                        json.dumps(tpl["edges"], ensure_ascii=False),
                        is_en,
                        wh_secret,
                        next_str,
                        next_ts,
                        now_str,
                        now_str,
                    ))
                await db.commit()
                logger.info("Seeded default n8n-style daily workflows into ops_workflows.")
            else:
                # Ensure existing seeded daily workflows inherit fallback_on_error=True if unset
                for wf_seed_id in ("wf_daily_morning_brief", "wf_daily_security_audit", "wf_daily_custom_ai_task"):
                    async with db.execute("SELECT nodes_json FROM ops_workflows WHERE id = ?", (wf_seed_id,)) as cur_s:
                        srow = await cur_s.fetchone()
                    if srow and srow["nodes_json"]:
                        try:
                            snodes = json.loads(srow["nodes_json"])
                            changed = False
                            for nd in snodes:
                                if nd.get("type") == "ai_agent":
                                    nc = nd.setdefault("config", {})
                                    if "fallback_on_error" not in nc:
                                        nc["fallback_on_error"] = True
                                        changed = True
                            if changed:
                                await db.execute(
                                    "UPDATE ops_workflows SET nodes_json = ? WHERE id = ?",
                                    (json.dumps(snodes, ensure_ascii=False), wf_seed_id),
                                )
                        except Exception:
                            pass
                await db.commit()
        finally:
            await db.close()

    @classmethod
    def _hydrate_row(cls, row: Any) -> Dict[str, Any]:
        d = dict(row)
        try:
            d["nodes"] = json.loads(d.get("nodes_json") or "[]")
        except Exception:
            d["nodes"] = []
        try:
            d["edges"] = json.loads(d.get("edges_json") or "[]")
        except Exception:
            d["edges"] = []

        # Human readable schedule
        ttype = d.get("trigger_type", "daily")
        expr = d.get("schedule_expr", "")
        if ttype in ("manual", "webhook"):
            d["human_en"] = "Webhook HTTP Trigger" if ttype == "webhook" else "Manual Trigger"
            d["human_bn"] = "ওয়েবহুক HTTP ট্রিগার" if ttype == "webhook" else "ম্যানুয়াল ট্রিগার"
        elif expr:
            try:
                cron = CronExpression(expr)
                d["human_en"] = cron.to_human_en()
                d["human_bn"] = cron.to_human_bn()
            except Exception:
                d["human_en"] = expr
                d["human_bn"] = expr
        else:
            d["human_en"] = "Scheduled"
            d["human_bn"] = "নির্ধারিত সময়"

        d["is_enabled"] = bool(d.get("is_enabled", 0))
        d["next_runs_preview"] = compute_upcoming_runs(
            d.get("schedule_expr"),
            d.get("timezone") or "Asia/Dhaka",
            ttype,
            count=3
        ) if d["is_enabled"] else []
        return d

    @classmethod
    async def list_workflows(cls) -> List[Dict[str, Any]]:
        db = await cls.get_db()
        try:
            async with db.execute("SELECT * FROM ops_workflows ORDER BY is_enabled DESC, updated_at DESC") as cur:
                rows = await cur.fetchall()
            return [cls._hydrate_row(r) for r in rows]
        finally:
            await db.close()

    @classmethod
    async def get_workflow(cls, workflow_id: str) -> Optional[Dict[str, Any]]:
        db = await cls.get_db()
        try:
            async with db.execute("SELECT * FROM ops_workflows WHERE id = ?", (workflow_id,)) as cur:
                row = await cur.fetchone()
            return cls._hydrate_row(row) if row else None
        finally:
            await db.close()

    @classmethod
    async def create_workflow(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        wf_id = data.get("id") or f"wf_{uuid.uuid4().hex[:8]}"
        name = (data.get("name") or "Untitled Auto-Workflow").strip()
        description = (data.get("description") or "").strip()
        icon = (data.get("icon") or "⚡").strip()
        trigger_type = (data.get("trigger_type") or "daily").strip()
        daily_time = (data.get("daily_time") or "09:00").strip()
        timezone_str = (data.get("timezone") or "Asia/Dhaka").strip()
        schedule_expr = (data.get("schedule_expr") or "").strip()
        if trigger_type == "daily" and not schedule_expr:
            schedule_expr = daily_time_to_cron(daily_time, "daily")
        elif trigger_type in ("cron", "interval") and not schedule_expr:
            schedule_expr = daily_time_to_cron(daily_time, "daily")

        nodes = data.get("nodes") or [
            {
                "id": "node_1",
                "type": "trigger_daily" if trigger_type in ("daily", "cron", "interval") else f"trigger_{trigger_type}",
                "title": f"Daily Trigger ({daily_time})" if trigger_type == "daily" else "Workflow Trigger",
                "x": 60,
                "y": 140,
                "config": {"daily_time": daily_time, "timezone": timezone_str, "frequency": trigger_type}
            },
            {
                "id": "node_2",
                "type": "ai_agent",
                "title": "Autonomous AI Agent",
                "x": 380,
                "y": 140,
                "config": {
                    "prompt": description or "Check system health and summarize today's updates.",
                    "system_instruction": "Execute tools if needed and return structured insights.",
                    "model": "",
                    "use_memory": True,
                    "enable_tools": True,
                    "language": "bn"
                }
            }
        ]
        edges = data.get("edges")
        if edges is None:
            edges = [{"id": "e1", "source": "node_1", "target": "node_2", "condition": ""}] if len(nodes) >= 2 else []

        is_enabled = 1 if data.get("is_enabled", True) else 0
        next_str, next_ts, _, _ = compute_next_run(schedule_expr, timezone_str, trigger_type) if is_enabled else (None, None, "", "")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        wh_secret = data.get("webhook_secret") or f"whsec_{uuid.uuid4().hex[:16]}"

        db = await cls.get_db()
        try:
            await db.execute("""
                INSERT INTO ops_workflows (
                    id, name, description, icon, trigger_type, schedule_expr,
                    daily_time, timezone, nodes_json, edges_json, is_enabled,
                    webhook_secret, next_run, next_run_ts, last_status,
                    run_count, success_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'IDLE', 0, 0, ?, ?)
            """, (
                wf_id, name, description, icon, trigger_type, schedule_expr,
                daily_time, timezone_str,
                json.dumps(nodes, ensure_ascii=False),
                json.dumps(edges, ensure_ascii=False),
                is_enabled, wh_secret, next_str, next_ts, now_str, now_str
            ))
            await db.commit()
        finally:
            await db.close()

        return await cls.get_workflow(wf_id)

    @classmethod
    async def update_workflow(cls, workflow_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        existing = await cls.get_workflow(workflow_id)
        if not existing:
            return None

        name = (data.get("name", existing["name"]) or existing["name"]).strip()
        description = (data.get("description", existing["description"]) or "").strip()
        icon = (data.get("icon", existing["icon"]) or "⚡").strip()
        trigger_type = (data.get("trigger_type", existing["trigger_type"]) or "daily").strip()
        daily_time = (data.get("daily_time", existing["daily_time"]) or "09:00").strip()
        timezone_str = (data.get("timezone", existing["timezone"]) or "Asia/Dhaka").strip()
        schedule_expr = data.get("schedule_expr", existing["schedule_expr"])
        if trigger_type == "daily" and "daily_time" in data and "schedule_expr" not in data:
            schedule_expr = daily_time_to_cron(daily_time, "daily")

        nodes = data.get("nodes", existing["nodes"])
        edges = data.get("edges", existing["edges"])
        is_enabled = 1 if data.get("is_enabled", existing["is_enabled"]) else 0

        # Sync trigger node metadata if nodes exist
        for n in nodes:
            ntype = n.get("type", "")
            if ntype.startswith("trigger_"):
                cfg = n.setdefault("config", {})
                if trigger_type == "daily":
                    cfg["daily_time"] = daily_time
                    cfg["timezone"] = timezone_str
                break

        next_str, next_ts, _, _ = compute_next_run(schedule_expr, timezone_str, trigger_type) if is_enabled else (None, None, "", "")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db = await cls.get_db()
        try:
            # Auto-snapshot previous graph revision before overwriting
            try:
                async with db.execute(
                    "SELECT COALESCE(MAX(version_num), 0) AS vmax FROM ops_workflow_versions WHERE workflow_id = ?",
                    (workflow_id,)
                ) as cur:
                    row = await cur.fetchone()
                    next_ver = (row["vmax"] if row else 0) + 1
                await db.execute("""
                    INSERT INTO ops_workflow_versions (
                        id, workflow_id, version_num, name, schedule_expr, daily_time, timezone,
                        nodes_json, edges_json, saved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"wfver_{uuid.uuid4().hex[:10]}",
                    workflow_id,
                    next_ver,
                    existing["name"],
                    existing.get("schedule_expr", ""),
                    existing.get("daily_time", "09:00"),
                    existing.get("timezone", "Asia/Dhaka"),
                    json.dumps(existing.get("nodes", []), ensure_ascii=False),
                    json.dumps(existing.get("edges", []), ensure_ascii=False),
                    now_str
                ))
                # Prune older than latest 15 versions per workflow
                await db.execute("""
                    DELETE FROM ops_workflow_versions
                    WHERE workflow_id = ? AND id NOT IN (
                        SELECT id FROM ops_workflow_versions WHERE workflow_id = ? ORDER BY version_num DESC LIMIT 15
                    )
                """, (workflow_id, workflow_id))
            except Exception as ver_err:
                logger.warning(f"Version snapshot skipped for '{workflow_id}': {ver_err}")

            await db.execute("""
                UPDATE ops_workflows
                SET name = ?, description = ?, icon = ?, trigger_type = ?,
                    schedule_expr = ?, daily_time = ?, timezone = ?,
                    nodes_json = ?, edges_json = ?, is_enabled = ?,
                    next_run = ?, next_run_ts = ?, updated_at = ?
                WHERE id = ?
            """, (
                name, description, icon, trigger_type,
                schedule_expr, daily_time, timezone_str,
                json.dumps(nodes, ensure_ascii=False),
                json.dumps(edges, ensure_ascii=False),
                is_enabled, next_str, next_ts, now_str, workflow_id
            ))
            await db.commit()
        finally:
            await db.close()

        return await cls.get_workflow(workflow_id)

    @classmethod
    async def toggle_workflow(cls, workflow_id: str) -> Optional[Dict[str, Any]]:
        wf = await cls.get_workflow(workflow_id)
        if not wf:
            return None
        new_enabled = 0 if wf["is_enabled"] else 1
        next_str, next_ts, _, _ = (
            compute_next_run(wf.get("schedule_expr"), wf.get("timezone", "Asia/Dhaka"), wf.get("trigger_type", "daily"))
            if new_enabled else (None, None, "", "")
        )
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db = await cls.get_db()
        try:
            await db.execute(
                "UPDATE ops_workflows SET is_enabled = ?, next_run = ?, next_run_ts = ?, updated_at = ? WHERE id = ?",
                (new_enabled, next_str, next_ts, now_str, workflow_id)
            )
            await db.commit()
        finally:
            await db.close()
        return await cls.get_workflow(workflow_id)

    @classmethod
    async def delete_workflow(cls, workflow_id: str) -> bool:
        db = await cls.get_db()
        try:
            cur = await db.execute("DELETE FROM ops_workflows WHERE id = ?", (workflow_id,))
            await db.execute("DELETE FROM ops_workflow_runs WHERE workflow_id = ?", (workflow_id,))
            await db.execute("DELETE FROM ops_workflow_versions WHERE workflow_id = ?", (workflow_id,))
            await db.commit()
            return cur.rowcount > 0
        finally:
            await db.close()

    @classmethod
    async def list_versions(cls, workflow_id: str, limit: int = 15) -> List[Dict[str, Any]]:
        db = await cls.get_db()
        try:
            async with db.execute(
                "SELECT id, workflow_id, version_num, name, schedule_expr, daily_time, timezone, nodes_json, edges_json, saved_at "
                "FROM ops_workflow_versions WHERE workflow_id = ? ORDER BY version_num DESC LIMIT ?",
                (workflow_id, limit)
            ) as cur:
                rows = await cur.fetchall()
            out = []
            for r in rows:
                d = dict(r)
                try:
                    d["nodes_count"] = len(json.loads(d.get("nodes_json") or "[]"))
                    d["edges_count"] = len(json.loads(d.get("edges_json") or "[]"))
                except Exception:
                    d["nodes_count"] = 0
                    d["edges_count"] = 0
                out.append(d)
            return out
        finally:
            await db.close()

    @classmethod
    async def restore_version(cls, workflow_id: str, version_id: str) -> Optional[Dict[str, Any]]:
        db = await cls.get_db()
        try:
            async with db.execute(
                "SELECT * FROM ops_workflow_versions WHERE id = ? AND workflow_id = ?",
                (version_id, workflow_id)
            ) as cur:
                ver = await cur.fetchone()
        finally:
            await db.close()
        if not ver:
            return None
        try:
            nodes = json.loads(ver["nodes_json"] or "[]")
            edges = json.loads(ver["edges_json"] or "[]")
        except Exception:
            nodes, edges = [], []
        return await cls.update_workflow(workflow_id, {
            "name": ver["name"] or "Restored Workflow",
            "schedule_expr": ver["schedule_expr"],
            "daily_time": ver["daily_time"],
            "timezone": ver["timezone"],
            "nodes": nodes,
            "edges": edges
        })

    @classmethod
    async def list_secrets(cls) -> List[Dict[str, Any]]:
        db = await cls.get_db()
        try:
            async with db.execute("SELECT key, value_enc, is_secret, description, updated_at FROM ops_workflow_secrets ORDER BY key ASC") as cur:
                rows = await cur.fetchall()
            from security.crypto import DataCrypto
            crypto = DataCrypto()
            items = []
            for r in rows:
                raw_val = crypto.decrypt_text(r["value_enc"])
                is_sec = bool(r["is_secret"])
                preview = ("••••" + raw_val[-4:]) if (is_sec and len(raw_val) > 4) else ("••••••" if is_sec else raw_val)
                items.append({
                    "key": r["key"],
                    "value_preview": preview,
                    "is_secret": is_sec,
                    "description": r["description"] or "",
                    "updated_at": r["updated_at"]
                })
            return items
        finally:
            await db.close()

    @classmethod
    async def upsert_secret(cls, key: str, value: str, is_secret: bool = True, description: str = "") -> Dict[str, Any]:
        import re as _re
        clean_key = _re.sub(r"[^A-Za-z0-9_]", "_", (key or "").strip()).upper()
        if not clean_key:
            raise ValueError("Variable/Secret key cannot be empty.")
        from security.crypto import DataCrypto
        crypto = DataCrypto()
        enc_val = crypto.encrypt_text(str(value or ""))
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db = await cls.get_db()
        try:
            await db.execute("""
                INSERT INTO ops_workflow_secrets (key, value_enc, is_secret, description, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_enc = excluded.value_enc,
                    is_secret = excluded.is_secret,
                    description = excluded.description,
                    updated_at = excluded.updated_at
            """, (clean_key, enc_val, 1 if is_secret else 0, (description or "").strip(), now_str))
            await db.commit()
        finally:
            await db.close()
        return {"key": clean_key, "is_secret": is_secret, "updated_at": now_str}

    @classmethod
    async def delete_secret(cls, key: str) -> bool:
        db = await cls.get_db()
        try:
            cur = await db.execute("DELETE FROM ops_workflow_secrets WHERE key = ?", (key.strip(),))
            await db.commit()
            return cur.rowcount > 0
        finally:
            await db.close()

    @classmethod
    async def get_secrets_for_runtime(cls) -> Tuple[Dict[str, str], List[str]]:
        """Returns decrypted {KEY: val} dict and list of sensitive strings for log redaction."""
        try:
            db = await cls.get_db()
            try:
                async with db.execute("SELECT key, value_enc, is_secret FROM ops_workflow_secrets") as cur:
                    rows = await cur.fetchall()
            finally:
                await db.close()
            from security.crypto import DataCrypto
            crypto = DataCrypto()
            vars_map: Dict[str, str] = {}
            redact_vals: List[str] = []
            for r in rows:
                val = crypto.decrypt_text(r["value_enc"])
                vars_map[r["key"]] = val
                if r["is_secret"] and len(val) >= 6:
                    redact_vals.append(val)
            return vars_map, redact_vals
        except Exception as e:
            logger.debug(f"Could not load workflow secrets: {e}")
            return {}, []

    # ==========================================================================
    # Telegram Connection Config, Status Sync & Delivery Log Store
    # ==========================================================================
    @classmethod
    async def _ensure_telegram_tables(cls, db):
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ops_channels (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                platform TEXT NOT NULL,
                icon TEXT DEFAULT '📡',
                token TEXT,
                webhook_url TEXT,
                chat_id TEXT,
                is_enabled INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Disconnected',
                last_tested TEXT
            )
        """)
        await db.execute("""
            INSERT OR IGNORE INTO ops_channels (id, name, platform, icon, token, webhook_url, chat_id, is_enabled, status, last_tested)
            VALUES ('chan_telegram', 'Telegram Corporate Bot', 'telegram', '✈️', '', 'https://api.telegram.org/bot', '', 0, 'Disconnected', NULL)
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ops_telegram_config (
                id TEXT PRIMARY KEY,
                bot_token_enc TEXT DEFAULT '',
                chat_id TEXT DEFAULT '',
                bot_id TEXT DEFAULT '',
                bot_username TEXT DEFAULT '',
                bot_first_name TEXT DEFAULT '',
                is_enabled INTEGER DEFAULT 0,
                interactive_chat_enabled INTEGER DEFAULT 1,
                auto_send_reports INTEGER DEFAULT 1,
                allowed_chat_ids TEXT DEFAULT '',
                last_update_id INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Disconnected',
                last_verified_at TEXT DEFAULT '',
                last_tested_at TEXT DEFAULT '',
                last_error TEXT DEFAULT '',
                updated_at TEXT NOT NULL
            )
        """)
        # Safe schema migration for existing ops.db databases
        async with db.execute("PRAGMA table_info(ops_telegram_config)") as pcur:
            existing_cols = {r[1] for r in await pcur.fetchall()}
        migrations = [
            ("interactive_chat_enabled", "INTEGER DEFAULT 1"),
            ("auto_send_reports", "INTEGER DEFAULT 1"),
            ("allowed_chat_ids", "TEXT DEFAULT ''"),
            ("last_update_id", "INTEGER DEFAULT 0"),
        ]
        for col_name, col_def in migrations:
            if col_name not in existing_cols:
                await db.execute(f"ALTER TABLE ops_telegram_config ADD COLUMN {col_name} {col_def}")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS ops_telegram_logs (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                workflow_id TEXT DEFAULT '',
                workflow_name TEXT DEFAULT '',
                node_id TEXT DEFAULT '',
                bot_username TEXT DEFAULT '',
                chat_id TEXT DEFAULT '',
                message_preview TEXT DEFAULT '',
                status TEXT NOT NULL,
                http_status INTEGER DEFAULT 0,
                telegram_message_id TEXT DEFAULT '',
                error_detail TEXT DEFAULT '',
                latency_ms INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tg_logs_created ON ops_telegram_logs(created_at DESC)")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ops_telegram_chats (
                id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL,
                sender_name TEXT DEFAULT '',
                direction TEXT NOT NULL,
                intent TEXT DEFAULT '',
                user_message TEXT DEFAULT '',
                reply_message TEXT DEFAULT '',
                workflow_status_summary TEXT DEFAULT '',
                linked_workflow_id TEXT DEFAULT '',
                status TEXT DEFAULT 'SUCCESS',
                latency_ms INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tg_chats_created ON ops_telegram_chats(created_at DESC)")

    @staticmethod
    def mask_telegram_token(token: str) -> str:
        tok = (token or "").strip()
        if not tok:
            return ""
        if ":" in tok:
            prefix, rest = tok.split(":", 1)
            tail = rest[-4:] if len(rest) >= 4 else "••••"
            return f"{prefix[:6]}:••••{tail}"
        return f"••••{tok[-4:]}" if len(tok) > 4 else "••••"

    @classmethod
    async def get_telegram_config(cls, include_plaintext_token: bool = False) -> Dict[str, Any]:
        from security.crypto import DataCrypto
        crypto = DataCrypto()
        db = await cls.get_db()
        try:
            await cls._ensure_telegram_tables(db)
            async with db.execute("SELECT * FROM ops_telegram_config WHERE id = 'default'") as cur:
                row = await cur.fetchone()
            async with db.execute("SELECT * FROM ops_channels WHERE id = 'chan_telegram'") as cur2:
                chan_row = await cur2.fetchone()

            now_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if not row:
                # Hydrate cleanly if user previously saved token/chat_id inside ops_channels
                chan_tok = (chan_row["token"] if chan_row else "") or ""
                chan_cid = (chan_row["chat_id"] if chan_row else "") or ""
                chan_en = int(chan_row["is_enabled"]) if chan_row else 0
                chan_st = (chan_row["status"] if chan_row else "Disconnected") or "Disconnected"
                chan_tested = (chan_row["last_tested"] if chan_row else "") or ""
                tok_enc = crypto.encrypt_text(chan_tok) if chan_tok else ""
                await db.execute("""
                    INSERT INTO ops_telegram_config
                    (id, bot_token_enc, chat_id, bot_id, bot_username, bot_first_name, is_enabled, status, last_verified_at, last_tested_at, last_error, updated_at)
                    VALUES ('default', ?, ?, '', '', '', ?, ?, '', ?, '', ?)
                """, (tok_enc, chan_cid, chan_en, chan_st, chan_tested, now_s))
                await db.commit()
                async with db.execute("SELECT * FROM ops_telegram_config WHERE id = 'default'") as cur3:
                    row = await cur3.fetchone()

            raw = dict(row)
            plain_tok = crypto.decrypt_text(raw.get("bot_token_enc") or "")
            if not plain_tok and chan_row and (chan_row["token"] or "").strip():
                plain_tok = chan_row["token"].strip()

            chat_id = (raw.get("chat_id") or "").strip() or ((chan_row["chat_id"] or "").strip() if chan_row else "")
            is_enabled = bool(raw.get("is_enabled"))
            status = (raw.get("status") or "Disconnected").strip()
            if not plain_tok:
                status = "Disconnected"
                is_enabled = False
            connected = bool(is_enabled and status == "Connected" and plain_tok)

            async with db.execute("""
                SELECT
                    COUNT(*) as total_logs,
                    SUM(CASE WHEN status IN ('SENT', 'SUCCESS') THEN 1 ELSE 0 END) as sent_count,
                    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_count,
                    MAX(created_at) as last_log_at
                FROM ops_telegram_logs
            """) as scur:
                srow = await scur.fetchone()
            async with db.execute("SELECT COUNT(*) as cnt FROM ops_telegram_chats") as ccur:
                crow = await ccur.fetchone()

            raw_inter = raw.get("interactive_chat_enabled")
            raw_autorep = raw.get("auto_send_reports")
            res = {
                "connected": connected,
                "status": status,
                "is_enabled": is_enabled,
                "interactive_chat_enabled": True if raw_inter is None else bool(raw_inter),
                "auto_send_reports": True if raw_autorep is None else bool(raw_autorep),
                "allowed_chat_ids": (raw.get("allowed_chat_ids") or "").strip(),
                "last_update_id": int(raw.get("last_update_id") or 0),
                "has_token": bool(plain_tok),
                "token_preview": cls.mask_telegram_token(plain_tok),
                "chat_id": chat_id,
                "bot_id": raw.get("bot_id") or "",
                "bot_username": raw.get("bot_username") or "",
                "bot_first_name": raw.get("bot_first_name") or "",
                "last_verified_at": raw.get("last_verified_at") or "",
                "last_tested_at": raw.get("last_tested_at") or "",
                "last_error": raw.get("last_error") or "",
                "updated_at": raw.get("updated_at") or "",
                "total_logs": int(srow["total_logs"] or 0) if srow else 0,
                "sent_count": int(srow["sent_count"] or 0) if srow else 0,
                "failed_count": int(srow["failed_count"] or 0) if srow else 0,
                "total_chats": int(crow["cnt"] or 0) if crow else 0,
                "last_log_at": (srow["last_log_at"] or "") if srow else "",
            }
            if include_plaintext_token:
                res["_bot_token"] = plain_tok
            return res
        finally:
            await db.close()

    @classmethod
    async def save_telegram_config(
        cls,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        interactive_chat_enabled: Optional[bool] = None,
        auto_send_reports: Optional[bool] = None,
        allowed_chat_ids: Optional[str] = None,
        last_update_id: Optional[int] = None,
        status: Optional[str] = None,
        bot_id: Optional[str] = None,
        bot_username: Optional[str] = None,
        bot_first_name: Optional[str] = None,
        last_verified_at: Optional[str] = None,
        last_tested_at: Optional[str] = None,
        last_error: Optional[str] = None,
        clear_token: bool = False,
    ) -> Dict[str, Any]:
        from security.crypto import DataCrypto
        crypto = DataCrypto()
        current = await cls.get_telegram_config(include_plaintext_token=True)

        if clear_token:
            final_token = ""
        elif bot_token is not None and bot_token.strip():
            final_token = bot_token.strip()
        else:
            final_token = current.get("_bot_token", "")

        final_chat_id = current["chat_id"] if chat_id is None else chat_id.strip()
        final_enabled = current["is_enabled"] if is_enabled is None else bool(is_enabled)
        final_interactive = current["interactive_chat_enabled"] if interactive_chat_enabled is None else bool(interactive_chat_enabled)
        final_autoreport = current["auto_send_reports"] if auto_send_reports is None else bool(auto_send_reports)
        final_allowed = current["allowed_chat_ids"] if allowed_chat_ids is None else str(allowed_chat_ids).strip()
        final_upd_id = current["last_update_id"] if last_update_id is None else int(last_update_id)
        final_status = current["status"] if status is None else status.strip()
        if clear_token or not final_token:
            final_enabled = False
            final_status = "Disconnected"

        if clear_token:
            final_bot_id = ""
            final_bot_user = ""
            final_bot_name = ""
            final_upd_id = 0
        else:
            final_bot_id = current["bot_id"] if bot_id is None else str(bot_id).strip()
            final_bot_user = current["bot_username"] if bot_username is None else str(bot_username).strip()
            final_bot_name = current["bot_first_name"] if bot_first_name is None else str(bot_first_name).strip()
        final_verified = current["last_verified_at"] if last_verified_at is None else str(last_verified_at)
        final_tested = current["last_tested_at"] if last_tested_at is None else str(last_tested_at)
        final_err = current["last_error"] if last_error is None else str(last_error)

        now_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tok_enc = crypto.encrypt_text(final_token) if final_token else ""

        db = await cls.get_db()
        try:
            await cls._ensure_telegram_tables(db)
            await db.execute("""
                UPDATE ops_telegram_config
                SET bot_token_enc = ?, chat_id = ?, bot_id = ?, bot_username = ?, bot_first_name = ?,
                    is_enabled = ?, interactive_chat_enabled = ?, auto_send_reports = ?,
                    allowed_chat_ids = ?, last_update_id = ?,
                    status = ?, last_verified_at = ?, last_tested_at = ?, last_error = ?, updated_at = ?
                WHERE id = 'default'
            """, (
                tok_enc, final_chat_id, final_bot_id, final_bot_user, final_bot_name,
                1 if final_enabled else 0, 1 if final_interactive else 0, 1 if final_autoreport else 0,
                final_allowed, final_upd_id,
                final_status, final_verified, final_tested, final_err, now_s
            ))
            await db.execute("""
                UPDATE ops_channels
                SET token = ?, chat_id = ?, is_enabled = ?, status = ?,
                    last_tested = COALESCE(NULLIF(?, ''), last_tested)
                WHERE id = 'chan_telegram'
            """, (final_token, final_chat_id, 1 if final_enabled else 0, final_status, final_tested))
            await db.commit()
        finally:
            await db.close()

        return await cls.get_telegram_config(include_plaintext_token=False)

    @classmethod
    async def record_telegram_log(
        cls,
        event_type: str,
        status: str,
        workflow_id: str = "",
        workflow_name: str = "",
        node_id: str = "",
        bot_username: str = "",
        chat_id: str = "",
        message_preview: str = "",
        http_status: int = 0,
        telegram_message_id: str = "",
        error_detail: str = "",
        latency_ms: int = 0,
    ) -> Dict[str, Any]:
        log_id = f"tglog_{uuid.uuid4().hex[:10]}"
        now_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db = await cls.get_db()
        try:
            await cls._ensure_telegram_tables(db)
            await db.execute("""
                INSERT INTO ops_telegram_logs
                (id, event_type, workflow_id, workflow_name, node_id, bot_username, chat_id,
                 message_preview, status, http_status, telegram_message_id, error_detail, latency_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id,
                (event_type or "event").strip(),
                (workflow_id or "").strip(),
                (workflow_name or "").strip(),
                (node_id or "").strip(),
                (bot_username or "").strip(),
                (chat_id or "").strip(),
                (message_preview or "")[:400],
                (status or "INFO").strip(),
                int(http_status or 0),
                str(telegram_message_id or ""),
                (error_detail or "")[:500],
                int(latency_ms or 0),
                now_s
            ))
            # Retain latest 250 logs
            await db.execute("""
                DELETE FROM ops_telegram_logs WHERE id NOT IN (
                    SELECT id FROM ops_telegram_logs ORDER BY created_at DESC, rowid DESC LIMIT 250
                )
            """)
            await db.commit()
        finally:
            await db.close()
        return {"id": log_id, "created_at": now_s, "status": status}

    @classmethod
    async def list_telegram_logs(cls, limit: int = 80, status_filter: str = "", event_filter: str = "") -> List[Dict[str, Any]]:
        db = await cls.get_db()
        try:
            await cls._ensure_telegram_tables(db)
            clauses = []
            params: List[Any] = []
            if status_filter and status_filter.upper() != "ALL":
                sf = status_filter.upper()
                if sf == "SUCCESS":
                    clauses.append("status IN ('SENT', 'SUCCESS', 'CONNECTED')")
                elif sf == "FAILED":
                    clauses.append("status IN ('FAILED', 'ERROR')")
                else:
                    clauses.append("status = ?")
                    params.append(sf)
            if event_filter:
                clauses.append("event_type = ?")
                params.append(event_filter)
            where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            params.append(int(limit))
            async with db.execute(f"SELECT * FROM ops_telegram_logs {where_sql} ORDER BY created_at DESC, rowid DESC LIMIT ?", tuple(params)) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]
        finally:
            await db.close()

    @classmethod
    async def clear_telegram_logs(cls) -> int:
        db = await cls.get_db()
        try:
            await cls._ensure_telegram_tables(db)
            cur = await db.execute("DELETE FROM ops_telegram_logs")
            await db.commit()
            return cur.rowcount or 0
        finally:
            await db.close()

    @classmethod
    async def record_telegram_chat(
        cls,
        chat_id: str,
        sender_name: str = "",
        direction: str = "incoming",
        intent: str = "",
        user_message: str = "",
        reply_message: str = "",
        workflow_status_summary: str = "",
        linked_workflow_id: str = "",
        status: str = "SUCCESS",
        latency_ms: int = 0,
    ) -> Dict[str, Any]:
        cid = f"tgchat_{uuid.uuid4().hex[:10]}"
        now_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db = await cls.get_db()
        try:
            await cls._ensure_telegram_tables(db)
            await db.execute("""
                INSERT INTO ops_telegram_chats
                (id, chat_id, sender_name, direction, intent, user_message, reply_message,
                 workflow_status_summary, linked_workflow_id, status, latency_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cid,
                str(chat_id or ""),
                (sender_name or "")[:120],
                (direction or "incoming").strip(),
                (intent or "").strip(),
                (user_message or "")[:2000],
                (reply_message or "")[:4000],
                (workflow_status_summary or "")[:1200],
                (linked_workflow_id or "").strip(),
                (status or "SUCCESS").strip(),
                int(latency_ms or 0),
                now_s,
            ))
            await db.execute("""
                DELETE FROM ops_telegram_chats WHERE id NOT IN (
                    SELECT id FROM ops_telegram_chats ORDER BY created_at DESC, rowid DESC LIMIT 120
                )
            """)
            await db.commit()
        finally:
            await db.close()
        return {
            "id": cid,
            "chat_id": str(chat_id or ""),
            "sender_name": sender_name,
            "direction": direction,
            "intent": intent,
            "user_message": user_message,
            "reply_message": reply_message,
            "workflow_status_summary": workflow_status_summary,
            "linked_workflow_id": linked_workflow_id,
            "status": status,
            "latency_ms": latency_ms,
            "created_at": now_s,
        }

    @classmethod
    async def list_telegram_chats(
        cls,
        limit: int = 40,
        q: str = "",
        intent: str = "",
    ) -> List[Dict[str, Any]]:
        db = await cls.get_db()
        try:
            await cls._ensure_telegram_tables(db)
            clauses = ["1=1"]
            params: List[Any] = []
            clean_q = (q or "").strip()
            if clean_q:
                like_q = f"%{clean_q}%"
                clauses.append(
                    "(user_message LIKE ? OR reply_message LIKE ? OR sender_name LIKE ? OR workflow_status_summary LIKE ?)"
                )
                params.extend([like_q, like_q, like_q, like_q])
            if intent and intent.strip().lower() != "all":
                clauses.append("LOWER(intent) = ?")
                params.append(intent.strip().lower())
            params.append(max(1, min(int(limit or 40), 200)))
            sql = f"SELECT * FROM ops_telegram_chats WHERE {' AND '.join(clauses)} ORDER BY created_at DESC, rowid DESC LIMIT ?"
            async with db.execute(sql, tuple(params)) as cur:
                return [dict(r) for r in await cur.fetchall()]
        finally:
            await db.close()

    @classmethod
    async def clear_telegram_chats(cls) -> int:
        db = await cls.get_db()
        try:
            await cls._ensure_telegram_tables(db)
            cur = await db.execute("DELETE FROM ops_telegram_chats")
            await db.commit()
            return cur.rowcount or 0
        finally:
            await db.close()

    @classmethod
    async def build_workflows_status_report(cls, max_workflows: int = 6, max_runs: int = 4) -> Dict[str, Any]:
        """Builds a compact live WORKFLOWS (Auto) status digest + formatted report text for Telegram/UI."""
        wfs = await cls.list_workflows()
        runs = await cls.list_runs(limit=max_runs)
        active_wfs = [w for w in wfs if w.get("is_enabled")]
        total_runs = sum(int(w.get("run_count") or 0) for w in wfs)
        total_ok = sum(int(w.get("success_count") or 0) for w in wfs)
        rate = round((total_ok / total_runs) * 100) if total_runs > 0 else 100

        lines = [
            f"📊 WORKFLOWS (Auto) Status Report",
            f"• Total Workflows: {len(wfs)} | Active Auto: {len(active_wfs)} | Total Runs: {total_runs} ({rate}% OK)",
        ]
        if wfs:
            lines.append("\n⚙️ Active & Recent Workflows:")
            for w in wfs[:max_workflows]:
                en_badge = "🟢 ON" if w.get("is_enabled") else "⏸️ OFF"
                st = w.get("last_status") or "IDLE"
                nxt = w.get("next_run") or "-"
                lines.append(f"- {w.get('name')} [{en_badge}] | Last: {st} | Next: {nxt}")

        if runs:
            lines.append("\n🕒 Recent Executions:")
            for r in runs[:max_runs]:
                icon = "✅" if r.get("status") == "SUCCESS" else ("⚠️" if r.get("status") == "PARTIAL" else "🔴")
                lines.append(f"- {icon} {r.get('workflow_name')} ({r.get('status')}, {r.get('duration_ms', 0)}ms) @ {r.get('started_at')}")

        summary_line = f"Workflows: {len(wfs)} Total ({len(active_wfs)} Active) | Runs: {total_runs} ({rate}% OK)"
        if runs:
            r0 = runs[0]
            summary_line += f" | Latest: {r0.get('workflow_name')}={r0.get('status')}"

        return {
            "total_workflows": len(wfs),
            "active_workflows": len(active_wfs),
            "total_runs": total_runs,
            "success_rate": rate,
            "summary_line": summary_line,
            "report_text": "\n".join(lines),
        }

    @classmethod
    async def install_template(cls, template_id: str) -> Optional[Dict[str, Any]]:
        tpl = next((t for t in WORKFLOW_TEMPLATES if t["id"] == template_id), None)
        if not tpl:
            return None
        payload = dict(tpl)
        payload["id"] = f"wf_{uuid.uuid4().hex[:8]}"
        payload["is_enabled"] = True
        return await cls.create_workflow(payload)

    @classmethod
    async def build_quick_daily_workflow(
        cls,
        name: str,
        instruction: str,
        daily_time: str = "09:00",
        frequency: str = "daily",
        timezone_str: str = "Asia/Dhaka",
        model: str = "",
        project_name: str = "",
        save_report: bool = True,
        save_memory: bool = False,
        post_to_chat: bool = True,
        notify_channels: bool = False,
        custom_webhook_url: str = "",
        language: str = "bn",
        use_mcp: bool = True
    ) -> Dict[str, Any]:
        """
        Synthesizes a complete n8n-style multi-node DAG workflow from natural-language daily instructions.
        """
        schedule_expr = daily_time_to_cron(daily_time, frequency)
        freq_map = {
            "daily": f"প্রতিদিন {daily_time}",
            "hourly": "প্রতি ঘণ্টায়",
            "every_6h": "প্রতি ৬ ঘণ্টায়",
            "weekly": f"সাপ্তাহিক ({daily_time})",
            "every_15m": "প্রতি ১৫ মিনিটে"
        }
        trig_title = f"⏰ {freq_map.get(frequency, f'Daily {daily_time}')}"

        nodes: List[Dict[str, Any]] = [
            {
                "id": "node_1",
                "type": "trigger_daily",
                "title": trig_title,
                "x": 50,
                "y": 150,
                "config": {"daily_time": daily_time, "timezone": timezone_str, "frequency": frequency}
            },
            {
                "id": "node_2",
                "type": "ai_agent",
                "title": "🧠 অটোনোমাস এআই টাস্ক এজেন্ট",
                "x": 360,
                "y": 150,
                "config": {
                    "prompt": f"আজকের তারিখ: {{{{trigger.date}}}} ({{{{trigger.time}}}})\n\nদৈনিক অটোমেটেড টাস্ক নির্দেশনা:\n{instruction.strip()}",
                    "system_instruction": (
                        "You are an autonomous daily agent executing a scheduled user instruction. "
                        "Use available tools (ping, port scan, SQLite inspector, memory search, python sandbox, skills) "
                        "whenever verification or live data is helpful. Produce a clear, structured executive result."
                    ),
                    "model": model or "",
                    "project_name": project_name or "",
                    "use_memory": True,
                    "enable_tools": True,
                    "use_mcp": bool(use_mcp),
                    "language": language or "bn",
                    "max_turns": 6,
                    "fallback_on_error": True
                }
            }
        ]
        edges: List[Dict[str, Any]] = [
            {"id": "e1", "source": "node_1", "target": "node_2", "condition": ""}
        ]

        last_node_id = "node_2"
        next_x = 680

        if save_report:
            rid = f"node_{len(nodes) + 1}"
            nodes.append({
                "id": rid,
                "type": "save_report",
                "title": "📄 দৈনিক AI রিপোর্ট সেভ",
                "x": next_x,
                "y": 150,
                "config": {
                    "title": f"{name} - {{{{trigger.date}}}}",
                    "report_type": "executive_summary",
                    "content": "{{nodes.node_2.output}}",
                    "index_in_memory": True
                }
            })
            edges.append({"id": f"e{len(edges)+1}", "source": last_node_id, "target": rid, "condition": ""})
            last_node_id = rid
            next_x += 310

        if save_memory:
            mid = f"node_{len(nodes) + 1}"
            nodes.append({
                "id": mid,
                "type": "memory_save",
                "title": "💾 প্রজেক্ট মেমোরিতে সেভ",
                "x": next_x,
                "y": 150,
                "config": {
                    "project_name": project_name or "myagent",
                    "key": "daily_auto_{{trigger.date}}",
                    "category": "notes",
                    "context": "production",
                    "content": "{{nodes.node_2.output}}",
                    "save_to_vector": True
                }
            })
            edges.append({"id": f"e{len(edges)+1}", "source": last_node_id, "target": mid, "condition": ""})
            last_node_id = mid
            next_x += 310

        if post_to_chat or notify_channels or custom_webhook_url:
            nid = f"node_{len(nodes) + 1}"
            target_mode = "chat_and_channels" if notify_channels else "chat_session"
            nodes.append({
                "id": nid,
                "type": "notify_channel",
                "title": "📣 চ্যাট ও চ্যানেল নোটিফিকেশন",
                "x": next_x,
                "y": 150,
                "config": {
                    "target": target_mode,
                    "session_title": "📅 Daily Automated Agent Reports",
                    "title": f"⚡ {name} ({{{{trigger.date}}}})",
                    "message": "{{nodes.node_2.output}}",
                    "custom_webhook_url": custom_webhook_url or ""
                }
            })
            edges.append({"id": f"e{len(edges)+1}", "source": last_node_id, "target": nid, "condition": ""})

        return await cls.create_workflow({
            "name": name,
            "description": instruction.strip(),
            "icon": "⚡",
            "trigger_type": "daily" if frequency == "daily" else "cron",
            "schedule_expr": schedule_expr,
            "daily_time": daily_time,
            "timezone": timezone_str,
            "nodes": nodes,
            "edges": edges,
            "is_enabled": True
        })

    @classmethod
    async def sync_missing_next_runs(cls):
        """Ensures all enabled scheduled workflows have a valid future next_run_ts."""
        try:
            db = await cls.get_db()
            try:
                now_ts = time.time()
                async with db.execute(
                    "SELECT id, trigger_type, schedule_expr, timezone, next_run_ts FROM ops_workflows WHERE is_enabled = 1"
                ) as cur:
                    rows = await cur.fetchall()
                for r in rows:
                    ttype = (r["trigger_type"] or "daily").lower()
                    if ttype in ("manual", "webhook"):
                        continue
                    nr_ts = r["next_run_ts"]
                    if not nr_ts or float(nr_ts) <= now_ts:
                        next_str, next_ts, _, _ = compute_next_run(
                            r["schedule_expr"], r["timezone"] or "Asia/Dhaka", ttype
                        )
                        if next_ts:
                            await db.execute(
                                "UPDATE ops_workflows SET next_run = ?, next_run_ts = ? WHERE id = ?",
                                (next_str, next_ts, r["id"])
                            )
                await db.commit()
            finally:
                await db.close()
        except Exception as e:
            logger.error(f"Error syncing workflow next runs: {e}")

    @classmethod
    def _build_runs_where(
        cls,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        trigger_source: Optional[str] = None,
        q: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> tuple[str, List[Any]]:
        clauses = ["1=1"]
        params: List[Any] = []
        if workflow_id:
            clauses.append("workflow_id = ?")
            params.append(workflow_id)
        if status and status.upper() != "ALL":
            clauses.append("UPPER(status) = ?")
            params.append(status.upper())
        if trigger_source and trigger_source.lower() != "all":
            clauses.append("LOWER(trigger_source) = ?")
            params.append(trigger_source.lower())
        clean_q = (q or "").strip()
        if clean_q:
            like_q = f"%{clean_q}%"
            clauses.append(
                "(id LIKE ? OR workflow_name LIKE ? OR workflow_id LIKE ? OR final_output LIKE ? OR error_message LIKE ? OR node_results_json LIKE ?)"
            )
            params.extend([like_q, like_q, like_q, like_q, like_q, like_q])
        if date_from:
            clauses.append("substr(started_at, 1, 10) >= ?")
            params.append(date_from[:10])
        if date_to:
            clauses.append("substr(started_at, 1, 10) <= ?")
            params.append(date_to[:10])
        return " AND ".join(clauses), params

    @classmethod
    async def list_runs(
        cls,
        workflow_id: Optional[str] = None,
        limit: int = 30,
        status: Optional[str] = None,
        trigger_source: Optional[str] = None,
        q: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        res = await cls.query_runs(
            workflow_id=workflow_id,
            status=status,
            trigger_source=trigger_source,
            q=q,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
        return res["runs"]

    @classmethod
    async def query_runs(
        cls,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        trigger_source: Optional[str] = None,
        q: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        db = await cls.get_db()
        try:
            where_sql, params = cls._build_runs_where(
                workflow_id=workflow_id,
                status=status,
                trigger_source=trigger_source,
                q=q,
                date_from=date_from,
                date_to=date_to,
            )
            async with db.execute(
                f"""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN UPPER(status) = 'SUCCESS' THEN 1 ELSE 0 END) AS success_cnt,
                    SUM(CASE WHEN UPPER(status) = 'FAILED' THEN 1 ELSE 0 END) AS failed_cnt,
                    SUM(CASE WHEN UPPER(status) = 'RUNNING' THEN 1 ELSE 0 END) AS running_cnt,
                    SUM(CASE WHEN UPPER(status) = 'STOPPED' THEN 1 ELSE 0 END) AS stopped_cnt,
                    AVG(COALESCE(duration_ms, 0)) AS avg_ms
                FROM ops_workflow_runs
                WHERE {where_sql}
                """,
                tuple(params),
            ) as sc:
                srow = dict(await sc.fetchone())

            safe_limit = max(1, min(int(limit or 50), 200))
            safe_offset = max(0, int(offset or 0))
            sql = f"SELECT * FROM ops_workflow_runs WHERE {where_sql} ORDER BY started_at DESC LIMIT ? OFFSET ?"
            async with db.execute(sql, tuple(params + [safe_limit, safe_offset])) as cur:
                rows = await cur.fetchall()
            runs = []
            for r in rows:
                d = dict(r)
                try:
                    d["node_results"] = json.loads(d.get("node_results_json") or "[]")
                except Exception:
                    d["node_results"] = []
                runs.append(d)

            total = int(srow.get("total") or 0)
            succ = int(srow.get("success_cnt") or 0)
            return {
                "runs": runs,
                "total": total,
                "limit": safe_limit,
                "offset": safe_offset,
                "stats": {
                    "total": total,
                    "success": succ,
                    "failed": int(srow.get("failed_cnt") or 0),
                    "running": int(srow.get("running_cnt") or 0),
                    "stopped": int(srow.get("stopped_cnt") or 0),
                    "avg_duration_ms": int(round(srow.get("avg_ms") or 0)),
                    "success_rate": round((succ / total) * 100, 1) if total > 0 else 100.0,
                },
            }
        finally:
            await db.close()

    @classmethod
    async def get_run(cls, run_id: str) -> Optional[Dict[str, Any]]:
        db = await cls.get_db()
        try:
            async with db.execute("SELECT * FROM ops_workflow_runs WHERE id = ?", (run_id,)) as cur:
                row = await cur.fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d["node_results"] = json.loads(d.get("node_results_json") or "[]")
            except Exception:
                d["node_results"] = []
            return d
        finally:
            await db.close()

    @classmethod
    async def delete_run(cls, run_id: str) -> bool:
        db = await cls.get_db()
        try:
            cur = await db.execute("DELETE FROM ops_workflow_runs WHERE id = ?", (run_id,))
            await db.commit()
            return (cur.rowcount or 0) > 0
        finally:
            await db.close()

    @classmethod
    async def clear_runs(
        cls,
        workflow_id: Optional[str] = None,
        older_than_days: Optional[int] = None,
        status: Optional[str] = None,
    ) -> int:
        db = await cls.get_db()
        try:
            clauses = ["UPPER(status) != 'RUNNING'"]
            params: List[Any] = []
            if workflow_id:
                clauses.append("workflow_id = ?")
                params.append(workflow_id)
            if status and status.upper() != "ALL":
                clauses.append("UPPER(status) = ?")
                params.append(status.upper())
            if older_than_days is not None and int(older_than_days) > 0:
                cutoff = (datetime.now() - timedelta(days=int(older_than_days))).strftime("%Y-%m-%d %H:%M:%S")
                clauses.append("started_at < ?")
                params.append(cutoff)
            where_sql = " AND ".join(clauses)
            cur = await db.execute(f"DELETE FROM ops_workflow_runs WHERE {where_sql}", tuple(params))
            await db.commit()
            return int(cur.rowcount or 0)
        finally:
            await db.close()

    @classmethod
    async def duplicate_workflow(cls, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Creates an editable clone of an existing workflow with fresh ID and webhook secret."""
        src = await cls.get_workflow(workflow_id)
        if not src:
            return None
        clone_payload = {
            "name": f"{src['name']} (Copy)",
            "description": src.get("description", ""),
            "icon": src.get("icon", "⚡"),
            "trigger_type": src.get("trigger_type", "daily"),
            "schedule_expr": src.get("schedule_expr", ""),
            "daily_time": src.get("daily_time", "09:00"),
            "timezone": src.get("timezone", "Asia/Dhaka"),
            "nodes": src.get("nodes", []),
            "edges": src.get("edges", []),
            "is_enabled": False
        }
        return await cls.create_workflow(clone_payload)

    @classmethod
    async def import_workflow(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Imports an exported workflow JSON structure into ops_workflows as a new workflow."""
        wf_data = payload.get("workflow", payload) if isinstance(payload, dict) else {}
        if not isinstance(wf_data, dict) or not wf_data.get("nodes"):
            raise ValueError("Invalid workflow JSON: missing 'nodes' array.")
        clean_payload = {
            "name": (wf_data.get("name") or "Imported n8n Workflow").strip(),
            "description": wf_data.get("description", ""),
            "icon": wf_data.get("icon", "📥"),
            "trigger_type": wf_data.get("trigger_type", "daily"),
            "schedule_expr": wf_data.get("schedule_expr", ""),
            "daily_time": wf_data.get("daily_time", "09:00"),
            "timezone": wf_data.get("timezone", "Asia/Dhaka"),
            "nodes": wf_data.get("nodes", []),
            "edges": wf_data.get("edges", []),
            "is_enabled": bool(wf_data.get("is_enabled", False))
        }
        return await cls.create_workflow(clean_payload)

    @classmethod
    async def architect_workflow_from_goal(
        cls,
        goal: str,
        name: str = "",
        daily_time: str = "09:00",
        frequency: str = "daily",
        timezone_str: str = "Asia/Dhaka",
        model: str = "",
        project_name: str = "",
        auto_enable: bool = True
    ) -> Dict[str, Any]:
        """
        AI Workflow Architect:
        Designs a rich, branched, production-grade multi-node DAG workflow from any plain-language goal.
        Combines LLM planning (when reachable) with deterministic multi-domain architecture synthesis.
        """
        import re as _re
        clean_goal = (goal or "").strip()
        if not clean_goal:
            raise ValueError("Workflow goal cannot be empty.")

        lower = clean_goal.lower()
        schedule_expr = daily_time_to_cron(daily_time, frequency)
        derived_name = (name or "").strip() or (clean_goal[:48] + ("..." if len(clean_goal) > 48 else ""))

        # Detect specialized intents from the user prompt
        wants_ping = any(k in lower for k in ["ping", "network", "lan", "latency", "পিং", "নেটওয়ার্ক", "সার্ভার"])
        wants_ports = any(k in lower for k in ["port", "scan", "পোর্ট", "স্ক্যান", "security", "সিকিউরিটি", "vulnerability", "audit", "dlp"])
        wants_http = any(k in lower for k in ["http", "api", "url", "webhook", "fetch", "endpoint", "এপিআই"])
        wants_mcp = any(k in lower for k in ["mcp", "model context", "fetch_article", "fs_read", "sqlite_schema", "external tool", "এমসিপি"])
        wants_db = any(k in lower for k in ["db", "sql", "sqlite", "database", "query", "ডাটাবেস", "মেমোরি", "নলেজ"])
        wants_python = any(k in lower for k in ["python", "csv", "excel", "metric", "score", "parse", "calculate", "পাইথন", "হিসাব", "স্কোর"])
        wants_memory = any(k in lower for k in ["memory", "remember", "note", "project", "মেমোরি", "নোট", "প্রজেক্ট"])
        wants_condition = any(k in lower for k in ["if ", "else", "alert", "error", "warning", "fail", "down", "যদি", "সতর্ক", "অ্যালার্ট", "সমস্যা"])
        wants_notify_ext = any(k in lower for k in ["telegram", "discord", "slack", "channel", "টেলিগ্রাম", "ডিসকর্ড", "স্ল্যাক", "চ্যানেল"])

        # Extract any URL or IP list mentioned in the prompt
        found_urls = _re.findall(r"https?://[^\s'\"<>]+", clean_goal)
        found_ips = _re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", clean_goal)

        # Optionally attempt LLM refinement for workflow title/prompt enhancement if reachable
        architect_notes = "Deterministic + Autonomous Multi-Node DAG Architecture"

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        # 1. Trigger Node
        freq_labels = {
            "daily": f"প্রতিদিন {daily_time}",
            "hourly": "প্রতি ঘণ্টায়",
            "every_6h": "প্রতি ৬ ঘণ্টায়",
            "weekly": f"সাপ্তাহিক ({daily_time})",
            "every_15m": "প্রতি ১৫ মিনিটে"
        }
        nodes.append({
            "id": "node_1",
            "type": "trigger_daily",
            "title": f"⏰ {freq_labels.get(frequency, daily_time)}",
            "x": 40,
            "y": 150,
            "config": {"daily_time": daily_time, "timezone": timezone_str, "frequency": frequency}
        })

        col_x = 320
        collector_ids: List[str] = []

        # 2. Data Collection / Diagnostics Layer (parallelizable upstream branches!)
        collect_nodes: List[Dict[str, Any]] = []
        if found_ips and len(found_ips) >= 2:
            collect_nodes.append({
                "type": "loop_foreach",
                "title": "🔁 ব্যাচ সার্ভার পিং",
                "config": {
                    "items_text": "\n".join(found_ips[:12]),
                    "action_type": "ping",
                    "tool_name": "network_port_scan",
                    "args_template_json": "{\"target\": \"{{item}}\"}"
                }
            })
        elif wants_ping:
            collect_nodes.append({
                "type": "subagent",
                "title": "🌐 নেটওয়ার্ক ও সার্ভার চেক",
                "config": {
                    "agent_id": "net_ping_subagent",
                    "task": f"Inspect server & network latency for goal: {clean_goal}",
                    "model": model or ""
                }
            })

        if wants_ports:
            target_host = found_ips[0] if found_ips else "127.0.0.1"
            collect_nodes.append({
                "type": "subagent" if not found_ips else "tool_call",
                "title": "🛡️ সিকিউরিটি ও পোর্ট অডিট",
                "config": (
                    {
                        "tool_name": "network_port_scan",
                        "args_json": json.dumps({"target": target_host, "ports": [22, 80, 443, 3399, 8000]})
                    } if found_ips else {
                        "agent_id": "security_auditor_agent",
                        "task": f"Execute security & DLP compliance audit: {clean_goal}",
                        "model": model or ""
                    }
                )
            })

        if wants_http or found_urls:
            collect_nodes.append({
                "type": "http_request",
                "title": "📡 API / HTTP ডেটা ফেচ",
                "config": {
                    "method": "GET",
                    "url": found_urls[0] if found_urls else "https://httpbin.org/get",
                    "headers_json": "{\"Accept\": \"application/json\"}",
                    "body_json": ""
                }
            })

        if wants_mcp:
            mcp_tool_name = "fetch_article_markdown" if found_urls else "fs_read_dir"
            mcp_args = {"url": found_urls[0]} if found_urls else {"path": ""}
            collect_nodes.append({
                "type": "mcp_tool",
                "title": "🔌 MCP টুল এক্সিকিউশন",
                "config": {
                    "server_id": "",
                    "tool_name": mcp_tool_name,
                    "args_json": json.dumps(mcp_args),
                    "fallback_on_error": False
                }
            })

        if wants_db:
            collect_nodes.append({
                "type": "knowledge_db_query",
                "title": "🗄️ DB ও নলেজ কোয়েরি",
                "config": {
                    "query_mode": "sqlite",
                    "db_name": "ops.db",
                    "sql_query": "SELECT name, last_status, run_count, last_run FROM ops_workflows ORDER BY updated_at DESC LIMIT 8;"
                }
            })

        if not collect_nodes:
            # Default telemetry starter tool so AI always has fresh live context
            collect_nodes.append({
                "type": "tool_call",
                "title": "🛠️ সিস্টেম ও রিসোর্স চেক",
                "config": {"tool_name": "system_info", "args_json": "{}"}
            })

        if len(collect_nodes) == 1:
            nid = f"node_{len(nodes) + 1}"
            cnode = collect_nodes[0]
            nodes.append({"id": nid, "type": cnode["type"], "title": cnode["title"], "x": col_x, "y": 150, "config": cnode["config"]})
            edges.append({"id": f"e{len(edges)+1}", "source": "node_1", "target": nid, "condition": ""})
            collector_ids.append(nid)
            col_x += 300
        else:
            start_y = 50
            for idx, cnode in enumerate(collect_nodes):
                nid = f"node_{len(nodes) + 1}"
                nodes.append({"id": nid, "type": cnode["type"], "title": cnode["title"], "x": col_x, "y": start_y + idx * 145, "config": cnode["config"]})
                edges.append({"id": f"e{len(edges)+1}", "source": "node_1", "target": nid, "condition": ""})
                collector_ids.append(nid)
            col_x += 300

            # Automatically insert Merge Combine node to join all parallel fan-out branches cleanly!
            merge_id = f"node_{len(nodes) + 1}"
            nodes.append({
                "id": merge_id,
                "type": "merge_combine",
                "title": "🤝 প্যারালাল ব্রাঞ্চ মার্জ",
                "x": col_x,
                "y": 150,
                "config": {"mode": "markdown_sections", "include_empty": False}
            })
            for src_id in collector_ids:
                edges.append({"id": f"e{len(edges)+1}", "source": src_id, "target": merge_id, "condition": ""})
            collector_ids = [merge_id]
            col_x += 290

        # 3. Optional Python Data Transform Step
        last_stage_ids = list(collector_ids)
        if wants_python:
            py_id = f"node_{len(nodes) + 1}"
            nodes.append({
                "id": py_id,
                "type": "python_transform",
                "title": "🐍 Python ডেটা প্রসেসিং",
                "x": col_x,
                "y": 150,
                "config": {
                    "code": "raw = str(prev_output or '')\nlines = [l.strip() for l in raw.splitlines() if l.strip()]\nerrs = [l for l in lines if any(k in l.upper() for k in ('ERROR', 'FAIL', 'CRITICAL', 'OFFLINE'))]\nprint(f'Summary Metrics -> Total Lines: {len(lines)}, Flags: {len(errs)}')\nprint('\\n'.join(lines[:30]))"
                }
            })
            for src_id in last_stage_ids:
                edges.append({"id": f"e{len(edges)+1}", "source": src_id, "target": py_id, "condition": ""})
            last_stage_ids = [py_id]
            col_x += 290

        # 4. Core Autonomous AI Agent Node (Synthesizes all collected data + uses tools/RAG)
        context_refs = "\n\n".join(f"[{cid} ফলাফল]:\n{{{{nodes.{cid}.output}}}}" for cid in last_stage_ids)
        ai_id = f"node_{len(nodes) + 1}"
        nodes.append({
            "id": ai_id,
            "type": "ai_agent",
            "title": "🧠 অটোনোমাস এআই আর্কিটেক্ট এজেন্ট",
            "x": col_x,
            "y": 150,
            "config": {
                "prompt": (
                    f"আজকের তারিখ: {{{{trigger.date}}}} ({{{{trigger.time}}}})\n\n"
                    f"মূল লক্ষ্য:\n{clean_goal}\n\n"
                    f"সংগৃহীত লাইভ টেলিমেট্রি ও তথ্য:\n{context_refs}\n\n"
                    "সব তথ্য বিশ্লেষণ করে সুস্পষ্ট বাংলা সারসংক্ষেপ, ঝুঁকি বা সমস্যা থাকলে WARNING/ALERT এবং পরবর্তী করণীয় লিখুন।"
                ),
                "system_instruction": "Autonomous workflow specialist. Call additional tools only if missing data is needed, then output a crisp executive summary.",
                "model": model or "",
                "project_name": project_name or "",
                "use_memory": True,
                "enable_tools": True,
                "language": "bn",
                "max_turns": 5,
                "fallback_on_error": True
            }
        })
        for src_id in last_stage_ids:
            edges.append({"id": f"e{len(edges)+1}", "source": src_id, "target": ai_id, "condition": ""})
        col_x += 300

        # 5. Conditional Branching + Outputs Layer
        if wants_condition or wants_notify_ext:
            cond_id = f"node_{len(nodes) + 1}"
            nodes.append({
                "id": cond_id,
                "type": "condition",
                "title": "🔀 সতর্কতা যাচাই (IF Issue?)",
                "x": col_x,
                "y": 150,
                "config": {
                    "target": "{{prev.output}}",
                    "operator": "regex",
                    "value": "(ALERT|CRITICAL|ERROR|FAILED|OFFLINE|WARNING)"
                }
            })
            edges.append({"id": f"e{len(edges)+1}", "source": ai_id, "target": cond_id, "condition": ""})
            col_x += 290

            # True Branch -> Priority Notify
            alert_id = f"node_{len(nodes) + 1}"
            nodes.append({
                "id": alert_id,
                "type": "notify_channel",
                "title": "🚨 প্রায়োরিটি অ্যালার্ট নোটিফাই",
                "x": col_x,
                "y": 55,
                "config": {
                    "target": "chat_and_channels",
                    "session_title": "📅 Daily Automated Agent Reports",
                    "title": f"🚨 ALERT: {derived_name} ({{{{trigger.date}}}})",
                    "message": f"{{{{nodes.{ai_id}.output}}}}",
                    "custom_webhook_url": ""
                }
            })
            edges.append({"id": f"e{len(edges)+1}", "source": cond_id, "target": alert_id, "condition": "true"})

            # False Branch -> Save Report (+ optional Memory + Chat Digest)
            rpt_id = f"node_{len(nodes) + 1}"
            nodes.append({
                "id": rpt_id,
                "type": "save_report",
                "title": "📄 দৈনিক AI রিপোর্ট আর্কাইভ",
                "x": col_x,
                "y": 245,
                "config": {
                    "title": f"{derived_name} - {{{{trigger.date}}}}",
                    "report_type": "executive_summary",
                    "content": f"{{{{nodes.{ai_id}.output}}}}",
                    "index_in_memory": True
                }
            })
            edges.append({"id": f"e{len(edges)+1}", "source": cond_id, "target": rpt_id, "condition": "false"})

            col_x += 290
            prev_out = rpt_id
            if wants_memory or project_name:
                mem_id = f"node_{len(nodes) + 1}"
                nodes.append({
                    "id": mem_id,
                    "type": "memory_save",
                    "title": "💾 প্রজেক্ট মেমোরিতে সেভ",
                    "x": col_x,
                    "y": 245,
                    "config": {
                        "project_name": project_name or "myagent",
                        "key": "arch_daily_{{trigger.date}}",
                        "category": "notes",
                        "context": "production",
                        "content": f"{{{{nodes.{ai_id}.output}}}}",
                        "save_to_vector": True
                    }
                })
                edges.append({"id": f"e{len(edges)+1}", "source": prev_out, "target": mem_id, "condition": ""})
                prev_out = mem_id
                col_x += 280

            chat_id = f"node_{len(nodes) + 1}"
            nodes.append({
                "id": chat_id,
                "type": "notify_channel",
                "title": "💬 চ্যাট ডাইজেস্ট পাঠান",
                "x": col_x,
                "y": 245,
                "config": {
                    "target": "chat_session",
                    "session_title": "📅 Daily Automated Agent Reports",
                    "title": f"✅ {derived_name} ({{{{trigger.date}}}})",
                    "message": f"{{{{nodes.{ai_id}.output}}}}",
                    "custom_webhook_url": ""
                }
            })
            edges.append({"id": f"e{len(edges)+1}", "source": prev_out, "target": chat_id, "condition": ""})
        else:
            prev_out = ai_id
            rpt_id = f"node_{len(nodes) + 1}"
            nodes.append({
                "id": rpt_id,
                "type": "save_report",
                "title": "📄 দৈনিক AI রিপোর্ট আর্কাইভ",
                "x": col_x,
                "y": 150,
                "config": {
                    "title": f"{derived_name} - {{{{trigger.date}}}}",
                    "report_type": "executive_summary",
                    "content": f"{{{{nodes.{ai_id}.output}}}}",
                    "index_in_memory": True
                }
            })
            edges.append({"id": f"e{len(edges)+1}", "source": prev_out, "target": rpt_id, "condition": ""})
            prev_out = rpt_id
            col_x += 290

            if wants_memory or project_name:
                mem_id = f"node_{len(nodes) + 1}"
                nodes.append({
                    "id": mem_id,
                    "type": "memory_save",
                    "title": "💾 প্রজেক্ট মেমোরিতে সেভ",
                    "x": col_x,
                    "y": 150,
                    "config": {
                        "project_name": project_name or "myagent",
                        "key": "arch_daily_{{trigger.date}}",
                        "category": "notes",
                        "context": "production",
                        "content": f"{{{{nodes.{ai_id}.output}}}}",
                        "save_to_vector": True
                    }
                })
                edges.append({"id": f"e{len(edges)+1}", "source": prev_out, "target": mem_id, "condition": ""})
                prev_out = mem_id
                col_x += 290

            chat_id = f"node_{len(nodes) + 1}"
            nodes.append({
                "id": chat_id,
                "type": "notify_channel",
                "title": "📣 চ্যাট ও চ্যানেল নোটিফিকেশন",
                "x": col_x,
                "y": 150,
                "config": {
                    "target": "chat_and_channels" if wants_notify_ext else "chat_session",
                    "session_title": "📅 Daily Automated Agent Reports",
                    "title": f"⚡ {derived_name} ({{{{trigger.date}}}})",
                    "message": f"{{{{nodes.{ai_id}.output}}}}",
                    "custom_webhook_url": ""
                }
            })
            edges.append({"id": f"e{len(edges)+1}", "source": prev_out, "target": chat_id, "condition": ""})

        wf = await cls.create_workflow({
            "name": derived_name,
            "description": f"{clean_goal} ({architect_notes})",
            "icon": "🧠",
            "trigger_type": "daily" if frequency == "daily" else "cron",
            "schedule_expr": schedule_expr,
            "daily_time": daily_time,
            "timezone": timezone_str,
            "nodes": nodes,
            "edges": edges,
            "is_enabled": auto_enable
        })
        return wf

