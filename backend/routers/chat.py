# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.2.0
import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from models.schemas import ChatRequest, ChatResponse
from agent.core_agent import CompanyAIAgent
from memory.chat_session_store import ChatSessionStore
from routers.auth import get_optional_current_user

router = APIRouter(prefix="/api/chat", tags=["Chat & Agent"])

_agent_instance = None

def get_agent() -> CompanyAIAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = CompanyAIAgent()
    return _agent_instance

@router.post("/stream")
async def stream_chat_endpoint(
    request: ChatRequest,
    agent: CompanyAIAgent = Depends(get_agent),
    current_user: dict = Depends(get_optional_current_user)
):
    """
    Streams the AI Agent response in real-time using Server-Sent Events (SSE)
    enforcing prompt firewall, DLP sanitization, and Document-Level Security (DLS).
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
                user_role=user_role
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
            model=request.model
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
