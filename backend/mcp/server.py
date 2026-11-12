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
                            "You have access to 35+ high-efficiency tools (including dedicated IT Administrator tools) and 67+ specialized domain skills:\n"
                            "- IT Infrastructure & Network Ops: ping_network_diagnostics, network_port_scan, lan_subnet_discovery_scan, network_traceroute_or_path, subnet_ip_calculator\n"
                            "- DNS, SSL/TLS & HTTP Monitoring: dns_lookup_diagnostics, ssl_tls_cert_inspector, http_endpoint_health_check\n"
                            "- Server Telemetry, Logs & Maintenance: system_info, server_process_and_ports_audit, system_logs_inspector, cron_schedule_and_maintenance_planner, it_security_utility\n"
                            "- Prompt Engineering & Workflows: enhance_prompt, list_workflows, run_workflow_now, get_workflows_status_report\n"
                            "- Project Memory Vault: save_project_memory, get_project_memory, search_project_memory, save_project_info, get_project_info, list_all_projects\n"
                            "- Autonomous Skills Hub & RAG: list_available_skills, invoke_agent_skill, query_company_memory, save_company_memory, python_runner."
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
                if not isinstance(arguments, dict):
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32602, "message": "Invalid params: 'arguments' must be a JSON object."}
                    }
                try:
                    output = await asyncio.wait_for(
                        AgentTools.dispatch_tool(tool_name, arguments),
                        timeout=45.0
                    )
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
                except asyncio.TimeoutError:
                    logger.warning(f"MCP tool '{tool_name}' timed out after 45s.")
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Tool Execution Timeout: '{tool_name}' exceeded 45s safety limit. Verify target host reachability or narrow scan scope."
                                }
                            ],
                            "isError": True
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
                                "name": "prompt_optimizer_meta",
                                "description": "Transforms any raw user prompt into an elite, multi-layered, constraint-hardened AI prompt",
                                "arguments": [
                                    {"name": "prompt", "description": "Raw prompt draft to optimize", "required": True},
                                    {"name": "mode", "description": "developer, architect, analysis, executive, or concise", "required": False}
                                ]
                            },
                            {
                                "name": "project_context_discovery",
                                "description": "Fetch project architecture blueprint, credentials, and past memories before starting tasks on a project",
                                "arguments": [
                                    {"name": "project_name", "description": "Project name (e.g. myagent, 48_otnarp, ampshop)", "required": True}
                                ]
                            },
                            {
                                "name": "network_deep_diagnostic",
                                "description": "Full ICMP ping + asynchronous TCP port scan audit of an internal or external IP",
                                "arguments": [
                                    {"name": "target", "description": "Target IP address or domain (e.g. 192.168.9.1)", "required": True}
                                ]
                            },
                            {
                                "name": "code_security_and_quality_audit",
                                "description": "Deep static security scan for leaked API secrets, SQLi, eval risks, and architectural flaws",
                                "arguments": [
                                    {"name": "code", "description": "Code snippet to inspect", "required": True},
                                    {"name": "language", "description": "Language e.g. python, javascript", "required": False}
                                ]
                            },
                            {
                                "name": "database_performance_tuning",
                                "description": "SQLite schema audit, index review, and query plan bottleneck resolution",
                                "arguments": [
                                    {"name": "db_name", "description": "Database filename e.g. chat_history.db, ops.db", "required": False}
                                ]
                            },
                            {
                                "name": "project_sprint_task_planner",
                                "description": "Decompose a feature or project goal into structured 1h/4h sprint plans",
                                "arguments": [
                                    {"name": "goal", "description": "Feature or milestone objective", "required": True},
                                    {"name": "sprint_hours", "description": "Sprint duration in hours (default 4)", "required": False}
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
                                "name": "executive_daily_briefing",
                                "description": "Aggregate system diagnostics, active projects, and git logs into an executive status report",
                                "arguments": []
                            },
                            {
                                "name": "it_infrastructure_health_audit",
                                "description": "Full IT Admin server audit: CPU/RAM/Disk, top processes, listening ports, workflow errors, and logs",
                                "arguments": []
                            },
                            {
                                "name": "ssl_and_dns_security_check",
                                "description": "Audit domain DNS (A/MX/TXT/SPF/DMARC), TLS certificate expiry, and HTTP security headers",
                                "arguments": [
                                    {"name": "domain", "description": "Target domain or hostname (e.g. itsupport.com.bd)", "required": True}
                                ]
                            },
                            {
                                "name": "lan_incident_triage",
                                "description": "Subnet calculation, LAN live host discovery, ping, and traceroute incident triage",
                                "arguments": [
                                    {"name": "target_or_subnet", "description": "Target IP or CIDR subnet (e.g. 192.168.9.0/24 or 192.168.9.2)", "required": True}
                                ]
                            }
                        ]
                    }
                }

            # 7. Get prompt template
            elif method == "prompts/get":
                p_name = params.get("name")
                p_args = params.get("arguments", {})
                
                if p_name == "prompt_optimizer_meta":
                    raw_p = p_args.get("prompt", "")
                    mode = p_args.get("mode", "developer")
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "description": f"Optimize prompt in {mode} mode",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": {
                                        "type": "text",
                                        "text": (
                                            f"Call the `enhance_prompt` tool with prompt='{raw_p}' and mode='{mode}'. "
                                            f"Also review any relevant skills via `list_available_skills` and return the finalized elite master prompt."
                                        )
                                    }
                                }
                            ]
                        }
                    }
                elif p_name == "network_deep_diagnostic":
                    tgt = p_args.get("target", "192.168.9.1")
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "description": f"Deep network ping + TCP port scan audit for {tgt}",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": {
                                        "type": "text",
                                        "text": (
                                            f"Perform a comprehensive network audit on target '{tgt}' from MyAgent Server (192.168.9.9):\n"
                                            f"1. Call `ping_network_diagnostics` on '{tgt}' (count=3).\n"
                                            f"2. Call `network_port_scan` on '{tgt}'.\n"
                                            f"Synthesize latency, packet loss, open services, and potential firewall/security risks."
                                        )
                                    }
                                }
                            ]
                        }
                    }
                elif p_name == "code_security_and_quality_audit":
                    lang = p_args.get("language", "python")
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "description": f"Code security and static quality audit ({lang})",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": {
                                        "type": "text",
                                        "text": (
                                            f"1. Run `code_quality_and_security_audit` on the provided {lang} code.\n"
                                            f"2. Run `invoke_agent_skill` for skill_name='security-ast-scanner' to check OWASP patterns.\n"
                                            f"Provide concrete remediations and hardened code fixes."
                                        )
                                    }
                                }
                            ]
                        }
                    }
                elif p_name == "database_performance_tuning":
                    db_n = p_args.get("db_name", "chat_history.db")
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "description": f"Database schema & performance audit for {db_n}",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": {
                                        "type": "text",
                                        "text": (
                                            f"Inspect `{db_n}` using `sqlite_schema_inspector` to dump tables and row counts, "
                                            f"and apply `invoke_agent_skill` with 'database-query-optimizer' to suggest index optimizations."
                                        )
                                    }
                                }
                            ]
                        }
                    }
                elif p_name == "project_sprint_task_planner":
                    goal = p_args.get("goal", "Implement new enterprise microservice")
                    hrs = p_args.get("sprint_hours", 4)
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "description": f"Sprint breakdown for: {goal}",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": {
                                        "type": "text",
                                        "text": (
                                            f"Use `generate_task_breakdown` for goal='{goal}' (sprint_hours={hrs}), "
                                            f"and check `list_all_projects` to align milestones with existing project blueprints."
                                        )
                                    }
                                }
                            ]
                        }
                    }
                elif p_name == "executive_daily_briefing":
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "description": "Executive daily technical & infrastructure briefing",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": {
                                        "type": "text",
                                        "text": (
                                            "Synthesize an executive status briefing by running:\n"
                                            "1. `system_info` for container CPU/RAM/Disk status\n"
                                            "2. `git_repo_inspector` for recent commits\n"
                                            "3. `list_all_projects` for active project health and memory metrics."
                                        )
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
                elif p_name == "it_infrastructure_health_audit":
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "description": "Full IT Infrastructure Health & Log Audit",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": {
                                        "type": "text",
                                        "text": (
                                            "Run a complete IT Administrator server health audit:\n"
                                            "1. Call `system_info` and `server_process_and_ports_audit` (top_n=12).\n"
                                            "2. Call `system_logs_inspector` (log_source='all', level='ALL', tail_lines=25).\n"
                                            "3. Call `get_workflows_status_report`.\n"
                                            "Summarize resource bottlenecks, listening sockets, errors, and corrective recommendations."
                                        )
                                    }
                                }
                            ]
                        }
                    }
                elif p_name == "ssl_and_dns_security_check":
                    dom = p_args.get("domain", "itsupport.com.bd")
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "description": f"DNS, SSL/TLS & HTTP Security Check for {dom}",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": {
                                        "type": "text",
                                        "text": (
                                            f"Perform a full domain and edge security audit for '{dom}':\n"
                                            f"1. Call `dns_lookup_diagnostics` with domain='{dom}'.\n"
                                            f"2. Call `ssl_tls_cert_inspector` with host='{dom}' and port=443.\n"
                                            f"3. Call `http_endpoint_health_check` with url='https://{dom}'.\n"
                                            f"Report certificate expiry countdown, SPF/DMARC status, and missing HTTP hardening headers."
                                        )
                                    }
                                }
                            ]
                        }
                    }
                elif p_name == "lan_incident_triage":
                    tgt = p_args.get("target_or_subnet", "192.168.9.0/24")
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "description": f"LAN Network Incident Triage for {tgt}",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": {
                                        "type": "text",
                                        "text": (
                                            f"Triage network connectivity for '{tgt}':\n"
                                            f"- If CIDR: call `subnet_ip_calculator` and `lan_subnet_discovery_scan` on '{tgt}'.\n"
                                            f"- If host/IP: call `ping_network_diagnostics`, `network_port_scan`, and `network_traceroute_or_path` on '{tgt}'.\n"
                                            f"Highlight unreachable hops, latency spikes, and open administrative ports."
                                        )
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
                    },
                    {
                        "uri": "myagent://it/server-health",
                        "name": "IT Admin Host & Port Telemetry",
                        "description": "Live top processes, listening TCP/UDP ports, NIC traffic, and recent logs snapshot",
                        "mimeType": "text/markdown"
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
                mime_type = "application/json"
                if "it/server-health" in uri:
                    from mcp.it_admin_tools import ITAdminTools
                    sys_diag = await asyncio.to_thread(AgentTools.system_info)
                    proc_diag = await ITAdminTools.server_process_and_ports_audit(top_n=10, sort_by="memory", include_connections=True)
                    res_text = f"{sys_diag}\n\n{proc_diag}"
                    mime_type = "text/markdown"
                elif "diagnostics" in uri:
                    res_text = await asyncio.to_thread(AgentTools.system_info)
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
                                "mimeType": mime_type,
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

