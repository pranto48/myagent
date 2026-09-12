# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.2.0
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from mcp.store import MCPStore
from mcp.manager import MCPManager
from agent.tools import AgentTools

router = APIRouter(prefix="/api/mcp", tags=["Model Context Protocol (MCP)"])

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
