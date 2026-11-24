# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.1.0
import logging
from typing import Dict, Any, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, EmailStr
from config import settings
from routers.auth import get_current_user
from services.resend_service import resend_service

logger = logging.getLogger("myagent.routers.email")

router = APIRouter(prefix="/api/email", tags=["Email & Resend"])


class TestEmailRequest(BaseModel):
    to: str
    subject: Optional[str] = "MyAgent Test Notification"
    body: Optional[str] = "This is an automated test email sent from MyAgent Enterprise using the Resend API."
    from_email: Optional[str] = None


class SendEmailRequest(BaseModel):
    to: Union[str, List[str]]
    subject: str
    body: Optional[str] = ""
    html: Optional[str] = ""
    from_email: Optional[str] = None
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None


@router.get("/resend/status")
async def get_resend_status():
    """
    Returns live connection status with Resend API, including verified domains,
    active key metadata, and configured default sender.
    """
    try:
        status = await resend_service.check_status()
        return status
    except Exception as e:
        logger.error(f"Failed to check Resend status: {e}")
        return {
            "ok": False,
            "configured": bool(getattr(settings, "RESEND_API_KEY", "")),
            "is_valid": False,
            "error": str(e),
            "domains": [],
            "verified_domains": []
        }


@router.post("/resend/test")
async def send_resend_test_email(payload: TestEmailRequest):
    """
    Dispatches a single test email using the configured Resend API key.
    """
    if not payload.to or "@" not in payload.to:
        raise HTTPException(status_code=400, detail="Invalid recipient email address.")

    res = await resend_service.send_email(
        to=payload.to,
        subject=payload.subject or "MyAgent Test Notification",
        body=payload.body or "This is a test email.",
        from_email=payload.from_email
    )

    if not res.get("ok"):
        raise HTTPException(status_code=502, detail=res.get("error", "Email dispatch failed."))

    return {
        "success": True,
        "message": "Test email successfully dispatched via Resend!",
        "details": res
    }


@router.post("/resend/send")
async def send_resend_email_api(payload: SendEmailRequest):
    """
    Universal email sending endpoint for autonomous workflows, web panel, and sub-agents.
    """
    res = await resend_service.send_email(
        to=payload.to,
        subject=payload.subject,
        body=payload.body or "",
        html=payload.html or "",
        from_email=payload.from_email,
        cc=payload.cc,
        bcc=payload.bcc
    )

    if not res.get("ok"):
        raise HTTPException(status_code=502, detail=res.get("error", "Email dispatch failed."))

    return {
        "success": True,
        "message": "Email sent successfully!",
        "details": res
    }
