# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 3.3.0
# Workflows API Router — n8n-Style Visual Automation & Daily AI Task Engine
# ==============================================================================

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query, Header

from routers.auth import get_current_user, get_optional_current_user
from workflows.store import WorkflowStore, WORKFLOW_TEMPLATES, NODE_CATALOG
from workflows.engine import workflow_engine, _redact_secrets_in_obj

logger = logging.getLogger("myagent.routers.workflows")

router = APIRouter(prefix="/api/workflows", tags=["Workflows & Daily Automation"])


@router.get("")
async def list_workflows(user=Depends(get_optional_current_user)):
    """Lists all n8n-style workflows with running status, schedules, and aggregate KPIs."""
    await WorkflowStore.init_tables_and_seed()
    workflows = await WorkflowStore.list_workflows()
    for wf in workflows:
        if workflow_engine.is_running(wf["id"]):
            wf["last_status"] = "RUNNING"
        wf["is_running"] = workflow_engine.is_running(wf["id"])

    recent_runs = await WorkflowStore.list_runs(limit=25)
    total_runs = sum(int(w.get("run_count") or 0) for w in workflows)
    total_success = sum(int(w.get("success_count") or 0) for w in workflows)
    active_count = sum(1 for w in workflows if w.get("is_enabled"))

    return {
        "success": True,
        "workflows": workflows,
        "recent_runs": recent_runs,
        "stats": {
            "total_workflows": len(workflows),
            "active_workflows": active_count,
            "total_runs": total_runs,
            "success_rate": round((total_success / total_runs) * 100, 1) if total_runs > 0 else 100.0
        }
    }


@router.get("/templates")
async def get_workflow_catalog_and_templates(user=Depends(get_optional_current_user)):
    """Returns pre-built workflow templates, node palette definitions, available tools, subagents, and models."""
    from agent.tools import AgentTools
    from agent.openrouter_client import OPENROUTER_ALL_FREE_MODELS, FEATURED_OPENROUTER_MODELS, OpenRouterService
    from agent.subagents.work_engine import SubAgentWorkEngine
    from mcp.store import MCPStore
    from mcp.server import MyAgentMCPServer
    from config import settings

    tools_schema = await AgentTools.get_all_tools_schema()
    mcp_servers = await MCPStore.list_servers()
    tool_names = []
    for t in tools_schema:
        fn = t.get("function", {})
        t_name = fn.get("name")
        if not t_name:
            continue
        desc = fn.get("description", "")
        is_mcp = str(desc).startswith("[MCP:")
        tool_names.append({
            "name": t_name,
            "description": desc,
            "source": "mcp" if is_mcp else "builtin",
            "parameters": fn.get("parameters", {"type": "object", "properties": {}})
        })
    subagents = await SubAgentWorkEngine.get_all_subagents()

    models = [
        {"id": "", "label": f"Default ({settings.LLM_MODEL})"},
        {"id": settings.LLM_MODEL, "label": f"Local/Primary ({settings.LLM_MODEL})"}
    ]
    for m in OPENROUTER_ALL_FREE_MODELS[:10]:
        models.append({"id": m["id"], "label": f"[Free] {m['name']} ({m['id']})"})
    for m in FEATURED_OPENROUTER_MODELS[:5]:
        models.append({"id": m["id"], "label": f"[OpenRouter] {m['name']}"})

    all_wfs = await WorkflowStore.list_workflows()
    return {
        "success": True,
        "templates": WORKFLOW_TEMPLATES,
        "node_catalog": NODE_CATALOG,
        "tools": tool_names,
        "mcp_servers": mcp_servers,
        "mcp_server_enabled": MyAgentMCPServer.is_enabled(),
        "workflows_list": [{"id": w["id"], "name": w["name"], "icon": w.get("icon", "⚡")} for w in all_wfs],
        "subagents": [
            {"id": "swarm", "name": "🐝 Full Multi-Agent Swarm Orchestrator", "icon": "🐝"},
            *[
                {"id": s["id"], "name": f"{s.get('icon', '🤖')} {s['name']}", "icon": s.get("icon", "🤖")}
                for s in subagents
            ]
        ],
        "models": models,
        "openrouter_configured": OpenRouterService.is_configured()
    }


@router.get("/vars/list")
async def list_workflow_variables(user=Depends(get_optional_current_user)):
    """Lists all global encrypted secrets & workflow environment variables."""
    await WorkflowStore.init_tables_and_seed()
    items = await WorkflowStore.list_secrets()
    return {"success": True, "variables": items}


@router.post("/vars/save")
async def save_workflow_variable(
    data: Dict[str, Any] = Body(...),
    user=Depends(get_optional_current_user)
):
    """Creates or updates an AES-256 encrypted secret/variable accessible as {{vars.KEY}}."""
    await WorkflowStore.init_tables_and_seed()
    try:
        saved = await WorkflowStore.upsert_secret(
            key=data.get("key", ""),
            value=data.get("value", ""),
            is_secret=bool(data.get("is_secret", True)),
            description=data.get("description", "")
        )
        return {"success": True, "variable": saved, "message": f"Saved variable {saved['key']}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/vars/{key}")
async def delete_workflow_variable(
    key: str,
    user=Depends(get_optional_current_user)
):
    """Deletes a global workflow variable/secret by key."""
    ok = await WorkflowStore.delete_secret(key)
    if not ok:
        raise HTTPException(status_code=404, detail="Variable not found.")
    return {"success": True, "message": f"Deleted variable '{key}'."}


# ==============================================================================
# MCP Hub Integration Endpoints for WORKFLOWS (Auto)
# ==============================================================================
@router.get("/mcp/servers")
async def get_workflow_mcp_servers(user=Depends(get_optional_current_user)):
    """Lists all registered external/local MCP servers and discovered tools for WORKFLOWS (Auto)."""
    from mcp.store import MCPStore
    from mcp.server import MyAgentMCPServer
    servers = await MCPStore.list_servers()
    return {
        "success": True,
        "mcp_servers": servers,
        "mcp_server_enabled": MyAgentMCPServer.is_enabled(),
    }


@router.post("/mcp/ping/{server_id}")
async def ping_workflow_mcp_server(
    server_id: str,
    user=Depends(get_optional_current_user)
):
    """Pings an MCP server and refreshes its discovered tools cache inside WORKFLOWS (Auto)."""
    from mcp.manager import MCPManager
    from mcp.store import MCPStore
    ping_res = await MCPManager.ping_server(server_id)
    servers = await MCPStore.list_servers()
    return {
        "success": bool(ping_res.get("success")),
        "ping": ping_res,
        "mcp_servers": servers,
    }


# ==============================================================================
# Telegram Bot Connection, Status & Log Center for WORKFLOWS (Auto)
# ==============================================================================
def _with_tg_runtime(cfg: Dict[str, Any]) -> Dict[str, Any]:
    from workflows.telegram_service import telegram_chat_listener
    out = dict(cfg)
    out.pop("_bot_token", None)
    out.update(telegram_chat_listener.get_runtime_state())
    return out


@router.get("/telegram/status")
async def get_workflow_telegram_status(
    live_check: bool = Query(False),
    user=Depends(get_optional_current_user)
):
    """Returns Telegram connection configuration, live connected status, polling state, and log statistics."""
    import time as _t
    from workflows.telegram_service import telegram_verify_token

    await WorkflowStore.init_tables_and_seed()
    cfg = await WorkflowStore.get_telegram_config(include_plaintext_token=live_check)

    if live_check and cfg.get("_bot_token"):
        tok = cfg.get("_bot_token") or ""
        verify = await telegram_verify_token(tok)
        now_s = _t.strftime("%Y-%m-%d %H:%M:%S")
        if verify.get("ok"):
            cfg = await WorkflowStore.save_telegram_config(
                status="Connected" if cfg.get("is_enabled") else "Standby",
                bot_id=verify.get("bot_id", ""),
                bot_username=verify.get("bot_username", ""),
                bot_first_name=verify.get("bot_first_name", ""),
                last_verified_at=now_s,
                last_error="",
            )
            await WorkflowStore.record_telegram_log(
                event_type="verify",
                status="CONNECTED",
                bot_username=verify.get("bot_username", ""),
                chat_id=cfg.get("chat_id", ""),
                message_preview=f"Live bot verified: {verify.get('bot_username')}",
                http_status=200,
                latency_ms=verify.get("latency_ms", 0),
            )
        else:
            err = verify.get("error") or "Telegram API verification failed"
            cfg = await WorkflowStore.save_telegram_config(
                status="Error",
                last_verified_at=now_s,
                last_error=err,
            )
            await WorkflowStore.record_telegram_log(
                event_type="verify",
                status="FAILED",
                bot_username=cfg.get("bot_username", ""),
                chat_id=cfg.get("chat_id", ""),
                message_preview="Live token verification failed",
                http_status=verify.get("http_status", 0),
                error_detail=err,
                latency_ms=verify.get("latency_ms", 0),
            )

    return {"success": True, "telegram": _with_tg_runtime(cfg)}


@router.post("/telegram/connect")
async def connect_workflow_telegram(
    data: Dict[str, Any] = Body(...),
    user=Depends(get_optional_current_user)
):
    """Connects/updates Telegram Bot credentials, verifies via getMe, and configures two-way chat & auto reports."""
    import time as _t
    from workflows.telegram_service import telegram_verify_token, telegram_detect_chats, telegram_chat_listener

    await WorkflowStore.init_tables_and_seed()
    telegram_chat_listener.clear_error()
    raw_token = data.get("bot_token")
    chat_id = data.get("chat_id")
    is_enabled = bool(data.get("is_enabled", True))
    verify_live = bool(data.get("verify_live", True))
    inter_val = data.get("interactive_chat_enabled")
    autorep_val = data.get("auto_send_reports")
    allowed_cids = data.get("allowed_chat_ids")

    current = await WorkflowStore.get_telegram_config(include_plaintext_token=True)
    effective_tok = (raw_token.strip() if isinstance(raw_token, str) and raw_token.strip() else current.get("_bot_token", ""))
    effective_cid = (chat_id.strip() if isinstance(chat_id, str) else current.get("chat_id", ""))

    if not effective_tok:
        raise HTTPException(status_code=400, detail="Telegram Bot Token দিন (@BotFather থেকে প্রাপ্ত)।")

    now_s = _t.strftime("%Y-%m-%d %H:%M:%S")
    detected_chats: List[Dict[str, Any]] = []

    extra_kwargs: Dict[str, Any] = {}
    if inter_val is not None:
        extra_kwargs["interactive_chat_enabled"] = bool(inter_val)
    if autorep_val is not None:
        extra_kwargs["auto_send_reports"] = bool(autorep_val)
    if allowed_cids is not None:
        extra_kwargs["allowed_chat_ids"] = str(allowed_cids)

    if not is_enabled:
        saved = await WorkflowStore.save_telegram_config(
            bot_token=effective_tok,
            chat_id=effective_cid,
            is_enabled=False,
            status="Disconnected",
            last_error="",
            **extra_kwargs,
        )
        await WorkflowStore.record_telegram_log(
            event_type="disconnect",
            status="DISCONNECTED",
            bot_username=saved.get("bot_username", ""),
            chat_id=effective_cid,
            message_preview="Telegram connection disabled",
        )
        return {"success": True, "verified": False, "telegram": _with_tg_runtime(saved), "detected_chats": []}

    if verify_live:
        verify = await telegram_verify_token(effective_tok)
        if not verify.get("ok"):
            err = verify.get("error") or "Telegram Bot verification failed"
            saved = await WorkflowStore.save_telegram_config(
                bot_token=effective_tok,
                chat_id=effective_cid,
                is_enabled=False,
                status="Error",
                last_verified_at=now_s,
                last_error=err,
                **extra_kwargs,
            )
            await WorkflowStore.record_telegram_log(
                event_type="connect",
                status="FAILED",
                chat_id=effective_cid,
                message_preview="Bot connection verification failed",
                http_status=verify.get("http_status", 0),
                error_detail=err,
                latency_ms=verify.get("latency_ms", 0),
            )
            return {
                "success": False,
                "verified": False,
                "error": err,
                "telegram": _with_tg_runtime(saved),
                "detected_chats": [],
            }

        # Auto-discover chat_id if left empty
        if not effective_cid:
            det = await telegram_detect_chats(effective_tok, bot_username=verify.get("bot_username", ""))
            detected_chats = det.get("chats", [])
            if detected_chats:
                effective_cid = detected_chats[0]["chat_id"]

        next_status = "Connected" if effective_cid else "Standby"
        saved = await WorkflowStore.save_telegram_config(
            bot_token=effective_tok,
            chat_id=effective_cid,
            is_enabled=True,
            status=next_status,
            bot_id=verify.get("bot_id", ""),
            bot_username=verify.get("bot_username", ""),
            bot_first_name=verify.get("bot_first_name", ""),
            last_verified_at=now_s,
            last_error="",
            **extra_kwargs,
        )
        await WorkflowStore.record_telegram_log(
            event_type="connect",
            status="CONNECTED" if effective_cid else "SUCCESS",
            bot_username=saved.get("bot_username", ""),
            chat_id=effective_cid,
            message_preview=f"Bot {saved.get('bot_username')} connected successfully" if effective_cid else f"Bot {saved.get('bot_username')} verified; waiting for Chat ID (/start + Auto-Detect)",
            http_status=200,
            latency_ms=verify.get("latency_ms", 0),
        )
        return {
            "success": True,
            "verified": True,
            "message": f"Telegram connected as {saved.get('bot_username')}" if effective_cid else f"Bot {saved.get('bot_username')} verified! Send /start to your bot in Telegram, then click Auto-Detect Chat ID.",
            "telegram": _with_tg_runtime(saved),
            "detected_chats": detected_chats,
        }

    # Offline / skip live verification save
    saved = await WorkflowStore.save_telegram_config(
        bot_token=effective_tok,
        chat_id=effective_cid,
        is_enabled=True,
        status="Connected" if (effective_tok and effective_cid) else "Standby",
        last_error="",
        **extra_kwargs,
    )
    await WorkflowStore.record_telegram_log(
        event_type="connect",
        status="CONNECTED" if saved.get("connected") else "SUCCESS",
        bot_username=saved.get("bot_username", ""),
        chat_id=effective_cid,
        message_preview="Telegram credentials saved (without live ping)",
    )
    return {"success": True, "verified": False, "telegram": _with_tg_runtime(saved), "detected_chats": []}


@router.post("/telegram/detect-chat")
async def detect_workflow_telegram_chats(
    data: Optional[Dict[str, Any]] = Body(default=None),
    user=Depends(get_optional_current_user)
):
    """Detects Chat IDs from recent Telegram /getUpdates messages."""
    from workflows.telegram_service import telegram_detect_chats

    await WorkflowStore.init_tables_and_seed()
    body = data if isinstance(data, dict) else {}
    current = await WorkflowStore.get_telegram_config(include_plaintext_token=True)
    tok = (body.get("bot_token") or "").strip() or current.get("_bot_token", "")
    if not tok:
        raise HTTPException(status_code=400, detail="প্রথমে Bot Token দিন বা সংরক্ষণ করুন।")
    res = await telegram_detect_chats(tok, bot_username=current.get("bot_username", ""))
    return {"success": res["ok"], **res}


@router.post("/telegram/test")
async def test_workflow_telegram_message(
    data: Optional[Dict[str, Any]] = Body(default=None),
    user=Depends(get_optional_current_user)
):
    """Dispatches a real Telegram test notification and logs delivery diagnostics."""
    from workflows.telegram_service import telegram_send_message

    await WorkflowStore.init_tables_and_seed()
    body = data if isinstance(data, dict) else {}
    cfg = await WorkflowStore.get_telegram_config(include_plaintext_token=True)
    tok = (body.get("bot_token") or "").strip() or cfg.get("_bot_token", "")
    cid = (body.get("chat_id") or "").strip() or cfg.get("chat_id", "")
    msg = (body.get("message") or "").strip() or (
        f"⚡ MyAgent WORKFLOWS (Auto) — Telegram Test OK!\n"
        f"Bot: {cfg.get('bot_username') or 'Configured'}\nStatus: Connected & Ready for Automated Workflows."
    )
    res = await telegram_send_message(
        token=tok,
        chat_id=cid,
        text=msg,
        parse_mode=(body.get("parse_mode") or "").strip(),
        event_type="test_send",
        workflow_name="Manual Telegram Connection Test",
        bot_username=cfg.get("bot_username") or "",
    )
    updated_cfg = _with_tg_runtime(await WorkflowStore.get_telegram_config(include_plaintext_token=False))
    return {"success": res["ok"], "delivery": res, "telegram": updated_cfg}


@router.post("/telegram/disconnect")
async def disconnect_workflow_telegram(
    data: Optional[Dict[str, Any]] = Body(default=None),
    user=Depends(get_optional_current_user)
):
    """Disconnects Telegram integration (and optionally wipes saved Bot Token)."""
    from workflows.telegram_service import telegram_chat_listener
    await WorkflowStore.init_tables_and_seed()
    telegram_chat_listener.clear_error()
    body = data if isinstance(data, dict) else {}
    clear_token = bool(body.get("clear_token", False))
    clear_chat = bool(body.get("clear_chat_id", False))
    before = await WorkflowStore.get_telegram_config(include_plaintext_token=False)
    saved = await WorkflowStore.save_telegram_config(
        chat_id="" if clear_chat else None,
        is_enabled=False,
        status="Disconnected",
        last_error="",
        clear_token=clear_token,
    )
    await WorkflowStore.record_telegram_log(
        event_type="disconnect",
        status="DISCONNECTED",
        bot_username=before.get("bot_username", ""),
        chat_id=before.get("chat_id", ""),
        message_preview="Telegram disconnected" + (" & token cleared" if clear_token else ""),
    )
    return {"success": True, "telegram": _with_tg_runtime(saved)}


@router.get("/telegram/logs")
async def get_workflow_telegram_logs(
    limit: int = Query(80, le=200),
    status: str = Query("ALL"),
    event_type: str = Query(""),
    user=Depends(get_optional_current_user)
):
    """Returns Telegram connection & delivery audit logs along with current connection status."""
    await WorkflowStore.init_tables_and_seed()
    logs = await WorkflowStore.list_telegram_logs(limit=limit, status_filter=status, event_filter=event_type)
    cfg = _with_tg_runtime(await WorkflowStore.get_telegram_config(include_plaintext_token=False))
    return {"success": True, "logs": logs, "telegram": cfg}


@router.delete("/telegram/logs")
async def clear_workflow_telegram_logs(user=Depends(get_optional_current_user)):
    """Clears Telegram delivery & event logs."""
    await WorkflowStore.init_tables_and_seed()
    deleted = await WorkflowStore.clear_telegram_logs()
    return {"success": True, "deleted": deleted}


@router.get("/telegram/chats")
async def get_workflow_telegram_chats(
    limit: int = Query(50, le=200),
    q: str = Query(""),
    intent: str = Query(""),
    user=Depends(get_optional_current_user)
):
    """Returns two-way Telegram chat conversations, automated reports, and current WORKFLOWS (Auto) status."""
    await WorkflowStore.init_tables_and_seed()
    chats = await WorkflowStore.list_telegram_chats(limit=limit, q=q, intent=intent)
    digest = await WorkflowStore.build_workflows_status_report(max_workflows=6, max_runs=4)
    cfg = _with_tg_runtime(await WorkflowStore.get_telegram_config(include_plaintext_token=False))
    return {"success": True, "chats": chats, "workflow_digest": digest, "telegram": cfg}


@router.post("/telegram/chat/command")
async def run_telegram_chat_command(
    data: Dict[str, Any] = Body(...),
    user=Depends(get_optional_current_user)
):
    """Executes an interactive Telegram chat command (e.g. 'ping 192.168.9.2 server and show status'), logs chat & optionally replies to Telegram."""
    from workflows.telegram_service import handle_telegram_chat_message

    await WorkflowStore.init_tables_and_seed()
    msg = (data.get("message") or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Command message cannot be empty.")

    cfg = await WorkflowStore.get_telegram_config(include_plaintext_token=False)
    chat_id = (data.get("chat_id") or "").strip() or cfg.get("chat_id") or "studio_console"
    sender_name = (data.get("sender_name") or "").strip() or "Studio / Telegram User"
    send_to_tg = bool(data.get("send_to_telegram", False))

    res = await handle_telegram_chat_message(
        chat_id=chat_id,
        sender_name=sender_name,
        text=msg,
        dry_send=(not send_to_tg),
        source="studio_or_api",
    )
    return {"success": True, **res}


@router.post("/telegram/send-report")
async def send_workflow_status_report_to_telegram(
    data: Optional[Dict[str, Any]] = Body(default=None),
    user=Depends(get_optional_current_user)
):
    """Sends a formatted WORKFLOWS (Auto) Status Report (or specific workflow's latest run) straight to Telegram chat."""
    from workflows.telegram_service import telegram_send_message, format_workflow_execution_report

    await WorkflowStore.init_tables_and_seed()
    body = data if isinstance(data, dict) else {}
    wf_id = (body.get("workflow_id") or "").strip()
    cfg = await WorkflowStore.get_telegram_config(include_plaintext_token=True)
    tok = cfg.get("_bot_token") or ""
    cid = (body.get("chat_id") or "").strip() or cfg.get("chat_id") or ""

    if wf_id:
        runs = await WorkflowStore.list_runs(workflow_id=wf_id, limit=1)
        wf = await WorkflowStore.get_workflow(wf_id)
        if runs:
            report_text = format_workflow_execution_report(runs[0])
            wf_name = runs[0].get("workflow_name") or (wf.get("name") if wf else wf_id)
            st_label = runs[0].get("status", "INFO")
        elif wf:
            report_text = f"📊 WORKFLOWS (Auto) — {wf['name']}\n• Status: {wf.get('last_status', 'IDLE')}\n• Schedule: {wf.get('human_bn') or wf.get('daily_time')}\n• Next Run: {wf.get('next_run') or '-'}"
            wf_name = wf["name"]
            st_label = wf.get("last_status", "IDLE")
        else:
            raise HTTPException(status_code=404, detail="Workflow not found.")
        summary_line = f"{wf_name} ({st_label})"
    else:
        digest = await WorkflowStore.build_workflows_status_report(max_workflows=8, max_runs=5)
        report_text = digest["report_text"]
        wf_name = "WORKFLOWS (Auto) Full Report"
        st_label = "REPORT"
        summary_line = digest["summary_line"]

    chat_entry = await WorkflowStore.record_telegram_chat(
        chat_id=cid or "studio_report",
        sender_name=wf_name,
        direction="report",
        intent="workflow_report",
        user_message=f"📤 WORKFLOWS (Auto) Report: {wf_name}",
        reply_message=report_text,
        workflow_status_summary=summary_line,
        linked_workflow_id=wf_id,
        status=st_label,
    )

    delivery = None
    if tok and cid:
        delivery = await telegram_send_message(
            token=tok,
            chat_id=cid,
            text=report_text,
            event_type="workflow_report",
            workflow_id=wf_id,
            workflow_name=wf_name,
            bot_username=cfg.get("bot_username") or "",
        )

    return {
        "success": True if (delivery is None or delivery.get("ok")) else False,
        "report_text": report_text,
        "chat": chat_entry,
        "delivery": delivery,
    }


@router.delete("/telegram/chats")
async def clear_workflow_telegram_chats(user=Depends(get_optional_current_user)):
    """Clears recorded Telegram chat messages & report stream."""
    await WorkflowStore.init_tables_and_seed()
    deleted = await WorkflowStore.clear_telegram_chats()
    return {"success": True, "deleted": deleted}


@router.post("/telegram/webhook")
async def receive_telegram_bot_webhook(data: Dict[str, Any] = Body(...)):
    """Optional inbound Telegram Bot API Webhook endpoint for setups with a public HTTPS URL."""
    from workflows.telegram_service import handle_telegram_chat_message

    await WorkflowStore.init_tables_and_seed()
    msg = data.get("message") or data.get("edited_message") or {}
    text = (msg.get("text") or "").strip()
    chat = msg.get("chat") or {}
    incoming_cid = str(chat.get("id") or "").strip()
    if not text or not incoming_cid:
        return {"ok": True, "ignored": True}

    cfg = await WorkflowStore.get_telegram_config(include_plaintext_token=False)
    allowed_set = set()
    if cfg.get("chat_id"):
        allowed_set.add(cfg["chat_id"])
    for extra in (cfg.get("allowed_chat_ids") or "").split(","):
        if extra.strip():
            allowed_set.add(extra.strip())

    if allowed_set and incoming_cid not in allowed_set:
        return {"ok": False, "error": "Unauthorized chat_id"}

    sender = chat.get("username") or chat.get("first_name") or incoming_cid
    res = await handle_telegram_chat_message(
        chat_id=incoming_cid,
        sender_name=str(sender),
        text=text,
        dry_send=False,
        source="telegram_webhook",
    )
    return {"ok": True, "intent": res.get("intent")}


@router.get("/runs/recent")
async def list_recent_workflow_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    workflow_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    trigger_source: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    user=Depends(get_optional_current_user)
):
    """Returns searchable & filterable recent workflow runs across all workflows with aggregate stats."""
    res = await WorkflowStore.query_runs(
        workflow_id=workflow_id or None,
        status=status or None,
        trigger_source=trigger_source or None,
        q=q or None,
        date_from=date_from or None,
        date_to=date_to or None,
        limit=limit,
        offset=offset,
    )
    return {"success": True, **res}


@router.post("/runs/clear")
async def clear_workflow_run_history(
    data: Dict[str, Any] = Body(default={}),
    user=Depends(get_optional_current_user)
):
    """Clears completed workflow run history (optionally filtered by workflow_id, status, or older_than_days)."""
    deleted = await WorkflowStore.clear_runs(
        workflow_id=data.get("workflow_id") or None,
        older_than_days=data.get("older_than_days"),
        status=data.get("status") or None,
    )
    return {"success": True, "deleted": deleted}


@router.get("/runs/{run_id}")
async def get_single_workflow_run(
    run_id: str,
    user=Depends(get_optional_current_user)
):
    """Fetches a single workflow run with its complete step-by-step node trace."""
    run = await WorkflowStore.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found.")
    return {"success": True, "run": run}


@router.delete("/runs/{run_id}")
async def delete_single_workflow_run(
    run_id: str,
    user=Depends(get_optional_current_user)
):
    """Deletes a single workflow execution history record."""
    deleted = await WorkflowStore.delete_run(run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workflow run not found.")
    return {"success": True, "deleted_run_id": run_id}


@router.get("/history/unified")
async def get_unified_chat_and_workflow_history(
    kind: str = Query("all"),
    q: str = Query(""),
    status: str = Query(""),
    workflow_id: str = Query(""),
    role: str = Query(""),
    limit: int = Query(60, ge=1, le=200),
    user=Depends(get_optional_current_user)
):
    """Returns a combined chronological timeline and statistics across Chat AI, WORKFLOWS (Auto), and Telegram Chat."""
    from memory.chat_session_store import ChatSessionStore

    await WorkflowStore.init_tables_and_seed()
    norm_kind = (kind or "all").strip().lower()

    chat_sessions = await ChatSessionStore.list_sessions(q=q if norm_kind in ("all", "chat") else "", include_archived=True, limit=limit)
    chat_msgs_data = await ChatSessionStore.search_messages(
        q=q if norm_kind in ("all", "chat") else "",
        role=role if role else None,
        limit=limit,
    )
    all_chat_msgs_stats = await ChatSessionStore.search_messages(q="", limit=1)
    all_chat_sessions_all = await ChatSessionStore.list_sessions(q="", include_archived=True, limit=300)

    runs_res = await WorkflowStore.query_runs(
        workflow_id=workflow_id or None,
        status=status or None,
        q=q if norm_kind in ("all", "workflow") else None,
        limit=limit,
    )
    all_runs_stats = (await WorkflowStore.query_runs(limit=1))["stats"]

    tg_chats = await WorkflowStore.list_telegram_chats(
        limit=limit,
        q=q if norm_kind in ("all", "telegram") else "",
    )
    all_tg_chats = await WorkflowStore.list_telegram_chats(limit=200)

    timeline: List[Dict[str, Any]] = []
    if norm_kind in ("all", "chat"):
        for m in chat_msgs_data.get("items", []):
            timeline.append({
                "kind": "chat",
                "id": f"msg_{m['id']}",
                "raw_id": m["id"],
                "session_id": m["session_id"],
                "title": m.get("session_title") or "Chat AI",
                "subtitle": f"{str(m.get('role', 'user')).upper()} • {m.get('model_name') or 'AI'}",
                "status": "AUTOMATION" if m.get("session_source") == "automation" else str(m.get("role") or "user").upper(),
                "preview": (m.get("content") or "")[:360],
                "content": m.get("content") or "",
                "model_name": m.get("model_name") or "",
                "role": m.get("role") or "user",
                "timestamp": m.get("created_at") or "",
                "meta": {"session_source": m.get("session_source") or "webchat", "sources": m.get("sources") or []},
            })

    if norm_kind in ("all", "workflow"):
        for r in runs_res.get("runs", []):
            steps = r.get("node_results") or []
            timeline.append({
                "kind": "workflow",
                "id": r["id"],
                "raw_id": r["id"],
                "workflow_id": r.get("workflow_id"),
                "title": r.get("workflow_name") or r.get("workflow_id"),
                "subtitle": f"Trigger: {r.get('trigger_source', 'manual')} • {len(steps)} nodes • {r.get('duration_ms', 0)} ms",
                "status": r.get("status") or "UNKNOWN",
                "preview": (r.get("final_output") or r.get("error_message") or "")[:360],
                "content": r.get("final_output") or r.get("error_message") or "",
                "duration_ms": r.get("duration_ms") or 0,
                "trigger_source": r.get("trigger_source") or "manual",
                "timestamp": r.get("started_at") or "",
                "meta": {"node_count": len(steps), "finished_at": r.get("finished_at") or ""},
            })

    if norm_kind in ("all", "telegram"):
        for tg in tg_chats:
            preview_txt = f"Q: {tg.get('user_message') or ''}\nA: {tg.get('reply_message') or ''}".strip()
            timeline.append({
                "kind": "telegram",
                "id": tg["id"],
                "raw_id": tg["id"],
                "workflow_id": tg.get("linked_workflow_id") or "",
                "title": f"Telegram ({tg.get('sender_name') or tg.get('chat_id') or 'Bot'})",
                "subtitle": f"Intent: {tg.get('intent') or 'chat'} • {tg.get('latency_ms') or 0} ms",
                "status": tg.get("status") or "SUCCESS",
                "preview": preview_txt[:360],
                "content": preview_txt,
                "timestamp": tg.get("created_at") or "",
                "meta": {"direction": tg.get("direction") or "incoming", "intent": tg.get("intent") or "chat"},
            })

    timeline.sort(key=lambda item: str(item.get("timestamp") or ""), reverse=True)
    timeline = timeline[:limit]

    return {
        "success": True,
        "kind": norm_kind,
        "summary": {
            "total_chat_sessions": len(all_chat_sessions_all),
            "total_chat_messages": all_chat_msgs_stats.get("total", 0),
            "total_workflow_runs": all_runs_stats.get("total", 0),
            "workflow_success_rate": all_runs_stats.get("success_rate", 100.0),
            "workflow_failed_runs": all_runs_stats.get("failed", 0),
            "total_telegram_chats": len(all_tg_chats),
        },
        "timeline": timeline,
        "chat_sessions": chat_sessions,
        "chat_messages": chat_msgs_data,
        "workflow_runs": runs_res,
        "telegram_chats": tg_chats,
    }


@router.post("/quick-daily")
async def create_quick_daily_workflow(
    data: Dict[str, Any] = Body(...),
    user=Depends(get_optional_current_user)
):
    """
    Creates & activates a multi-node Daily Autonomous Agent Workflow from natural language instructions.
    """
    instruction = (data.get("instruction") or "").strip()
    if not instruction:
        raise HTTPException(status_code=400, detail="Daily task instruction cannot be empty.")

    name = (data.get("name") or instruction[:48]).strip()
    daily_time = (data.get("daily_time") or "09:00").strip()
    frequency = (data.get("frequency") or "daily").strip()
    timezone_str = (data.get("timezone") or "Asia/Dhaka").strip()
    model = (data.get("model") or "").strip()
    project_name = (data.get("project_name") or "").strip()
    save_report = bool(data.get("save_report", True))
    save_memory = bool(data.get("save_memory", False))
    post_to_chat = bool(data.get("post_to_chat", True))
    notify_channels = bool(data.get("notify_channels", False))
    custom_webhook_url = (data.get("custom_webhook_url") or "").strip()
    language = (data.get("language") or "bn").strip()
    use_mcp = bool(data.get("use_mcp", True))

    wf = await WorkflowStore.build_quick_daily_workflow(
        name=name,
        instruction=instruction,
        daily_time=daily_time,
        frequency=frequency,
        timezone_str=timezone_str,
        model=model,
        project_name=project_name,
        save_report=save_report,
        save_memory=save_memory,
        post_to_chat=post_to_chat,
        notify_channels=notify_channels,
        custom_webhook_url=custom_webhook_url,
        language=language,
        use_mcp=use_mcp
    )

    run_immediately = bool(data.get("run_immediately", False))
    run_res = None
    if run_immediately:
        run_res = await workflow_engine.execute_workflow(wf["id"], trigger_source="manual")
        wf = await WorkflowStore.get_workflow(wf["id"])

    return {
        "success": True,
        "workflow": wf,
        "run_result": run_res,
        "message": f"Daily workflow '{name}' activated ({daily_time} {timezone_str})."
    }


@router.post("/ai-architect")
async def ai_architect_workflow(
    data: Dict[str, Any] = Body(...),
    user=Depends(get_optional_current_user)
):
    """Designs & activates a rich branched multi-node n8n workflow DAG from a plain goal description."""
    goal = (data.get("goal") or data.get("instruction") or "").strip()
    if not goal:
        raise HTTPException(status_code=400, detail="Goal prompt cannot be empty.")

    name = (data.get("name") or "").strip()
    daily_time = (data.get("daily_time") or "09:00").strip()
    frequency = (data.get("frequency") or "daily").strip()
    timezone_str = (data.get("timezone") or "Asia/Dhaka").strip()
    model = (data.get("model") or "").strip()
    project_name = (data.get("project_name") or "").strip()

    wf = await WorkflowStore.architect_workflow_from_goal(
        goal=goal,
        name=name,
        daily_time=daily_time,
        frequency=frequency,
        timezone_str=timezone_str,
        model=model,
        project_name=project_name,
        auto_enable=bool(data.get("is_enabled", True))
    )
    return {
        "success": True,
        "workflow": wf,
        "message": f"AI Architect built workflow '{wf['name']}' with {len(wf.get('nodes', []))} connected nodes."
    }


@router.post("/import")
async def import_workflow_json(
    data: Dict[str, Any] = Body(...),
    user=Depends(get_optional_current_user)
):
    """Imports a shared/exported n8n-style workflow JSON into MyAgent."""
    try:
        wf = await WorkflowStore.import_workflow(data)
        return {"success": True, "workflow": wf, "message": f"Imported workflow '{wf['name']}'."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/node/test")
async def test_single_workflow_node(
    data: Dict[str, Any] = Body(...),
    user=Depends(get_optional_current_user)
):
    """Tests a single workflow node configuration directly inside the n8n studio inspector."""
    node = data.get("node")
    if not isinstance(node, dict):
        raise HTTPException(status_code=400, detail="Missing 'node' dictionary.")
    sample_input = str(data.get("sample_input") or "")

    from datetime import datetime
    from workflows.store import _get_tzinfo
    now_tz = datetime.now(_get_tzinfo("Asia/Dhaka"))
    vars_map, secret_values = await WorkflowStore.get_secrets_for_runtime()
    ctx = {
        "workflow": {"id": "test", "name": "Studio Node Test"},
        "trigger": {
            "source": "node_test",
            "dry_run": False,
            "date": now_tz.strftime("%Y-%m-%d"),
            "time": now_tz.strftime("%H:%M:%S"),
            "datetime": now_tz.strftime("%Y-%m-%d %H:%M:%S"),
            "iso": now_tz.isoformat(),
            "weekday": now_tz.strftime("%A"),
            "timezone": "Asia/Dhaka",
            "payload": {"sample": sample_input}
        },
        "vars": vars_map,
        "secrets": vars_map,
        "nodes": {},
        "prev": {"output": sample_input, "status": "SUCCESS", "node_id": "sample_prev", "error": "", "data": {}},
        "prev_all": [{"node_id": "sample_prev", "title": "Sample Input", "type": "manual", "status": "SUCCESS", "output": sample_input, "data": {}}],
        "_dry_run": False,
        "_depth": 0,
        "_wf_id": ""
    }
    res = _redact_secrets_in_obj(await workflow_engine.execute_single_node(node, ctx), secret_values)
    return {"success": res["status"] != "FAILED", "result": res}


@router.post("/templates/{template_id}/install")
async def install_workflow_template(
    template_id: str,
    user=Depends(get_optional_current_user)
):
    """Clones a pre-built workflow template into active workflows."""
    wf = await WorkflowStore.install_template(template_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Template not found.")
    return {"success": True, "workflow": wf, "message": f"Template '{wf['name']}' installed."}


@router.post("/webhook/{workflow_id}")
async def trigger_workflow_via_webhook(
    workflow_id: str,
    payload: Optional[Dict[str, Any]] = Body(default={}),
    x_webhook_secret: Optional[str] = Header(default=None, alias="X-Webhook-Secret"),
    secret: Optional[str] = Query(default=None)
):
    """Public/Secret-verified inbound Webhook endpoint to execute a workflow externally."""
    wf = await WorkflowStore.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found.")

    expected_secret = wf.get("webhook_secret") or ""
    provided_secret = x_webhook_secret or secret or ""
    # Allow execution without secret ONLY if workflow secret was explicitly cleared, or verify match
    if expected_secret and provided_secret and provided_secret != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid webhook secret.")

    res = await workflow_engine.execute_workflow(
        workflow_id=workflow_id,
        trigger_source="webhook",
        trigger_payload=payload or {}
    )
    return res


@router.post("")
async def create_workflow(
    data: Dict[str, Any] = Body(...),
    user=Depends(get_optional_current_user)
):
    """Creates a custom multi-node n8n-style workflow."""
    if not (data.get("name") or "").strip():
        raise HTTPException(status_code=400, detail="Workflow name cannot be empty.")
    wf = await WorkflowStore.create_workflow(data)
    return {"success": True, "workflow": wf, "message": "Workflow created successfully."}


@router.get("/{workflow_id}/live-status")
async def get_workflow_live_status(
    workflow_id: str,
    user=Depends(get_optional_current_user)
):
    """Returns real-time node execution progress while a workflow is running."""
    return {"success": True, **workflow_engine.get_live_status(workflow_id)}


@router.post("/{workflow_id}/duplicate")
async def duplicate_workflow(
    workflow_id: str,
    user=Depends(get_optional_current_user)
):
    """Duplicates an existing workflow so users can clone and customize variations safely."""
    cloned = await WorkflowStore.duplicate_workflow(workflow_id)
    if not cloned:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return {"success": True, "workflow": cloned, "message": f"Cloned '{cloned['name']}'."}


@router.get("/{workflow_id}/export")
async def export_workflow_json(
    workflow_id: str,
    user=Depends(get_optional_current_user)
):
    """Exports workflow schema as clean portable JSON."""
    wf = await WorkflowStore.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    export_obj = {
        "schema_version": "myagent_workflow_v1",
        "name": wf["name"],
        "description": wf.get("description", ""),
        "icon": wf.get("icon", "⚡"),
        "trigger_type": wf.get("trigger_type", "daily"),
        "schedule_expr": wf.get("schedule_expr", ""),
        "daily_time": wf.get("daily_time", "09:00"),
        "timezone": wf.get("timezone", "Asia/Dhaka"),
        "nodes": wf.get("nodes", []),
        "edges": wf.get("edges", [])
    }
    return {"success": True, "workflow": export_obj}


@router.get("/{workflow_id}")
async def get_workflow_details(
    workflow_id: str,
    user=Depends(get_optional_current_user)
):
    """Returns a single workflow definition and its recent runs."""
    wf = await WorkflowStore.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    wf["is_running"] = workflow_engine.is_running(workflow_id)
    runs = await WorkflowStore.list_runs(workflow_id=workflow_id, limit=15)
    return {"success": True, "workflow": wf, "runs": runs}


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    data: Dict[str, Any] = Body(...),
    user=Depends(get_optional_current_user)
):
    """Updates workflow graph (nodes, edges), schedule, or configuration."""
    wf = await WorkflowStore.update_workflow(workflow_id, data)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return {"success": True, "workflow": wf, "message": "Workflow updated successfully."}


@router.put("/{workflow_id}/toggle")
async def toggle_workflow(
    workflow_id: str,
    user=Depends(get_optional_current_user)
):
    """Enables or disables automatic scheduled execution of a workflow."""
    wf = await WorkflowStore.toggle_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return {"success": True, "workflow": wf, "is_enabled": wf["is_enabled"]}


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    user=Depends(get_optional_current_user)
):
    """Deletes a workflow and all its run logs."""
    ok = await WorkflowStore.delete_workflow(workflow_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return {"success": True, "message": "Workflow deleted."}


@router.post("/{workflow_id}/run")
async def run_workflow_now(
    workflow_id: str,
    data: Optional[Dict[str, Any]] = Body(default=None),
    user=Depends(get_optional_current_user)
):
    """Manually executes a workflow DAG immediately (supports payload & dry_run) and returns full trace."""
    try:
        body = data if isinstance(data, dict) else {}
        payload = body.get("payload", {})
        dry_run = bool(body.get("dry_run", False))
        res = await workflow_engine.execute_workflow(
            workflow_id=workflow_id,
            trigger_source="manual",
            trigger_payload=payload,
            dry_run=dry_run
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Manual workflow execution failed for '{workflow_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@router.post("/{workflow_id}/stop")
async def stop_workflow_run(
    workflow_id: str,
    user=Depends(get_optional_current_user)
):
    """Signals an active workflow run to cancel cleanly."""
    stopped = workflow_engine.stop_workflow(workflow_id)
    return {"success": True, "stopped": stopped, "message": "Cancellation signal sent." if stopped else "Workflow is not currently running."}


@router.get("/{workflow_id}/versions")
async def get_workflow_versions(
    workflow_id: str,
    limit: int = Query(15, le=30),
    user=Depends(get_optional_current_user)
):
    """Lists saved revision snapshots of a workflow for 1-click rollback."""
    versions = await WorkflowStore.list_versions(workflow_id, limit=limit)
    return {"success": True, "versions": versions}


@router.post("/{workflow_id}/versions/{version_id}/restore")
async def restore_workflow_version(
    workflow_id: str,
    version_id: str,
    user=Depends(get_optional_current_user)
):
    """Restores a prior workflow snapshot (and saves current state as a new revision)."""
    wf = await WorkflowStore.restore_version(workflow_id, version_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow version snapshot not found.")
    return {"success": True, "workflow": wf, "message": "Workflow version restored cleanly."}


@router.get("/{workflow_id}/runs")
async def get_workflow_runs(
    workflow_id: str,
    limit: int = Query(25, le=100),
    user=Depends(get_optional_current_user)
):
    """Returns execution runs for a specific workflow."""
    runs = await WorkflowStore.list_runs(workflow_id=workflow_id, limit=limit)
    return {"success": True, "runs": runs}

