# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.1.0
import os
import asyncio
import re
import html as html_lib
import time
import logging
from typing import Dict, Any, List, Optional, Union
import httpx
from config import settings

logger = logging.getLogger("myagent.services.resend")

RESEND_API_BASE = "https://api.resend.com"

class ResendEmailService:
    """
    Resilient Resend Email Service for MyAgent:
      - Sends high-deliverability emails via Resend REST API (https://api.resend.com/emails)
      - Auto-detects verified sending domains (e.g. itsupport.bd) vs sandbox (onboarding@resend.dev)
      - Generates beautiful responsive HTML email templates with MyAgent branding
      - Integrated with WORKFLOWS (Auto), AgentTools, MCP Server, and Telegram Bot
    """

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or getattr(settings, "RESEND_API_KEY", "")

    def get_api_key(self) -> str:
        return (self._api_key or getattr(settings, "RESEND_API_KEY", "") or "").strip()

    @staticmethod
    def mask_api_key(key: str) -> str:
        k = (key or "").strip()
        if not k:
            return ""
        if len(k) <= 8:
            return "***"
        return f"{k[:7]}...{k[-4:]}"

    async def check_status(self, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Validates API key against Resend API and retrieves active keys and verified domains.
        """
        key = (api_key or self.get_api_key()).strip()
        if not key:
            return {
                "ok": False,
                "configured": False,
                "api_key_masked": "",
                "is_valid": False,
                "error": "Resend API key is not configured.",
                "active_key_name": "",
                "domains": [],
                "verified_domains": [],
                "default_from": getattr(settings, "RESEND_DEFAULT_FROM", "MyAgent <onboarding@resend.dev>"),
                "recommended_from": getattr(settings, "RESEND_DEFAULT_FROM", "MyAgent <onboarding@resend.dev>")
            }

        headers = {
            "Authorization": f"Bearer {key}",
            "User-Agent": "MyAgent-Enterprise/3.1"
        }

        t0 = time.time()
        domains_list: List[Dict[str, Any]] = []
        verified_domains: List[str] = []
        active_key_name = ""

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 1. Inspect API keys
                r_keys = await client.get(f"{RESEND_API_BASE}/api-keys", headers=headers)
                if r_keys.status_code == 200:
                    keys_data = r_keys.json().get("data", [])
                    if keys_data:
                        active_key_name = keys_data[0].get("name", "active_key")
                elif r_keys.status_code == 401:
                    return {
                        "ok": False,
                        "configured": True,
                        "api_key_masked": self.mask_api_key(key),
                        "is_valid": False,
                        "error": "Invalid API key (401 Unauthorized).",
                        "active_key_name": "",
                        "domains": [],
                        "verified_domains": [],
                        "default_from": getattr(settings, "RESEND_DEFAULT_FROM", "MyAgent <onboarding@resend.dev>"),
                        "recommended_from": getattr(settings, "RESEND_DEFAULT_FROM", "MyAgent <onboarding@resend.dev>")
                    }

                # 2. Inspect Domains
                r_domains = await client.get(f"{RESEND_API_BASE}/domains", headers=headers)
                if r_domains.status_code == 200:
                    d_items = r_domains.json().get("data", [])
                    for d in d_items:
                        d_name = d.get("name", "")
                        d_status = d.get("status", "")
                        domains_list.append({
                            "id": d.get("id"),
                            "name": d_name,
                            "status": d_status,
                            "region": d.get("region", "us-east-1"),
                            "sending": d.get("capabilities", {}).get("sending", "disabled")
                        })
                        if d_status == "verified":
                            verified_domains.append(d_name)

            # Recommend sender based on verified domains
            recommended_from = getattr(settings, "RESEND_DEFAULT_FROM", "MyAgent <onboarding@resend.dev>")
            if "itsupport.bd" in verified_domains:
                recommended_from = "MyAgent <notifications@itsupport.bd>"
            elif verified_domains:
                recommended_from = f"MyAgent <notifications@{verified_domains[0]}>"

            latency_ms = int((time.time() - t0) * 1000)
            return {
                "ok": True,
                "configured": True,
                "api_key_masked": self.mask_api_key(key),
                "is_valid": True,
                "error": "",
                "latency_ms": latency_ms,
                "active_key_name": active_key_name,
                "domains": domains_list,
                "verified_domains": verified_domains,
                "default_from": getattr(settings, "RESEND_DEFAULT_FROM", "MyAgent <onboarding@resend.dev>"),
                "recommended_from": recommended_from
            }

        except Exception as e:
            logger.error(f"Error checking Resend status: {e}")
            return {
                "ok": False,
                "configured": True,
                "api_key_masked": self.mask_api_key(key),
                "is_valid": False,
                "error": str(e),
                "active_key_name": "",
                "domains": [],
                "verified_domains": [],
                "default_from": getattr(settings, "RESEND_DEFAULT_FROM", "MyAgent <onboarding@resend.dev>"),
                "recommended_from": getattr(settings, "RESEND_DEFAULT_FROM", "MyAgent <onboarding@resend.dev>")
            }

    @staticmethod
    def build_html_template(
        subject: str,
        body_text: str,
        subtitle: str = "MyAgent Autonomous Intelligence Alert"
    ) -> str:
        """
        Creates a clean, responsive, dark/light-compatible HTML email template.
        """
        # Convert plain newlines to paragraphs/linebreaks and markdown headers
        escaped_body = html_lib.escape(body_text.strip())
        
        # Simple markdown enhancements for headers and bold
        formatted_body = re.sub(r'###\s+(.*?)\n', r'<h3 style="color:#0ea5e9;margin:16px 0 8px;">\1</h3>', escaped_body)
        formatted_body = re.sub(r'##\s+(.*?)\n', r'<h2 style="color:#38bdf8;margin:20px 0 10px;">\1</h2>', formatted_body)
        formatted_body = re.sub(r'#\s+(.*?)\n', r'<h1 style="color:#0284c7;margin:24px 0 12px;">\1</h1>', formatted_body)
        formatted_body = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', formatted_body)
        formatted_body = re.sub(r'`(.*?)`', r'<code style="background:#0f172a;color:#38bdf8;padding:2px 6px;border-radius:4px;font-size:0.88em;">\1</code>', formatted_body)
        formatted_body = formatted_body.replace("\n\n", "</p><p style='margin:0 0 14px;'>").replace("\n", "<br/>")

        now_str = time.strftime("%Y-%m-%d %H:%M:%S UTC")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html_lib.escape(subject)}</title>
</head>
<body style="margin:0;padding:24px 12px;background-color:#0b0f19;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#e2e8f0;line-height:1.6;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:620px;margin:0 auto;background:#111827;border:1px solid #1f2937;border-radius:12px;overflow:hidden;box-shadow:0 10px 25px rgba(0,0,0,0.5);">
    <!-- Header -->
    <tr>
      <td style="padding:24px 28px;background:linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);border-bottom:1px solid #312e81;">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td>
              <span style="font-size:24px;line-height:1;margin-right:8px;">🤖</span>
              <strong style="font-size:19px;color:#f8fafc;letter-spacing:0.5px;">MyAgent Enterprise</strong>
              <div style="font-size:12px;color:#94a3b8;margin-top:4px;">{html_lib.escape(subtitle)}</div>
            </td>
            <td align="right" style="vertical-align:top;">
              <span style="display:inline-block;padding:4px 10px;background:rgba(56,189,248,0.15);color:#38bdf8;border:1px solid rgba(56,189,248,0.3);border-radius:20px;font-size:11px;font-weight:600;">
                Resend Verified
              </span>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- Subject Banner -->
    <tr>
      <td style="padding:20px 28px 10px;background:#111827;">
        <h2 style="margin:0;font-size:18px;color:#38bdf8;font-weight:600;">{html_lib.escape(subject)}</h2>
      </td>
    </tr>

    <!-- Body Content -->
    <tr>
      <td style="padding:14px 28px 28px;background:#111827;color:#cbd5e1;font-size:14px;line-height:1.7;">
        <div style="background:#0b0f19;border:1px solid #1e293b;border-radius:8px;padding:20px 22px;">
          <p style="margin:0 0 14px;">{formatted_body}</p>
        </div>
      </td>
    </tr>

    <!-- Footer -->
    <tr>
      <td style="padding:18px 28px;background:#090d16;border-top:1px solid #1f2937;font-size:11px;color:#64748b;text-align:center;">
        <div>Sent autonomically by <strong>MyAgent System</strong> | IT Support BD</div>
        <div style="margin-top:4px;">Timestamp: {now_str} • Host: 192.168.9.9:3399</div>
      </td>
    </tr>
  </table>
</body>
</html>"""

    async def send_email(
        self,
        to: Union[str, List[str]],
        subject: str,
        body: str = "",
        html: str = "",
        from_email: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
        tags: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Dispatches an email via Resend REST API (https://api.resend.com/emails).
        """
        key = self.get_api_key()
        if not key:
            return {
                "ok": False,
                "error": "Resend API key is not configured. Set RESEND_API_KEY in .env or settings.",
                "id": None
            }

        # Format recipient list
        recipients: List[str] = []
        if isinstance(to, str):
            # Support comma-separated emails
            recipients = [e.strip() for e in to.split(",") if e.strip() and "@" in e]
        elif isinstance(to, list):
            recipients = [str(e).strip() for e in to if e and "@" in str(e)]

        if not recipients:
            return {
                "ok": False,
                "error": f"Invalid recipient email address: '{to}'. Must contain a valid email address.",
                "id": None
            }

        clean_subject = (subject or "MyAgent Autonomous Notification").strip()
        clean_body = (body or "").strip()

        # Resolve sender: check if from_email provided, else use verified or onboarding default
        sender = (from_email or "").strip()
        if not sender:
            # Check configured verified domain or default
            v_from = getattr(settings, "RESEND_VERIFIED_FROM", "MyAgent <notifications@itsupport.bd>")
            d_from = getattr(settings, "RESEND_DEFAULT_FROM", "MyAgent <onboarding@resend.dev>")
            sender = v_from if v_from else d_from

        # Prepare HTML body
        html_content = html.strip() if html else self.build_html_template(clean_subject, clean_body or clean_subject)

        payload: Dict[str, Any] = {
            "from": sender,
            "to": recipients,
            "subject": clean_subject,
            "html": html_content,
            "text": clean_body or clean_subject
        }

        if cc:
            payload["cc"] = [str(e).strip() for e in cc if e]
        if bcc:
            payload["bcc"] = [str(e).strip() for e in bcc if e]
        if reply_to:
            payload["reply_to"] = reply_to.strip()
        if tags:
            payload["tags"] = tags

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "MyAgent-Enterprise/3.1"
        }

        t0 = time.time()
        res = None
        last_net_err = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=25.0) as client:
                    res = await client.post(
                        f"{RESEND_API_BASE}/emails",
                        json=payload,
                        headers=headers
                    )
                break
            except Exception as net_ex:
                last_net_err = net_ex
                logger.warning(f"Resend API connection attempt {attempt+1} failed: {net_ex}")
                if attempt < 2:
                    await asyncio.sleep(1.5)

        if res is None:
            return {
                "ok": False,
                "error": f"Resend API network exception: {last_net_err}",
                "id": None
            }

        latency_ms = int((time.time() - t0) * 1000)
        status_code = res.status_code

        try:
            data = res.json()
        except Exception:
            data = {"raw_text": res.text}

        if status_code in (200, 201):
            msg_id = data.get("id") or ""
            logger.info(f"Resend email dispatched successfully! ID={msg_id}, To={recipients}, Sender={sender}")
            return {
                "ok": True,
                "id": msg_id,
                "from": sender,
                "to": recipients,
                "subject": clean_subject,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "error": ""
            }

        # If sender failed because custom domain is not yet active or sandbox rule:
        # Auto-fallback to onboarding@resend.dev if first attempt failed on custom domain
        err_msg = data.get("message") or res.text
        if status_code in (403, 422) and "onboarding@resend.dev" not in sender:
            logger.warning(f"Resend custom sender failed ({err_msg}). Retrying with sandbox sender 'onboarding@resend.dev'...")
            payload["from"] = "MyAgent <onboarding@resend.dev>"
            async with httpx.AsyncClient(timeout=15.0) as client:
                fallback_res = await client.post(
                    f"{RESEND_API_BASE}/emails",
                    json=payload,
                    headers=headers
                )
            if fallback_res.status_code in (200, 201):
                fb_data = fallback_res.json()
                msg_id = fb_data.get("id") or ""
                return {
                    "ok": True,
                    "id": msg_id,
                    "from": payload["from"],
                    "to": recipients,
                    "subject": clean_subject,
                    "status_code": fallback_res.status_code,
                    "fallback_used": True,
                    "error": ""
                }

        logger.error(f"Resend email failed: HTTP {status_code} - {err_msg}")
        return {
            "ok": False,
            "id": None,
            "from": sender,
            "to": recipients,
            "subject": clean_subject,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "error": f"Resend API Error (HTTP {status_code}): {err_msg}"
        }

# Singleton instance
resend_service = ResendEmailService()
