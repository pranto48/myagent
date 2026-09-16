# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.0.0
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from security.audit import SecurityAuditStore
from security.dlp import DLPEngine
from security.firewall import PromptFirewall
from security.crypto import DataCrypto
from memory.vector_store import VectorStore
from routers.auth import get_current_user

router = APIRouter(prefix="/api/security", tags=["Data Security & Compliance"])

audit_store = SecurityAuditStore()
vector_store = VectorStore()
crypto_engine = DataCrypto()

class SandboxTestRequest(BaseModel):
    sample_text: str = Field(..., description="Text or prompt to analyze through DLP and Firewall")

class ClassificationUpdateRequest(BaseModel):
    document_id: str
    security_level: str = Field("INTERNAL", description="PUBLIC, INTERNAL, CONFIDENTIAL, or RESTRICTED_ADMIN")

@router.get("/stats")
async def get_security_overview(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns security telemetry, active threat posture, and encryption state."""
    stats = await audit_store.get_security_stats()
    return stats

@router.get("/audit-logs")
async def get_audit_trail(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    severity: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieves immutable security audit logs with filtering and pagination."""
    if current_user.get("role") not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Security audit logs require Analyst or Admin clearance.")
    
    result = await audit_store.get_audit_logs(
        limit=limit,
        offset=offset,
        severity=severity,
        action=action,
        search=search
    )
    return result

@router.post("/sandbox-test")
async def run_security_sandbox(
    payload: SandboxTestRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Interactive testbed for administrators to inspect text against DLP PII masking
    and Prompt Injection firewall rules in real-time.
    """
    text = payload.sample_text
    
    # 1. Run through Firewall
    firewall_res = PromptFirewall.inspect_prompt(text)
    
    # 2. Run through DLP
    dlp_res = DLPEngine.inspect_text(text)

    # 3. Simulate AES-256 encryption & decryption cycle
    encrypted_sample = crypto_engine.encrypt_text(text[:64])
    decrypted_sample = crypto_engine.decrypt_text(encrypted_sample)

    return {
        "firewall": firewall_res,
        "dlp": dlp_res,
        "crypto_demo": {
            "cipher": "AES-256-GCM",
            "encrypted_preview": encrypted_sample,
            "decrypted_matches": decrypted_sample == text[:64]
        }
    }

@router.put("/documents/{doc_id}/classification")
async def update_document_security_level(
    doc_id: str,
    payload: ClassificationUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Updates the sensitivity classification for a specific document."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only administrators can reclassify document security levels.")

    valid_levels = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED_ADMIN"]
    level = payload.security_level.upper()
    if level not in valid_levels:
        raise HTTPException(status_code=400, detail=f"Invalid classification. Must be one of {valid_levels}")

    # Reclassify in vector store
    success = vector_store.reclassify_document(doc_id, level)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found or reclassification failed.")

    # Record audit log
    await audit_store.log_event(
        action="DOCUMENT_RECLASSIFIED",
        username=current_user.get("sub", "admin"),
        user_role=current_user.get("role", "admin"),
        resource=doc_id,
        severity="WARNING",
        details={"new_classification": level}
    )

    return {"status": "success", "document_id": doc_id, "security_level": level}
