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
from typing import Dict, Any, List, Optional, Set, Tuple

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
    """
    Recursively interpolates template expressions:
      - {{trigger.date}}, {{trigger.iso}}, {{trigger.payload.key}}
      - {{prev.output}}, {{prev.json.field}}, {{prev.error}}
      - {{nodes.node_2.output}}, {{nodes.node_2.data.status_code}}
      - Optional truncation filter: {{prev.output|500}}
    """
    if isinstance(value, dict):
        return {k: _resolve_template_value(v, ctx) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_template_value(v, ctx) for v in value]
    if not isinstance(value, str) or "{{" not in value:
        return value

    def _lookup(expr: str) -> str:
        raw_expr = expr.strip()
        trunc_len: Optional[int] = None
        if "|" in raw_expr:
            path_part, mod_part = raw_expr.split("|", 1)
            raw_expr = path_part.strip()
            if mod_part.strip().isdigit():
                trunc_len = int(mod_part.strip())

        parts = raw_expr.split(".")
        cur: Any = ctx
        for idx, p in enumerate(parts):
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            elif p == "json" and isinstance(cur, dict) and "output" in cur:
                try:
                    cur = json.loads(str(cur["output"]))
                except Exception:
                    return ""
            elif isinstance(cur, str):
                # Attempt JSON traversal if upstream output is JSON string
                try:
                    parsed = json.loads(cur)
                    if isinstance(parsed, dict) and p in parsed:
                        cur = parsed[p]
                    else:
                        return ""
                except Exception:
                    return ""
            elif isinstance(cur, list) and p.isdigit() and 0 <= int(p) < len(cur):
                cur = cur[int(p)]
            else:
                return ""

        if cur is None:
            res = ""
        elif isinstance(cur, (dict, list)):
            res = json.dumps(cur, ensure_ascii=False, indent=2)
        else:
            res = str(cur)

        if trunc_len is not None and len(res) > trunc_len:
            res = res[:trunc_len] + "..."
        return res

    return re.sub(r"\{\{\s*([a-zA-Z0-9_\.\-\|]+)\s*\}\}", lambda m: _lookup(m.group(1)), value)


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


def _redact_secrets_in_obj(obj: Any, secrets_list: List[str]) -> Any:
    """Recursively redacts stored sensitive secrets from logged outputs & JSON telemetry."""
    if not secrets_list:
        return obj
    if isinstance(obj, str):
        res = obj
        for sv in secrets_list:
            if sv and len(sv) >= 6 and sv in res:
                res = res.replace(sv, "***REDACTED***")
        return res
    if isinstance(obj, list):
        return [_redact_secrets_in_obj(item, secrets_list) for item in obj]
    if isinstance(obj, dict):
        return {k: _redact_secrets_in_obj(v, secrets_list) for k, v in obj.items()}
    return obj


class WorkflowEngine:
    """
    Parallel Wave DAG Workflow Engine inspired by n8n:
      - Concurrent asyncio.gather execution across independent branches (Fan-Out & Merge Fan-In)
      - Supports IF/Else (`true`/`false`), Multi-Way Switch Router (`route_1`/`route_2`/`default`), & Modular Sub-Workflows
      - Global Encrypted Secrets Vault (`{{vars.*}}` / `{{secrets.*}}`) with automatic output redaction
      - Live multi-node execution telemetry, dry-run simulation, pinned outputs, retries & cancellation
    """

    def __init__(self):
        self._active_runs: Set[str] = set()
        self._cancel_flags: Set[str] = set()
        self._live_progress: Dict[str, Dict[str, Any]] = {}

    def is_running(self, workflow_id: str) -> bool:
        return workflow_id in self._active_runs

    def stop_workflow(self, workflow_id: str) -> bool:
        """Signals a running workflow to cancel cleanly before the next wave or timer interval."""
        if workflow_id in self._active_runs:
            self._cancel_flags.add(workflow_id)
            return True
        return False

    def get_live_status(self, workflow_id: str) -> Dict[str, Any]:
        prog = self._live_progress.get(workflow_id)
        return {
            "is_running": workflow_id in self._active_runs,
            "progress": dict(prog) if prog else None
        }

    async def execute_workflow(
        self,
        workflow_id: str,
        trigger_source: str = "manual",
        trigger_payload: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        depth: int = 0
    ) -> Dict[str, Any]:
        """Executes a workflow DAG with concurrent parallel waves, retries, redaction & full telemetry."""
        if depth > 3:
            raise ValueError("Sub-workflow recursion depth limit (3) exceeded.")

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
        self._cancel_flags.discard(workflow_id)
        run_id = f"wfrun_{uuid.uuid4().hex[:10]}"
        t0 = time.time()

        vars_map, secret_values_to_redact = await WorkflowStore.get_secrets_for_runtime()

        tz = _get_tzinfo(wf.get("timezone", "Asia/Dhaka"))
        now_tz = datetime.now(tz)
        started_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._live_progress[workflow_id] = {
            "run_id": run_id,
            "status": "RUNNING",
            "started_at": started_str,
            "current_node_id": None,
            "active_node_ids": [],
            "completed_count": 0,
            "total_count": len(wf.get("nodes") or []),
            "node_results": []
        }

        # Mark RUNNING in DB
        try:
            db = await WorkflowStore.get_db()
            try:
                await db.execute("UPDATE ops_workflows SET last_status = 'RUNNING' WHERE id = ?", (workflow_id,))
                await db.execute("""
                    INSERT INTO ops_workflow_runs (
                        id, workflow_id, workflow_name, trigger_source, status, started_at, node_results_json
                    ) VALUES (?, ?, ?, ?, 'RUNNING', ?, '[]')
                """, (run_id, workflow_id, wf["name"], f"{trigger_source}{'[DRY]' if dry_run else ''}", started_str))
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
                    "dry_run": dry_run,
                    "date": now_tz.strftime("%Y-%m-%d"),
                    "time": now_tz.strftime("%H:%M:%S"),
                    "datetime": now_tz.strftime("%Y-%m-%d %H:%M:%S"),
                    "iso": now_tz.isoformat(),
                    "weekday": now_tz.strftime("%A"),
                    "timezone": wf.get("timezone", "Asia/Dhaka"),
                    "payload": trigger_payload or {}
                },
                "vars": vars_map,
                "secrets": vars_map,
                "nodes": {},
                "prev": {"output": "", "status": "IDLE", "node_id": "", "error": "", "data": {}},
                "prev_all": [],
                "_dry_run": dry_run,
                "_depth": depth,
                "_wf_id": workflow_id,
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

                roots = [
                    n["id"] for n in nodes
                    if n.get("id") and (n.get("type", "").startswith("trigger_") or len(incoming[n["id"]]) == 0)
                ]
                if not roots and nodes[0].get("id"):
                    roots = [nodes[0]["id"]]

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

                resolved: Set[str] = set()
                active_edges: Set[str] = set()
                executed_outputs_ordered: List[str] = []
                cancelled = False

                def _propagate_outgoing(src_nid: str, src_res: Dict[str, Any]):
                    src_type = (node_map[src_nid].get("type") or "").strip().lower()
                    src_cfg = node_map[src_nid].get("config") or {}
                    continue_fail = bool(src_cfg.get("continue_on_fail", False))
                    if src_res.get("status") == "FAILED" and not continue_fail:
                        return

                    if src_type == "condition":
                        matched = bool(src_res.get("data", {}).get("matched", False))
                        for e in outgoing[src_nid]:
                            cond = (e.get("condition") or "").strip().lower()
                            if (
                                cond in ("", "always")
                                or (cond in ("true", "yes", "1", "match") and matched)
                                or (cond in ("false", "no", "0", "else") and not matched)
                            ):
                                active_edges.add(f"{e['source']}->{e['target']}:{e.get('condition', '')}")
                    elif src_type == "switch_router":
                        selected_route = (src_res.get("data", {}).get("selected_route") or "default").strip().lower()
                        for e in outgoing[src_nid]:
                            cond = (e.get("condition") or "").strip().lower()
                            if cond in ("", "always", selected_route):
                                active_edges.add(f"{e['source']}->{e['target']}:{e.get('condition', '')}")
                    else:
                        for e in outgoing[src_nid]:
                            active_edges.add(f"{e['source']}->{e['target']}:{e.get('condition', '')}")

                async def _run_single_wave_node(nid: str) -> Dict[str, Any]:
                    node = node_map[nid]
                    ntype = node.get("type", "")
                    node_cfg = node.get("config") or {}

                    inc_edges_reachable = [e for e in incoming[nid] if e["source"] in reachable]
                    active_inc_edges = [
                        e for e in inc_edges_reachable
                        if f"{e['source']}->{e['target']}:{e.get('condition', '')}" in active_edges
                    ]

                    node_ctx = dict(ctx)
                    prev_list = []
                    for ae in active_inc_edges:
                        sid = ae["source"]
                        if sid in ctx["nodes"]:
                            se = ctx["nodes"][sid]
                            prev_list.append({
                                "node_id": sid,
                                "title": se.get("title", sid),
                                "type": se.get("type", ""),
                                "status": se.get("status", "SUCCESS"),
                                "output": se.get("output", ""),
                                "data": se.get("data", {})
                            })
                    node_ctx["prev_all"] = prev_list
                    if prev_list:
                        last_p = prev_list[-1]
                        node_ctx["prev"] = {
                            "node_id": last_p["node_id"],
                            "output": last_p["output"],
                            "status": last_p["status"],
                            "error": last_p["output"] if last_p["status"] == "FAILED" else "",
                            "data": last_p["data"]
                        }

                    # 1. Pinned output short-circuit for instant downstream debugging
                    is_pinned = bool(node_cfg.get("use_pinned") or node.get("use_pinned"))
                    pinned_val = node_cfg.get("pinned_output") if node_cfg.get("pinned_output") is not None else node.get("pinned_output")
                    if is_pinned and pinned_val is not None and str(pinned_val) != "":
                        return {
                            "node_id": nid,
                            "type": ntype,
                            "title": node.get("title", ntype),
                            "status": "SUCCESS",
                            "duration_ms": 0,
                            "output": str(pinned_val),
                            "summary": "📌 Pinned Output Used",
                            "data": {"pinned": True}
                        }

                    # 2. Retry-aware execution
                    max_retries = max(0, min(3, int(node_cfg.get("retry_count", 0) or 0)))
                    continue_on_fail = bool(node_cfg.get("continue_on_fail", False))
                    n_res = await self.execute_single_node(node, node_ctx)
                    for r_attempt in range(max_retries):
                        if n_res["status"] != "FAILED" or workflow_id in self._cancel_flags:
                            break
                        await asyncio.sleep(min(1.5 * (r_attempt + 1), 4.0))
                        n_res = await self.execute_single_node(node, node_ctx)
                        if n_res["status"] != "FAILED":
                            n_res["summary"] = f"{n_res.get('summary', '')} (retry #{r_attempt + 1})".strip()

                    if n_res["status"] == "FAILED" and continue_on_fail:
                        n_res["summary"] = f"{n_res.get('summary', '')} [continue-on-fail]".strip()
                    return _redact_secrets_in_obj(n_res, secret_values_to_redact)

                while len(resolved) < len(reachable):
                    if workflow_id in self._cancel_flags:
                        cancelled = True
                        break

                    # Find all reachable unresolved nodes whose incoming reachable dependencies finished
                    ready_ids = sorted([
                        nid for nid in (reachable - resolved)
                        if all(e["source"] in resolved for e in incoming[nid] if e["source"] in reachable)
                    ], key=lambda x: (node_map[x].get("x", 0), node_map[x].get("y", 0)))

                    if not ready_ids:
                        # Cycle guard fallback
                        ready_ids = sorted(list(reachable - resolved), key=lambda x: node_map[x].get("x", 0))

                    active_wave_ids: List[str] = []

                    for nid in ready_ids:
                        node = node_map[nid]
                        ntype = node.get("type", "")
                        node_cfg = node.get("config") or {}
                        is_root = nid in roots and len(incoming[nid]) == 0
                        inc_edges_reachable = [e for e in incoming[nid] if e["source"] in reachable]
                        active_inc_edges = [
                            e for e in inc_edges_reachable
                            if f"{e['source']}->{e['target']}:{e.get('condition', '')}" in active_edges
                        ]

                        if not is_root and inc_edges_reachable and not active_inc_edges:
                            skip_entry = {
                                "node_id": nid,
                                "type": ntype,
                                "title": node.get("title", ntype),
                                "status": "SKIPPED",
                                "duration_ms": 0,
                                "output": "Skipped (upstream condition/switch branch not active).",
                                "summary": "Branch not taken",
                                "data": {}
                            }
                            ctx["nodes"][nid] = skip_entry
                            node_results.append(skip_entry)
                            resolved.add(nid)
                            continue

                        if node.get("disabled") or node_cfg.get("disabled"):
                            prev_txt = ctx["nodes"][active_inc_edges[-1]["source"]].get("output", "") if active_inc_edges and active_inc_edges[-1]["source"] in ctx["nodes"] else ""
                            bypass_entry = {
                                "node_id": nid,
                                "type": ntype,
                                "title": node.get("title", ntype),
                                "status": "SKIPPED",
                                "duration_ms": 0,
                                "output": prev_txt,
                                "summary": "Muted / Bypassed",
                                "data": {"bypassed": True}
                            }
                            ctx["nodes"][nid] = bypass_entry
                            node_results.append(bypass_entry)
                            resolved.add(nid)
                            for e in outgoing[nid]:
                                active_edges.add(f"{e['source']}->{e['target']}:{e.get('condition', '')}")
                            continue

                        active_wave_ids.append(nid)

                    if active_wave_ids:
                        if workflow_id in self._live_progress:
                            self._live_progress[workflow_id]["active_node_ids"] = list(active_wave_ids)
                            self._live_progress[workflow_id]["current_node_id"] = active_wave_ids[0]
                            self._live_progress[workflow_id]["node_results"] = list(node_results)
                            self._live_progress[workflow_id]["completed_count"] = len(node_results)

                        wave_results = await asyncio.gather(
                            *(_run_single_wave_node(nid) for nid in active_wave_ids),
                            return_exceptions=True
                        )

                        for nid, w_res in zip(active_wave_ids, wave_results):
                            if isinstance(w_res, Exception):
                                w_res = {
                                    "node_id": nid,
                                    "type": node_map[nid].get("type", ""),
                                    "title": node_map[nid].get("title", nid),
                                    "status": "FAILED",
                                    "duration_ms": 0,
                                    "output": f"Parallel execution exception: {str(w_res)}",
                                    "summary": "Exception",
                                    "data": {}
                                }
                            ctx["nodes"][nid] = w_res
                            node_results.append(w_res)
                            resolved.add(nid)

                            if w_res.get("status") != "FAILED" and w_res.get("output") and not node_map[nid].get("type", "").startswith("trigger_"):
                                executed_outputs_ordered.append(w_res["output"])
                                final_output = w_res["output"]

                            _propagate_outgoing(nid, w_res)

                    if workflow_id in self._live_progress:
                        self._live_progress[workflow_id]["node_results"] = list(node_results)
                        self._live_progress[workflow_id]["completed_count"] = len(node_results)

                if cancelled:
                    overall_status = "CANCELLED"
                    error_message = "Workflow execution stopped by user."
                else:
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
            self._cancel_flags.discard(workflow_id)
            if workflow_id in self._live_progress:
                self._live_progress[workflow_id]["status"] = overall_status
                self._live_progress[workflow_id]["current_node_id"] = None
                self._live_progress[workflow_id]["active_node_ids"] = []

        final_output = _redact_secrets_in_obj(final_output, secret_values_to_redact)
        error_message = _redact_secrets_in_obj(error_message, secret_values_to_redact)

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

        run_summary = {
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
            "error_message": error_message,
        }

        # Auto-dispatch WORKFLOWS (Auto) Report to connected Telegram if enabled & not already notified
        if not dry_run and trigger_source not in ("sub_workflow", "telegram_chat"):
            try:
                already_tg = any(
                    s.get("type") == "notify_channel"
                    and s.get("status") == "SUCCESS"
                    and any("Telegram(" in str(d) for d in (s.get("data") or {}).get("delivered_to", []))
                    for s in node_results
                )
                if not already_tg:
                    tg_cfg = await WorkflowStore.get_telegram_config(include_plaintext_token=True)
                    if tg_cfg.get("connected") and tg_cfg.get("auto_send_reports") and tg_cfg.get("chat_id") and tg_cfg.get("_bot_token"):
                        from workflows.telegram_service import telegram_send_message, format_workflow_execution_report
                        report_txt = format_workflow_execution_report(run_summary)
                        await WorkflowStore.record_telegram_chat(
                            chat_id=tg_cfg["chat_id"],
                            sender_name=f"AutoReport: {wf['name']}",
                            direction="report",
                            intent="workflow_report",
                            user_message=f"[Auto Report] {wf['name']} ({overall_status})",
                            reply_message=report_txt,
                            workflow_status_summary=f"{wf['name']} -> {overall_status} ({duration_ms}ms)",
                            linked_workflow_id=workflow_id,
                            status=overall_status,
                            latency_ms=duration_ms,
                        )
                        await telegram_send_message(
                            token=tg_cfg["_bot_token"],
                            chat_id=tg_cfg["chat_id"],
                            text=report_txt,
                            event_type="workflow_report",
                            workflow_id=workflow_id,
                            workflow_name=wf["name"],
                            bot_username=tg_cfg.get("bot_username") or "",
                        )
            except Exception as auto_tg_err:
                logger.debug(f"Auto workflow Telegram report note: {auto_tg_err}")

        # Auto-dispatch WORKFLOWS (Auto) Report to Resend Email if enabled in workflow & not already emailed
        if not dry_run and trigger_source not in ("sub_workflow",):
            try:
                wf_cfg = wf.get("config") or {}
                auto_email = bool(wf.get("auto_send_email") or wf_cfg.get("auto_email") or wf.get("email_to") or wf_cfg.get("email_to"))
                target_email = (wf.get("email_to") or wf_cfg.get("email_to") or "").strip()
                if auto_email and target_email:
                    already_emailed = any(
                        s.get("type") == "resend_email"
                        and s.get("status") == "SUCCESS"
                        for s in node_results
                    )
                    if not already_emailed:
                        from services.resend_service import resend_service
                        if resend_service.is_configured():
                            subject = f"[{overall_status}] Workflow: {wf['name']} ({started_str[:16]})"
                            email_body = (
                                f"Autonomous Workflow '{wf['name']}' execution completed.\n\n"
                                f"Status: {overall_status}\n"
                                f"Trigger: {trigger_source}\n"
                                f"Duration: {duration_ms} ms\n"
                                f"Started: {started_str}\n"
                                f"Finished: {finished_str}\n\n"
                                f"Final Output:\n{str(final_output)[:2500]}"
                            )
                            await resend_service.send_email(
                                to=[target_email],
                                subject=subject,
                                body=email_body,
                                workflow_name=wf["name"],
                                run_id=run_id
                            )
            except Exception as auto_email_err:
                logger.debug(f"Auto workflow Resend email report note: {auto_email_err}")

        return run_summary

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
            vars_map, _ = await WorkflowStore.get_secrets_for_runtime()
            now_tz = datetime.now(_get_tzinfo("Asia/Dhaka"))
            ctx = {
                "workflow": {"id": "test", "name": "Single Node Test"},
                "trigger": {
                    "source": "node_test",
                    "dry_run": False,
                    "date": now_tz.strftime("%Y-%m-%d"),
                    "time": now_tz.strftime("%H:%M:%S"),
                    "datetime": now_tz.strftime("%Y-%m-%d %H:%M:%S"),
                    "iso": now_tz.isoformat(),
                    "weekday": now_tz.strftime("%A"),
                    "timezone": "Asia/Dhaka",
                    "payload": {}
                },
                "vars": vars_map,
                "secrets": vars_map,
                "nodes": {},
                "prev": {"output": "", "status": "IDLE", "node_id": "", "error": "", "data": {}},
                "prev_all": [],
                "_dry_run": False,
                "_depth": 0,
                "_wf_id": ""
            }

        is_dry_run = bool(ctx.get("_dry_run", False))
        parent_wf_id = ctx.get("_wf_id", "")
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
                use_mcp = bool(cfg.get("use_mcp", True))
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
                        include_mcp=use_mcp,
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
                    err_detail = res.get("error") or res.get("output") or "LLM unavailable"
                    is_conn_err = any(
                        tok in str(err_detail).lower()
                        for tok in ("connection error", "timed out", "connecterror", "offline", "unavailable", "apiconnectionerror")
                    )
                    explicit_flag = cfg.get("fallback_on_error")
                    allow_fallback = bool(explicit_flag) or (explicit_flag is None and is_conn_err)

                    if allow_fallback:
                        # Collect all executed non-trigger upstream node outputs cleanly
                        upstream_sections: List[str] = []
                        upstream_anomaly = False
                        for up_id, up_entry in (ctx.get("nodes") or {}).items():
                            if not isinstance(up_entry, dict):
                                continue
                            up_type = str(up_entry.get("type") or "")
                            if up_type.startswith("trigger_"):
                                continue
                            up_out = str(up_entry.get("output") or "").strip()
                            if not up_out:
                                continue
                            up_title = up_entry.get("title") or up_id
                            up_status = str(up_entry.get("status") or "").upper()
                            if up_status == "FAILED" or re.search(r'"offline_count"\s*:\s*[1-9]|STATUS:\s*OFFLINE|\bOFFLINE\b|\bCRITICAL\b', up_out, flags=re.IGNORECASE):
                                upstream_anomaly = True
                            upstream_sections.append(f"#### {up_title} ({up_status})\n{up_out[:1800]}")

                        combined_upstream = "\n\n".join(upstream_sections) if upstream_sections else (ctx.get("prev", {}).get("output", "") or "")
                        data["degraded_offline"] = True
                        data["llm_error"] = err_detail
                        status = "SUCCESS"
                        summary = f"Auto Telemetry Digest (LLM Unreachable: {res.get('model_used')})"
                        health_line = (
                            "🚨 CRITICAL: সিস্টেম/নেটওয়ার্ক টেলিমেট্রিতে সমস্যা বা অফলাইন রিসোর্স শনাক্ত হয়েছে!"
                            if upstream_anomaly
                            else "✅ ALL SYSTEMS HEALTHY (লাইভ টেলিমেট্রি ও ডায়াগনস্টিকস যাচাই সম্পন্ন)"
                        )
                        output = (
                            f"### 📊 অটোনোমাস টেলিমেট্রি ডাইজেস্ট ({ctx.get('trigger', {}).get('datetime', '')})\n"
                            f"- **স্বাস্থ্য অবস্থা:** {health_line}\n"
                            f"- **নোট:** প্রাইমারি AI মডেল (`{res.get('model_used')}`) সাড়া দেয়নি ({err_detail[:120]}); সংগৃহীত সিস্টেম ও নেটওয়ার্ক ডেটা নিচে যুক্ত করা হলো।\n\n"
                            f"{combined_upstream or '(কোনো আপস্ট্রিম ডেটা পাওয়া যায়নি)'}"
                        )
                    else:
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

            # 4A-2. Explicit MCP Hub Tool Call Node
            elif ntype == "mcp_tool":
                from mcp.manager import MCPManager
                server_id = (cfg.get("server_id") or "").strip()
                tool_name = (cfg.get("tool_name") or "").strip()
                if not tool_name:
                    raise ValueError("MCP tool_name cannot be empty.")

                raw_args = cfg.get("args_json", "{}")
                if isinstance(raw_args, dict):
                    tool_args = raw_args
                else:
                    try:
                        tool_args = json.loads(str(raw_args).strip() or "{}")
                    except Exception:
                        tool_args = {"input": str(raw_args or ctx.get("prev", {}).get("output", ""))}

                if is_dry_run:
                    output = f"[🧪 DRY-RUN PREVIEW] Would call MCP tool '{tool_name}' (server='{server_id or 'auto'}') with args={json.dumps(tool_args, ensure_ascii=False)}"
                    data = {"dry_run": True, "server_id": server_id, "tool_name": tool_name, "args": tool_args, "source": "mcp"}
                    summary = f"[DRY-RUN] MCP: {tool_name}"
                else:
                    mcp_out = await asyncio.wait_for(
                        MCPManager.call_tool(tool_name, tool_args, server_id=server_id or None),
                        timeout=60.0
                    )
                    output = str(mcp_out)
                    is_err_out = output.startswith("MCP Error:") or output.startswith("Error executing MCP tool")
                    data = {
                        "server_id": server_id or "auto",
                        "tool_name": tool_name,
                        "args": tool_args,
                        "source": "mcp",
                    }
                    if is_err_out and not bool(cfg.get("fallback_on_error", False)):
                        status = "FAILED"
                        summary = f"MCP '{tool_name}' error"
                    else:
                        summary = f"🔌 MCP '{tool_name}' ({len(output)} chars)"

            # 4B. Python Data Transform Node
            elif ntype == "python_transform":
                import io
                import math
                import csv
                import statistics
                import collections
                import itertools
                import contextlib
                import datetime as _dt

                code = str(raw_cfg.get("code") or cfg.get("code") or "").strip()
                if not code:
                    raise ValueError("Python Transform node code is empty.")

                nodes_data_view = {
                    nid_k: {
                        "output": nv.get("output", ""),
                        "status": nv.get("status", ""),
                        "data": nv.get("data", {})
                    }
                    for nid_k, nv in (ctx.get("nodes") or {}).items()
                }
                prev_raw = ctx.get("prev", {}).get("output", "")
                prev_json = None
                try:
                    prev_json = json.loads(str(prev_raw))
                except Exception:
                    pass

                safe_env = {
                    "__builtins__": __builtins__,
                    "prev_output": prev_raw,
                    "prev_json": prev_json,
                    "prev_data": ctx.get("prev", {}).get("data", {}),
                    "prev_all": ctx.get("prev_all", []),
                    "nodes_data": nodes_data_view,
                    "vars": ctx.get("vars", {}),
                    "secrets": ctx.get("secrets", {}),
                    "trigger": ctx.get("trigger", {}),
                    "workflow": ctx.get("workflow", {}),
                    "json": json,
                    "re": re,
                    "math": math,
                    "csv": csv,
                    "statistics": statistics,
                    "collections": collections,
                    "itertools": itertools,
                    "datetime": _dt,
                    "time": time,
                    "len": len,
                    "any": any,
                    "all": all,
                    "sum": sum,
                    "min": min,
                    "max": max,
                    "round": round,
                    "abs": abs,
                    "sorted": sorted,
                    "enumerate": enumerate,
                    "isinstance": isinstance,
                }
                try:
                    import pandas as pd
                    safe_env["pd"] = pd
                    safe_env["pandas"] = pd
                except Exception:
                    pass
                try:
                    import numpy as np
                    safe_env["np"] = np
                    safe_env["numpy"] = np
                except Exception:
                    pass

                stdout_buf = io.StringIO()
                def _run_py():
                    with contextlib.redirect_stdout(stdout_buf):
                        exec(code, safe_env)
                    return stdout_buf.getvalue().strip()

                py_out = await asyncio.wait_for(asyncio.to_thread(_run_py), timeout=30.0)
                output = py_out or "(Python executed cleanly with empty stdout)"
                data = {"lines": len(output.splitlines())}
                summary = f"Python transformed ({len(output)} chars)"

            # 4B2. No-Code Ping Status Report Formatter Node
            elif ntype == "ping_report_formatter":
                sec1_title = str(cfg.get("section1_title") or "Unit router ping status:").strip()
                sec2_title = str(cfg.get("section2_title") or "Server Ping Status:").strip()
                sec3_title = str(cfg.get("section3_title") or "Wireless Network Status-").strip()
                loss_text = str(cfg.get("loss_text") or "IP ping loss").strip()

                enable_nas = bool(cfg.get("enable_nas_report", True))
                nas_ip = str(cfg.get("nas_ip") or "192.168.9.5").strip()
                nas_name = str(cfg.get("nas_name") or "NAS Server").strip()
                nas_cap_str = str(cfg.get("nas_capacity_free") or "48% Capacity free").strip()
                sec_nas_title = str(cfg.get("section_nas_title") or "NAS Server Storage Status:").strip()
                nas_mount_path = str(cfg.get("nas_mount_path") or "").strip()

                raw_routers = str(cfg.get("unit_routers_text") or "")
                raw_servers = str(cfg.get("servers_text") or "")
                raw_aps = str(cfg.get("access_points_text") or "")

                def _parse_lines_to_targets(text: str):
                    parsed = []
                    for line in text.splitlines():
                        line = line.strip().rstrip(",")
                        if not line or line.startswith("#"):
                            continue
                        ip_m = re.search(r"((?:\d{1,3}\.){3}\d{1,3})", line)
                        if ip_m:
                            ip_val = ip_m.group(1).strip()
                            lbl = line[:ip_m.start()].strip()
                            lbl = re.sub(r"^\d+[\.\-\)]\s*", "", lbl)
                            lbl = re.sub(r"[\s:=|\-]+IP[\s:=|\-]*$", "", lbl, flags=re.IGNORECASE)
                            lbl = re.sub(r"[\s:=|\-]+$", "", lbl).strip()
                            if not lbl:
                                lbl = ip_val
                            parsed.append((lbl, ip_val))
                    return parsed

                unit_routers = _parse_lines_to_targets(raw_routers)
                servers = _parse_lines_to_targets(raw_servers)
                access_points = _parse_lines_to_targets(raw_aps)

                # Collect ping results from prev node or all prior nodes
                item_map: Dict[str, Dict[str, Any]] = {}

                prev_data_dict = ctx.get("prev", {}).get("data", {}) or {}
                items_list = prev_data_dict.get("items") or []
                if not items_list:
                    for _nid, _nv in (ctx.get("nodes") or {}).items():
                        _it = (_nv.get("data") or {}).get("items")
                        if _it and isinstance(_it, list):
                            items_list = _it
                            break

                if items_list:
                    for it in items_list:
                        if isinstance(it, dict) and "item" in it:
                            item_map[str(it["item"]).strip()] = it

                prev_text = str(ctx.get("prev", {}).get("output", "") or "")
                all_targets = unit_routers + servers + access_points
                if enable_nas and nas_ip:
                    all_targets.append((nas_name, nas_ip))
                for _, ip_target in all_targets:
                    if ip_target not in item_map:
                        for line in prev_text.splitlines():
                            if re.search(r"\b" + re.escape(ip_target) + r"\b", line):
                                is_online = ("ONLINE" in line) and not any(bad in line.upper() for bad in ("OFFLINE", "ERROR", "100%", "FAIL"))
                                item_map[ip_target] = {
                                    "item": ip_target,
                                    "status": "ONLINE" if is_online else "OFFLINE",
                                    "output": line
                                }
                                break

                def _extract_ms(ip_val: str) -> str:
                    info = item_map.get(ip_val)
                    if not info or info.get("status") != "ONLINE":
                        return loss_text
                    out_str = str(info.get("output", ""))
                    m = re.search(r"\(([\d\.]+)\s*ms\)", out_str)
                    if m:
                        ms_val = int(round(float(m.group(1))))
                        return f"{ms_val}ms"
                    return loss_text

                out_lines: List[str] = []
                if sec1_title:
                    out_lines.append(sec1_title)
                for name, ip in unit_routers:
                    res_ms = _extract_ms(ip)
                    out_lines.append(f"{name} Average Ping Time for {ip}: {res_ms}")

                if servers:
                    if out_lines:
                        out_lines.append("")
                    if sec2_title:
                        out_lines.append(sec2_title)
                    for idx, (name, ip) in enumerate(servers, 1):
                        res_ms = _extract_ms(ip)
                        if res_ms == loss_text:
                            out_lines.append(f"{idx}.\t{name} {ip} Average Ping Time: {loss_text}")
                        else:
                            out_lines.append(f"{idx}.\t{name} {ip} Average Ping Time {res_ms}")

                # NAS Server Storage Status Section
                nas_report_line = ""
                is_nas_online = False
                cap_display = nas_cap_str
                if enable_nas and nas_ip:
                    free_pct_detected = None
                    check_path = nas_mount_path if (nas_mount_path and os.path.exists(nas_mount_path)) else None
                    if not check_path and os.path.exists("/mnt/nas"):
                        check_path = "/mnt/nas"
                    if not check_path:
                        try:
                            cwd = os.getcwd()
                            if "192.168.9.5" in cwd or "nas" in cwd.lower():
                                check_path = cwd
                        except Exception:
                            pass

                    if check_path:
                        try:
                            import shutil as _shutil
                            du = _shutil.disk_usage(check_path)
                            free_pct_detected = int(round((du.free / du.total) * 100))
                        except Exception:
                            pass

                    if free_pct_detected is not None:
                        cap_display = f"{free_pct_detected}% Capacity free"
                    else:
                        cap_display = nas_cap_str

                    if not cap_display.endswith("free") and "%" in cap_display:
                        cap_display = f"{cap_display} Capacity free"

                    nas_ping_res = _extract_ms(nas_ip)
                    if nas_ping_res != loss_text:
                        is_nas_online = True
                        nas_report_line = f"{nas_name}: Operational ({cap_display})"
                    else:
                        if nas_ip not in item_map:
                            try:
                                import socket
                                with socket.create_connection((nas_ip, 445), timeout=1.5):
                                    is_nas_online = True
                            except Exception:
                                pass
                        if is_nas_online:
                            nas_report_line = f"{nas_name}: Operational ({cap_display})"
                        else:
                            nas_report_line = f"{nas_name}: Offline ({loss_text})"

                    if out_lines:
                        out_lines.append("")
                    if sec_nas_title:
                        out_lines.append(sec_nas_title)
                    out_lines.append(nas_report_line)

                offline_aps = []
                if access_points:
                    if out_lines:
                        out_lines.append("")
                    if sec3_title:
                        out_lines.append(sec3_title)
                    total_aps = len(access_points)
                    for name, ip in access_points:
                        res_ms = _extract_ms(ip)
                        if res_ms == loss_text:
                            offline_aps.append((name, ip))

                    out_lines.append(f"1.\tTotal Access Points: {total_aps}")
                    out_lines.append(f"2.\tOffline Access Points: {len(offline_aps)}")

                    if offline_aps:
                        out_lines.append("")
                        out_lines.append("Offline AP List:")
                        for off_name, off_ip in offline_aps:
                            out_lines.append(f"•\t{off_name} {off_ip}: Link Down ({loss_text})")

                output = "\n".join(out_lines)
                nas_summary_tag = f", NAS: {'OK' if is_nas_online else 'Down'}" if enable_nas else ""
                summary = f"Ping Report ({len(unit_routers)} routers, {len(servers)} servers, {len(access_points)} APs{nas_summary_tag})"
                data = {
                    "total_routers": len(unit_routers),
                    "total_servers": len(servers),
                    "total_aps": len(access_points),
                    "offline_aps_count": len(offline_aps),
                    "routers": [{"name": n, "ip": ip, "latency": _extract_ms(ip)} for n, ip in unit_routers],
                    "servers": [{"name": n, "ip": ip, "latency": _extract_ms(ip)} for n, ip in servers],
                    "access_points": [{"name": n, "ip": ip, "latency": _extract_ms(ip), "status": "OFFLINE" if _extract_ms(ip) == loss_text else "ONLINE"} for n, ip in access_points],
                    "nas_storage": {
                        "enabled": enable_nas,
                        "name": nas_name,
                        "ip": nas_ip,
                        "status": "Operational" if is_nas_online else "Offline",
                        "capacity": cap_display if enable_nas else "",
                        "line": nas_report_line
                    }
                }

            # 4C. ForEach Batch Loop Iterator Node
            elif ntype == "loop_foreach":
                from agent.tools import AgentTools
                raw_items = cfg.get("items_text") or ""
                if not raw_items.strip():
                    raw_items = str(ctx.get("prev", {}).get("output", ""))

                items: List[str] = []
                # Try JSON list first
                try:
                    parsed_items = json.loads(raw_items.strip())
                    if isinstance(parsed_items, list):
                        items = [str(x).strip() for x in parsed_items if str(x).strip()]
                except Exception:
                    pass
                if not items:
                    for ln in re.split(r"[\r\n,]+", raw_items):
                        val = ln.strip()
                        if val and not val.startswith("#"):
                            items.append(val)
                items = items[:150]
                if not items:
                    raise ValueError("No items supplied for ForEach Batch Loop.")

                action_type = (cfg.get("action_type") or "ping").strip().lower()
                tool_name = (cfg.get("tool_name") or "network_port_scan").strip()
                args_tpl = str(cfg.get("args_template_json") or "{\"target\": \"{{item}}\"}")
                http_url_tpl = str(cfg.get("http_url") or "")
                http_method = (cfg.get("http_method") or "GET").strip().upper()

                batch_results: List[Dict[str, Any]] = []
                lines_md: List[str] = [f"| # | Item | Status | Summary |", "|---|---|---|---|"]

                # Run loop items with controlled concurrency (Semaphore = 3) to prevent switch/firewall ICMP rate-limiting
                sem = asyncio.Semaphore(3)

                async def _exec_loop_item(idx_i: int, item_val: str) -> Dict[str, Any]:
                    async with sem:
                        await asyncio.sleep(0.05)
                        item_status = "OK"
                        item_out = ""
                        try:
                            if action_type == "ping":
                                from agent.subagents.ping_agent import NetworkPingSubAgent
                                # Attempt 1: Initial ping check
                                p_res = await asyncio.wait_for(
                                    NetworkPingSubAgent.ping_target(target=item_val, count=2, timeout=1.5),
                                    timeout=12.0
                                )
                                ok_p = bool(p_res.get("success", False))
                                retry_note = ""

                                # If ping is not okay, ping 2nd time to confirm status before reporting
                                if not ok_p:
                                    logger.info(f"Target '{item_val}' ping not okay on 1st check. Retrying 2nd time to confirm...")
                                    await asyncio.sleep(1.2)
                                    p_res2 = await asyncio.wait_for(
                                        NetworkPingSubAgent.ping_target(target=item_val, count=2, timeout=1.5),
                                        timeout=12.0
                                    )
                                    if bool(p_res2.get("success", False)):
                                        p_res = p_res2
                                        ok_p = True
                                        retry_note = " (confirmed OK on 2nd attempt)"
                                        logger.info(f"Target '{item_val}' confirmed ONLINE on 2nd ping check.")
                                    else:
                                        p_res = p_res2
                                        retry_note = " (confirmed OFFLINE after 2 attempts)"
                                        logger.info(f"Target '{item_val}' confirmed OFFLINE after 2nd ping check.")

                                item_status = "ONLINE" if ok_p else "OFFLINE"
                                lat = p_res.get("latency_ms", "-")
                                item_out = f"{p_res.get('status', item_status)} ({lat} ms) - {p_res.get('detail', p_res.get('method', 'ICMP'))}{retry_note}"
                            elif action_type == "http" and http_url_tpl:
                                url_i = http_url_tpl.replace("{{item}}", item_val)
                                async with httpx.AsyncClient(timeout=12.0, verify=False) as client:
                                    resp_i = await client.request(http_method, url_i)
                                    item_status = f"HTTP {resp_i.status_code}"
                                    if resp_i.status_code >= 400:
                                        item_status = f"ERROR HTTP {resp_i.status_code}"
                                    item_out = resp_i.text[:350]
                            else:
                                args_str = args_tpl.replace("{{item}}", item_val)
                                try:
                                    parsed_args = json.loads(args_str)
                                except Exception:
                                    parsed_args = {"target": item_val}
                                t_res = await asyncio.wait_for(
                                    AgentTools.dispatch_tool(tool_name, parsed_args),
                                    timeout=25.0
                                )
                                item_out = str(t_res).strip()
                                low_out = item_out.lower()
                                if any(bad in low_out for bad in ("error", "failed", "100% packet loss", "unreachable", "offline")):
                                    item_status = "ERROR"
                        except Exception as it_err:
                            item_status = "ERROR"
                            item_out = str(it_err)

                        return {
                            "idx": idx_i,
                            "item": item_val,
                            "status": item_status,
                            "output": item_out[:600]
                        }

                tasks = [_exec_loop_item(idx_i, item_val) for idx_i, item_val in enumerate(items, 1)]
                res_list = await asyncio.gather(*tasks)

                for res in res_list:
                    batch_results.append({"item": res["item"], "status": res["status"], "output": res["output"]})
                    one_line = " ".join(res["output"].splitlines())[:120].replace("|", "/")
                    lines_md.append(f"| {res['idx']} | `{res['item']}` | **{res['status']}** | {one_line} |")

                err_items = sum(1 for b in batch_results if b["status"] in ("ERROR", "OFFLINE") or "ERROR" in b["status"])
                data = {"total_items": len(batch_results), "error_items": err_items, "items": batch_results}
                output = "\n".join(lines_md)
                summary = f"Loop {len(batch_results)} item(s) ({err_items} error)"

            # 4D. Delay / Wait Timer Node (cancellable cleanly)
            elif ntype == "delay_wait":
                sec = min(max(float(cfg.get("seconds", 2) or 2), 0.1), 60.0)
                if not is_dry_run:
                    elapsed_w = 0.0
                    while elapsed_w < sec:
                        if parent_wf_id and parent_wf_id in self._cancel_flags:
                            break
                        step_w = min(0.25, sec - elapsed_w)
                        await asyncio.sleep(step_w)
                        elapsed_w += step_w
                output = ctx.get("prev", {}).get("output", "") or f"Waited {sec:.1f}s"
                data = {"waited_seconds": sec}
                summary = f"Waited {sec:.1f}s" + (" (dry)" if is_dry_run else "")

            # 4E. Merge / Multi-Branch Combine Node
            elif ntype == "merge_combine":
                mode = (cfg.get("mode") or "markdown_sections").strip().lower()
                inc_empty = bool(cfg.get("include_empty", False))
                prev_all = ctx.get("prev_all") or []
                if not prev_all and ctx.get("prev", {}).get("output"):
                    prev_all = [ctx["prev"]]

                valid_items = [
                    p for p in prev_all
                    if inc_empty or str(p.get("output") or "").strip()
                ]
                if mode == "json_array":
                    output = json.dumps(
                        [{"node_id": p.get("node_id"), "title": p.get("title"), "status": p.get("status"), "output": p.get("output")} for p in valid_items],
                        ensure_ascii=False, indent=2
                    )
                else:
                    sections = []
                    for p in valid_items:
                        title_p = p.get("title") or p.get("node_id") or "Branch"
                        sections.append(f"### [{p.get('node_id', 'branch')}] {title_p} ({p.get('status', 'OK')})\n{p.get('output', '')}")
                    output = "\n\n---\n\n".join(sections) if sections else "No upstream branch outputs to merge."
                data = {"merged_count": len(valid_items), "branch_ids": [p.get("node_id") for p in valid_items]}
                summary = f"Merged {len(valid_items)} branch(es)"

            # 4F. Multi-Way Switch Router Node
            elif ntype == "switch_router":
                target_val = cfg.get("target")
                if not target_val:
                    target_val = ctx.get("prev", {}).get("output", "")
                r1_op = cfg.get("route1_op", "regex")
                r1_val = cfg.get("route1_val", "")
                r2_op = cfg.get("route2_op", "regex")
                r2_val = cfg.get("route2_val", "")

                selected_route = "default"
                if r1_val and _evaluate_condition(target_val, r1_op, r1_val):
                    selected_route = "route_1"
                elif r2_val and _evaluate_condition(target_val, r2_op, r2_val):
                    selected_route = "route_2"

                pass_through = ctx.get("prev", {}).get("output", "")
                output = pass_through if pass_through else f"Switch selected: {selected_route}"
                data = {"selected_route": selected_route, "route_1": r1_val, "route_2": r2_val}
                summary = f"Switch -> {selected_route.upper()}"

            # 4G. Sub-Workflow Call Node (Modular Reusable Pipelines)
            elif ntype == "sub_workflow":
                target_wf_id = (cfg.get("target_workflow_id") or "").strip()
                if not target_wf_id:
                    raise ValueError("Sub-Workflow node requires selecting a Target Workflow ID.")
                if target_wf_id == parent_wf_id:
                    raise ValueError("Workflow cannot invoke itself directly as a sub-workflow.")
                raw_pl = cfg.get("payload_json", "{}")
                sub_payload = {}
                if isinstance(raw_pl, dict):
                    sub_payload = raw_pl
                elif isinstance(raw_pl, str) and raw_pl.strip():
                    try:
                        sub_payload = json.loads(raw_pl)
                    except Exception:
                        sub_payload = {"input": raw_pl}

                depth_next = int(ctx.get("_depth", 0)) + 1
                sub_res = await self.execute_workflow(
                    workflow_id=target_wf_id,
                    trigger_source=f"sub_workflow:{parent_wf_id or 'manual'}",
                    trigger_payload=sub_payload,
                    dry_run=is_dry_run,
                    depth=depth_next
                )
                output = sub_res.get("final_output", "") or f"Sub-workflow '{target_wf_id}' status: {sub_res.get('status')}"
                data = {
                    "sub_workflow_id": target_wf_id,
                    "sub_run_id": sub_res.get("run_id"),
                    "sub_status": sub_res.get("status"),
                    "duration_ms": sub_res.get("duration_ms")
                }
                if sub_res.get("status") == "FAILED":
                    status = "FAILED"
                summary = f"SubWF '{sub_res.get('workflow_name', target_wf_id)}' ({sub_res.get('status')})"

            # 4H. SQLite DB & Hybrid Vector RAG Knowledge Query Node
            elif ntype == "knowledge_db_query":
                q_mode = (cfg.get("query_mode") or "sqlite").strip().lower()
                if q_mode == "rag":
                    rag_q = (cfg.get("rag_query") or ctx.get("prev", {}).get("output") or "").strip()
                    top_k = max(1, min(12, int(cfg.get("top_k", 5) or 5)))
                    from memory.vector_store import VectorMemoryStore
                    hits = VectorMemoryStore().super_fast_search(query=rag_q, top_k=top_k, user_role="admin")
                    if not hits:
                        output = f"No vector/knowledge hits found for query: {rag_q}"
                    else:
                        lines = [f"- **[{h.get('source', 'Memory')} score={h.get('score', 0):.2f}]** {str(h.get('content', ''))[:400]}" for h in hits]
                        output = "\n".join(lines)
                    data = {"mode": "rag", "hits_count": len(hits)}
                    summary = f"RAG Query ({len(hits)} hits)"
                else:
                    allowed_dbs = {"ops.db", "chat_history.db", "reports.db", "project_memory.db", "security_audit.db"}
                    db_name = os.path.basename((cfg.get("db_name") or "ops.db").strip())
                    if db_name not in allowed_dbs:
                        raise ValueError(f"DB '{db_name}' not allowed. Choose from: {', '.join(sorted(allowed_dbs))}")
                    sql_q = (cfg.get("sql_query") or "SELECT name FROM sqlite_master WHERE type='table';").strip()
                    sql_head = sql_q.lstrip().split()[0].upper() if sql_q.strip() else ""
                    if sql_head not in ("SELECT", "PRAGMA", "WITH", "EXPLAIN"):
                        raise ValueError("Security rule: only read-only SELECT, PRAGMA, or WITH SQLite queries are allowed.")

                    data_dir = _get_reports_db_dir()
                    db_path = os.path.join(data_dir, db_name)
                    if not os.path.exists(db_path):
                        db_path = os.path.join("./data", db_name)

                    def _exec_read_sql():
                        conn = sqlite3.connect(db_path)
                        conn.row_factory = sqlite3.Row
                        cur = conn.execute(sql_q)
                        rows_raw = cur.fetchmany(30)
                        cols = [d[0] for d in (cur.description or [])]
                        rows_list = [dict(zip(cols, r)) for r in rows_raw] if cols else []
                        conn.close()
                        return cols, rows_list

                    cols, rows_list = await asyncio.to_thread(_exec_read_sql)
                    if not rows_list:
                        output = f"SQL Query returned 0 rows from `{db_name}`."
                    else:
                        header_md = "| " + " | ".join(cols) + " |"
                        sep_md = "|" + "|".join(["---"] * len(cols)) + "|"
                        body_md = [
                            "| " + " | ".join(str(row.get(c, ""))[:120].replace("|", "/").replace("\n", " ") for c in cols) + " |"
                            for row in rows_list
                        ]
                        output = f"### SQLite Query (`{db_name}` • {len(rows_list)} row(s))\n" + "\n".join([header_md, sep_md] + body_md)
                    data = {"mode": "sqlite", "db_name": db_name, "row_count": len(rows_list), "rows": rows_list[:15]}
                    summary = f"SQL '{db_name}' ({len(rows_list)} rows)"

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

                if is_dry_run and method != "GET":
                    output = f"[🧪 DRY-RUN PREVIEW] Skipped external {method} {url}\nBody:\n{str(raw_body)[:800]}"
                    data = {"dry_run": True, "method": method, "url": url}
                    summary = f"[DRY-RUN] {method} {url}"
                else:
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

                if is_dry_run:
                    output = f"[🧪 DRY-RUN PREVIEW] Would save memory [{project_name}/{key}]:\n{content[:600]}"
                    data = {"dry_run": True, "project_name": project_name, "key": key}
                    summary = f"[DRY-RUN] Memory {project_name}/{key}"
                else:
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

                if is_dry_run:
                    output = f"[🧪 DRY-RUN PREVIEW] Would archive report '{rpt_title}':\n{content[:600]}"
                    data = {"dry_run": True, "title": rpt_title}
                    summary = "[DRY-RUN] Save Report"
                else:
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
                from workflows.telegram_service import telegram_send_message

                target_mode = (cfg.get("target") or "chat_and_channels").strip().lower()
                sess_title = (cfg.get("session_title") or "📅 Daily Automated Agent Reports").strip()
                msg_title = (cfg.get("title") or ctx["workflow"]["name"]).strip()
                msg_body = (cfg.get("message") or ctx.get("prev", {}).get("output") or "").strip()
                custom_wh = (cfg.get("custom_webhook_url") or "").strip()
                tg_chat_override = (cfg.get("telegram_chat_id") or "").strip()
                tg_parse_mode = (cfg.get("parse_mode") or "").strip()

                full_digest = f"### {msg_title}\n\n{msg_body}"
                if is_dry_run:
                    extra_cid = f" (chat_id={tg_chat_override})" if tg_chat_override else ""
                    output = f"[🧪 DRY-RUN PREVIEW] Would notify ({target_mode}{extra_cid}) titled '{msg_title}':\n{msg_body[:600]}"
                    data = {"dry_run": True, "target": target_mode, "telegram_chat_override": tg_chat_override}
                    summary = f"[DRY-RUN] Notify {target_mode}"
                else:
                    delivered_to: List[str] = []
                    channel_errors: List[str] = []

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
                            channel_errors.append(f"ChatSession: {cs_err}")

                    # B. Dispatch to Telegram (Workflow Telegram Connection) + other ops_channels
                    if target_mode in ("chat_and_channels", "channels", "configured", "all", "telegram", "discord", "slack"):
                        if target_mode in ("chat_and_channels", "channels", "configured", "all", "telegram"):
                            try:
                                tg_cfg = await WorkflowStore.get_telegram_config(include_plaintext_token=True)
                                tg_tok = tg_cfg.get("_bot_token") or ""
                                tg_cid = tg_chat_override or tg_cfg.get("chat_id") or ""
                                tg_should_send = bool(tg_tok and tg_cid and (tg_cfg.get("is_enabled") or target_mode == "telegram"))
                                if tg_should_send:
                                    tg_res = await telegram_send_message(
                                        token=tg_tok,
                                        chat_id=tg_cid,
                                        text=f"{msg_title}\n\n{msg_body[:3700]}",
                                        parse_mode=tg_parse_mode,
                                        event_type="workflow_notify",
                                        workflow_id=ctx["workflow"]["id"],
                                        workflow_name=ctx["workflow"]["name"],
                                        node_id=nid,
                                        bot_username=tg_cfg.get("bot_username") or "",
                                    )
                                    if tg_res.get("ok"):
                                        mid = tg_res.get("telegram_message_id")
                                        delivered_to.append(f"Telegram(ok{', msg=' + mid if mid else ''})")
                                    else:
                                        channel_errors.append(f"Telegram: {tg_res.get('error')}")
                                elif target_mode == "telegram":
                                    err_msg = "Telegram bot is not connected or missing Bot Token / Chat ID."
                                    await WorkflowStore.record_telegram_log(
                                        event_type="workflow_notify",
                                        status="FAILED",
                                        workflow_id=ctx["workflow"]["id"],
                                        workflow_name=ctx["workflow"]["name"],
                                        node_id=nid,
                                        bot_username=tg_cfg.get("bot_username") or "",
                                        chat_id=tg_cid,
                                        message_preview=msg_title,
                                        error_detail=err_msg,
                                    )
                                    channel_errors.append(err_msg)
                            except Exception as tg_err:
                                logger.warning(f"Telegram dispatch warning: {tg_err}")
                                channel_errors.append(f"Telegram: {tg_err}")

                        # Dispatch non-Telegram ops_channels (Discord, Slack, etc.)
                        if target_mode != "telegram":
                            try:
                                ops_db = await WorkflowStore.get_db()
                                try:
                                    async with ops_db.execute("SELECT * FROM ops_channels WHERE is_enabled = 1 AND platform != 'telegram'") as cur:
                                        chans = [dict(r) for r in await cur.fetchall()]
                                finally:
                                    await ops_db.close()

                                for ch in chans:
                                    plat = (ch.get("platform") or "").lower()
                                    if target_mode in ("discord", "slack") and plat != target_mode:
                                        continue
                                    wh_url = (ch.get("webhook_url") or "").strip()
                                    async with httpx.AsyncClient(timeout=12.0, verify=False) as client:
                                        if plat == "discord" and wh_url.startswith("http"):
                                            r = await client.post(wh_url, json={"content": f"**{msg_title}**\n{msg_body[:1900]}"})
                                            delivered_to.append(f"Discord({r.status_code})")
                                        elif plat == "slack" and wh_url.startswith("http"):
                                            r = await client.post(wh_url, json={"text": f"*{msg_title}*\n{msg_body[:3000]}"})
                                            delivered_to.append(f"Slack({r.status_code})")
                            except Exception as ch_err:
                                logger.warning(f"Channel dispatch warning: {ch_err}")
                                channel_errors.append(f"Channels: {ch_err}")

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
                            channel_errors.append(f"Webhook: {str(wh_err)[:60]}")

                    # D. Resend Email Dispatch
                    email_target = (cfg.get("email_to") or cfg.get("to_email") or "").strip()
                    should_email = (target_mode in ("email", "resend", "all") or (target_mode == "chat_and_channels" and email_target))
                    if should_email:
                        try:
                            from services.resend_service import resend_service
                            target_recipients = email_target or getattr(settings, "RESEND_ADMIN_EMAIL", "")
                            if target_recipients:
                                mail_res = await resend_service.send_email(
                                    to=target_recipients,
                                    subject=msg_title,
                                    body=msg_body
                                )
                                if mail_res.get("ok"):
                                    mid = mail_res.get("id") or ""
                                    delivered_to.append(f"ResendEmail(ok{', id=' + mid[:8] if mid else ''})")
                                else:
                                    channel_errors.append(f"ResendEmail: {mail_res.get('error')}")
                            elif target_mode in ("email", "resend"):
                                channel_errors.append("ResendEmail: No recipient email address specified in email_to.")
                        except Exception as mail_err:
                            logger.warning(f"Resend notify warning: {mail_err}")
                            channel_errors.append(f"ResendEmail: {mail_err}")

                    if target_mode in ("telegram", "email", "resend") and channel_errors and not delivered_to:
                        status = "FAILED"
                        data = {"delivered_to": [], "errors": channel_errors, "title": msg_title}
                        output = f"❌ {target_mode.capitalize()} delivery failed: {'; '.join(channel_errors)}"
                        summary = f"{target_mode.capitalize()} failed: {channel_errors[0][:50]}"
                    else:
                        data = {"delivered_to": delivered_to, "errors": channel_errors, "title": msg_title}
                        err_note = f"\n⚠️ Errors: {'; '.join(channel_errors)}" if channel_errors else ""
                        output = f"✅ Delivered to: {', '.join(delivered_to) if delivered_to else 'OpsLogs only'}{err_note}\n\n{msg_body[:800]}"
                        summary = f"Notified {', '.join(delivered_to) if delivered_to else 'Log'}"

            # 10. Resend Email Dedicated Node
            elif ntype in ("resend_email", "send_email"):
                from services.resend_service import resend_service

                to_email = (cfg.get("to") or cfg.get("to_email") or "").strip()
                subject = (cfg.get("subject") or f"[{ctx['workflow']['name']}] Notification").strip()
                body = (cfg.get("body") or cfg.get("message") or ctx.get("prev", {}).get("output") or "").strip()
                from_email = (cfg.get("from_email") or cfg.get("from") or "").strip()
                custom_html = (cfg.get("html") or "").strip()

                if not to_email:
                    to_email = getattr(settings, "RESEND_ADMIN_EMAIL", "") or ""

                if not to_email:
                    raise ValueError("No recipient email ('to') specified for Resend Email node.")

                if is_dry_run:
                    output = f"[🧪 DRY-RUN PREVIEW] Would send Resend Email to '{to_email}' with subject '{subject}':\n{body[:600]}"
                    data = {"dry_run": True, "to": to_email, "subject": subject, "from": from_email or "default"}
                    summary = f"[DRY-RUN] Email to {to_email}"
                else:
                    mail_res = await resend_service.send_email(
                        to=to_email,
                        subject=subject,
                        body=body,
                        html=custom_html,
                        from_email=from_email or None
                    )
                    if not mail_res.get("ok"):
                        raise RuntimeError(f"Resend email delivery failed: {mail_res.get('error')}")

                    msg_id = mail_res.get("id") or ""
                    data = mail_res
                    output = (
                        f"✅ Email successfully delivered via Resend API!\n"
                        f"- Message ID: `{msg_id}`\n"
                        f"- To: `{', '.join(mail_res.get('to', []))}`\n"
                        f"- From: `{mail_res.get('from')}`\n"
                        f"- Subject: `{subject}`\n\n"
                        f"{body[:500]}"
                    )
                    summary = f"Email sent ({msg_id[:12]})"

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
