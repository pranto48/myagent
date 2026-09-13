# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 3.0.0
# Reports API Router
# ==============================================================================

import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from agent.report_agent import ReportAgent, REPORT_TEMPLATES
from routers.auth import get_optional_current_user

router = APIRouter(prefix="/api/reports", tags=["Report Generator"])

_report_agent = None

def get_report_agent() -> ReportAgent:
    global _report_agent
    if _report_agent is None:
        _report_agent = ReportAgent()
    return _report_agent


class ReportGenerateRequest(BaseModel):
    report_type: str = Field(default="executive_summary", description="Type: executive_summary, data_analysis, kpi_report, incident_report, meeting_minutes, company_policy, custom")
    topic: str = Field(..., description="The main subject or topic of the report")
    additional_context: Optional[str] = Field(default="", description="Extra instructions or context for the report")


@router.get("/templates")
async def list_report_templates():
    """Returns all available report templates."""
    return {
        "templates": [
            {
                "id": key,
                "name": val["name"],
                "icon": val["icon"]
            }
            for key, val in REPORT_TEMPLATES.items()
        ]
    }


@router.post("/generate")
async def generate_report(
    request: ReportGenerateRequest,
    current_user: dict = Depends(get_optional_current_user)
):
    """
    Generates an AI-powered enterprise report using company knowledge base.
    Saves the report to persistent storage and indexes it into memory.
    """
    if request.report_type not in REPORT_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"Invalid report_type. Valid types: {list(REPORT_TEMPLATES.keys())}")

    if not request.topic.strip():
        raise HTTPException(status_code=400, detail="Report topic cannot be empty.")

    agent = get_report_agent()
    username = current_user.get("sub", "admin") if current_user else "admin"

    result = await agent.generate_report(
        report_type=request.report_type,
        topic=request.topic.strip(),
        additional_context=request.additional_context or "",
        created_by=username
    )

    return result


@router.get("/list")
async def list_reports(
    limit: int = 50,
    current_user: dict = Depends(get_optional_current_user)
):
    """Returns a list of all generated reports with metadata (no content)."""
    agent = get_report_agent()
    reports = agent.list_reports(limit=limit)
    return {"reports": reports, "total": len(reports)}


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    current_user: dict = Depends(get_optional_current_user)
):
    """Returns a single report with full content."""
    agent = get_report_agent()
    report = agent.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    current_user: dict = Depends(get_optional_current_user)
):
    """Downloads a report as a Markdown text file."""
    agent = get_report_agent()
    report = agent.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    filename = f"{report_id}_{report['topic'][:30].replace(' ', '_')}.md"
    content = report["content"]

    return PlainTextResponse(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\""
        }
    )


@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    current_user: dict = Depends(get_optional_current_user)
):
    """Deletes a report permanently."""
    agent = get_report_agent()
    deleted = agent.delete_report(report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found.")
    return {"success": True, "message": f"রিপোর্ট `{report_id}` সফলভাবে মুছে ফেলা হয়েছে।"}
