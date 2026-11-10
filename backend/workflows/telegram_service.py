# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 3.5.0
# Shared Telegram Bot API Service for Workflows (Auto) & Ops Channels
# ==============================================================================

import time
import logging
from typing import Any, Dict, List

import httpx

from workflows.store import WorkflowStore

logger = logging.getLogger("myagent.workflows.telegram")

TELEGRAM_API_BASE = "https://api.telegram.org"


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
    clean_text = (text or "").strip()[:3900] or "(Empty workflow message)"
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

    t0 = time.time()
    url = f"{TELEGRAM_API_BASE}/bot{tok}/sendMessage"
    payload: Dict[str, Any] = {"chat_id": cid, "text": clean_text}
    pm = (parse_mode or "").strip()
    if pm in ("Markdown", "MarkdownV2", "HTML"):
        payload["parse_mode"] = pm

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(url, json=payload)
            # Retry once as plain text if entity parsing fails on rich agent markdown output
            if resp.status_code == 400 and "parse_mode" in payload and "parse entities" in resp.text.lower():
                payload.pop("parse_mode", None)
                resp = await client.post(url, json=payload)

        latency_ms = int((time.time() - t0) * 1000)
        try:
            body = resp.json()
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
