# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.0.0
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
from models.schemas import DocumentInfo, QuickNoteRequest

router = APIRouter(prefix="/api/documents", tags=["Company Documents"])

@router.post("/quick-note")
async def create_quick_note(req: QuickNoteRequest):
    """
    Saves an instant note/knowledge snippet directly to agent memory and disk (< 50ms).
    """
    store = VectorMemoryStore()
    try:
        res = store.add_note(
            title=req.title,
            content=req.content,
            category=req.category or "notes",
            security_level=req.security_level or "INTERNAL"
        )
        return {
            "success": True,
            "message": f"নোট '{req.title}' সফলভাবে এজেন্টের স্থায়ী মেমোরিতে সংরক্ষণ করা হয়েছে।",
            "note": res
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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

def parse_doc_filename(name: str):
    """
    Parses 'doc_<hex>_<realname>' into (doc_id, realname).
    Returns (None, None) if not matching.
    """
    if not name.startswith("doc_"):
        return None, None
    parts = name.split("_", 2)
    if len(parts) >= 3:
        doc_id = f"{parts[0]}_{parts[1]}"
        return doc_id, parts[2]
    return None, None

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

    for file_path in docs_dir.glob("doc_*_*"):
        if file_path.is_file() and not file_path.name.startswith("."):
            doc_id, filename = parse_doc_filename(file_path.name)
            if not doc_id or doc_id in seen_ids:
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

@router.post("/reindex")
async def reindex_documents(doc_id: str = None):
    """
    Re-chunks and re-indexes stored documents using the upgraded smart, table-aware vector pipeline.
    Preserves all physical files while rebuilding optimal vector embeddings and FTS indexes.
    """
    store = VectorMemoryStore()
    docs_dir = Path(settings.DOCUMENTS_DIR)
    
    if not docs_dir.exists():
        return {"success": True, "message": "কোনো সংরক্ষিত ফাইল পাওয়া যায়নি।", "reindexed_count": 0}

    files_to_process = []
    seen_ids = set()

    for file_path in docs_dir.glob("doc_*_*"):
        if file_path.is_file() and not file_path.name.startswith("."):
            d_id, filename = parse_doc_filename(file_path.name)
            if not d_id or (doc_id and d_id != doc_id):
                continue
            if d_id in seen_ids:
                continue
            seen_ids.add(d_id)
            files_to_process.append((file_path, d_id, filename))

    if not files_to_process:
        return {"success": True, "message": "রি-ইনডেক্স করার মতো কোনো ফাইল পাওয়া যায়নি।", "total_files": 0, "total_chunks": 0}

    total_chunks = 0
    reindexed_files = []
    start_time = time.time()

    for file_path, d_id, filename in files_to_process:
        try:
            # 1. Clear old chunks for this document
            store.delete_document(d_id)

            # 2. Process with upgraded table-aware / smart chunker
            chunks = DocumentProcessor.process_file_into_chunks(
                file_path=str(file_path),
                doc_id=d_id,
                original_filename=filename
            )

            # 3. Add to vector store
            stored_count = store.add_chunks(chunks)
            total_chunks += stored_count
            reindexed_files.append({
                "doc_id": d_id,
                "filename": filename,
                "chunks": stored_count,
                "status": "reindexed"
            })
        except Exception as e:
            reindexed_files.append({
                "doc_id": d_id,
                "filename": filename,
                "status": "error",
                "error": str(e)
            })

    # Run optimizer after re-indexing
    try:
        store.optimize_memory_store()
    except Exception:
        pass

    elapsed = round(time.time() - start_time, 2)
    return {
        "success": True,
        "message": f"সফলভাবে {len(reindexed_files)} টি ফাইল পুনরায় প্রসেস ও ইনডেক্স করা হয়েছে (মোট {total_chunks} চাঙ্ক, সময় {elapsed}s)।",
        "total_files": len(reindexed_files),
        "total_chunks": total_chunks,
        "elapsed_seconds": elapsed,
        "details": reindexed_files
    }

