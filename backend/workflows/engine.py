# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 3.3.0
# n8n-Style DAG Workflow Execution Engine & Autonomous Node Runners
# ==============================================================================

import os
import re
import json
import uuid
import time
import sqlite3
import asyncio
import logging
import traceback
from collections import defaultdict, deque
from datetime import datetime
from typing import Dict, Any, List, Optional, Set

import httpx

try:
    from config import settings
except ImportError:
    class _FallbackSettings:
        DATA_DIR = os.environ.get("DATA_DIR", "./data")
        LLM_MODEL = os.environ.get("LLM_MODEL", "gemini-3.7-flash")
        AGENT_NAME = os.environ.get("AGENT_NAME", "Company Data Intelligence Agent")
    settings = _FallbackSettings()

from workflows.store import WorkflowStore, compute_next_run, _get_tzinfo

logger = logging.getLogger("myagent.workflows.engine")


def _get_reports_db_dir() -> str:
    data_dir = getattr(settings, "DATA_DIR", "./data")
    if os.name == "nt" or not os.path.exists(data_dir):
        data_dir = os.path.abspath("./data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def _resolve_template_value(value: Any, ctx: Dict[str, Any]) -> Any:
    """Recursively interpolates {{trigger.date}}, {{prev.output}}, {{nodes.id.output}}, {{workflow.name}}."""
    if isinstance(value, dict):
        return {k: _resolve_template_value(v, ctx) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_template_value(v, ctx) for v in value]
    if not isinstance(value, str) or "{{" not in value:
        return value

    def _lookup(expr: str) -> str:
        path = expr.strip()
        parts = path.split(".")
        cur: Any = ctx
        for p in parts:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                return ""
        if cur is None:
            return ""
        if isinstance(cur, (dict, list)):
            return json.dumps(cur, ensure_ascii=False, indent=2)
        return str(cur)

    return re.sub(r"\{\{\s*([a-zA-Z0-9_\.\-]+)\s*\}\}", lambda m: _lookup(m.group(1)), value)


def _evaluate_condition(target_val: str, operator: str, expected_val: str) -> bool:
    op = (operator or "contains").strip().lower()
    src = "" if target_val is None else str(target_val)
    exp = "" if expected_val is None else str(expected_val)

    if op == "contains":
        return exp.lower() in src.lower()
    if op == "not_contains":
        return exp.lower() not in src.lower()
    if op == "equals":
        return src.strip().lower() == exp.strip().lower()
    if op == "not_equals":
        return src.strip().lower() != exp.strip().lower()
    if op in ("regex", "regex_match"):
        try:
            return bool(re.search(exp, src, flags=re.IGNORECASE | re.MULTILINE))
        except Exception:
            return False
    if op == "not_empty":
        return bool(src.strip())
    if op == "empty":
        return not bool(src.strip())
    if op in ("greater_than", "less_than"):
        try:
            num_src = float(re.search(r"-?\d+(?:\.\d+)?", src).group(0)) if re.search(r"-?\d+(?:\.\d+)?", src) else 0.0
            num_exp = float(exp)
            return num_src > num_exp if op == "greater_than" else num_src < num_exp
        except Exception:
            return False
    return False


class WorkflowEngine:
    """
    DAG-based Visual Workflow Engine inspired by n8n:
      - Topological scheduling across trigger -> action/agent -> IF/Else -> output pipelines
      - Supports conditional branching (`true` / `false` edge labels) & branch skipping
      - Real autonomous tool calling AI agents, subagents, tools, HTTP webhooks, reports & memories
    """

    def __init__(self):
        self._active_runs: Set[str] = set()

    def is_running(self, workflow_id: str) -> bool:
        return workflow_id in self._active_runs

    async def execute_workflow(
        self,
        workflow_id: str,
        trigger_source: str = "manual",
        trigger_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Executes an entire workflow DAG end-to-end and logs full step trace into ops_workflow_runs."""
        wf = await WorkflowStore.get_workflow(workflow_id)
        if not wf:
            raise ValueError(f"Workflow '{workflow_id}' not found.")

        if workflow_id in self._active_runs:
            return {
                "success": False,
                "workflow_id": workflow_id,
                "status": "ALREADY_RUNNING",
                "message": "Workflow is already executing."
            }

        self._active_runs.add(workflow_id)
        run_id = f"wfrun_{uuid.uuid4().hex[:10]}"
        t0 = time.time()

        tz = _get_tzinfo(wf.get("timezone", "Asia/Dhaka"))
        now_tz = datetime.now(tz)
        started_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Mark RUNNING in DB
        try:
            db = await WorkflowStore.get_db()
            try:
                await db.execute("UPDATE ops_workflows SET last_status = 'RUNNING' WHERE id = ?", (workflow_id,))
                await db.execute("""
                    INSERT INTO ops_workflow_runs (
                        id, workflow_id, workflow_name, trigger_source, status, started_at, node_results_json
                    ) VALUES (?, ?, ?, ?, 'RUNNING', ?, '[]')
                """, (run_id, workflow_id, wf["name"], trigger_source, started_str))
                await db.commit()
            finally:
                await db.close()
        except Exception as db_err:
            logger.warning(f"Failed initial workflow run insert: {db_err}")

        node_results: List[Dict[str, Any]] = []
        final_output = ""
        error_message = ""
        overall_status = "SUCCESS"

        try:
            nodes: List[Dict[str, Any]] = wf.get("nodes") or []
            edges: List[Dict[str, Any]] = wf.get("edges") or []

            ctx: Dict[str, Any] = {
                "workflow": {"id": workflow_id, "name": wf["name"]},
                "trigger": {
                    "source": trigger_source,
                    "date": now_tz.strftime("%Y-%m-%d"),
                    "time": now_tz.strftime("%H:%M:%S"),
                    "datetime": now_tz.strftime("%Y-%m-%d %H:%M:%S"),
                    "weekday": now_tz.strftime("%A"),
                    "timezone": wf.get("timezone", "Asia/Dhaka"),
                    "payload": trigger_payload or {}
                },
                "nodes": {},
                "prev": {"output": "", "status": "IDLE", "node_id": ""}
            }

            if not nodes:
                overall_status = "FAILED"
                error_message = "Workflow has no nodes defined."
            else:
                node_map = {n["id"]: n for n in nodes if n.get("id")}
                outgoing: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
                incoming: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

                for e in edges:
                    src = e.get("source")
                    tgt = e.get("target")
                    if src in node_map and tgt in node_map and src != tgt:
                        outgoing[src].append(e)
                        incoming[tgt].append(e)

                # Identify root / trigger nodes
                roots = [
                    n["id"] for n in nodes
                    if n.get("id") and (n.get("type", "").startswith("trigger_") or len(incoming[n["id"]]) == 0)
                ]
                if not roots and nodes[0].get("id"):
                    roots = [nodes[0]["id"]]

                # BFS to collect reachable nodes from roots
                reachable: Set[str] = set()
                q_bfs = deque(roots)
                while q_bfs:
                    curr = q_bfs.popleft()
                    if curr in reachable:
                        continue
                    reachable.add(curr)
                    for e in outgoing[curr]:
                        if e["target"] not in reachable:
                            q_bfs.append(e["target"])

                # Kahn topological sort on reachable nodes
                in_deg = {nid: 0 for nid in reachable}
                for nid in reachable:
                    for e in incoming[nid]:
                        if e["source"] in reachable:
                            in_deg[nid] += 1

                ready = deque(
                    sorted([nid for nid, deg in in_deg.items() if deg == 0], key=lambda x: node_map[x].get("x", 0))
                )
                topo_order: List[str] = []
                while ready:
                    curr = ready.popleft()
                    topo_order.append(curr)
                    for e in outgoing[curr]:
                        tgt = e["target"]
                        if tgt in in_deg:
                            in_deg[tgt] -= 1
                            if in_deg[tgt] == 0:
                                ready.append(tgt)

                # Fallback if cycle left some reachable nodes unvisited
                for nid in sorted(reachable, key=lambda x: node_map[x].get("x", 0)):
                    if nid not in topo_order:
                        topo_order.append(nid)

                active_edges: Set[str] = set()
                executed_outputs_ordered: List[str] = []
                failed_count = 0
                succeeded_count = 0

                for nid in topo_order:
                    node = node_map[nid]
                    ntype = node.get("type", "")
                    is_root = nid in roots and len(incoming[nid]) == 0

                    # Check whether at least one active edge feeds into this node
                    inc_edges_reachable = [e for e in incoming[nid] if e["source"] in reachable]
                    active_inc_edges = [
                        e for e in inc_edges_reachable
                        if f"{e['source']}->{e['target']}:{e.get('condition', '')}" in active_edges
                    ]

                    if not is_root and inc_edges_reachable and not active_inc_edges:
                        # Untaken branch -> SKIPPED
                        skip_entry = {
                            "node_id": nid,
                            "type": ntype,
                            "title": node.get("title", ntype),
                            "status": "SKIPPED",
                            "duration_ms": 0,
                            "output": "Skipped (upstream condition branch not active).",
                            "summary": "Branch not taken",
                            "data": {}
                        }
                        ctx["nodes"][nid] = skip_entry
                        node_results.append(skip_entry)
                        continue

                    # Resolve prev context from latest active incoming node
                    if active_inc_edges:
                        last_src = active_inc_edges[-1]["source"]
                        if last_src in ctx["nodes"]:
                            src_entry = ctx["nodes"][last_src]
                            ctx["prev"] = {
                                "node_id": last_src,
                                "output": src_entry.get("output", ""),
                                "status": src_entry.get("status", "SUCCESS"),
                                "data": src_entry.get("data", {})
                            }

                    # Execute this node
                    n_res = await self.execute_single_node(node, ctx)
                    ctx["nodes"][nid] = n_res
                    node_results.append(n_res)

                    if n_res["status"] == "FAILED":
                        failed_count += 1
                    else:
                        succeeded_count += 1
                        if n_res.get("output") and not ntype.startswith("trigger_"):
                            executed_outputs_ordered.append(n_res["output"])
                            final_output = n_res["output"]

                    # Activate outgoing edges
                    if ntype == "condition":
                        matched = bool(n_res.get("data", {}).get("matched", False))
                        for e in outgoing[nid]:
                            cond = (e.get("condition") or "").strip().lower()
                            if (
                                cond in ("", "always")
                                or (cond in ("true", "yes", "1", "match") and matched)
                                or (cond in ("false", "no", "0", "else") and not matched)
                            ):
                                active_edges.add(f"{e['source']}->{e['target']}:{e.get('condition', '')}")
                    else:
                        for e in outgoing[nid]:
                            active_edges.add(f"{e['source']}->{e['target']}:{e.get('condition', '')}")

                non_trigger_success = sum(
                    1 for r in node_results
                    if not r.get("type", "").startswith("trigger_") and r.get("status") == "SUCCESS"
                )
                non_trigger_fail = sum(
                    1 for r in node_results
                    if not r.get("type", "").startswith("trigger_") and r.get("status") == "FAILED"
                )
                if non_trigger_fail > 0 and non_trigger_success == 0:
                    overall_status = "FAILED"
                elif non_trigger_fail > 0:
                    overall_status = "PARTIAL"
                else:
                    overall_status = "SUCCESS"

                if not final_output and executed_outputs_ordered:
                    final_output = executed_outputs_ordered[-1]
                elif not final_output and node_results:
                    final_output = node_results[-1].get("output", "")

        except Exception as exec_err:
            overall_status = "FAILED"
            error_message = f"{str(exec_err)}\n{traceback.format_exc()[:500]}"
            logger.error(f"Workflow '{workflow_id}' execution error: {exec_err}")
        finally:
            self._active_runs.discard(workflow_id)

        duration_ms = int((time.time() - t0) * 1000)
        finished_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Recalculate next_run if workflow is enabled and scheduled
        next_str, next_ts = wf.get("next_run"), wf.get("next_run_ts")
        if wf.get("is_enabled") and wf.get("trigger_type") not in ("manual", "webhook"):
            calc_str, calc_ts, _, _ = compute_next_run(
                wf.get("schedule_expr"), wf.get("timezone", "Asia/Dhaka"), wf.get("trigger_type", "daily")
            )
            if calc_ts:
                next_str, next_ts = calc_str, calc_ts

        # Persist run completion and stats
        try:
            db = await WorkflowStore.get_db()
            try:
                await db.execute("""
                    UPDATE ops_workflow_runs
                    SET status = ?, finished_at = ?, duration_ms = ?,
                        node_results_json = ?, final_output = ?, error_message = ?
                    WHERE id = ?
                """, (
                    overall_status,
                    finished_str,
                    duration_ms,
                    json.dumps(node_results, ensure_ascii=False),
                    final_output[:20000] if final_output else "",
                    error_message,
                    run_id
                ))

                inc_success = 1 if overall_status in ("SUCCESS", "PARTIAL") else 0
                await db.execute("""
                    UPDATE ops_workflows
                    SET last_run = ?, next_run = ?, next_run_ts = ?,
                        last_status = ?, run_count = run_count + 1,
                        success_count = success_count + ?
                    WHERE id = ?
                """, (finished_str, next_str, next_ts, overall_status, inc_success, workflow_id))

                # Also write audit entry in ops_logs
                await db.execute("""
                    INSERT INTO ops_logs (id, timestamp, level, module, message, details)
                    VALUES (?, ?, ?, 'WorkflowEngine', ?, ?)
                """, (
                    str(uuid.uuid4()),
                    finished_str,
                    "SUCCESS" if overall_status == "SUCCESS" else ("WARN" if overall_status == "PARTIAL" else "ERROR"),
                    f"Workflow '{wf['name']}' finished ({overall_status}) in {duration_ms}ms via {trigger_source}.",
                    json.dumps({
                        "workflow_id": workflow_id,
                        "run_id": run_id,
                        "steps": len(node_results),
                        "duration_ms": duration_ms
                    }, ensure_ascii=False)
                ))
                await db.commit()
            finally:
                await db.close()
        except Exception as save_err:
            logger.error(f"Error persisting workflow run '{run_id}': {save_err}")

        return {
            "success": overall_status in ("SUCCESS", "PARTIAL"),
            "run_id": run_id,
            "workflow_id": workflow_id,
            "workflow_name": wf["name"],
            "trigger_source": trigger_source,
            "status": overall_status,
            "started_at": started_str,
            "finished_at": finished_str,
            "duration_ms": duration_ms,
            "next_run": next_str,
            "node_results": node_results,
            "final_output": final_output,
            "error_message": error_message
        }

    async def execute_single_node(
        self,
        node: Dict[str, Any],
        ctx: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Executes a single workflow node with template resolution and rich structured output."""
        t0 = time.time()
        nid = node.get("id", "node_test")
        ntype = (node.get("type") or "ai_agent").strip().lower()
        title = node.get("title") or ntype
        raw_cfg = node.get("config") or {}

        if ctx is None:
            now_tz = datetime.now(_get_tzinfo("Asia/Dhaka"))
            ctx = {
                "workflow": {"id": "test", "name": "Single Node Test"},
                "trigger": {
                    "source": "node_test",
                    "date": now_tz.strftime("%Y-%m-%d"),
                    "time": now_tz.strftime("%H:%M:%S"),
                    "datetime": now_tz.strftime("%Y-%m-%d %H:%M:%S"),
                    "weekday": now_tz.strftime("%A"),
                    "timezone": "Asia/Dhaka",
                    "payload": {}
                },
                "nodes": {},
                "prev": {"output": "", "status": "IDLE", "node_id": ""}
            }

        cfg = _resolve_template_value(raw_cfg, ctx)
        status = "SUCCESS"
        output = ""
        summary = ""
        data: Dict[str, Any] = {}

        try:
            # 1. Trigger Nodes
            if ntype.startswith("trigger_"):
                trig = ctx.get("trigger", {})
                payload = trig.get("payload", {})
                output = json.dumps(trig, ensure_ascii=False, indent=2) if payload else (
                    f"Triggered [{trig.get('source', 'manual')}] at {trig.get('datetime')} ({trig.get('timezone')})"
                )
                summary = f"Triggered ({trig.get('source', 'manual')})"
                data = dict(trig)

            # 2. Autonomous AI Agent Node (with multi-turn tool calling & RAG)
            elif ntype == "ai_agent":
                from agent.core_agent import get_shared_agent
                agent = get_shared_agent()
                prompt_text = cfg.get("prompt") or ctx.get("prev", {}).get("output") or "Analyze current status."
                sys_inst = cfg.get("system_instruction", "")
                model_name = (cfg.get("model") or "").strip() or None
                proj_name = (cfg.get("project_name") or "").strip() or None
                use_mem = bool(cfg.get("use_memory", True))
                enable_tools = bool(cfg.get("enable_tools", True))
                lang = cfg.get("language", "bn")
                max_turns = int(cfg.get("max_turns", 5))

                res = await asyncio.wait_for(
                    agent.run_autonomous_task(
                        prompt=prompt_text,
                        model=model_name,
                        system_instruction=sys_inst,
                        project_name=proj_name,
                        use_memory=use_mem,
                        enable_tools=enable_tools,
                        language=lang,
                        max_turns=max_turns
                    ),
                    timeout=120.0
                )
                output = res.get("output", "")
                data = {
                    "model_used": res.get("model_used"),
                    "tool_trace": res.get("tool_trace", []),
                    "sources_count": len(res.get("sources", [])),
                    "reasoning": res.get("reasoning", "")
                }
                if not res.get("success"):
                    status = "FAILED"
                    summary = f"AI Agent failed ({res.get('model_used')})"
                else:
                    tc_cnt = len(data["tool_trace"])
                    summary = f"Model: {data['model_used']} | {tc_cnt} tool call(s)"

            # 3. Specialized Sub-Agent / Swarm Node
            elif ntype == "subagent":
                from agent.subagents.work_engine import SubAgentWorkEngine
                agent_id = (cfg.get("agent_id") or "task_planner_agent").strip()
                task_text = cfg.get("task") or ctx.get("prev", {}).get("output") or "Analyze system operations."
                model_name = (cfg.get("model") or "").strip() or None

                if agent_id == "swarm":
                    swarm_res = await asyncio.wait_for(
                        SubAgentWorkEngine.orchestrate_swarm_mission(goal=task_text, model_override=model_name),
                        timeout=120.0
                    )
                    output = swarm_res.get("executive_summary", "") or json.dumps(swarm_res, ensure_ascii=False)
                    data = {"agents_engaged": swarm_res.get("agents_engaged", []), "mission_id": swarm_res.get("mission_id")}
                    summary = f"Swarm ({len(data['agents_engaged'])} agents)"
                else:
                    sub_res = await asyncio.wait_for(
                        SubAgentWorkEngine.execute_subagent_task(
                            agent_id=agent_id,
                            task_instruction=task_text,
                            model_override=model_name
                        ),
                        timeout=90.0
                    )
                    if not sub_res.get("success", True):
                        status = "FAILED"
                        output = sub_res.get("error", "Subagent execution failed.")
                        summary = f"Subagent '{agent_id}' error"
                    else:
                        output = sub_res.get("output", "")
                        data = {
                            "agent_id": agent_id,
                            "model_used": sub_res.get("model_used"),
                            "tool_summary": sub_res.get("tool_summary"),
                            "tool_data": sub_res.get("tool_data")
                        }
                        summary = f"{sub_res.get('agent_name', agent_id)} ({sub_res.get('execution_time_ms', 0)}ms)"

            # 4. Direct Built-in / MCP Tool Execution Node
            elif ntype == "tool_call":
                from agent.tools import AgentTools
                tool_name = (cfg.get("tool_name") or "system_info").strip()
                raw_args = cfg.get("args_json", "{}")
                if isinstance(raw_args, dict):
                    tool_args = raw_args
                else:
                    try:
                        tool_args = json.loads(str(raw_args).strip() or "{}")
                    except Exception:
                        tool_args = {}

                t_out = await asyncio.wait_for(AgentTools.dispatch_tool(tool_name, tool_args), timeout=60.0)
                output = str(t_out)
                data = {"tool_name": tool_name, "args": tool_args}
                summary = f"Tool '{tool_name}' executed"

            # 5. IF / Else Conditional Branching Node
            elif ntype == "condition":
                target_val = cfg.get("target")
                if not target_val:
                    target_val = ctx.get("prev", {}).get("output", "")
                operator = cfg.get("operator", "contains")
                expected = cfg.get("value", "")

                matched = _evaluate_condition(target_val, operator, expected)
                # Pass upstream output through so downstream nodes keep receiving data!
                pass_through = ctx.get("prev", {}).get("output", "")
                output = pass_through if pass_through else f"Condition evaluated: {matched}"
                data = {
                    "matched": matched,
                    "branch": "true" if matched else "false",
                    "operator": operator,
                    "expected": expected
                }
                summary = f"IF {operator} '{expected}' -> {'TRUE' if matched else 'FALSE'}"

            # 6. HTTP Request Node
            elif ntype == "http_request":
                method = (cfg.get("method") or "POST").strip().upper()
                url = (cfg.get("url") or "").strip()
                if not url:
                    raise ValueError("HTTP Request node requires a target URL.")

                raw_headers = cfg.get("headers_json", "{}")
                headers = json.loads(raw_headers) if isinstance(raw_headers, str) and raw_headers.strip() else (
                    raw_headers if isinstance(raw_headers, dict) else {}
                )
                raw_body = cfg.get("body_json", "")
                json_body = None
                text_body = None
                if isinstance(raw_body, dict):
                    json_body = raw_body
                elif isinstance(raw_body, str) and raw_body.strip():
                    try:
                        json_body = json.loads(raw_body)
                    except Exception:
                        text_body = raw_body

                async with httpx.AsyncClient(timeout=20.0, verify=False) as client:
                    if method == "GET":
                        resp = await client.get(url, headers=headers)
                    elif method == "DELETE":
                        resp = await client.delete(url, headers=headers)
                    else:
                        if json_body is not None:
                            resp = await client.request(method, url, headers=headers, json=json_body)
                        else:
                            resp = await client.request(method, url, headers=headers, content=text_body)

                resp_text = resp.text[:4000]
                data = {"status_code": resp.status_code, "url": url, "method": method}
                output = f"HTTP {resp.status_code} ({method} {url}):\n{resp_text}"
                summary = f"{method} {url} -> HTTP {resp.status_code}"
                if resp.status_code >= 400:
                    status = "FAILED"

            # 7. Project & Vector Memory Save Node
            elif ntype == "memory_save":
                from memory.project_store import ProjectMemoryStore
                project_name = (cfg.get("project_name") or "myagent").strip()
                key = (cfg.get("key") or f"workflow_note_{int(time.time())}").strip()
                category = (cfg.get("category") or "notes").strip()
                context_tag = (cfg.get("context") or "production").strip()
                content = (cfg.get("content") or ctx.get("prev", {}).get("output") or "").strip()

                if not content:
                    raise ValueError("No content available to save to memory.")

                pm_res = await ProjectMemoryStore.save_memory(
                    project_name=project_name,
                    key=key,
                    content=content,
                    title=f"Workflow Auto-Memory: {key}",
                    category=category,
                    context=context_tag,
                    tags=[project_name, category, "workflow_auto"]
                )

                vec_doc_id = None
                if cfg.get("save_to_vector", True):
                    try:
                        from memory.vector_store import VectorMemoryStore
                        vs = VectorMemoryStore()
                        v_res = vs.add_note(
                            title=f"[{project_name}] {key}",
                            content=content[:4000],
                            category="workflow_memory",
                            tags=[project_name, category, "workflow"]
                        )
                        vec_doc_id = v_res.get("doc_id")
                    except Exception as ve:
                        logger.warning(f"Vector memory save skipped: {ve}")

                data = {"project_name": project_name, "key": key, "vector_doc_id": vec_doc_id, "saved": pm_res}
                output = f"✅ Saved to Project Memory [{project_name}/{key}]" + (f" & Vector Store ({vec_doc_id})" if vec_doc_id else "")
                summary = f"Saved [{project_name}/{key}]"

            # 8. Save Executive Report Node (saves .md file + reports.db for UI Reports tab!)
            elif ntype == "save_report":
                rpt_title = (cfg.get("title") or f"{ctx['workflow']['name']} - {ctx['trigger']['date']}").strip()
                rpt_type = (cfg.get("report_type") or "executive_summary").strip()
                content = (cfg.get("content") or ctx.get("prev", {}).get("output") or "").strip()
                if not content:
                    raise ValueError("No content available to archive as report.")

                data_dir = _get_reports_db_dir()
                reports_dir = os.path.join(data_dir, "reports")
                os.makedirs(reports_dir, exist_ok=True)

                rpt_id = f"rpt_{uuid.uuid4().hex[:10]}"
                ts_human = datetime.now().strftime("%d %B %Y, %H:%M")
                full_md = (
                    f"# {rpt_title}\n\n"
                    f"---\n**রিপোর্ট আইডি:** `{rpt_id}` | **তৈরি:** {ts_human} | **উৎস:** Automated Workflow\n---\n\n"
                    f"{content}\n"
                )
                safe_fname = re.sub(r"[^a-zA-Z0-9_\-]", "_", f"{rpt_id}_{rpt_title[:35]}") + ".md"
                md_path = os.path.join(reports_dir, safe_fname)
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(full_md)

                # Also write to reports.db so AI Reports UI displays it seamlessly
                reports_db_path = os.path.join(data_dir, "reports.db")
                def _insert_report():
                    conn = sqlite3.connect(reports_db_path)
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS reports (
                            id TEXT PRIMARY KEY,
                            title TEXT NOT NULL,
                            report_type TEXT NOT NULL,
                            topic TEXT,
                            content TEXT NOT NULL,
                            sources TEXT DEFAULT '[]',
                            created_by TEXT DEFAULT 'workflow_auto',
                            created_at TEXT NOT NULL,
                            word_count INTEGER DEFAULT 0
                        )
                    """)
                    conn.execute("""
                        INSERT INTO reports (id, title, report_type, topic, content, sources, created_by, created_at, word_count)
                        VALUES (?, ?, ?, ?, ?, '[]', 'workflow_auto', ?, ?)
                    """, (rpt_id, rpt_title, rpt_type, ctx["workflow"]["name"], full_md, datetime.now().isoformat(), len(full_md.split())))
                    conn.commit()
                    conn.close()

                await asyncio.to_thread(_insert_report)

                if cfg.get("index_in_memory", True):
                    try:
                        from memory.vector_store import VectorMemoryStore
                        VectorMemoryStore().add_note(
                            title=rpt_title,
                            content=full_md[:3500],
                            category="generated_report",
                            tags=["workflow_report", rpt_type]
                        )
                    except Exception:
                        pass

                data = {"report_id": rpt_id, "filename": safe_fname, "path": md_path}
                output = f"✅ Report archived: `{safe_fname}` (Report ID: `{rpt_id}` — visible in AI Reports tab)\n\n{content[:1200]}"
                summary = f"Report saved ({rpt_id})"

            # 9. Notify Channel & Chat Digest Node
            elif ntype == "notify_channel":
                target_mode = (cfg.get("target") or "chat_and_channels").strip().lower()
                sess_title = (cfg.get("session_title") or "📅 Daily Automated Agent Reports").strip()
                msg_title = (cfg.get("title") or ctx["workflow"]["name"]).strip()
                msg_body = (cfg.get("message") or ctx.get("prev", {}).get("output") or "").strip()
                custom_wh = (cfg.get("custom_webhook_url") or "").strip()

                full_digest = f"### {msg_title}\n\n{msg_body}"
                delivered_to: List[str] = []

                # A. Post to persistent Chat Session if requested
                if target_mode in ("chat_session", "chat_and_channels", "all"):
                    try:
                        from memory.chat_session_store import ChatSessionStore
                        sess_id = "session_daily_automations"
                        cs_db = await ChatSessionStore.get_db()
                        try:
                            async with cs_db.execute("SELECT id FROM sessions WHERE id = ?", (sess_id,)) as cur:
                                exists = await cur.fetchone()
                            now_s = time.strftime("%Y-%m-%d %H:%M:%S")
                            if not exists:
                                await cs_db.execute(
                                    "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                                    (sess_id, sess_title, now_s, now_s)
                                )
                            await cs_db.execute(
                                "INSERT INTO messages (session_id, role, content, sources, created_at) VALUES (?, 'assistant', ?, NULL, ?)",
                                (sess_id, full_digest, now_s)
                            )
                            await cs_db.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now_s, sess_id))
                            await cs_db.commit()
                            delivered_to.append(f"ChatSession({sess_id})")
                        finally:
                            await cs_db.close()
                    except Exception as cs_err:
                        logger.warning(f"Chat session digest delivery warning: {cs_err}")

                # B. Dispatch to configured ops_channels (Telegram, Discord, Slack) if requested
                if target_mode in ("chat_and_channels", "channels", "configured", "all", "telegram", "discord", "slack"):
                    try:
                        ops_db = await WorkflowStore.get_db()
                        try:
                            async with ops_db.execute("SELECT * FROM ops_channels WHERE is_enabled = 1") as cur:
                                chans = [dict(r) for r in await cur.fetchall()]
                        finally:
                            await ops_db.close()

                        for ch in chans:
                            plat = (ch.get("platform") or "").lower()
                            if target_mode in ("telegram", "discord", "slack") and plat != target_mode:
                                continue
                            token = (ch.get("token") or "").strip()
                            wh_url = (ch.get("webhook_url") or "").strip()
                            chat_id = (ch.get("chat_id") or "").strip()

                            async with httpx.AsyncClient(timeout=12.0, verify=False) as client:
                                if plat == "telegram" and token and chat_id:
                                    tg_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                    r = await client.post(tg_url, json={"chat_id": chat_id, "text": f"{msg_title}\n\n{msg_body[:3800]}"})
                                    delivered_to.append(f"Telegram({r.status_code})")
                                elif plat == "discord" and wh_url.startswith("http"):
                                    r = await client.post(wh_url, json={"content": f"**{msg_title}**\n{msg_body[:1900]}"})
                                    delivered_to.append(f"Discord({r.status_code})")
                                elif plat == "slack" and wh_url.startswith("http"):
                                    r = await client.post(wh_url, json={"text": f"*{msg_title}*\n{msg_body[:3000]}"})
                                    delivered_to.append(f"Slack({r.status_code})")
                    except Exception as ch_err:
                        logger.warning(f"Channel dispatch warning: {ch_err}")

                # C. Custom Outbound Webhook URL
                if custom_wh.startswith("http"):
                    try:
                        async with httpx.AsyncClient(timeout=12.0, verify=False) as client:
                            r = await client.post(custom_wh, json={
                                "event": "myagent_workflow_notification",
                                "workflow_id": ctx["workflow"]["id"],
                                "workflow_name": ctx["workflow"]["name"],
                                "title": msg_title,
                                "message": msg_body,
                                "timestamp": ctx["trigger"].get("datetime")
                            })
                            delivered_to.append(f"Webhook({r.status_code})")
                    except Exception as wh_err:
                        delivered_to.append(f"WebhookError({str(wh_err)[:40]})")

                data = {"delivered_to": delivered_to, "title": msg_title}
                output = f"✅ Delivered to: {', '.join(delivered_to) if delivered_to else 'OpsLogs only'}\n\n{msg_body[:800]}"
                summary = f"Notified {', '.join(delivered_to) if delivered_to else 'Log'}"

            else:
                status = "FAILED"
                output = f"Unknown workflow node type '{ntype}'."
                summary = "Unknown node type"

        except asyncio.TimeoutError:
            status = "FAILED"
            output = f"Node '{title}' timed out."
            summary = "Timed out"
        except Exception as node_err:
            status = "FAILED"
            output = f"Node '{title}' error: {str(node_err)}"
            summary = f"Error: {str(node_err)[:60]}"
            logger.error(f"Workflow node '{nid}' ({ntype}) failed: {node_err}")

        elapsed_ms = int((time.time() - t0) * 1000)
        return {
            "node_id": nid,
            "type": ntype,
            "title": title,
            "status": status,
            "duration_ms": elapsed_ms,
            "output": output,
            "summary": summary,
            "data": data
        }


workflow_engine = WorkflowEngine()
