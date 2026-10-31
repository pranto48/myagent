# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 3.2.0
# Autonomous Work Agent & Sub-Agent Swarm Orchestration Engine
# ==============================================================================

import os
import re
import time
import json
import uuid
import logging
import asyncio
import aiosqlite
from typing import List, Dict, Any, Optional
from config import settings
from agent.subagents.ping_agent import NetworkPingSubAgent
from agent.openrouter_client import OpenRouterService

logger = logging.getLogger("myagent.work_engine")

def get_db_path() -> str:
    if os.name == 'nt' or not os.path.exists(settings.DATA_DIR):
        return os.path.join("./data", "ops.db")
    return os.path.join(settings.DATA_DIR, "ops.db")

class SubAgentWorkEngine:
    """
    Autonomous multi-agent orchestration engine that coordinates work between
    the Master Work Agent and specialized Sub-Agents.
    """

    SUBAGENT_SYSTEM_PROMPTS = {
        "net_ping_subagent": (
            "You are the Network Telemetry & Ping Sentinel Sub-Agent. "
            "You diagnose intranet/extranet latency, packet loss, socket reachability, and network anomalies from the agent host IP (192.168.9.9). "
            "Provide concise, actionable network diagnostics in Bengali."
        ),
        "task_planner_agent": (
            "You are the Autonomous Task Planner & DAG Swarm Orchestrator Sub-Agent. "
            "You decompose complex enterprise work into atomic stages, calculate execution priorities, and orchestrate subagent workflows. "
            "Always structure execution plans clearly in Bengali."
        ),
        "memory_synthesizer_agent": (
            "You are the Persistent RAG & Knowledge Synthesizer Sub-Agent. "
            "You retrieve company records, vector memory chunks, synthesize facts, and distill intelligence graphs. "
            "Provide insightful, fact-grounded knowledge digests in Bengali."
        ),
        "security_auditor_agent": (
            "You are the Security, DLP & Compliance Sentinel Sub-Agent. "
            "You scan systems and user prompts for API credential leaks, PII breaches, prompt injection, and OWASP compliance vulnerabilities. "
            "Deliver uncompromising security assessments in Bengali."
        ),
        "devops_fleet_agent": (
            "You are the Docker Fleet & Systems Infrastructure Sub-Agent. "
            "You inspect container runtimes, port mappings, volume mounts, disk capacity, and service health across node servers. "
            "Provide precise Linux and Docker telemetry in Bengali."
        ),
        "executive_briefing_agent": (
            "You are the Executive Intelligence Digest Sub-Agent. "
            "You synthesize technical telemetry, multi-agent findings, and system metrics into polished, executive markdown briefings with key takeaways."
        )
    }

    @classmethod
    async def get_all_subagents(cls) -> List[Dict[str, Any]]:
        """Fetches all registered subagents from ops.db."""
        db_path = get_db_path()
        if not os.path.exists(db_path):
            return []
        
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM ops_subagents ORDER BY created_at ASC") as cursor:
                rows = await cursor.fetchall()
                result = []
                for r in rows:
                    d = dict(r)
                    try:
                        d["assigned_skills"] = json.loads(d.get("assigned_skills", "[]"))
                    except Exception:
                        d["assigned_skills"] = []
                    try:
                        d["metrics"] = json.loads(d.get("metrics_json", "{}"))
                    except Exception:
                        d["metrics"] = {}
                    result.append(d)
                return result

    @classmethod
    async def execute_subagent_task(
        cls,
        agent_id: str,
        task_instruction: str,
        model_override: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes a dedicated task on a specialized subagent, invoking relevant tools
        and returning full execution logs, latency, and synthesized output.
        """
        start_time = time.time()
        subagents = await cls.get_all_subagents()
        agent_info = next((s for s in subagents if s["id"] == agent_id), None)
        if not agent_info:
            return {
                "success": False,
                "agent_id": agent_id,
                "error": f"Subagent '{agent_id}' not found."
            }

        agent_name = agent_info.get("name", agent_id)
        target_model = model_override or agent_info.get("model") or settings.LLM_MODEL
        specialized_tool_data = None
        tool_log_message = ""

        # 1. Specialized Deterministic Tool Execution per Agent Type
        if agent_id == "net_ping_subagent":
            # Extract target IP or run batch ping
            ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', task_instruction)
            if ip_match:
                target_ip = ip_match.group(0)
                ping_type = "tcp" if "tcp" in task_instruction.lower() or "port" in task_instruction.lower() else "icmp"
                port = 80
                port_match = re.search(r'port\s+(\d+)', task_instruction.lower())
                if port_match:
                    port = int(port_match.group(1))
                specialized_tool_data = await NetworkPingSubAgent.ping_target(
                    target=target_ip,
                    ping_type=ping_type,
                    port=port,
                    count=3
                )
                tool_log_message = f"Pinged {target_ip} via {ping_type.upper()} - Latency: {specialized_tool_data.get('latency_ms')} ms ({specialized_tool_data.get('status')})"
            else:
                # Default to fleet ping
                specialized_tool_data = await NetworkPingSubAgent.batch_ping()
                tool_log_message = f"Fleet Batch Ping completed: {specialized_tool_data.get('healthy_count')}/{specialized_tool_data.get('total_tested')} nodes online."

        elif agent_id == "devops_fleet_agent":
            # Inspect system & docker status
            from agent.tools import AgentTools
            sys_info = AgentTools.system_info()
            specialized_tool_data = {
                "system_telemetry": sys_info,
                "node_ip": "192.168.9.9",
                "target_platform": "Docker Swarm / Linux Container"
            }
            tool_log_message = "Docker fleet and container resource telemetry sampled."

        elif agent_id == "security_auditor_agent":
            from security.dlp import DLPEngine
            from security.firewall import PromptFirewall
            dlp_scan = DLPEngine.inspect_text(task_instruction)
            fw_scan = PromptFirewall.inspect_prompt(task_instruction)
            specialized_tool_data = {
                "dlp_findings": dlp_scan,
                "firewall_evaluation": fw_scan,
                "compliance_status": "SECURE" if not fw_scan["blocked"] else "ALERT"
            }
            tool_log_message = f"DLP & prompt security audit completed. Redacted items: {dlp_scan['redacted_count']}."

        elif agent_id == "memory_synthesizer_agent":
            from memory.vector_store import VectorMemoryStore
            vs = VectorMemoryStore()
            query_text = task_instruction
            search_results = vs.similarity_search(query_text, top_k=3)
            specialized_tool_data = {
                "matched_chunks": len(search_results),
                "snippets": [
                    {"content": doc.page_content[:200], "source": doc.metadata.get("source", "Memory")}
                    for doc in search_results
                ]
            }
            tool_log_message = f"Retrieved {len(search_results)} relevant knowledge memory chunks."

        # 2. LLM Synthesis using Subagent Persona & Model
        system_prompt = cls.SUBAGENT_SYSTEM_PROMPTS.get(
            agent_id,
            f"You are subagent '{agent_name}'. Assist with precision and deliver your structured response in Bengali."
        )

        user_prompt_content = f"Task: {task_instruction}\n"
        if specialized_tool_data:
            user_prompt_content += f"\nObserved Real-time Telemetry / Tool Findings:\n{json.dumps(specialized_tool_data, indent=2, ensure_ascii=False)}\n"
        if context:
            user_prompt_content += f"\nContext:\n{json.dumps(context, indent=2, ensure_ascii=False)}\n"

        user_prompt_content += "\nProvide a clear, expert summary of your analysis, findings, and recommended next steps."

        synthesis_reply = ""
        model_used = target_model
        try:
            # Check if OpenRouter model
            if "/" in target_model or getattr(settings, "LLM_PROVIDER", "default") == "openrouter":
                if OpenRouterService.is_configured():
                    client = OpenRouterService.get_client()
                    model_to_call = target_model.replace("openrouter/", "")
                    resp = await client.chat.completions.create(
                        model=model_to_call,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt_content}
                        ],
                        temperature=0.2,
                        max_tokens=1024
                    )
                    synthesis_reply = resp.choices[0].message.content if resp.choices else ""
                    model_used = f"openrouter/{model_to_call}"
                else:
                    # Fallback to local
                    from agent.core_agent import get_shared_agent
                    agent = get_shared_agent()
                    resp = await agent.client.chat.completions.create(
                        model=settings.LLM_MODEL,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt_content}
                        ],
                        temperature=0.2,
                        max_tokens=1024
                    )
                    synthesis_reply = resp.choices[0].message.content if resp.choices else ""
                    model_used = f"{settings.LLM_MODEL} (fallback)"
            else:
                from agent.core_agent import get_shared_agent
                agent = get_shared_agent()
                resp = await agent.client.chat.completions.create(
                    model=target_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt_content}
                    ],
                    temperature=0.2,
                    max_tokens=1024
                )
                synthesis_reply = resp.choices[0].message.content if resp.choices else ""
        except Exception as e:
            logger.warning(f"Subagent LLM call error: {e}")
            synthesis_reply = f"টাস্ক সম্পাদন সম্পন্ন হয়েছে। পরিমাপকৃত ডাটা:\n{json.dumps(specialized_tool_data or {}, indent=2, ensure_ascii=False)}"

        elapsed_ms = round((time.time() - start_time) * 1000, 1)

        # 3. Update Subagent Execution Metric in ops.db
        try:
            db_path = get_db_path()
            if os.path.exists(db_path):
                async with aiosqlite.connect(db_path) as db:
                    metrics = agent_info.get("metrics", {})
                    metrics["tasks_run"] = metrics.get("tasks_run", 0) + 1
                    metrics["last_run_ms"] = elapsed_ms
                    metrics["last_active"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    await db.execute(
                        "UPDATE ops_subagents SET metrics_json = ?, status = 'ONLINE' WHERE id = ?",
                        (json.dumps(metrics), agent_id)
                    )
                    await db.commit()
        except Exception as e:
            pass

        return {
            "success": True,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "icon": agent_info.get("icon", "🤖"),
            "model_used": model_used,
            "execution_time_ms": elapsed_ms,
            "tool_summary": tool_log_message,
            "tool_data": specialized_tool_data,
            "output": synthesis_reply
        }

    @classmethod
    async def orchestrate_swarm_mission(
        cls,
        goal: str,
        selected_agents: Optional[List[str]] = None,
        model_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Coordinates an autonomous multi-subagent swarm mission:
        1. Analyzes and decomposes user goal into atomic sub-missions.
        2. Assigns subtasks to the most qualified Sub-Agents.
        3. Executes subagents in sequence/parallel.
        4. Synthesizes a unified Executive Briefing Report.
        """
        mission_id = f"mission_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        logger.info(f"Starting Swarm Mission [{mission_id}] for goal: {goal}")

        all_agents = await cls.get_all_subagents()
        available_ids = [a["id"] for a in all_agents if a.get("is_enabled", 1) == 1]

        # Determine participant agents
        if not selected_agents or "auto" in selected_agents:
            goal_lower = goal.lower()
            chosen = []
            if any(k in goal_lower for k in ["ping", "network", "latency", "ip", "connection", "connect", "router", "host"]):
                chosen.append("net_ping_subagent")
            if any(k in goal_lower for k in ["docker", "container", "system", "ram", "cpu", "disk", "service", "infra"]):
                chosen.append("devops_fleet_agent")
            if any(k in goal_lower for k in ["security", "token", "password", "leak", "firewall", "vuln", "compliance"]):
                chosen.append("security_auditor_agent")
            if any(k in goal_lower for k in ["memory", "document", "knowledge", "doc", "data", "search", "rag"]):
                chosen.append("memory_synthesizer_agent")
            
            # Always include task planner or briefing agent for synthesis
            if not chosen:
                chosen = ["task_planner_agent", "net_ping_subagent", "devops_fleet_agent"]
            chosen.append("executive_briefing_agent")
            # Deduplicate preserving order
            participants = [a for a in chosen if a in available_ids]
        else:
            participants = [a for a in selected_agents if a in available_ids]

        stages = []
        context_accumulator = {}

        # Execute subagents in pipeline
        for agent_id in participants:
            if agent_id == "executive_briefing_agent":
                continue # Run briefing at the end
            
            stage_instruction = f"Goal Context: {goal}. Analyze and perform your domain operations."
            step_res = await cls.execute_subagent_task(
                agent_id=agent_id,
                task_instruction=stage_instruction,
                model_override=model_override,
                context=context_accumulator
            )
            stages.append(step_res)
            context_accumulator[agent_id] = {
                "summary": step_res.get("tool_summary"),
                "findings": step_res.get("output")
            }

        # Final Synthesis by Executive Briefing Sub-Agent
        briefing_prompt = (
            f"Consolidate the multi-agent findings for Master Goal: '{goal}'.\n"
            f"Participating Agents: {', '.join(participants)}.\n"
            f"Subagent Findings Summary:\n{json.dumps(context_accumulator, indent=2, ensure_ascii=False)}\n\n"
            f"Format your response as a professional Executive Briefing with:\n"
            f"1. 🎯 মূল উদ্দেশ্য ও সারসংক্ষেপ (Executive Summary)\n"
            f"2. 🔍 সাব-এজেন্টদের লাইভ ডায়াগনস্টিক রিপোর্ট (Agent Findings Breakdown)\n"
            f"3. 🚀 প্রস্তাবিত পদক্ষেপ ও সুপারিশ (Actionable Next Steps)"
        )

        briefing_res = await cls.execute_subagent_task(
            agent_id="executive_briefing_agent",
            task_instruction=briefing_prompt,
            model_override=model_override
        )
        stages.append(briefing_res)

        total_time_ms = round((time.time() - start_time) * 1000, 1)

        return {
            "success": True,
            "mission_id": mission_id,
            "goal": goal,
            "total_duration_ms": total_time_ms,
            "agents_engaged": participants,
            "stages": stages,
            "executive_summary": briefing_res.get("output", ""),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
