# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 3.5.0
# Shared Telegram Bot API Service for Workflows (Auto) & Ops Channels
# ==============================================================================

import re
import time
import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

from workflows.store import WorkflowStore

logger = logging.getLogger("myagent.workflows.telegram")

TELEGRAM_API_BASE = "https://api.telegram.org"


TELEGRAM_BOT_COMMANDS = [
    {"command": "status", "description": "Show WORKFLOWS (Auto) live status & recent runs"},
    {"command": "ping", "description": "Ping server(s) e.g. /ping 192.168.9.2 + workflow status"},
    {"command": "port", "description": "TCP port scan host e.g. /port 192.168.9.2"},
    {"command": "health", "description": "Live CPU, RAM, Disk & Docker server health"},
    {"command": "history", "description": "Show last 5 workflow execution runs & traces"},
    {"command": "workflows", "description": "List all saved daily workflows & schedules"},
    {"command": "run", "description": "Execute a workflow immediately e.g. /run morning"},
    {"command": "enable", "description": "Enable a workflow schedule e.g. /enable morning"},
    {"command": "disable", "description": "Pause a workflow schedule e.g. /disable morning"},
    {"command": "create", "description": "Auto-create a daily workflow from plain goal"},
    {"command": "id", "description": "Show your Telegram Chat ID & quick commands"},
    {"command": "help", "description": "Show interactive command reference"},
]


def _sanitize_tg_error(err_text: str, token: str) -> str:
    msg = str(err_text or "")
    if token and len(token) >= 6:
        msg = msg.replace(token, WorkflowStore.mask_telegram_token(token) or "***BOT_TOKEN***")
    return msg[:450]


async def telegram_verify_token(token: str) -> Dict[str, Any]:
    """Calls Telegram getMe to verify token validity and fetch bot identity."""
    tok = (token or "").strip()
    if not tok:
        return {
            "ok": False,
            "http_status": 0,
            "latency_ms": 0,
            "bot_id": "",
            "bot_username": "",
            "bot_first_name": "",
            "error": "Bot token is empty.",
        }

    t0 = time.time()
    url = f"{TELEGRAM_API_BASE}/bot{tok}/getMe"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
        latency_ms = int((time.time() - t0) * 1000)
        try:
            body = resp.json()
        except Exception:
            body = {}

        if resp.status_code == 200 and body.get("ok") and isinstance(body.get("result"), dict):
            r = body["result"]
            uname = r.get("username") or ""
            if uname and not uname.startswith("@"):
                uname = f"@{uname}"
            return {
                "ok": True,
                "http_status": 200,
                "latency_ms": latency_ms,
                "bot_id": str(r.get("id") or ""),
                "bot_username": uname,
                "bot_first_name": str(r.get("first_name") or ""),
                "error": "",
            }

        desc = body.get("description") or resp.text[:200] or f"HTTP {resp.status_code}"
        return {
            "ok": False,
            "http_status": resp.status_code,
            "latency_ms": latency_ms,
            "bot_id": "",
            "bot_username": "",
            "bot_first_name": "",
            "error": _sanitize_tg_error(desc, tok),
        }
    except Exception as e:
        return {
            "ok": False,
            "http_status": 0,
            "latency_ms": int((time.time() - t0) * 1000),
            "bot_id": "",
            "bot_username": "",
            "bot_first_name": "",
            "error": _sanitize_tg_error(str(e), tok),
        }


async def telegram_detect_chats(token: str, bot_username: str = "") -> Dict[str, Any]:
    """Queries Telegram getUpdates to discover recent Chat IDs that interacted with the bot."""
    tok = (token or "").strip()
    if not tok:
        return {"ok": False, "chats": [], "error": "No saved bot token found."}

    t0 = time.time()
    url = f"{TELEGRAM_API_BASE}/bot{tok}/getUpdates"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params={"limit": 20})
            if resp.status_code == 409:
                # Auto-clear conflicting webhook so long-polling getUpdates works immediately
                await client.post(
                    f"{TELEGRAM_API_BASE}/bot{tok}/deleteWebhook",
                    json={"drop_pending_updates": False},
                )
                resp = await client.get(url, params={"limit": 20})
        latency_ms = int((time.time() - t0) * 1000)
        try:
            body = resp.json()
        except Exception:
            body = {}

        if resp.status_code != 200 or not body.get("ok"):
            desc = body.get("description") or f"HTTP {resp.status_code}"
            err = _sanitize_tg_error(desc, tok)
            await WorkflowStore.record_telegram_log(
                event_type="detect_chat",
                status="FAILED",
                bot_username=bot_username,
                message_preview="Auto-detect Chat ID (/getUpdates)",
                http_status=resp.status_code,
                error_detail=err,
                latency_ms=latency_ms,
            )
            return {"ok": False, "chats": [], "error": err}

        seen: Dict[str, Dict[str, Any]] = {}
        for upd in body.get("result") or []:
            msg = upd.get("message") or upd.get("edited_message") or upd.get("channel_post") or upd.get("my_chat_member") or {}
            chat = msg.get("chat") or {}
            cid = chat.get("id")
            if cid is None:
                continue
            cid_str = str(cid)
            label = chat.get("title") or " ".join(filter(None, [chat.get("first_name"), chat.get("last_name")])) or chat.get("username") or cid_str
            seen[cid_str] = {
                "chat_id": cid_str,
                "type": chat.get("type", "private"),
                "title": label,
                "username": f"@{chat['username']}" if chat.get("username") else "",
                "sample_text": str(msg.get("text") or "")[:80],
            }

        # Include previously recorded interactive chat IDs in case polling consumed /getUpdates
        try:
            recent_chats = await WorkflowStore.list_telegram_chats(limit=20)
            for ch in recent_chats:
                cid_str = str(ch.get("chat_id") or "").strip()
                if cid_str and cid_str not in seen:
                    seen[cid_str] = {
                        "chat_id": cid_str,
                        "type": "private",
                        "title": ch.get("sender_name") or cid_str,
                        "username": "",
                        "sample_text": str(ch.get("user_message") or "")[:80],
                    }
        except Exception:
            pass

        chats = list(seen.values())
        await WorkflowStore.record_telegram_log(
            event_type="detect_chat",
            status="SUCCESS",
            bot_username=bot_username,
            chat_id=chats[0]["chat_id"] if chats else "",
            message_preview=f"Detected {len(chats)} chat(s) from /getUpdates",
            http_status=200,
            latency_ms=latency_ms,
        )
        return {"ok": True, "chats": chats, "error": ""}
    except Exception as e:
        err = _sanitize_tg_error(str(e), tok)
        await WorkflowStore.record_telegram_log(
            event_type="detect_chat",
            status="FAILED",
            bot_username=bot_username,
            message_preview="Auto-detect Chat ID (/getUpdates)",
            error_detail=err,
            latency_ms=int((time.time() - t0) * 1000),
        )
        return {"ok": False, "chats": [], "error": err}


async def telegram_sync_commands(token: str) -> bool:
    """Registers slash command autocomplete menu on the Telegram Bot via setMyCommands."""
    tok = (token or "").strip()
    if not tok:
        return False
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                f"{TELEGRAM_API_BASE}/bot{tok}/setMyCommands",
                json={"commands": TELEGRAM_BOT_COMMANDS},
            )
        return resp.status_code == 200
    except Exception:
        return False


async def telegram_send_chat_action(token: str, chat_id: str, action: str = "typing") -> None:
    """Shows immediate 'typing...' indicator inside Telegram while heavy diagnostics run."""
    tok = (token or "").strip()
    cid = (chat_id or "").strip()
    if not tok or not cid:
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{TELEGRAM_API_BASE}/bot{tok}/sendChatAction",
                json={"chat_id": cid, "action": action},
            )
    except Exception:
        pass


def _split_telegram_text(text: str, max_len: int = 3850) -> List[str]:
    clean = (text or "").strip() or "(Empty workflow message)"
    if len(clean) <= max_len:
        return [clean]
    chunks: List[str] = []
    remaining = clean
    while remaining and len(chunks) < 3:
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n", 0, max_len)
        if split_at < max_len // 2:
            split_at = max_len
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    if remaining and chunks:
        chunks[-1] = chunks[-1][:max_len - 20] + "\n... (truncated)"
    return chunks


async def telegram_send_message(
    token: str,
    chat_id: str,
    text: str,
    parse_mode: str = "",
    event_type: str = "workflow_notify",
    workflow_id: str = "",
    workflow_name: str = "",
    node_id: str = "",
    bot_username: str = "",
) -> Dict[str, Any]:
    """Sends a real Telegram Bot API sendMessage, logs telemetry, and updates connection health."""
    tok = (token or "").strip()
    cid = (chat_id or "").strip()
    clean_text = (text or "").strip()[:11500] or "(Empty workflow message)"
    preview = clean_text.replace("\n", " ")[:180]
    now_s = time.strftime("%Y-%m-%d %H:%M:%S")

    if not tok or not cid:
        missing = "Bot Token" if not tok else "Chat ID"
        err = f"Telegram configuration incomplete: missing {missing}."
        await WorkflowStore.record_telegram_log(
            event_type=event_type,
            status="FAILED",
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            node_id=node_id,
            bot_username=bot_username,
            chat_id=cid,
            message_preview=preview,
            error_detail=err,
        )
        return {
            "ok": False,
            "http_status": 0,
            "telegram_message_id": "",
            "latency_ms": 0,
            "error": err,
        }

    bot_prefix_id = tok.split(":")[0].strip() if ":" in tok else ""
    if bot_prefix_id and cid == bot_prefix_id:
        try:
            cfg_fallback = await WorkflowStore.get_telegram_config(include_plaintext_token=False)
            allowed_candidates = [
                x.strip()
                for x in (cfg_fallback.get("allowed_chat_ids") or "").split(",")
                if x.strip() and x.strip() != bot_prefix_id
            ]
            if allowed_candidates:
                cid = allowed_candidates[0]
            else:
                err = "Target Chat ID cannot be the Bot's own ID. Send /start to your bot and click Auto-Detect Chat ID."
                await WorkflowStore.record_telegram_log(
                    event_type=event_type,
                    status="FAILED",
                    workflow_id=workflow_id,
                    workflow_name=workflow_name,
                    node_id=node_id,
                    bot_username=bot_username,
                    chat_id=cid,
                    message_preview=preview,
                    error_detail=err,
                )
                return {
                    "ok": False,
                    "http_status": 403,
                    "telegram_message_id": "",
                    "latency_ms": 0,
                    "error": err,
                }
        except Exception:
            pass

    t0 = time.time()
    url = f"{TELEGRAM_API_BASE}/bot{tok}/sendMessage"
    chunks = _split_telegram_text(clean_text, max_len=3850)
    pm = (parse_mode or "").strip()

    try:
        resp = None
        body: Dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=14.0) as client:
            for chunk_txt in chunks:
                payload: Dict[str, Any] = {"chat_id": cid, "text": chunk_txt}
                if pm in ("Markdown", "MarkdownV2", "HTML"):
                    payload["parse_mode"] = pm
                resp = await client.post(url, json=payload)
                # Retry once as plain text if entity parsing fails on rich agent markdown output
                if resp.status_code == 400 and "parse_mode" in payload and "parse entities" in resp.text.lower():
                    payload.pop("parse_mode", None)
                    resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    break

        latency_ms = int((time.time() - t0) * 1000)
        try:
            body = resp.json() if resp is not None else {}
        except Exception:
            body = {}

        if resp.status_code == 200 and body.get("ok"):
            msg_id = str((body.get("result") or {}).get("message_id") or "")
            await WorkflowStore.record_telegram_log(
                event_type=event_type,
                status="SENT",
                workflow_id=workflow_id,
                workflow_name=workflow_name,
                node_id=node_id,
                bot_username=bot_username,
                chat_id=cid,
                message_preview=preview,
                http_status=200,
                telegram_message_id=msg_id,
                latency_ms=latency_ms,
            )
            await WorkflowStore.save_telegram_config(
                status="Connected",
                last_tested_at=now_s,
                last_error="",
            )
            return {
                "ok": True,
                "http_status": 200,
                "telegram_message_id": msg_id,
                "latency_ms": latency_ms,
                "error": "",
            }

        desc = body.get("description") or resp.text[:220] or f"HTTP {resp.status_code}"
        err = _sanitize_tg_error(desc, tok)
        await WorkflowStore.record_telegram_log(
            event_type=event_type,
            status="FAILED",
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            node_id=node_id,
            bot_username=bot_username,
            chat_id=cid,
            message_preview=preview,
            http_status=resp.status_code,
            error_detail=err,
            latency_ms=latency_ms,
        )
        new_st = "Error" if resp.status_code == 401 else None
        await WorkflowStore.save_telegram_config(
            status=new_st,
            last_tested_at=now_s,
            last_error=err,
        )
        return {
            "ok": False,
            "http_status": resp.status_code,
            "telegram_message_id": "",
            "latency_ms": latency_ms,
            "error": err,
        }
    except Exception as e:
        latency_ms = int((time.time() - t0) * 1000)
        err = _sanitize_tg_error(str(e), tok)
        await WorkflowStore.record_telegram_log(
            event_type=event_type,
            status="FAILED",
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            node_id=node_id,
            bot_username=bot_username,
            chat_id=cid,
            message_preview=preview,
            error_detail=err,
            latency_ms=latency_ms,
        )
        await WorkflowStore.save_telegram_config(last_tested_at=now_s, last_error=err)
        return {
            "ok": False,
            "http_status": 0,
            "telegram_message_id": "",
            "latency_ms": latency_ms,
            "error": err,
        }


def format_workflow_execution_report(run_res: Dict[str, Any]) -> str:
    """Formats a crisp Telegram-ready execution report for a finished WORKFLOWS (Auto) run."""
    st = str(run_res.get("status") or "UNKNOWN").upper()
    icon = "✅" if st == "SUCCESS" else ("⚠️" if st == "PARTIAL" else ("🛑" if st == "CANCELLED" else "❌"))
    wf_name = run_res.get("workflow_name") or run_res.get("workflow_id") or "Workflow"
    dur = run_res.get("duration_ms", 0)
    trig = run_res.get("trigger_source", "auto")
    steps = run_res.get("node_results") or []
    step_lines = []
    for s in steps[:10]:
        s_st = s.get("status", "")
        s_ic = "✅" if s_st == "SUCCESS" else ("⏭️" if s_st == "SKIPPED" else "❌")
        step_lines.append(f"{s_ic} {s.get('title', s.get('type'))}: {s.get('summary') or s_st}")

    final_out = str(run_res.get("final_output") or "").strip()
    if len(final_out) > 1200:
        final_out = final_out[:1200] + "..."
    err_msg = str(run_res.get("error_message") or "").strip()

    lines = [
        f"{icon} WORKFLOWS (Auto) Report — {wf_name}",
        f"• Status: {st} | Trigger: {trig} | Duration: {dur}ms",
        f"• Finished: {run_res.get('finished_at') or time.strftime('%Y-%m-%d %H:%M:%S')} | Next: {run_res.get('next_run') or '-'}",
    ]
    if step_lines:
        lines.append("\n🧩 Pipeline Steps:\n" + "\n".join(step_lines))
    if final_out:
        lines.append("\n📄 Output:\n" + final_out)
    if err_msg and st in ("FAILED", "CANCELLED"):
        lines.append("\n⚠️ Error: " + err_msg[:300])
    return "\n".join(lines)[:3850]


def _extract_targets(text: str) -> List[str]:
    ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)
    if ips:
        # Deduplicate while preserving order
        seen: List[str] = []
        for ip in ips:
            if ip not in seen:
                seen.append(ip)
        return seen[:5]

    m = re.search(r"(?:ping|port|check|server)\s+([a-zA-Z0-9][a-zA-Z0-9.-]{2,60})", text, flags=re.IGNORECASE)
    if m:
        cand = m.group(1).strip(".,;!?")
        noise = {"server", "status", "and", "show", "check", "now", "please", "workflow", "workflows"}
        if cand.lower() not in noise and ("." in cand or "-" in cand):
            return [cand]
    return []


async def handle_telegram_chat_message(
    chat_id: str,
    sender_name: str,
    text: str,
    dry_send: bool = False,
    source: str = "telegram",
) -> Dict[str, Any]:
    """
    Processes an interactive Telegram chat message (e.g. 'ping 192.168.9.2 server and show status'),
    executes diagnostics / WORKFLOWS (Auto) actions, records both chat & log entries, and replies to Telegram.
    """
    t0 = time.time()
    msg = (text or "").strip()
    low = msg.lower()
    targets = _extract_targets(msg)
    intent = "ai_chat"
    linked_wf_id = ""
    action_status = "SUCCESS"

    # Resolve current WORKFLOWS (Auto) snapshot upfront
    wf_digest = await WorkflowStore.build_workflows_status_report(max_workflows=6, max_runs=4)
    wf_status_summary = wf_digest["summary_line"]
    reply_text = ""

    # A. /start, /id, /help
    if re.match(r"^/(start|id|help)\b", low) or low in ("help", "menu", "commands"):
        intent = "help"
        reply_text = (
            f"🤖 MyAgent WORKFLOWS (Auto) Interactive Bot\n"
            f"🆔 Your Chat ID: `{chat_id}`\n\n"
            f"⚡ Quick Chat Commands:\n"
            f"• `ping 192.168.9.2` — সার্ভার পিং + WORKFLOWS (Auto) স্ট্যাটাস\n"
            f"• `/port 192.168.9.2` — পোর্ট স্ক্যান + স্ট্যাটাস\n"
            f"• `/health` — CPU, RAM, Disk ও সার্ভার হেলথ\n"
            f"• `/status` — WORKFLOWS (Auto) পূর্ণ স্ট্যাটাস রিপোর্ট\n"
            f"• `/history` — সাম্প্রতিক ৫টি ওয়ার্কফ্লো রান ইতিহাস\n"
            f"• `/workflows` — সব ওয়ার্কফ্লোর তালিকা ও সময়সূচি\n"
            f"• `/run <name_or_id>` — তাৎক্ষণিক ওয়ার্কফ্লো রান ও রিপোর্ট\n"
            f"• `/enable <name>` / `/disable <name>` — শিডিউল অন/অফ\n"
            f"• `/create <daily goal>` — অটো নতুন ডেইলি ওয়ার্কফ্লো তৈরি\n\n"
            f"{wf_digest['report_text']}"
        )

    # B. /create <goal>
    elif re.match(r"^/(create|architect)\s+(.+)", msg, flags=re.IGNORECASE) or low.startswith("create workflow "):
        intent = "workflow_create"
        goal = re.sub(r"^(?:/create|/architect|create\s+workflow)\s+", "", msg, flags=re.IGNORECASE).strip()
        wf = await WorkflowStore.architect_workflow_from_goal(goal=goal, is_enabled=True)
        linked_wf_id = wf["id"]
        node_chain = " → ".join(n.get("title") or n.get("type") for n in (wf.get("nodes") or []))
        wf_digest = await WorkflowStore.build_workflows_status_report(max_workflows=6, max_runs=4)
        wf_status_summary = wf_digest["summary_line"]
        reply_text = (
            f"⚡ New Workflow Created & Activated!\n"
            f"• Name: {wf['name']}\n"
            f"• ID: {wf['id']} | Schedule: {wf.get('human_bn') or wf.get('daily_time')}\n"
            f"• Nodes ({len(wf.get('nodes', []))}): {node_chain}\n\n"
            f"{wf_digest['report_text']}"
        )

    # C. /run <name_or_id>
    elif re.match(r"^/run\s+(.+)", msg, flags=re.IGNORECASE) or re.match(r"^run\s+workflow\s+(.+)", msg, flags=re.IGNORECASE):
        intent = "workflow_run"
        query = re.sub(r"^(?:/run|run\s+workflow)\s+", "", msg, flags=re.IGNORECASE).strip().lower()
        all_wfs = await WorkflowStore.list_workflows()
        matched = next(
            (w for w in all_wfs if w["id"].lower() == query or query in (w.get("name") or "").lower()),
            None,
        )
        if not matched:
            action_status = "FAILED"
            names_preview = "\n".join(f"• {w['id']}: {w['name']}" for w in all_wfs[:8])
            reply_text = (
                f"❌ Workflow '{query}' পাওয়া যায়নি।\n\nAvailable Workflows:\n{names_preview or '(None)'}\n\n"
                f"📊 {wf_status_summary}"
            )
        else:
            from workflows.engine import workflow_engine
            linked_wf_id = matched["id"]
            run_res = await workflow_engine.execute_workflow(
                workflow_id=matched["id"],
                trigger_source="telegram_chat",
                trigger_payload={"chat_id": chat_id, "sender": sender_name, "command": msg},
            )
            action_status = "SUCCESS" if run_res.get("success") else "FAILED"
            wf_digest = await WorkflowStore.build_workflows_status_report(max_workflows=6, max_runs=4)
            wf_status_summary = wf_digest["summary_line"]
            reply_text = format_workflow_execution_report(run_res)

    # D. Port Scan
    elif re.match(r"^/port\b", low) or ("port" in low and targets):
        intent = "port_scan"
        target_host = targets[0] if targets else ""
        if not target_host:
            action_status = "FAILED"
            reply_text = f"❌ পোর্ট স্ক্যানের জন্য IP বা হোস্ট দিন (যেমন `/port 192.168.9.2`)।\n\n{wf_digest['report_text']}"
        else:
            from agent.tools import AgentTools
            port_report = await AgentTools.network_port_scan(target=target_host)
            reply_text = f"🔍 Port Scan ({target_host}):\n{port_report[:1600]}\n\n{wf_digest['report_text']}"

    # E. Network Ping Diagnostics (User example: "ping 192.168.9.2 server and let me show status")
    elif re.match(r"^/ping\b", low) or (
        targets and (
            "ping" in low or "পিং" in msg or "status" in low or "check" in low
            or "server" in low or "সার্ভার" in msg or "online" in low or "alive" in low
        )
    ):
        intent = "ping"
        if not targets:
            action_status = "FAILED"
            reply_text = f"❌ পিং করার জন্য টার্গেট IP লিখুন (যেমন: `ping 192.168.9.2`)।\n\n{wf_digest['report_text']}"
        else:
            from agent.subagents.ping_agent import NetworkPingSubAgent
            ping_results = await asyncio.gather(
                *[NetworkPingSubAgent.ping_target(target=t, ping_type="icmp", count=3) for t in targets]
            )
            ping_lines = []
            any_offline = False
            for r in ping_results:
                st = r.get("status", "UNKNOWN")
                if st == "OFFLINE":
                    any_offline = True
                ic = "🟢" if st == "ONLINE" else ("🟡" if st == "DEGRADED" else "🔴")
                ping_lines.append(
                    f"{ic} Server {r.get('target_ip')} — Status: {st}\n"
                    f"   • Avg Latency: {r.get('latency_ms', 'N/A')} ms | Packet Loss: {r.get('packet_loss', 0)}%\n"
                    f"   • Method: {r.get('method', 'ICMP')} (From: {r.get('source_server_ip', '192.168.9.9')})"
                )
            if any_offline and len(ping_results) == 1:
                action_status = "WARN"
            reply_text = (
                "📡 Server Ping & Live Status Report\n"
                + "\n".join(ping_lines)
                + "\n\n"
                + wf_digest["report_text"]
            )

    # E2. Server Health (/health, cpu, ram, disk)
    elif re.match(r"^/health\b", low) or any(
        k in low for k in ["server health", "সার্ভার হেলথ", "system info", "cpu usage", "ram usage", "disk space"]
    ):
        intent = "server_health"
        from agent.tools import AgentTools
        sys_txt = await asyncio.to_thread(AgentTools.system_info)
        reply_text = f"🏥 Live Server Health Diagnostics:\n{sys_txt[:1800]}\n\n{wf_digest['report_text']}"

    # E3. Recent Workflow Execution History (/history, /runs, recent runs)
    elif re.match(r"^/(history|runs|logs)\b", low) or any(
        k in low for k in ["run history", "recent runs", "last run", "গত রান", "হিস্ট্রি"]
    ):
        intent = "workflow_history"
        recent_runs = await WorkflowStore.list_runs(limit=6)
        if not recent_runs:
            reply_text = f"📜 এখনও কোনো ওয়ার্কফ্লো রান ইতিহাস নেই।\n\n{wf_digest['report_text']}"
        else:
            r_lines = ["📜 Recent WORKFLOWS (Auto) Executions (Last 6):"]
            for idx, rr in enumerate(recent_runs, 1):
                rst = str(rr.get("status") or "").upper()
                ric = "✅" if rst == "SUCCESS" else ("⚠️" if rst == "PARTIAL" else ("🛑" if rst == "STOPPED" else "❌"))
                snip = (rr.get("error_message") or rr.get("final_output") or "").replace("\n", " ").strip()[:110]
                r_lines.append(
                    f"{idx}. {ric} {rr.get('workflow_name') or rr.get('workflow_id')} [{rst}]\n"
                    f"   • Trigger: {rr.get('trigger_source', 'manual')} | {rr.get('duration_ms', 0)}ms | {rr.get('started_at', '')}\n"
                    + (f"   • Output: {snip}" if snip else "")
                )
            reply_text = "\n".join(r_lines) + f"\n\n📊 {wf_status_summary}"

    # E4. List Workflows (/workflows, /list)
    elif re.match(r"^/(workflows|list)\b", low) or low in ("workflows", "list workflows"):
        intent = "workflow_list"
        all_wfs = await WorkflowStore.list_workflows()
        if not all_wfs:
            reply_text = "⚙️ কোনো সংরক্ষিত ওয়ার্কফ্লো পাওয়া যায়নি।"
        else:
            w_lines = [f"⚙️ Saved WORKFLOWS (Auto) ({len(all_wfs)}):"]
            for w in all_wfs[:15]:
                st_badge = "🟢 ON" if w.get("is_enabled") else "⏸️ OFF"
                w_lines.append(
                    f"• {w.get('icon', '⚡')} {w.get('name')} [{st_badge}]\n"
                    f"  ID: `{w['id']}` | Sched: {w.get('human_bn') or w.get('daily_time') or w.get('trigger_type')} | Last: {w.get('last_status', 'IDLE')} | Next: {w.get('next_run') or '-'}"
                )
            reply_text = "\n".join(w_lines)

    # E5. Enable / Disable Workflow Schedule (/enable <q> | /disable <q>)
    elif re.match(r"^/(enable|disable)\s+(.+)", msg, flags=re.IGNORECASE):
        m_tog = re.match(r"^/(enable|disable)\s+(.+)", msg, flags=re.IGNORECASE)
        want_enable = m_tog.group(1).lower() == "enable"
        query = m_tog.group(2).strip().lower()
        intent = "workflow_toggle"
        all_wfs = await WorkflowStore.list_workflows()
        matched = next(
            (w for w in all_wfs if w["id"].lower() == query or query in (w.get("name") or "").lower()),
            None,
        )
        if not matched:
            action_status = "FAILED"
            reply_text = f"❌ Workflow '{query}' পাওয়া যায়নি।\n\n{wf_digest['report_text']}"
        else:
            linked_wf_id = matched["id"]
            updated_wf = await WorkflowStore.set_workflow_enabled(matched["id"], want_enable)
            wf_digest = await WorkflowStore.build_workflows_status_report(max_workflows=6, max_runs=4)
            wf_status_summary = wf_digest["summary_line"]
            state_txt = "🟢 ENABLED" if want_enable else "⏸️ PAUSED"
            reply_text = (
                f"{state_txt} Workflow '{matched['name']}' (`{matched['id']}`)\n"
                f"• Next Run: {(updated_wf or {}).get('next_run') or '-'}\n\n"
                f"{wf_digest['report_text']}"
            )

    # F. Explicit WORKFLOWS (Auto) Status / Report
    elif re.match(r"^/(status|report)\b", low) or any(
        k in low for k in ["workflow status", "workflows status", "ওয়ার্কফ্লো", "স্ট্যাটাস", "রিপোর্ট", "auto report", "show status"]
    ):
        intent = "workflow_status"
        reply_text = wf_digest["report_text"]

    # G. General AI Chat fallback (with RAG + ProjectMemory offline synthesis if LLM unreachable)
    else:
        intent = "ai_chat"
        try:
            from agent.core_agent import get_shared_agent
            agent = get_shared_agent()
            ai_res = await asyncio.wait_for(
                agent.run_autonomous_task(
                    prompt=f"[Telegram Chat Request from {sender_name or chat_id}]: {msg}\n(Also be concise for Telegram.)",
                    use_memory=True,
                    enable_tools=True,
                    language="bn",
                    max_turns=4,
                ),
                timeout=45.0,
            )
            if ai_res.get("success") and ai_res.get("output"):
                reply_text = f"{ai_res['output'][:2200]}\n\n---\n📊 {wf_status_summary}"
            else:
                err_txt = ai_res.get("error") or "Primary LLM offline"
                kb_snippets: List[str] = []
                try:
                    from memory.project_store import ProjectMemoryStore
                    pm_hits = await ProjectMemoryStore.search_memories(query=msg[:120], limit=3)
                    for h in pm_hits[:3]:
                        kb_snippets.append(f"• [{h.get('project_name')}/{h.get('key')}]: {str(h.get('content') or '')[:220]}")
                except Exception:
                    pass
                try:
                    from memory.vector_store import VectorMemoryStore
                    v_hits = VectorMemoryStore().search(msg[:120], top_k=2)
                    for vh in v_hits[:2]:
                        meta = vh.get("metadata") or {}
                        kb_snippets.append(f"• [Memory: {meta.get('title') or meta.get('source', 'Note')}]: {str(vh.get('content') or '')[:220]}")
                except Exception:
                    pass

                kb_block = ("\n📚 সংরক্ষিত মেমোরি থেকে প্রাসঙ্গিক তথ্য:\n" + "\n".join(kb_snippets) + "\n") if kb_snippets else ""
                reply_text = (
                    f"⚠️ প্রাইমারি AI মডেল এখন অফলাইন ({err_txt})।\n"
                    f"{kb_block}\n"
                    f"⚡ ইনস্ট্যান্ট বট কমান্ড: `ping 192.168.9.2`, `/health`, `/port 192.168.9.2`, `/status`, `/history`, `/workflows`, `/run <name>`\n\n"
                    f"{wf_digest['report_text']}"
                )
        except Exception as ai_err:
            reply_text = (
                f"⚠️ Agent note: {str(ai_err)[:180]}\n\n"
                f"{wf_digest['report_text']}"
            )

    latency_ms = int((time.time() - t0) * 1000)

    chat_row = await WorkflowStore.record_telegram_chat(
        chat_id=chat_id or "studio_console",
        sender_name=sender_name or source,
        direction="incoming",
        intent=intent,
        user_message=msg,
        reply_message=reply_text,
        workflow_status_summary=wf_status_summary,
        linked_workflow_id=linked_wf_id,
        status=action_status,
        latency_ms=latency_ms,
    )

    await WorkflowStore.record_telegram_log(
        event_type="chat_in",
        status="SUCCESS",
        workflow_id=linked_wf_id,
        workflow_name=f"Telegram Chat ({intent})",
        chat_id=str(chat_id or ""),
        message_preview=f"[{sender_name or source}] {msg[:140]}",
        latency_ms=latency_ms,
    )

    delivery: Optional[Dict[str, Any]] = None
    if not dry_send and chat_id:
        cfg = await WorkflowStore.get_telegram_config(include_plaintext_token=True)
        tok = cfg.get("_bot_token") or ""
        if tok:
            delivery = await telegram_send_message(
                token=tok,
                chat_id=str(chat_id),
                text=reply_text,
                event_type="chat_reply",
                workflow_id=linked_wf_id,
                workflow_name=f"Telegram Reply ({intent})",
                bot_username=cfg.get("bot_username") or "",
            )

    return {
        "ok": True,
        "intent": intent,
        "status": action_status,
        "chat": chat_row,
        "reply_message": reply_text,
        "workflow_status_summary": wf_status_summary,
        "delivery": delivery,
    }


class TelegramChatListener:
    """
    Background Telegram Long-Polling Listener for Two-Way WORKFLOWS (Auto) Chat & Ping Diagnostics.
    Works cleanly inside private LANs (192.168.9.x) without requiring a public HTTPS domain or webhook.
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._polling_now = False
        self._last_poll_at = ""
        self._last_error = ""
        self._synced_tokens: set = set()

    def is_polling(self) -> bool:
        return bool(self._running and self._polling_now)

    def clear_error(self):
        self._last_error = ""

    def get_runtime_state(self) -> Dict[str, Any]:
        return {
            "polling_active": self.is_polling(),
            "listener_running": self._running,
            "last_poll_at": self._last_poll_at,
            "poll_error": self._last_error,
        }

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Telegram Two-Way Chat Listener initialized.")

    async def stop(self):
        self._running = False
        self._polling_now = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Telegram Two-Way Chat Listener stopped.")

    async def _poll_loop(self):
        while self._running:
            try:
                cfg = await WorkflowStore.get_telegram_config(include_plaintext_token=True)
                tok = cfg.get("_bot_token") or ""
                cid = (cfg.get("chat_id") or "").strip()
                can_poll = bool(
                    cfg.get("connected")
                    and cfg.get("interactive_chat_enabled")
                    and tok
                    and cid
                )
                if not can_poll:
                    self._polling_now = False
                    self._last_error = ""
                    await asyncio.sleep(3.0)
                    continue

                self._polling_now = True
                if tok not in self._synced_tokens:
                    self._synced_tokens.add(tok)
                    asyncio.create_task(telegram_sync_commands(tok))
                offset = int(cfg.get("last_update_id") or 0)
                params: Dict[str, Any] = {"timeout": 12, "limit": 20}
                if offset > 0:
                    params["offset"] = offset + 1

                url = f"{TELEGRAM_API_BASE}/bot{tok}/getUpdates"
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.get(url, params=params)
                    if resp.status_code == 409:
                        await client.post(
                            f"{TELEGRAM_API_BASE}/bot{tok}/deleteWebhook",
                            json={"drop_pending_updates": False},
                        )
                        resp = await client.get(url, params=params)

                self._last_poll_at = time.strftime("%Y-%m-%d %H:%M:%S")
                if resp.status_code != 200:
                    self._last_error = f"HTTP {resp.status_code}"
                    await asyncio.sleep(8.0)
                    continue

                body = resp.json()
                if not body.get("ok"):
                    self._last_error = _sanitize_tg_error(str(body.get("description") or "getUpdates failed"), tok)
                    await asyncio.sleep(8.0)
                    continue

                self._last_error = ""
                updates = body.get("result") or []
                if not updates:
                    await asyncio.sleep(1.0)
                    continue

                allowed_set = {cid}
                for extra in (cfg.get("allowed_chat_ids") or "").split(","):
                    if extra.strip():
                        allowed_set.add(extra.strip())

                max_upd_id = offset
                for upd in updates:
                    uid = int(upd.get("update_id") or 0)
                    if uid > max_upd_id:
                        max_upd_id = uid
                    msg = upd.get("message") or upd.get("edited_message") or {}
                    text = (msg.get("text") or "").strip()
                    chat = msg.get("chat") or {}
                    incoming_cid = str(chat.get("id") or "").strip()
                    if not text or not incoming_cid:
                        continue

                    sender = chat.get("username") or chat.get("first_name") or incoming_cid
                    if chat.get("username") and not str(sender).startswith("@"):
                        sender = f"@{sender}"

                    # Advance offset promptly to prevent reprocessing on slow commands
                    await WorkflowStore.save_telegram_config(last_update_id=max_upd_id)

                    if incoming_cid not in allowed_set:
                        if text.lower().startswith(("/start", "/id")):
                            await telegram_send_message(
                                token=tok,
                                chat_id=incoming_cid,
                                text=f"🆔 Your Telegram Chat ID is `{incoming_cid}`.\nAdd this Chat ID inside MyAgent WORKFLOWS (Auto) → Telegram Settings.",
                                event_type="chat_reply",
                                workflow_name="Telegram ID Lookup",
                                bot_username=cfg.get("bot_username") or "",
                            )
                        else:
                            await WorkflowStore.record_telegram_log(
                                event_type="chat_in",
                                status="FAILED",
                                chat_id=incoming_cid,
                                message_preview=f"Unauthorized chat [{sender}]: {text[:100]}",
                                error_detail=f"Chat ID {incoming_cid} not in allowed list.",
                            )
                        continue

                    try:
                        await telegram_send_chat_action(tok, incoming_cid, "typing")
                        await handle_telegram_chat_message(
                            chat_id=incoming_cid,
                            sender_name=sender,
                            text=text,
                            dry_send=False,
                            source="telegram_polling",
                        )
                    except Exception as h_err:
                        logger.error(f"Telegram chat message handler error: {h_err}")

                if max_upd_id > offset:
                    await WorkflowStore.save_telegram_config(last_update_id=max_upd_id)

            except asyncio.CancelledError:
                self._polling_now = False
                break
            except Exception as e:
                self._last_error = str(e)[:180]
                self._polling_now = False
                await asyncio.sleep(5.0)


telegram_chat_listener = TelegramChatListener()

