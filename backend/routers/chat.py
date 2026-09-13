# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.2.0
import os
import json
import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from models.schemas import ChatRequest, ChatResponse
from agent.core_agent import CompanyAIAgent
from memory.chat_session_store import ChatSessionStore
from memory.document_loader import DocumentProcessor
from memory.vector_store import VectorMemoryStore
from routers.auth import get_optional_current_user
from config import settings

router = APIRouter(prefix="/api/chat", tags=["Chat & Agent"])

_agent_instance = None

def get_agent() -> CompanyAIAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = CompanyAIAgent()
    return _agent_instance

@router.post("/upload")
async def upload_chat_files(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_optional_current_user)
):
    """
    Directly uploads and processes files (Excel, Photos/Images with OCR, PDF, Word, CSV)
    from the Gemini/ChatGPT-style chat bar.
    Indexes them into vector memory and returns structured summaries and table/OCR previews.
    """
    store = VectorMemoryStore()
    processed_results = []
    
    os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
    os.makedirs(settings.DOCUMENTS_DIR, exist_ok=True)

    for file in files:
        if not file.filename:
            continue

        safe_filename = Path(file.filename).name
        doc_id = f"chat_{uuid.uuid4().hex[:10]}"
        target_path = os.path.join(settings.UPLOADS_DIR, f"{doc_id}_{safe_filename}")
        doc_path = os.path.join(settings.DOCUMENTS_DIR, f"{doc_id}_{safe_filename}")

        # Save to uploads and documents directory
        try:
            with open(target_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            if target_path != doc_path:
                shutil.copyfile(target_path, doc_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"ফাইল সংরক্ষণ করতে সমস্যা: {str(e)}")

        # Process and index chunks into vector memory
        stored_count = 0
        try:
            chunks = DocumentProcessor.process_file_into_chunks(
                file_path=target_path,
                doc_id=doc_id,
                original_filename=safe_filename
            )
            stored_count = store.add_chunks(chunks)
        except Exception as chunk_err:
            pass

        # Generate rich instant summary, markdown table, or OCR extraction
        file_summary = DocumentProcessor.generate_file_quick_summary(
            file_path=target_path,
            filename=safe_filename
        )
        file_summary["doc_id"] = doc_id
        file_summary["chunks_indexed"] = stored_count
        processed_results.append(file_summary)

    return {
        "success": True,
        "message": f"সফলভাবে {len(processed_results)}টি ফাইল প্রসেস ও সংযুক্ত করা হয়েছে।",
        "files": processed_results
    }

@router.post("/stream")
async def stream_chat_endpoint(
    request: ChatRequest,
    agent: CompanyAIAgent = Depends(get_agent),
    current_user: dict = Depends(get_optional_current_user)
):
    """
    Streams the AI Agent response in real-time using Server-Sent Events (SSE)
    enforcing prompt firewall, DLP sanitization, Document-Level Security (DLS),
    and direct context injection for chat-attached files.
    """
    session_id = request.session_id
    username = current_user.get("sub", "guest")
    user_role = current_user.get("role", "viewer")

    # Record user message in persistent session store
    if session_id:
        await ChatSessionStore.add_message(session_id=session_id, role="user", content=request.prompt)

    async def event_generator():
        assistant_full_reply = ""
        citations = []
        try:
            generator = agent.stream_chat(
                prompt=request.prompt,
                history=request.history,
                use_memory=request.use_memory,
                temperature=request.temperature,
                model=request.model,
                username=username,
                user_role=user_role,
                attached_files=request.attached_files
            )

            async for chunk in generator:
                yield chunk
                # Extract tokens and sources for persistent logging
                if chunk.startswith("data: "):
                    payload_str = chunk[6:].strip()
                    if payload_str:
                        try:
                            data = json.loads(payload_str)
                            if data.get("type") == "token":
                                assistant_full_reply += data.get("token", "")
                            elif data.get("type") == "sources":
                                citations = data.get("sources", [])
                        except Exception:
                            pass

            # Save assistant response to session store
            if session_id and assistant_full_reply:
                await ChatSessionStore.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=assistant_full_reply,
                    sources=citations
                )

        except Exception as e:
            err_json = json.dumps({"type": "error", "error": str(e)})
            yield f"data: {err_json}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, agent: CompanyAIAgent = Depends(get_agent)):
    """
    Non-streaming standard chat endpoint with persistent session logging.
    """
    session_id = request.session_id
    if session_id:
        await ChatSessionStore.add_message(session_id=session_id, role="user", content=request.prompt)

    try:
        res = await agent.generate_response(
            prompt=request.prompt,
            history=request.history,
            use_memory=request.use_memory,
            temperature=request.temperature,
            model=request.model,
            attached_files=request.attached_files
        )

        if session_id:
            await ChatSessionStore.add_message(
                session_id=session_id,
                role="assistant",
                content=res["reply"],
                sources=res["sources"]
            )

        return ChatResponse(
            reply=res["reply"],
            sources=res["sources"],
            model_used=res["model_used"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
