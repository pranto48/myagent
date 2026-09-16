# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 3.0.0
# ==============================================================================

import os
import io
import time
import json
import uuid
import shutil
import zipfile
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import settings
from routers.auth import get_current_admin
from security.audit import SecurityAuditStore
from memory.vector_store import VectorMemoryStore
from memory.chat_session_store import ChatSessionStore

logger = logging.getLogger("myagent.backup")

router = APIRouter(prefix="/api/backup", tags=["Full System Backup & Disaster Recovery"])
audit_store = SecurityAuditStore()


class BackupCreateRequest(BaseModel):
    note: Optional[str] = "ম্যানুয়াল সম্পূর্ণ ব্যাকআপ"
    include_documents: bool = True
    include_chats: bool = True
    include_vector_db: bool = True
    include_settings: bool = True
    include_security_audit: bool = True


class RestoreRequest(BaseModel):
    filename: str
    create_safety_snapshot: bool = True


def get_safe_backup_path(filename: str) -> str:
    """Sanitizes filename and returns full path inside BACKUPS_DIR preventing path traversal."""
    clean_name = os.path.basename(filename)
    if not clean_name.endswith(".zip"):
        raise HTTPException(status_code=400, detail="অবৈধ ব্যাকআপ ফাইল ফরম্যাট। শুধুমাত্র .zip সমর্থিত।")
    backup_path = os.path.join(settings.BACKUPS_DIR, clean_name)
    return backup_path


def format_bytes(size: int) -> str:
    """Converts bytes to human readable string."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.2f} MB"


@router.post("/create")
async def create_backup(req: BackupCreateRequest, admin_user: dict = Depends(get_current_admin)):
    """
    Creates a full or modular compressed ZIP snapshot containing:
    1. Documents & uploaded files
    2. SQLite databases (chat history, user accounts, security audit, fast index)
    3. ChromaDB vector database index & embeddings
    4. System settings & configuration manifest
    """
    os.makedirs(settings.BACKUPS_DIR, exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_id = uuid.uuid4().hex[:8]
    zip_filename = f"myagent_backup_{timestamp_str}_{backup_id}.zip"
    zip_filepath = os.path.join(settings.BACKUPS_DIR, zip_filename)

    start_time = time.time()

    # Calculate statistics
    doc_count = len(os.listdir(settings.DOCUMENTS_DIR)) if os.path.exists(settings.DOCUMENTS_DIR) else 0
    upload_count = len(os.listdir(settings.UPLOADS_DIR)) if os.path.exists(settings.UPLOADS_DIR) else 0
    
    settings_payload = {
        "llm_base_url": settings.LLM_BASE_URL,
        "llm_model": settings.LLM_MODEL,
        "llm_api_key": settings.LLM_API_KEY,
        "agent_name": settings.AGENT_NAME,
        "agent_temperature": settings.AGENT_TEMPERATURE,
        "embedding_model": settings.EMBEDDING_MODEL,
        "chunking_size": settings.CHUNKING_SIZE,
        "chunking_overlap": settings.CHUNKING_OVERLAP,
        "top_k_results": settings.TOP_K_RESULTS,
        "web_port": settings.WEB_PORT,
        "backend_port": settings.BACKEND_PORT,
        "security": {
            "dlp_enabled": settings.DLP_ENABLED,
            "firewall_enabled": settings.FIREWALL_ENABLED,
            "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
            "audit_log_enabled": settings.AUDIT_LOG_ENABLED
        }
    }

    manifest = {
        "backup_id": backup_id,
        "version": "2.2.0",
        "created_at": datetime.now().isoformat(),
        "created_by": admin_user.get("sub", "admin"),
        "note": req.note,
        "modules": {
            "documents": req.include_documents,
            "chats": req.include_chats,
            "vector_db": req.include_vector_db,
            "settings": req.include_settings,
            "security_audit": req.include_security_audit
        },
        "stats": {
            "documents_count": doc_count,
            "uploads_count": upload_count
        },
        "settings": settings_payload
    }

    try:
        with zipfile.ZipFile(zip_filepath, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            # 1. Manifest
            zip_file.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

            # 2. Settings JSON
            if req.include_settings:
                zip_file.writestr("settings.json", json.dumps(settings_payload, ensure_ascii=False, indent=2))

            # 3. Documents
            if req.include_documents and os.path.exists(settings.DOCUMENTS_DIR):
                for root, _, files in os.walk(settings.DOCUMENTS_DIR):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, settings.DOCUMENTS_DIR)
                        zip_file.write(full_path, arcname=os.path.join("documents", rel_path))

            # 4. Uploads
            if req.include_documents and os.path.exists(settings.UPLOADS_DIR):
                for root, _, files in os.walk(settings.UPLOADS_DIR):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, settings.UPLOADS_DIR)
                        zip_file.write(full_path, arcname=os.path.join("uploads", rel_path))

            # 5. SQLite Databases
            if req.include_chats and os.path.exists(settings.SESSION_DB_PATH):
                zip_file.write(settings.SESSION_DB_PATH, arcname="databases/chat_history.db")
            
            fts_path = os.path.join(settings.DATA_DIR, "fast_index.db")
            if req.include_chats and os.path.exists(fts_path):
                zip_file.write(fts_path, arcname="databases/fast_index.db")

            if req.include_security_audit and os.path.exists(settings.AUDIT_DB_PATH):
                zip_file.write(settings.AUDIT_DB_PATH, arcname="databases/security_audit.db")

            # 6. ChromaDB Vector Store
            if req.include_vector_db and os.path.exists(settings.CHROMA_DIR):
                for root, _, files in os.walk(settings.CHROMA_DIR):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, settings.CHROMA_DIR)
                        zip_file.write(full_path, arcname=os.path.join("chroma_db", rel_path))

        file_size = os.path.getsize(zip_filepath)
        duration = round(time.time() - start_time, 2)

        # Audit event
        await audit_store.log_event(
            action="BACKUP_CREATED",
            resource="SystemBackup",
            username=admin_user.get("sub", "admin"),
            user_role=admin_user.get("role", "admin"),
            details={"message": f"Backup created: {zip_filename} ({format_bytes(file_size)}) in {duration}s"},
            severity="INFO"
        )

        return {
            "success": True,
            "message": f"সিস্টেমের সম্পূর্ণ ব্যাকআপ সফলভাবে তৈরি হয়েছে ({format_bytes(file_size)})",
            "backup": {
                "filename": zip_filename,
                "size_bytes": file_size,
                "size_formatted": format_bytes(file_size),
                "created_at": manifest["created_at"],
                "note": req.note,
                "duration_seconds": duration,
                "manifest": manifest
            }
        }
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        if os.path.exists(zip_filepath):
            try:
                os.remove(zip_filepath)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"ব্যাকআপ তৈরি ব্যর্থ হয়েছে: {str(e)}")


@router.get("/list")
async def list_backups(admin_user: dict = Depends(get_current_admin)):
    """
    Returns list of all available backups stored on server, sorted newest first.
    """
    os.makedirs(settings.BACKUPS_DIR, exist_ok=True)
    backups = []

    for item in os.listdir(settings.BACKUPS_DIR):
        if not item.endswith(".zip"):
            continue
        filepath = os.path.join(settings.BACKUPS_DIR, item)
        try:
            stat = os.stat(filepath)
            manifest = None
            try:
                with zipfile.ZipFile(filepath, "r") as z:
                    if "manifest.json" in z.namelist():
                        manifest = json.loads(z.read("manifest.json").decode("utf-8"))
            except Exception:
                manifest = None

            backups.append({
                "filename": item,
                "size_bytes": stat.st_size,
                "size_formatted": format_bytes(stat.st_size),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created_at": manifest.get("created_at") if manifest else datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created_by": manifest.get("created_by") if manifest else "unknown",
                "note": manifest.get("note") if manifest else "সিস্টেম ব্যাকআপ",
                "version": manifest.get("version") if manifest else "2.2.0",
                "modules": manifest.get("modules") if manifest else {}
            })
        except Exception as e:
            logger.warning(f"Error inspecting backup file {item}: {e}")

    backups.sort(key=lambda x: x["modified_at"], reverse=True)
    
    # Calculate storage stats
    total_backup_bytes = sum(b["size_bytes"] for b in backups)
    
    return {
        "total_backups": len(backups),
        "total_size_bytes": total_backup_bytes,
        "total_size_formatted": format_bytes(total_backup_bytes),
        "backups": backups
    }


@router.get("/download/{filename}")
async def download_backup(filename: str, admin_user: dict = Depends(get_current_admin)):
    """
    Streams the requested backup archive directly to the client browser.
    """
    filepath = get_safe_backup_path(filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="অনুরোধকৃত ব্যাকআপ ফাইলটি পাওয়া যায়নি।")

    return FileResponse(
        path=filepath,
        filename=os.path.basename(filepath),
        media_type="application/zip"
    )


@router.delete("/{filename}")
async def delete_backup(filename: str, admin_user: dict = Depends(get_current_admin)):
    """
    Permanently deletes a backup file from the server.
    """
    filepath = get_safe_backup_path(filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="ব্যাকআপ ফাইল পাওয়া যায়নি।")

    try:
        os.remove(filepath)
        await audit_store.log_event(
            action="BACKUP_DELETED",
            resource="SystemBackup",
            username=admin_user.get("sub", "admin"),
            user_role=admin_user.get("role", "admin"),
            details={"message": f"Backup deleted: {filename}"},
            severity="WARNING"
        )
        return {"success": True, "message": f"ব্যাকআপ ফাইল '{filename}' সফলভাবে মুছে ফেলা হয়েছে।"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ফাইল মুছতে ব্যর্থ: {str(e)}")


@router.post("/inspect")
async def inspect_backup(filename: str, admin_user: dict = Depends(get_current_admin)):
    """
    Inspects a backup zip archive and returns its manifest, structure, and integrity state.
    """
    filepath = get_safe_backup_path(filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="ব্যাকআপ ফাইল পাওয়া যায়নি।")

    try:
        with zipfile.ZipFile(filepath, "r") as z:
            file_list = z.namelist()
            manifest = None
            if "manifest.json" in file_list:
                manifest = json.loads(z.read("manifest.json").decode("utf-8"))

            return {
                "filename": filename,
                "total_files": len(file_list),
                "has_documents": any(f.startswith("documents/") for f in file_list),
                "has_databases": any(f.startswith("databases/") for f in file_list),
                "has_chroma": any(f.startswith("chroma_db/") for f in file_list),
                "has_settings": "settings.json" in file_list,
                "manifest": manifest
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"ব্যাকআপ ফাইল বিশ্লেষণ ব্যর্থ: {str(e)}")


def execute_restore_from_zip(zip_filepath: str, admin_user: dict, create_safety_snapshot: bool = True) -> Dict[str, Any]:
    """
    Synchronous core extraction and restoration engine:
    1. Creates optional safety snapshot before applying restore.
    2. Safely extracts files to target directories.
    3. Reloads vector memory store, caches, and application settings.
    """
    if not os.path.isfile(zip_filepath):
        raise HTTPException(status_code=404, detail="রিস্টোর করার ব্যাকআপ ফাইল পাওয়া যায়নি।")

    start_time = time.time()

    # Pre-restore safety snapshot
    if create_safety_snapshot:
        try:
            safety_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safety_name = f"safety_snapshot_before_restore_{safety_ts}.zip"
            safety_path = os.path.join(settings.BACKUPS_DIR, safety_name)
            with zipfile.ZipFile(safety_path, "w", compression=zipfile.ZIP_DEFLATED) as s_zip:
                for db_file in [settings.SESSION_DB_PATH, settings.AUDIT_DB_PATH, os.path.join(settings.DATA_DIR, "fast_index.db")]:
                    if os.path.exists(db_file):
                        s_zip.write(db_file, arcname=f"databases/{os.path.basename(db_file)}")
            logger.info(f"Safety snapshot created: {safety_name}")
        except Exception as e:
            logger.warning(f"Could not create pre-restore safety snapshot: {e}")

    restored_items = {
        "documents": 0,
        "uploads": 0,
        "databases": [],
        "chroma_db": False,
        "settings": False
    }

    try:
        with zipfile.ZipFile(zip_filepath, "r") as z:
            namelist = z.namelist()

            # 1. Extract documents
            for member in namelist:
                if member.startswith("documents/") and not member.endswith("/"):
                    target_file = os.path.join(settings.DOCUMENTS_DIR, os.path.relpath(member, "documents"))
                    os.makedirs(os.path.dirname(target_file), exist_ok=True)
                    with z.open(member) as source, open(target_file, "wb") as target:
                        shutil.copyfileobj(source, target)
                    restored_items["documents"] += 1

                elif member.startswith("uploads/") and not member.endswith("/"):
                    target_file = os.path.join(settings.UPLOADS_DIR, os.path.relpath(member, "uploads"))
                    os.makedirs(os.path.dirname(target_file), exist_ok=True)
                    with z.open(member) as source, open(target_file, "wb") as target:
                        shutil.copyfileobj(source, target)
                    restored_items["uploads"] += 1

            # 2. Extract SQLite databases
            for member in namelist:
                if member.startswith("databases/") and not member.endswith("/"):
                    db_name = os.path.basename(member)
                    if db_name == "chat_history.db":
                        target_db = settings.SESSION_DB_PATH
                    elif db_name == "security_audit.db":
                        target_db = settings.AUDIT_DB_PATH
                    elif db_name == "fast_index.db":
                        target_db = os.path.join(settings.DATA_DIR, "fast_index.db")
                    else:
                        target_db = os.path.join(settings.DATA_DIR, db_name)

                    os.makedirs(os.path.dirname(target_db), exist_ok=True)
                    with z.open(member) as source, open(target_db, "wb") as target:
                        shutil.copyfileobj(source, target)
                    restored_items["databases"].append(db_name)

            # 3. Extract ChromaDB
            chroma_members = [m for m in namelist if m.startswith("chroma_db/") and not m.endswith("/")]
            if chroma_members:
                for member in chroma_members:
                    target_file = os.path.join(settings.CHROMA_DIR, os.path.relpath(member, "chroma_db"))
                    os.makedirs(os.path.dirname(target_file), exist_ok=True)
                    with z.open(member) as source, open(target_file, "wb") as target:
                        shutil.copyfileobj(source, target)
                restored_items["chroma_db"] = True

            # 4. Restore Settings
            if "settings.json" in namelist:
                try:
                    s_data = json.loads(z.read("settings.json").decode("utf-8"))
                    if s_data.get("llm_base_url"):
                        settings.LLM_BASE_URL = s_data["llm_base_url"]
                    if s_data.get("llm_model"):
                        settings.LLM_MODEL = s_data["llm_model"]
                    if s_data.get("llm_api_key"):
                        settings.LLM_API_KEY = s_data["llm_api_key"]
                    if s_data.get("agent_temperature") is not None:
                        settings.AGENT_TEMPERATURE = float(s_data["agent_temperature"])
                    if s_data.get("top_k_results") is not None:
                        settings.TOP_K_RESULTS = int(s_data["top_k_results"])
                    restored_items["settings"] = True
                except Exception as e:
                    logger.warning(f"Failed to restore settings from backup: {e}")

        # Re-initialize singletons and memory stores
        try:
            v_store = VectorMemoryStore()
            if hasattr(v_store, "cache"):
                v_store.cache.clear()
            v_store._initialize()
        except Exception as e:
            logger.warning(f"Error re-initializing vector store post-restore: {e}")

        duration = round(time.time() - start_time, 2)

        return {
            "success": True,
            "message": "সিস্টেমের ব্যাকআপ সফলভাবে রিস্টোর করা হয়েছে।",
            "duration_seconds": duration,
            "restored_items": restored_items
        }
    except Exception as e:
        logger.error(f"Restore execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"রিস্টোর প্রক্রিয়া ব্যর্থ হয়েছে: {str(e)}")


@router.post("/restore")
async def restore_from_server(req: RestoreRequest, admin_user: dict = Depends(get_current_admin)):
    """
    Restores system data, chat history, vector index, and settings from a server-hosted backup file.
    """
    filepath = get_safe_backup_path(req.filename)
    result = execute_restore_from_zip(filepath, admin_user, create_safety_snapshot=req.create_safety_snapshot)

    # Log audit event
    await audit_store.log_event(
        action="BACKUP_RESTORED",
        resource="SystemBackup",
        username=admin_user.get("sub", "admin"),
        user_role=admin_user.get("role", "admin"),
        details={"message": f"Backup restored: {req.filename} in {result.get('duration_seconds')}s"},
        severity="WARNING"
    )

    return result


@router.post("/upload-restore")
async def upload_and_restore(file: UploadFile = File(...), admin_user: dict = Depends(get_current_admin)):
    """
    Uploads a .zip backup archive from the admin client and immediately validates & restores the system.
    """
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="শুধুমাত্র .zip ব্যাকআপ ফাইল আপলোড করা যাবে।")

    os.makedirs(settings.BACKUPS_DIR, exist_ok=True)
    temp_filename = f"uploaded_{int(time.time())}_{os.path.basename(file.filename)}"
    temp_filepath = os.path.join(settings.BACKUPS_DIR, temp_filename)

    try:
        with open(temp_filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Validate it is a valid zip
        if not zipfile.is_zipfile(temp_filepath):
            os.remove(temp_filepath)
            raise HTTPException(status_code=400, detail="ফাইলটি একটি সঠিক ZIP আর্কাইভ নয়।")

        result = execute_restore_from_zip(temp_filepath, admin_user, create_safety_snapshot=True)

        await audit_store.log_event(
            action="BACKUP_UPLOAD_RESTORED",
            resource="SystemBackup",
            username=admin_user.get("sub", "admin"),
            user_role=admin_user.get("role", "admin"),
            details={"message": f"Client uploaded and restored backup: {file.filename}"},
            severity="WARNING"
        )

        result["uploaded_filename"] = file.filename
        return result
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"আপলোড ও রিস্টোর প্রক্রিয়া ব্যর্থ: {str(e)}")
