from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from models.schemas import ChatRequest, ChatResponse
from agent.core_agent import CompanyAIAgent

router = APIRouter(prefix="/api/chat", tags=["Chat & Agent"])

# Global agent singleton
_agent_instance = None

def get_agent() -> CompanyAIAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = CompanyAIAgent()
    return _agent_instance

@router.post("/stream")
async def stream_chat_endpoint(request: ChatRequest, agent: CompanyAIAgent = Depends(get_agent)):
    """
    Streams the AI Agent response in real-time using Server-Sent Events (SSE).
    """
    try:
        generator = agent.stream_chat(
            prompt=request.prompt,
            history=request.history,
            use_memory=request.use_memory,
            temperature=request.temperature,
            model=request.model
        )
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, agent: CompanyAIAgent = Depends(get_agent)):
    """
    Non-streaming standard chat endpoint.
    """
    try:
        res = await agent.generate_response(
            prompt=request.prompt,
            history=request.history,
            use_memory=request.use_memory,
            temperature=request.temperature,
            model=request.model
        )
        return ChatResponse(
            reply=res["reply"],
            sources=res["sources"],
            model_used=res["model_used"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
