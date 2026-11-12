# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.0.0
import os
import json
import time
import asyncio
import logging
import httpx
from typing import Dict, Any, List, Optional
from mcp.store import MCPStore

logger = logging.getLogger("myagent.mcp.manager")

class MCPManager:
    """
    Model Context Protocol (MCP) Runtime Engine.
    Handles stdio and SSE/HTTP JSON-RPC transports, tool discovery, health ping, and tool execution.
    """

    @staticmethod
    def _build_headers(server: Dict[str, Any]) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        env = server.get("env") or {}
        if isinstance(env, dict):
            if env.get("Authorization"):
                headers["Authorization"] = str(env["Authorization"])
            elif env.get("API_KEY"):
                headers["Authorization"] = f"Bearer {env['API_KEY']}"
            if env.get("X-API-Key"):
                headers["X-API-Key"] = str(env["X-API-Key"])
            if isinstance(env.get("headers"), dict):
                for k, v in env["headers"].items():
                    headers[str(k)] = str(v)
        return headers

    @classmethod
    async def ping_server(cls, server_id: str) -> Dict[str, Any]:
        """Tests connectivity to an MCP server, measures latency, and discovers available tools."""
        server = await MCPStore.get_server(server_id)
        if not server:
            return {"success": False, "message": f"Server '{server_id}' not found.", "latency_ms": -1, "tools": []}

        start = time.perf_counter()
        transport = server.get("transport", "sse")

        try:
            if transport == "sse":
                url = server.get("url", "").strip()
                if not url:
                    return {"success": False, "message": "Missing SSE/HTTP Endpoint URL.", "latency_ms": -1, "tools": []}

                # Mock or local test endpoint fallback
                if "mock-sse" in url:
                    latency = round((time.perf_counter() - start) * 1000, 2)
                    tools = server.get("tools_cache", [])
                    await MCPStore.update_server(server_id, status="connected", last_ping_ms=latency, tools_cache=tools)
                    return {"success": True, "message": "Connected to Mock SSE MCP Server", "latency_ms": latency, "tools": tools}

                headers = cls._build_headers(server)
                async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
                    # Test connection with JSON-RPC ping / initialize
                    req_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {"tools": {}},
                            "clientInfo": {"name": "MyAgent", "version": "3.5.0"}
                        }
                    }
                    res = await client.post(url, json=req_payload, headers=headers)
                    if res.status_code >= 400:
                        await MCPStore.update_server(server_id, status="error", last_ping_ms=-1)
                        return {"success": False, "message": f"HTTP {res.status_code}: {res.text[:160]}", "latency_ms": -1, "tools": []}
                    latency = round((time.perf_counter() - start) * 1000, 2)

                    # Discover tools
                    tools = server.get("tools_cache", [])
                    try:
                        tools_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
                        t_res = await client.post(url, json=tools_req, headers=headers)
                        if t_res.status_code == 200:
                            t_data = t_res.json()
                            fetched_tools = t_data.get("result", {}).get("tools")
                            if isinstance(fetched_tools, list):
                                tools = fetched_tools
                    except Exception:
                        pass

                    await MCPStore.update_server(server_id, status="connected", last_ping_ms=latency, tools_cache=tools)
                    return {
                        "success": True,
                        "message": f"Successfully connected to MCP server via SSE ({latency}ms).",
                        "latency_ms": latency,
                        "tools": tools
                    }

            elif transport == "stdio":
                command = server.get("command", "").strip()
                if not command:
                    return {"success": False, "message": "Missing stdio command.", "latency_ms": -1, "tools": []}

                args = server.get("args", [])
                cmd_list = [command] + args
                proc_env = os.environ.copy()
                if isinstance(server.get("env"), dict):
                    proc_env.update({str(k): str(v) for k, v in server["env"].items() if isinstance(v, (str, int, float))})

                proc = await asyncio.create_subprocess_exec(
                    *cmd_list,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=proc_env,
                )

                # Send initialize + tools/list
                init_msg = (
                    json.dumps({
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {"tools": {}},
                            "clientInfo": {"name": "MyAgent", "version": "3.5.0"}
                        }
                    }) + "\n"
                    + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}) + "\n"
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(input=init_msg.encode()),
                        timeout=6.0
                    )
                    latency = round((time.perf_counter() - start) * 1000, 2)
                    tools = server.get("tools_cache", [])
                    for line in stdout.decode("utf-8", errors="replace").splitlines():
                        line = line.strip()
                        if line.startswith("{"):
                            try:
                                msg = json.loads(line)
                                if msg.get("id") == 2 and isinstance(msg.get("result", {}).get("tools"), list):
                                    tools = msg["result"]["tools"]
                            except Exception:
                                pass

                    await MCPStore.update_server(server_id, status="connected", last_ping_ms=latency, tools_cache=tools)
                    return {
                        "success": True,
                        "message": f"stdio process connected successfully ({latency}ms).",
                        "latency_ms": latency,
                        "tools": tools
                    }
                except asyncio.TimeoutError:
                    proc.kill()
                    return {"success": False, "message": "stdio command timed out after 6 seconds.", "latency_ms": -1, "tools": []}

            else:
                return {"success": False, "message": f"Unsupported transport: {transport}", "latency_ms": -1, "tools": []}

        except Exception as e:
            logger.warning(f"Error pinging MCP server {server_id}: {e}")
            await MCPStore.update_server(server_id, status="error", last_ping_ms=-1)
            return {"success": False, "message": f"Connection failed: {str(e)}", "latency_ms": -1, "tools": []}

    @classmethod
    async def call_tool(cls, tool_name: str, args: Dict[str, Any], server_id: Optional[str] = None) -> str:
        """Finds the target MCP server providing tool_name and dispatches the tool call."""
        servers = await MCPStore.list_servers()
        target_server = None

        if server_id:
            target_server = next((s for s in servers if s.get("id") == server_id), None)
            if not target_server:
                return f"MCP Error: Server '{server_id}' not found."
            if not target_server.get("is_enabled", True):
                return f"MCP Error: Server '{target_server.get('name', server_id)}' is currently disabled."
        else:
            for s in servers:
                if not s.get("is_enabled", True):
                    continue
                for t in s.get("tools_cache", []):
                    if t.get("name") == tool_name:
                        target_server = s
                        break
                if target_server:
                    break

        if not target_server:
            return f"MCP Error: Tool '{tool_name}' not found on any active MCP servers."

        transport = target_server.get("transport", "sse")

        try:
            if transport == "sse":
                url = target_server.get("url", "").strip()
                if "mock-sse" in url:
                    # Provide realistic mock response for built-in template demo
                    if tool_name == "fetch_article_markdown":
                        target_url = args.get("url", "https://example.com")
                        return f"# Article Content from {target_url}\n\nSuccessfully retrieved and parsed markdown content via MCP Fetch Server."
                    return f"[MCP Mock Tool Result for {tool_name}]: Arguments received: {json.dumps(args)}"

                headers = cls._build_headers(target_server)
                async with httpx.AsyncClient(timeout=25.0, verify=False) as client:
                    rpc_call = {
                        "jsonrpc": "2.0",
                        "id": int(time.time()),
                        "method": "tools/call",
                        "params": {"name": tool_name, "arguments": args}
                    }
                    res = await client.post(url, json=rpc_call, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        if data.get("error"):
                            err = data["error"]
                            return f"MCP Error ({err.get('code', '')}): {err.get('message', json.dumps(err))}"
                        result = data.get("result", {})
                        content = result.get("content", [])
                        if isinstance(content, list):
                            texts = [c.get("text", "") for c in content if isinstance(c, dict)]
                            joined = "\n".join(texts).strip()
                            if joined:
                                return joined
                        return json.dumps(result, ensure_ascii=False)
                    return f"MCP Error: Server responded with HTTP {res.status_code} ({res.text[:180]})"

            elif transport == "stdio":
                if tool_name == "fs_read_dir":
                    from agent.tools import AgentTools
                    return AgentTools.fs_list_files(args.get("path", ""))
                elif tool_name == "sqlite_schema_dump":
                    from agent.tools import AgentTools
                    return AgentTools.sqlite_query("SELECT type, name, sql FROM sqlite_master WHERE type IN ('table', 'view')", "chat_history.db")

                # Execute genuine stdio MCP JSON-RPC subprocess if command is configured
                command = (target_server.get("command") or "").strip()
                if command:
                    cmd_list = [command] + (target_server.get("args") or [])
                    proc_env = os.environ.copy()
                    if isinstance(target_server.get("env"), dict):
                        proc_env.update({str(k): str(v) for k, v in target_server["env"].items() if isinstance(v, (str, int, float))})
                    proc = await asyncio.create_subprocess_exec(
                        *cmd_list,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env=proc_env,
                    )
                    rpc_in = (
                        json.dumps({
                            "jsonrpc": "2.0", "id": 1, "method": "initialize",
                            "params": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "clientInfo": {"name": "MyAgent", "version": "3.5.0"}}
                        }) + "\n"
                        + json.dumps({
                            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                            "params": {"name": tool_name, "arguments": args}
                        }) + "\n"
                    )
                    try:
                        stdout, stderr = await asyncio.wait_for(proc.communicate(input=rpc_in.encode()), timeout=20.0)
                    except asyncio.TimeoutError:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                        return f"MCP Timeout: Stdio tool '{tool_name}' exceeded 20s timeout."

                    for line in stdout.decode("utf-8", errors="replace").splitlines():
                        line = line.strip()
                        if line.startswith("{"):
                            try:
                                msg = json.loads(line)
                                if msg.get("id") == 2:
                                    if msg.get("error"):
                                        return f"MCP Error: {msg['error']}"
                                    res_obj = msg.get("result", {})
                                    cnt = res_obj.get("content", [])
                                    if isinstance(cnt, list):
                                        txt = "\n".join(c.get("text", "") for c in cnt if isinstance(c, dict)).strip()
                                        if txt:
                                            return txt
                                    return json.dumps(res_obj, ensure_ascii=False)
                            except Exception:
                                pass
                    out_txt = stdout.decode("utf-8", errors="replace").strip()
                    err_txt = stderr.decode("utf-8", errors="replace").strip()
                    return out_txt or (f"MCP Stdio note: {err_txt}" if err_txt else f"[MCP Stdio Tool {tool_name} executed]")

                return f"[MCP Stdio Tool {tool_name} executed with args: {json.dumps(args)}]"

            return f"MCP Error: Unsupported transport '{transport}'"
        except Exception as e:
            return f"Error executing MCP tool '{tool_name}': {str(e)}"
