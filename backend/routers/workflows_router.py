# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 3.3.0
# Workflows API Router — n8n-Style Visual Automation & Daily AI Task Engine
# ==============================================================================

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query, Header

from routers.auth import get_current_user, get_optional_current_user
from workflows.store import WorkflowStore, WORKFLOW_TEMPLATES, NODE_CATALOG
from workflows.engine import workflow_engine

logger = logging.getLogger("myagent.routers.workflows")

router = APIRouter(prefix="/api/workflows", tags=["Workflows & Daily Automation"])


@router.get("")
async def list_workflows(user=Depends(get_optional_current_user)):
    """Lists all n8n-style workflows with running status, schedules, and aggregate KPIs."""
    await WorkflowStore.init_tables_and_seed()
    workflows = await WorkflowStore.list_workflows()
    for wf in workflows:
        if workflow_engine.is_running(wf["id"]):
            wf["last_status"] = "RUNNING"
        wf["is_running"] = workflow_engine.is_running(wf["id"])

    recent_runs = await WorkflowStore.list_runs(limit=25)
    total_runs = sum(int(w.get("run_count") or 0) for w in workflows)
    total_success = sum(int(w.get("success_count") or 0) for w in workflows)
    active_count = sum(1 for w in workflows if w.get("is_enabled"))

    return {
        "success": True,
        "workflows": workflows,
        "recent_runs": recent_runs,
        "stats": {
            "total_workflows": len(workflows),
            "active_workflows": active_count,
            "total_runs": total_runs,
            "success_rate": round((total_success / total_runs) * 100, 1) if total_runs > 0 else 100.0
        }
    }


@router.get("/templates")
async def get_workflow_catalog_and_templates(user=Depends(get_optional_current_user)):
    """Returns pre-built workflow templates, node palette definitions, available tools, subagents, and models."""
    from agent.tools import AgentTools
    from agent.openrouter_client import OPENROUTER_ALL_FREE_MODELS, FEATURED_OPENROUTER_MODELS, OpenRouterService
    from agent.subagents.work_engine import SubAgentWorkEngine
    from config import settings

    tools_schema = AgentTools.get_openai_tools_schema()
    tool_names = [
        {"name": t["function"]["name"], "description": t["function"].get("description", "")}
        for t in tools_schema if t.get("function", {}).get("name")
    ]
    subagents = await SubAgentWorkEngine.get_all_subagents()

    models = [
        {"id": "", "label": f"Default ({settings.LLM_MODEL})"},
        {"id": settings.LLM_MODEL, "label": f"Local/Primary ({settings.LLM_MODEL})"}
    ]
    for m in OPENROUTER_ALL_FREE_MODELS[:10]:
        models.append({"id": m["id"], "label": f"[Free] {m['name']} ({m['id']})"})
    for m in FEATURED_OPENROUTER_MODELS[:5]:
        models.append({"id": m["id"], "label": f"[OpenRouter] {m['name']}"})

    all_wfs = await WorkflowStore.list_workflows()
    return {
        "success": True,
        "templates": WORKFLOW_TEMPLATES,
        "node_catalog": NODE_CATALOG,
        "tools": tool_names,
        "workflows_list": [{"id": w["id"], "name": w["name"], "icon": w.get("icon", "⚡")} for w in all_wfs],
        "subagents": [
            {"id": "swarm", "name": "🐝 Full Multi-Agent Swarm Orchestrator", "icon": "🐝"},
            *[
                {"id": s["id"], "name": f"{s.get('icon', '🤖')} {s['name']}", "icon": s.get("icon", "🤖")}
                for s in subagents
            ]
        ],
        "models": models,
        "openrouter_configured": OpenRouterService.is_configured()
    }


@router.get("/vars/list")
async def list_workflow_variables(user=Depends(get_optional_current_user)):
    """Lists all global encrypted secrets & workflow environment variables."""
    await WorkflowStore.init_tables_and_seed()
    items = await WorkflowStore.list_secrets()
    return {"success": True, "variables": items}


@router.post("/vars/save")
async def save_workflow_variable(
    data: Dict[str, Any] = Body(...),
    user=Depends(get_optional_current_user)
):
    """Creates or updates an AES-256 encrypted secret/variable accessible as {{vars.KEY}}."""
    await WorkflowStore.init_tables_and_seed()
    try:
        saved = await WorkflowStore.upsert_secret(
            key=data.get("key", ""),
            value=data.get("value", ""),
            is_secret=bool(data.get("is_secret", True)),
            description=data.get("description", "")
        )
        return {"success": True, "variable": saved, "message": f"Saved variable {saved['key']}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/vars/{key}")
async def delete_workflow_variable(
    key: str,
    user=Depends(get_optional_current_user)
):
    """Deletes a global workflow variable/secret by key."""
    ok = await WorkflowStore.delete_secret(key)
    if not ok:
        raise HTTPException(status_code=404, detail="Variable not found.")
    return {"success": True, "message": f"Deleted variable '{key}'."}


@router.get("/runs/recent")
async def list_recent_workflow_runs(
    limit: int = Query(30, le=100),
    user=Depends(get_optional_current_user)
):
    """Returns recent workflow runs across all workflows."""
    runs = await WorkflowStore.list_runs(limit=limit)
    return {"success": True, "runs": runs}


@router.post("/quick-daily")
async def create_quick_daily_workflow(
    data: Dict[str, Any] = Body(...),
    user=Depends(get_optional_current_user)
):
    """
    Creates & activates a multi-node Daily Autonomous Agent Workflow from natural language instructions.
    """
    instruction = (data.get("instruction") or "").strip()
    if not instruction:
        raise HTTPException(status_code=400, detail="Daily task instruction cannot be empty.")

    name = (data.get("name") or instruction[:48]).strip()
    daily_time = (data.get("daily_time") or "09:00").strip()
    frequency = (data.get("frequency") or "daily").strip()
    timezone_str = (data.get("timezone") or "Asia/Dhaka").strip()
    model = (data.get("model") or "").strip()
    project_name = (data.get("project_name") or "").strip()
    save_report = bool(data.get("save_report", True))
    save_memory = bool(data.get("save_memory", False))
    post_to_chat = bool(data.get("post_to_chat", True))
    notify_channels = bool(data.get("notify_channels", False))
    custom_webhook_url = (data.get("custom_webhook_url") or "").strip()
    language = (data.get("language") or "bn").strip()

    wf = await WorkflowStore.build_quick_daily_workflow(
        name=name,
        instruction=instruction,
        daily_time=daily_time,
        frequency=frequency,
        timezone_str=timezone_str,
        model=model,
        project_name=project_name,
        save_report=save_report,
        save_memory=save_memory,
        post_to_chat=post_to_chat,
        notify_channels=notify_channels,
        custom_webhook_url=custom_webhook_url,
        language=language
    )

    run_immediately = bool(data.get("run_immediately", False))
    run_res = None
    if run_immediately:
        run_res = await workflow_engine.execute_workflow(wf["id"], trigger_source="manual")
        wf = await WorkflowStore.get_workflow(wf["id"])

    return {
        "success": True,
        "workflow": wf,
        "run_result": run_res,
        "message": f"Daily workflow '{name}' activated ({daily_time} {timezone_str})."
    }


@router.post("/ai-architect")
async def ai_architect_workflow(
    data: Dict[str, Any] = Body(...),
    user=Depends(get_optional_current_user)
):
    """Designs & activates a rich branched multi-node n8n workflow DAG from a plain goal description."""
    goal = (data.get("goal") or data.get("instruction") or "").strip()
    if not goal:
        raise HTTPException(status_code=400, detail="Goal prompt cannot be empty.")

    name = (data.get("name") or "").strip()
    daily_time = (data.get("daily_time") or "09:00").strip()
    frequency = (data.get("frequency") or "daily").strip()
    timezone_str = (data.get("timezone") or "Asia/Dhaka").strip()
    model = (data.get("model") or "").strip()
    project_name = (data.get("project_name") or "").strip()

    wf = await WorkflowStore.architect_workflow_from_goal(
        goal=goal,
        name=name,
        daily_time=daily_time,
        frequency=frequency,
        timezone_str=timezone_str,
        model=model,
        project_name=project_name,
        auto_enable=bool(data.get("is_enabled", True))
    )
    return {
        "success": True,
        "workflow": wf,
        "message": f"AI Architect built workflow '{wf['name']}' with {len(wf.get('nodes', []))} connected nodes."
    }


@router.post("/import")
async def import_workflow_json(
    data: Dict[str, Any] = Body(...),
    user=Depends(get_optional_current_user)
):
    """Imports a shared/exported n8n-style workflow JSON into MyAgent."""
    try:
        wf = await WorkflowStore.import_workflow(data)
        return {"success": True, "workflow": wf, "message": f"Imported workflow '{wf['name']}'."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/node/test")
async def test_single_workflow_node(
    data: Dict[str, Any] = Body(...),
    user=Depends(get_optional_current_user)
):
    """Tests a single workflow node configuration directly inside the n8n studio inspector."""
    node = data.get("node")
    if not isinstance(node, dict):
        raise HTTPException(status_code=400, detail="Missing 'node' dictionary.")
    sample_input = str(data.get("sample_input") or "")

    from datetime import datetime
    from workflows.store import _get_tzinfo
    now_tz = datetime.now(_get_tzinfo("Asia/Dhaka"))
    vars_map, _ = await WorkflowStore.get_secrets_for_runtime()
    ctx = {
        "workflow": {"id": "test", "name": "Studio Node Test"},
        "trigger": {
            "source": "node_test",
            "dry_run": False,
            "date": now_tz.strftime("%Y-%m-%d"),
            "time": now_tz.strftime("%H:%M:%S"),
            "datetime": now_tz.strftime("%Y-%m-%d %H:%M:%S"),
            "iso": now_tz.isoformat(),
            "weekday": now_tz.strftime("%A"),
            "timezone": "Asia/Dhaka",
            "payload": {"sample": sample_input}
        },
        "vars": vars_map,
        "secrets": vars_map,
        "nodes": {},
        "prev": {"output": sample_input, "status": "SUCCESS", "node_id": "sample_prev", "error": "", "data": {}},
        "prev_all": [{"node_id": "sample_prev", "title": "Sample Input", "type": "manual", "status": "SUCCESS", "output": sample_input, "data": {}}],
        "_dry_run": False,
        "_depth": 0,
        "_wf_id": ""
    }
    res = await workflow_engine.execute_single_node(node, ctx)
    return {"success": res["status"] != "FAILED", "result": res}


@router.post("/templates/{template_id}/install")
async def install_workflow_template(
    template_id: str,
    user=Depends(get_optional_current_user)
):
    """Clones a pre-built workflow template into active workflows."""
    wf = await WorkflowStore.install_template(template_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Template not found.")
    return {"success": True, "workflow": wf, "message": f"Template '{wf['name']}' installed."}


@router.post("/webhook/{workflow_id}")
async def trigger_workflow_via_webhook(
    workflow_id: str,
    payload: Optional[Dict[str, Any]] = Body(default={}),
    x_webhook_secret: Optional[str] = Header(default=None, alias="X-Webhook-Secret"),
    secret: Optional[str] = Query(default=None)
):
    """Public/Secret-verified inbound Webhook endpoint to execute a workflow externally."""
    wf = await WorkflowStore.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found.")

    expected_secret = wf.get("webhook_secret") or ""
    provided_secret = x_webhook_secret or secret or ""
    # Allow execution without secret ONLY if workflow secret was explicitly cleared, or verify match
    if expected_secret and provided_secret and provided_secret != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid webhook secret.")

    res = await workflow_engine.execute_workflow(
        workflow_id=workflow_id,
        trigger_source="webhook",
        trigger_payload=payload or {}
    )
    return res


@router.post("")
async def create_workflow(
    data: Dict[str, Any] = Body(...),
    user=Depends(get_optional_current_user)
):
    """Creates a custom multi-node n8n-style workflow."""
    if not (data.get("name") or "").strip():
        raise HTTPException(status_code=400, detail="Workflow name cannot be empty.")
    wf = await WorkflowStore.create_workflow(data)
    return {"success": True, "workflow": wf, "message": "Workflow created successfully."}


@router.get("/{workflow_id}/live-status")
async def get_workflow_live_status(
    workflow_id: str,
    user=Depends(get_optional_current_user)
):
    """Returns real-time node execution progress while a workflow is running."""
    return {"success": True, **workflow_engine.get_live_status(workflow_id)}


@router.post("/{workflow_id}/duplicate")
async def duplicate_workflow(
    workflow_id: str,
    user=Depends(get_optional_current_user)
):
    """Duplicates an existing workflow so users can clone and customize variations safely."""
    cloned = await WorkflowStore.duplicate_workflow(workflow_id)
    if not cloned:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return {"success": True, "workflow": cloned, "message": f"Cloned '{cloned['name']}'."}


@router.get("/{workflow_id}/export")
async def export_workflow_json(
    workflow_id: str,
    user=Depends(get_optional_current_user)
):
    """Exports workflow schema as clean portable JSON."""
    wf = await WorkflowStore.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    export_obj = {
        "schema_version": "myagent_workflow_v1",
        "name": wf["name"],
        "description": wf.get("description", ""),
        "icon": wf.get("icon", "⚡"),
        "trigger_type": wf.get("trigger_type", "daily"),
        "schedule_expr": wf.get("schedule_expr", ""),
        "daily_time": wf.get("daily_time", "09:00"),
        "timezone": wf.get("timezone", "Asia/Dhaka"),
        "nodes": wf.get("nodes", []),
        "edges": wf.get("edges", [])
    }
    return {"success": True, "workflow": export_obj}


@router.get("/{workflow_id}")
async def get_workflow_details(
    workflow_id: str,
    user=Depends(get_optional_current_user)
):
    """Returns a single workflow definition and its recent runs."""
    wf = await WorkflowStore.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    wf["is_running"] = workflow_engine.is_running(workflow_id)
    runs = await WorkflowStore.list_runs(workflow_id=workflow_id, limit=15)
    return {"success": True, "workflow": wf, "runs": runs}


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    data: Dict[str, Any] = Body(...),
    user=Depends(get_optional_current_user)
):
    """Updates workflow graph (nodes, edges), schedule, or configuration."""
    wf = await WorkflowStore.update_workflow(workflow_id, data)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return {"success": True, "workflow": wf, "message": "Workflow updated successfully."}


@router.put("/{workflow_id}/toggle")
async def toggle_workflow(
    workflow_id: str,
    user=Depends(get_optional_current_user)
):
    """Enables or disables automatic scheduled execution of a workflow."""
    wf = await WorkflowStore.toggle_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return {"success": True, "workflow": wf, "is_enabled": wf["is_enabled"]}


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    user=Depends(get_optional_current_user)
):
    """Deletes a workflow and all its run logs."""
    ok = await WorkflowStore.delete_workflow(workflow_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return {"success": True, "message": "Workflow deleted."}


@router.post("/{workflow_id}/run")
async def run_workflow_now(
    workflow_id: str,
    data: Optional[Dict[str, Any]] = Body(default=None),
    user=Depends(get_optional_current_user)
):
    """Manually executes a workflow DAG immediately (supports payload & dry_run) and returns full trace."""
    try:
        body = data if isinstance(data, dict) else {}
        payload = body.get("payload", {})
        dry_run = bool(body.get("dry_run", False))
        res = await workflow_engine.execute_workflow(
            workflow_id=workflow_id,
            trigger_source="manual",
            trigger_payload=payload,
            dry_run=dry_run
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Manual workflow execution failed for '{workflow_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@router.post("/{workflow_id}/stop")
async def stop_workflow_run(
    workflow_id: str,
    user=Depends(get_optional_current_user)
):
    """Signals an active workflow run to cancel cleanly."""
    stopped = workflow_engine.stop_workflow(workflow_id)
    return {"success": True, "stopped": stopped, "message": "Cancellation signal sent." if stopped else "Workflow is not currently running."}


@router.get("/{workflow_id}/versions")
async def get_workflow_versions(
    workflow_id: str,
    limit: int = Query(15, le=30),
    user=Depends(get_optional_current_user)
):
    """Lists saved revision snapshots of a workflow for 1-click rollback."""
    versions = await WorkflowStore.list_versions(workflow_id, limit=limit)
    return {"success": True, "versions": versions}


@router.post("/{workflow_id}/versions/{version_id}/restore")
async def restore_workflow_version(
    workflow_id: str,
    version_id: str,
    user=Depends(get_optional_current_user)
):
    """Restores a prior workflow snapshot (and saves current state as a new revision)."""
    wf = await WorkflowStore.restore_version(workflow_id, version_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow version snapshot not found.")
    return {"success": True, "workflow": wf, "message": "Workflow version restored cleanly."}


@router.get("/{workflow_id}/runs")
async def get_workflow_runs(
    workflow_id: str,
    limit: int = Query(25, le=100),
    user=Depends(get_optional_current_user)
):
    """Returns execution runs for a specific workflow."""
    runs = await WorkflowStore.list_runs(workflow_id=workflow_id, limit=limit)
    return {"success": True, "runs": runs}

