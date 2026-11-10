#!/usr/bin/env python3
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.1.0
"""
MyAgent Stdio-to-HTTP MCP Bridge.
Allows local MCP clients (Claude Desktop, Antigravity, Cursor, Cline) to connect
via stdio commands directly to the MyAgent Docker MCP Server on 192.168.9.9:3399.
"""

import os
import sys
import json
import urllib.request
import urllib.error

DEFAULT_URL = os.environ.get("MYAGENT_MCP_URL", "http://192.168.9.9:3399/api/mcp/server/rpc")

def main():
    target_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        
        line_str = line.strip()
        if not line_str:
            continue

        try:
            req_data = line_str.encode("utf-8")
            req = urllib.request.Request(
                target_url,
                data=req_data,
                headers={"Content-Type": "application/json", "User-Agent": "MyAgent-MCP-Bridge/3.1.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_data = resp.read().decode("utf-8")
                sys.stdout.write(resp_data + "\n")
                sys.stdout.flush()
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else str(e)
            sys.stdout.write(json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32000, "message": f"HTTP Error {e.code}: {err_body}"}
            }) + "\n")
            sys.stdout.flush()
        except Exception as ex:
            sys.stdout.write(json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32000, "message": f"Bridge error: {str(ex)}"}
            }) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()

