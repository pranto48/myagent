# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.1.0
import os
import uuid
import shutil
import time
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
from config import settings
from memory.document_loader import DocumentProcessor
from memory.vector_store import VectorMemoryStore
from models.schemas import DocumentInfo

router = APIRouter(prefix="/api/documents", tags=["Company Documents"])

@router.post("/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Uploads and indexes one or multiple company documents into vector memory.
    Supports PDF, DOCX, XLSX, CSV, TXT, JSON, MD.
    """
    store = VectorMemoryStore()
    processed_files = []

    for file in files:
        if not file.filename:
            continue

        doc_id = f"doc_{uuid.uuid4().hex[:10]}"
        safe_filename = Path(file.filename).name
        target_path = os.path.join(settings.DOCUMENTS_DIR, f"{doc_id}_{safe_filename}")

        # Save to disk
        try:
            with open(target_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file {safe_filename}: {str(e)}")

        # Process and chunk
        try:
            chunks = DocumentProcessor.process_file_into_chunks(
                file_path=target_path,
                doc_id=doc_id,
                original_filename=safe_filename
            )
            
            # Store in ChromaDB
            stored_count = store.add_chunks(chunks)
            file_size = os.path.getsize(target_path)

            processed_files.append({
                "doc_id": doc_id,
                "filename": safe_filename,
                "size_bytes": file_size,
                "chunks_count": stored_count,
                "status": "indexed"
            })
        except Exception as e:
            # Cleanup on failure
            if os.path.exists(target_path):
                os.remove(target_path)
            raise HTTPException(status_code=400, detail=f"Failed to index {safe_filename}: {str(e)}")

    return {
        "success": True,
        "message": f"Successfully processed and indexed {len(processed_files)} document(s)",
        "documents": processed_files
    }

@router.get("", response_model=List[DocumentInfo])
async def list_documents():
    """
    Lists all saved company documents and their chunk counts.
    """
    store = VectorMemoryStore()
    docs_dir = Path(settings.DOCUMENTS_DIR)
    
    if not docs_dir.exists():
        return []

    results = []
    seen_ids = set()

    for file_path in docs_dir.glob("*_*"):
        if file_path.is_file() and not file_path.name.startswith("."):
            parts = file_path.name.split("_", 1)
            if len(parts) == 2 and parts[0].startswith("doc_"):
                doc_id = parts[0]
                filename = parts[1]
                if doc_id in seen_ids:
                    continue
                seen_ids.add(doc_id)

                size = file_path.stat().st_size
                mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_path.stat().st_mtime))

                try:
                    query_result = store.collection.get(where={"doc_id": doc_id})
                    chunks_count = len(query_result["ids"]) if query_result and "ids" in query_result else 0
                except Exception:
                    chunks_count = 0

                results.append(DocumentInfo(
                    doc_id=doc_id,
                    filename=filename,
                    size_bytes=size,
                    chunks_count=chunks_count,
                    created_at=mtime
                ))

    return results

@router.get("/{doc_id}/chunks")
async def get_document_chunks(doc_id: str):
    """
    Returns all vector chunks associated with a specific document for inspection.
    """
    store = VectorMemoryStore()
    try:
        query_result = store.collection.get(where={"doc_id": doc_id}, include=["documents", "metadatas"])
        chunks = []
        if query_result and "ids" in query_result:
            ids = query_result["ids"]
            docs = query_result.get("documents", [])
            metas = query_result.get("metadatas", [])
            for i in range(len(ids)):
                chunks.append({
                    "chunk_id": ids[i],
                    "content": docs[i] if i < len(docs) else "",
                    "metadata": metas[i] if i < len(metas) else {}
                })
        return {"doc_id": doc_id, "total_chunks": len(chunks), "chunks": chunks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chunks for {doc_id}: {str(e)}")

@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """
    Deletes a document from disk and purges all its vector chunks from memory.
    """
    store = VectorMemoryStore()
    docs_dir = Path(settings.DOCUMENTS_DIR)

    # 1. Purge vectors
    store.delete_document(doc_id)

    # 2. Remove physical file
    deleted_file = False
    for file_path in docs_dir.glob(f"{doc_id}_*"):
        try:
            os.remove(file_path)
            deleted_file = True
        except Exception:
            pass

    return {
        "success": True,
        "message": f"Document {doc_id} and its memory vectors removed successfully."
    }
