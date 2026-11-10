# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.1.0
import json
import uuid
import asyncio
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from mcp.store import MCPStore
from mcp.manager import MCPManager
from mcp.server import MyAgentMCPServer
from agent.tools import AgentTools

router = APIRouter(prefix="/api/mcp", tags=["Model Context Protocol (MCP)"])

class ToggleServerRequest(BaseModel):
    is_enabled: bool

class AddMCPServerRequest(BaseModel):
    name: str
    transport: str = "sse"  # 'sse' or 'stdio'
    command: Optional[str] = None
    args: Optional[List[str]] = []
    url: Optional[str] = None
    env: Optional[Dict[str, str]] = {}
    is_enabled: bool = True

class UpdateMCPServerRequest(BaseModel):
    name: Optional[str] = None
    transport: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    is_enabled: Optional[bool] = None

class ExecuteToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}

@router.get("/servers")
async def list_mcp_servers():
    """Returns all registered MCP servers with connection status and tools count."""
    return await MCPStore.list_servers()

@router.post("/servers")
async def add_mcp_server(req: AddMCPServerRequest):
    """Registers a new external or local MCP server."""
    server = await MCPStore.add_server(
        name=req.name,
        transport=req.transport,
        command=req.command,
        args=req.args,
        url=req.url,
        env=req.env,
        is_enabled=req.is_enabled
    )
    # Trigger initial ping test asynchronously
    try:
        await MCPManager.ping_server(server["id"])
    except Exception:
        pass
    return await MCPStore.get_server(server["id"])

@router.get("/servers/{server_id}")
async def get_mcp_server(server_id: str):
    """Fetches details and discovered tools of a specific MCP server."""
    server = await MCPStore.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP Server not found.")
    return server

@router.put("/servers/{server_id}")
async def update_mcp_server(server_id: str, req: UpdateMCPServerRequest):
    """Updates an MCP server configuration or toggles enable/disable status."""
    updated = await MCPStore.update_server(
        server_id=server_id,
        name=req.name,
        transport=req.transport,
        command=req.command,
        args=req.args,
        url=req.url,
        env=req.env,
        is_enabled=req.is_enabled
    )
    if not updated:
        raise HTTPException(status_code=404, detail="MCP Server not found.")
    return updated

@router.delete("/servers/{server_id}")
async def delete_mcp_server(server_id: str):
    """Removes an MCP server registration."""
    success = await MCPStore.delete_server(server_id)
    if not success:
        raise HTTPException(status_code=404, detail="MCP Server not found.")
    return {"success": True, "message": f"MCP server '{server_id}' deleted."}

@router.post("/servers/{server_id}/ping")
async def ping_mcp_server(server_id: str):
    """Tests connectivity to the MCP server and discovers tool schemas."""
    return await MCPManager.ping_server(server_id)

@router.get("/tools")
async def get_all_tools():
    """Returns combined registry of built-in open source tools and active MCP tools."""
    builtin = AgentTools.get_openai_tools_schema()
    mcp_servers = await MCPStore.list_servers()
    all_tools = []

    for b in builtin:
        fn = b["function"]
        all_tools.append({
            "name": fn["name"],
            "description": fn["description"],
            "source": "builtin",
            "server_id": "local",
            "parameters": fn.get("parameters", {})
        })

    for s in mcp_servers:
        if not s.get("is_enabled", True):
            continue
        for t in s.get("tools_cache", []):
            all_tools.append({
                "name": t.get("name"),
                "description": t.get("description", "MCP Tool"),
                "source": "mcp",
                "server_id": s["id"],
                "server_name": s["name"],
                "parameters": t.get("inputSchema", {})
            })

    return {
        "total_tools": len(all_tools),
        "builtin_count": len(builtin),
        "mcp_count": len(all_tools) - len(builtin),
        "tools": all_tools
    }

@router.post("/tools/execute")
async def execute_tool(req: ExecuteToolRequest):
    """Manually tests and executes any built-in or MCP tool directly."""
    result = await AgentTools.dispatch_tool(req.tool_name, req.arguments)
    return {
        "tool_name": req.tool_name,
        "arguments": req.arguments,
        "output": result
    }

@router.post("/mock-sse")
async def mock_sse_endpoint(payload: Dict[str, Any]):
    """Mock MCP SSE/HTTP JSON-RPC handler for built-in template demonstrations."""
    method = payload.get("method", "")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": payload.get("id", 1),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "Mock SSE MCP Server", "version": "2.1.0"}
            }
        }
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": payload.get("id", 2),
            "result": {
                "tools": [
                    {
                        "name": "fetch_article_markdown",
                        "description": "Fetch remote web article and convert to clean markdown format",
                        "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}
                    }
                ]
            }
        }
    elif method == "tools/call":
        params = payload.get("params", {})
        tool_name = params.get("name", "")
        args = params.get("arguments", {})
        return {
            "jsonrpc": "2.0",
            "id": payload.get("id", 3),
            "result": {
                "content": [{"type": "text", "text": f"[MCP Result for {tool_name}]: {json.dumps(args)}"}]
            }
        }
    return {"jsonrpc": "2.0", "id": payload.get("id", 0), "result": "ok"}

# ==============================================================================
# MyAgent Built-in MCP Server Endpoints (Expose Docker App as MCP Server)
# ==============================================================================

@router.get("/server/status")
async def get_myagent_mcp_server_status(request: Request):
    """
    Returns live status, exposed tools list, and ready-to-copy client
    configurations (Claude Desktop, Cursor, Antigravity, Cline) for MyAgent MCP Server.
    """
    host = request.headers.get("host", "192.168.9.9:3399")
    return await MyAgentMCPServer.get_status(host=host)

@router.post("/server/toggle")
async def toggle_myagent_mcp_server(req: ToggleServerRequest):
    """Enables or disables the built-in MCP server feature."""
    new_state = await MyAgentMCPServer.set_enabled(req.is_enabled)
    return {
        "success": True,
        "is_enabled": new_state,
        "message": f"MyAgent MCP Server is now {'enabled' if new_state else 'disabled'}."
    }

@router.post("/server/rpc")
async def myagent_mcp_rpc(payload: Any, request: Request):
    """
    Stateless HTTP JSON-RPC 2.0 handler for MyAgent MCP Server.
    Supports single JSON-RPC calls or batches for tools/list, tools/call, prompts, resources.
    """
    if not MyAgentMCPServer.is_enabled():
        raise HTTPException(status_code=503, detail="MyAgent MCP Server is currently disabled.")
    host = request.headers.get("host", "192.168.9.9:3399")
    return await MyAgentMCPServer.handle_rpc(payload, host=host)

@router.get("/server/sse")
async def myagent_mcp_sse(request: Request):
    """
    Server-Sent Events (SSE) streaming endpoint for MCP clients
    (Claude Desktop, Cursor IDE, Antigravity, Cline).
    """
    if not MyAgentMCPServer.is_enabled():
        raise HTTPException(status_code=503, detail="MyAgent MCP Server is currently disabled.")

    session_id = uuid.uuid4().hex
    queue = MyAgentMCPServer.register_session(session_id)
    host = request.headers.get("host", "192.168.9.9:3399")
    messages_url = f"/api/mcp/server/messages?sessionId={session_id}"

    async def event_generator():
        try:
            # Step 1: Advertise message endpoint according to standard MCP SSE specification
            yield f"event: endpoint\ndata: {messages_url}\n\n"

            # Step 2: Stream outgoing message queue with keepalive
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: message\ndata: {json.dumps(msg, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            MyAgentMCPServer.unregister_session(session_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/server/messages")
async def myagent_mcp_messages(
    payload: Any,
    request: Request,
    sessionId: Optional[str] = None,
    session_id: Optional[str] = None
):
    """
    Receives JSON-RPC 2.0 messages from active SSE client sessions.
    Dispatches to MyAgent tool suite and streams responses back to the SSE session.
    """
    if not MyAgentMCPServer.is_enabled():
        raise HTTPException(status_code=503, detail="MyAgent MCP Server is currently disabled.")

    sid = sessionId or session_id
    host = request.headers.get("host", "192.168.9.9:3399")
    response = await MyAgentMCPServer.handle_rpc(payload, host=host)

    if sid and MyAgentMCPServer.has_session(sid):
        await MyAgentMCPServer.push_to_session(sid, response)

    return response
