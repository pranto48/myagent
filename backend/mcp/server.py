# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.1.0
import os
import json
import time
import uuid
import asyncio
import logging
from typing import Dict, Any, List, Optional
from config import settings
from agent.tools import AgentTools

logger = logging.getLogger("myagent.mcp.server")

class MyAgentMCPServer:
    """
    MyAgent Built-in Model Context Protocol (MCP) Server.
    
    Exposes MyAgent's full autonomous tool suite, network ping diagnostics,
    company hybrid vector memory (RAG), and data analytics to external AI clients
    (Claude Desktop, Cursor IDE, Antigravity IDE, Cline, and custom agents)
    over standard MCP Protocol (Version: 2024-11-05).
    """

    _is_enabled: bool = True
    _server_name: str = "myagent-docker-mcp"
    _server_title: str = "MyAgent Docker MCP Server"
    _version: str = "3.1.0"
    _protocol_version: str = "2024-11-05"
    
    # Active SSE sessions: {session_id: asyncio.Queue}
    _sessions: Dict[str, asyncio.Queue] = {}

    @classmethod
    def is_enabled(cls) -> bool:
        return cls._is_enabled

    @classmethod
    async def set_enabled(cls, enabled: bool) -> bool:
        cls._is_enabled = bool(enabled)
        logger.info(f"MyAgent MCP Server state toggled: enabled={cls._is_enabled}")
        return cls._is_enabled

    @classmethod
    def register_session(cls, session_id: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        cls._sessions[session_id] = queue
        logger.info(f"Registered new MCP SSE session: {session_id} (Total: {len(cls._sessions)})")
        return queue

    @classmethod
    def unregister_session(cls, session_id: str):
        if session_id in cls._sessions:
            del cls._sessions[session_id]
            logger.info(f"Unregistered MCP SSE session: {session_id} (Remaining: {len(cls._sessions)})")

    @classmethod
    def has_session(cls, session_id: str) -> bool:
        return session_id in cls._sessions

    @classmethod
    async def push_to_session(cls, session_id: str, message: Dict[str, Any]):
        queue = cls._sessions.get(session_id)
        if queue:
            await queue.put(message)

    @classmethod
    async def get_exposed_tools(cls) -> List[Dict[str, Any]]:
        """Returns all MyAgent tools formatted according to the standard MCP tool schema."""
        openai_tools = await AgentTools.get_all_tools_schema()
        mcp_tools = []
        
        for item in openai_tools:
            fn = item.get("function", {})
            name = fn.get("name")
            if not name:
                continue
            
            mcp_tools.append({
                "name": name,
                "description": fn.get("description", "MyAgent Autonomous Tool"),
                "inputSchema": fn.get("parameters", {
                    "type": "object",
                    "properties": {}
                })
            })
            
        return mcp_tools

    @classmethod
    async def get_status(cls, host: str = "192.168.9.9:3399") -> Dict[str, Any]:
        """Returns live status, exposed tools list, and 1-click configs for external clients."""
        tools = await cls.get_exposed_tools()
        
        # Ensure external port 3399 is present if host lacks port
        clean_host = host
        if ":" not in clean_host and settings.WEB_PORT not in (80, 443):
            clean_host = f"{clean_host}:{settings.WEB_PORT}"

        sse_url = f"http://{clean_host}/api/mcp/server/sse"
        rpc_url = f"http://{clean_host}/api/mcp/server/rpc"
        messages_url = f"http://{clean_host}/api/mcp/server/messages"

        # Ready-to-copy client configurations
        configs = {
            "claude_desktop": {
                "mcpServers": {
                    "myagent_docker": {
                        "url": sse_url
                    }
                }
            },
            "cursor": {
                "mcpServers": {
                    "myagent-docker": {
                        "url": sse_url
                    }
                }
            },
            "antigravity": {
                "mcpServers": {
                    "myagent_docker": {
                        "url": sse_url
                    }
                }
            },
            "cline": {
                "mcpServers": {
                    "myagent_docker": {
                        "url": sse_url
                    }
                }
            },
            "stdio_bridge_config": {
                "mcpServers": {
                    "myagent_bridge": {
                        "command": "python",
                        "args": ["-c", f"import sys, urllib.request, json; [print(urllib.request.urlopen(urllib.request.Request('{rpc_url}', data=l.encode('utf-8'), headers={{'Content-Type':'application/json'}})).read().decode('utf-8'), flush=True) for l in sys.stdin if l.strip()]"]
                    }
                }
            }
        }

        return {
            "is_enabled": cls._is_enabled,
            "server_name": cls._server_name,
            "server_title": cls._server_title,
            "version": cls._version,
            "protocol_version": cls._protocol_version,
            "server_host": host,
            "endpoints": {
                "sse": sse_url,
                "rpc": rpc_url,
                "messages": messages_url
            },
            "tools_count": len(tools),
            "tools": tools,
            "active_sessions_count": len(cls._sessions),
            "configs": configs
        }

    @classmethod
    async def handle_rpc(cls, payload: Any, host: str = "192.168.9.9:3399") -> Any:
        """Processes JSON-RPC 2.0 requests (supports single request or batch)."""
        if isinstance(payload, list):
            # Batch execution
            return [await cls._process_single_rpc(p, host) for p in payload]
        return await cls._process_single_rpc(payload, host)

    @classmethod
    async def _process_single_rpc(cls, req: Dict[str, Any], host: str) -> Dict[str, Any]:
        """Dispatches a single JSON-RPC 2.0 call."""
        if not isinstance(req, dict):
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32600, "message": "Invalid Request: expected JSON object."}
            }

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params") or {}

        if not method:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32600, "message": "Missing 'method' field in JSON-RPC request."}
            }

        try:
            # 1. MCP initialize handshake
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": cls._protocol_version,
                        "capabilities": {
                            "tools": {"listChanged": False},
                            "prompts": {"listChanged": False},
                            "resources": {"subscribe": False, "listChanged": False},
                            "logging": {}
                        },
                        "serverInfo": {
                            "name": cls._server_name,
                            "title": cls._server_title,
                            "version": cls._version
                        },
                        "instructions": (
                            "Connected to MyAgent Docker MCP Server on 192.168.9.9. "
                            "You have access to Per-Project Memory Vault (save_project_memory, get_project_memory, search_project_memory) "
                            "and Project Architecture Blueprints (save_project_info, get_project_info, list_all_projects), "
                            "corporate network diagnostic ping (ping_network_diagnostics), "
                            "hybrid memory RAG retrieval and storage (query_company_memory, save_company_memory), "
                            "data analytics (analyze_big_data, smart_data_summarizer), Python calculations "
                            "(python_runner), document readers (PDF, Word, Excel, OCR), and autonomous agents."
                        )
                    }
                }

            # 2. Notification acknowledged
            elif method in ("notifications/initialized", "initialized"):
                if req_id is not None:
                    return {"jsonrpc": "2.0", "id": req_id, "result": {}}
                return {}

            # 3. Protocol ping
            elif method == "ping":
                return {"jsonrpc": "2.0", "id": req_id, "result": {}}

            # 4. List available tools
            elif method == "tools/list":
                tools = await cls.get_exposed_tools()
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": tools
                    }
                }

            # 5. Execute tool call
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if not tool_name:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32602, "message": "Missing tool 'name' in tools/call parameters."}
                    }

                logger.info(f"Executing MyAgent MCP tool call: {tool_name} with args: {arguments}")
                try:
                    output = await AgentTools.dispatch_tool(tool_name, arguments)
                    output_text = str(output) if output is not None else "Tool executed successfully (empty output)."
                    
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": output_text
                                }
                            ],
                            "isError": False
                        }
                    }
                except Exception as ex:
                    logger.error(f"Error executing MCP tool {tool_name}: {ex}")
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Tool Execution Error: {str(ex)}"
                                }
                            ],
                            "isError": True
                        }
                    }

            # 6. List prompts
            elif method == "prompts/list":
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "prompts": [
                            {
                                "name": "network_ping_audit",
                                "description": "Sub-agent workflow to ping an internal or external IP and test connectivity",
                                "arguments": [
                                    {"name": "target", "description": "Target IP address or domain (e.g. 192.168.9.1)", "required": True}
                                ]
                            },
                            {
                                "name": "company_rag_search",
                                "description": "Search company hybrid vector memory and synthesize an accurate answer with references",
                                "arguments": [
                                    {"name": "query", "description": "Question or topic regarding company knowledge", "required": True}
                                ]
                            },
                            {
                                "name": "data_file_profiler",
                                "description": "Perform deep automated EDA and statistical profiling on a data file",
                                "arguments": [
                                    {"name": "filepath", "description": "Data file path (e.g. sales.csv)", "required": True}
                                ]
                            },
                            {
                                "name": "project_context_discovery",
                                "description": "Fetch project architecture blueprint, credentials, and past memories before starting tasks on a project",
                                "arguments": [
                                    {"name": "project_name", "description": "Project name (e.g. myagent, 48_otnarp, ampshop)", "required": True}
                                ]
                            }
                        ]
                    }
                }

            # 7. Get prompt template
            elif method == "prompts/get":
                p_name = params.get("name")
                p_args = params.get("arguments", {})
                
                if p_name == "network_ping_audit":
                    tgt = p_args.get("target", "192.168.9.1")
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "description": f"Network ping audit for {tgt}",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": {
                                        "type": "text",
                                        "text": f"Please use ping_network_diagnostics tool to check connectivity and latency to target '{tgt}' from MyAgent server (192.168.9.9) and provide a health report."
                                    }
                                }
                            ]
                        }
                    }
                elif p_name == "company_rag_search":
                    qry = p_args.get("query", "General company policies")
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "description": f"Company memory search for: {qry}",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": {
                                        "type": "text",
                                        "text": f"Please search the company memory using query_company_memory for '{qry}' and answer accurately."
                                    }
                                }
                            ]
                        }
                    }
                elif p_name == "project_context_discovery":
                    prj = p_args.get("project_name", "myagent")
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "description": f"Context discovery for project {prj}",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": {
                                        "type": "text",
                                        "text": f"Call get_project_info for '{prj}' and search_project_memory for '{prj}' to inspect all architecture details, credentials, and past checkpoints before writing code."
                                    }
                                }
                            ]
                        }
                    }
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "description": f"Prompt {p_name}",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": {"type": "text", "text": f"Execute workflow for {p_name}."}
                                }
                            ]
                        }
                    }

            # 8. List resources
            elif method == "resources/list":
                resources = [
                    {
                        "uri": "myagent://system/diagnostics",
                        "name": "Docker System Diagnostics",
                        "description": "Real-time CPU, RAM, disk and container health metrics",
                        "mimeType": "application/json"
                    },
                    {
                        "uri": "myagent://company/memory/stats",
                        "name": "Company Hybrid Memory Stats",
                        "description": "Summary of indexed document chunks and vector store status",
                        "mimeType": "application/json"
                    }
                ]
                try:
                    from memory.project_store import ProjectMemoryStore
                    projs = await ProjectMemoryStore.list_projects()
                    for p in projs:
                        p_name = p["name"]
                        resources.append({
                            "uri": f"project://{p_name}/info",
                            "name": f"Project Info: {p.get('display_name') or p_name}",
                            "description": p.get("description") or f"Architecture & tech stack for {p_name}",
                            "mimeType": "application/json"
                        })
                        resources.append({
                            "uri": f"project://{p_name}/memories",
                            "name": f"Project Memory Vault: {p_name} ({p.get('memories_count', 0)} records)",
                            "description": f"Stored memories, credentials, and architecture notes for {p_name}",
                            "mimeType": "application/json"
                        })
                except Exception as ex:
                    logger.warning(f"Failed loading project resources: {ex}")

                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "resources": resources
                    }
                }

            # 9. Read resource
            elif method == "resources/read":
                uri = params.get("uri", "")
                res_text = "{}"
                if "diagnostics" in uri:
                    res_text = AgentTools.system_info()
                elif "company/memory" in uri:
                    from memory.vector_store import VectorStore
                    res_text = json.dumps(VectorStore().get_stats(), indent=2)
                elif uri.startswith("project://"):
                    from memory.project_store import ProjectMemoryStore
                    parts = uri.replace("project://", "").split("/")
                    p_name = parts[0] if len(parts) > 0 else "myagent"
                    res_type = parts[1] if len(parts) > 1 else "info"
                    if res_type == "memories":
                        mems = await ProjectMemoryStore.search_memories(project_name=p_name, limit=100)
                        res_text = json.dumps(mems, indent=2, ensure_ascii=False)
                    else:
                        info = await ProjectMemoryStore.get_project_info(p_name)
                        res_text = json.dumps(info or {}, indent=2, ensure_ascii=False)
                
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": "application/json",
                                "text": res_text
                            }
                        ]
                    }
                }

            # Unknown method
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method '{method}' is not implemented by MyAgent MCP Server."
                    }
                }

        except Exception as e:
            logger.error(f"Internal JSON-RPC handling error for method '{method}': {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal MCP server error: {str(e)}"
                }
            }

