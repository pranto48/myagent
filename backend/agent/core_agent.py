# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.2.0
import os
import json
import logging
import asyncio
from typing import List, Dict, Any, AsyncGenerator, Optional
from openai import AsyncOpenAI, OpenAI
from config import settings
from memory.vector_store import VectorMemoryStore
from agent.prompts import SYSTEM_PROMPT_TEMPLATE, RAG_CONTEXT_WRAPPER
from agent.tools import AgentTools
from models.schemas import ChatMessage, SourceCitation
from security.firewall import PromptFirewall
from security.dlp import DLPEngine
from security.audit import SecurityAuditStore

logger = logging.getLogger("myagent.agent")

class CompanyAIAgent:
    """
    Enterprise Autonomous AI Agent with:
      - Super Fast Hybrid Vector & Keyword Retrieval (< 10ms)
      - Dynamic Open Source & MCP Tool Calling Execution
      - ReAct Pattern Fallback for Local LLM Models
      - Streaming Real-Time SSE Response Generation
    """

    def __init__(self):
        self.vector_store = VectorMemoryStore()
        self._init_llm_client()

    def _init_llm_client(self):
        """Initializes Async OpenAI client pointing to the target LLM server."""
        base_url = settings.LLM_BASE_URL.strip()
        if not base_url.endswith("/v1") and not "/v1/" in base_url:
            base_url = base_url.rstrip("/") + "/v1"

        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=settings.LLM_API_KEY or "not-needed",
            timeout=120.0
        )
        self.sync_client = OpenAI(
            base_url=base_url,
            api_key=settings.LLM_API_KEY or "not-needed",
            timeout=15.0
        )

    def refresh_client(self):
        """Re-initializes client after settings update."""
        self._init_llm_client()

    async def test_llm_connection(self) -> Dict[str, Any]:
        """Tests connectivity to the remote LLM server and checks available models."""
        try:
            loop = asyncio.get_event_loop()
            models_response = await loop.run_in_executor(
                None, lambda: self.sync_client.models.list()
            )
            model_names = [m.id for m in models_response.data] if hasattr(models_response, "data") else []
            return {
                "success": True,
                "message": f"Successfully connected to LLM server at {settings.LLM_BASE_URL}",
                "models_available": model_names,
                "active_model": settings.LLM_MODEL
            }
        except Exception as e:
            logger.warning(f"Connection test to LLM server failed: {e}")
            return {
                "success": False,
                "message": f"Could not connect to LLM server at {settings.LLM_BASE_URL}: {str(e)}",
                "models_available": [],
                "active_model": settings.LLM_MODEL
            }

    def _prepare_rag_context(self, prompt: str, user_role: str = "admin") -> tuple[str, List[SourceCitation]]:
        """Queries super-fast hybrid memory (< 10ms) and builds augmented prompt and citation list with DLS."""
        hits = self.vector_store.super_fast_search(query=prompt, top_k=settings.TOP_K_RESULTS, user_role=user_role)
        sources: List[SourceCitation] = []

        if not hits:
            return prompt, []

        context_blocks = []
        for i, hit in enumerate(hits, 1):
            source_file = hit.get("source", "Document")
            page_num = hit.get("page", 1)
            chunk_content = hit.get("content", "").strip()

            context_blocks.append(
                f"[Source #{i}: {source_file} (Page {page_num})]\n{chunk_content}"
            )
            sources.append(
                SourceCitation(
                    source=source_file,
                    chunk_id=hit.get("id", ""),
                    content=chunk_content[:200] + "..." if len(chunk_content) > 200 else chunk_content,
                    score=hit.get("score", 0.0),
                    page=page_num
                )
            )

        merged_context = "\n\n".join(context_blocks)
        augmented_prompt = RAG_CONTEXT_WRAPPER.format(
            context_chunks=merged_context,
            query=prompt
        )
        return augmented_prompt, sources

    async def stream_chat(
        self,
        prompt: str,
        history: List[ChatMessage],
        use_memory: bool = True,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
        username: str = "admin",
        user_role: str = "admin"
    ) -> AsyncGenerator[str, None]:
        """
        Executes agent reasoning with dynamic tool calling (local tools & MCP)
        enforcing Prompt Injection Firewall, DLP PII sanitization, and DLS.
        """
        audit_store = SecurityAuditStore()

        # 1. Prompt Firewall Check
        firewall_check = PromptFirewall.inspect_prompt(prompt)
        if firewall_check["blocked"]:
            await audit_store.log_event(
                action="PROMPT_INJECTION_BLOCKED",
                username=username,
                user_role=user_role,
                resource="chat",
                severity="CRITICAL",
                details={"threat_types": firewall_check["threat_types"], "reason": firewall_check["reason"]}
            )
            blocked_msg = "🛡️ [সিকিউরিটি সিস্টেম অ্যালার্ট]: আপনার ইনপুটে সম্ভাব্য প্রম্পট ইনজেকশন বা অননুমোদিত নির্দেশিকা সনাক্ত হওয়ায় ফায়ারওয়াল দ্বারা অনুরোধটি ব্লক করা হয়েছে।"
            yield f"data: {json.dumps({'type': 'token', 'token': blocked_msg})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        # 2. Inbound DLP Sanitization
        dlp_res = DLPEngine.inspect_text(prompt)
        if dlp_res["redacted_count"] > 0:
            await audit_store.log_event(
                action="DLP_TRIGGERED",
                username=username,
                user_role=user_role,
                resource="chat_prompt",
                severity="WARNING",
                details={"redacted_count": dlp_res["redacted_count"], "types": [f["type"] for f in dlp_res["findings"]]}
            )
            prompt = dlp_res["sanitized_text"]

        target_model = model or settings.LLM_MODEL
        target_temp = temperature if temperature is not None else settings.AGENT_TEMPERATURE

        sources: List[SourceCitation] = []
        user_content = prompt

        if use_memory:
            user_content, sources = self._prepare_rag_context(prompt, user_role=user_role)

        # 3. Send sources metadata first
        sources_payload = [s.model_dump() for s in sources]
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources_payload})}\n\n"

        # 2. Build conversation payload
        system_content = SYSTEM_PROMPT_TEMPLATE.format(agent_name=settings.AGENT_NAME)
        # Add tool usage instructions into system prompt for models without native function calling
        system_content += "\n\nAVAILABLE TOOLS: You have access to built-in tools (query_company_memory, web_search, web_scrape, python_runner, analyze_big_data, generate_data_report, read_pdf_document, read_word_document, read_excel_spreadsheet, read_image_ocr, fs_list_files, sqlite_query, system_info) and any connected MCP tools. You may call them using tool_calls or structured text: Action: <tool_name>\nAction Input: <json_arguments>"

        messages = [{"role": "system", "content": system_content}]

        # Add recent conversation history (limit to last 8 turns)
        for msg in history[-8:]:
            messages.append({"role": msg.role, "content": msg.content})

        # Add current user prompt (with RAG context if applicable)
        messages.append({"role": "user", "content": user_content})

        tools_schema = await AgentTools.get_all_tools_schema()

        # Tool calling loop (up to 3 tool turns)
        max_tool_turns = 3
        for turn in range(max_tool_turns):
            try:
                # First attempt with tools parameter
                stream = await self.client.chat.completions.create(
                    model=target_model,
                    messages=messages,
                    temperature=target_temp,
                    tools=tools_schema,
                    tool_choice="auto",
                    stream=True
                )
            except Exception as tool_call_err:
                # If model doesn't support tools parameter, fallback to plain stream
                logger.info(f"Model {target_model} does not support native function calling, falling back: {tool_call_err}")
                try:
                    stream = await self.client.chat.completions.create(
                        model=target_model,
                        messages=messages,
                        temperature=target_temp,
                        stream=True
                    )
                except Exception as plain_err:
                    logger.error(f"Error during LLM chat streaming: {plain_err}")
                    yield f"data: {json.dumps({'type': 'error', 'error': f'LLM Server Error: {str(plain_err)}'})}\n\n"
                    return

            tool_calls_detected = []
            current_tool_call = {"id": "", "name": "", "arguments": ""}
            full_assistant_message = ""

            try:
                async for chunk in stream:
                    if not chunk.choices or len(chunk.choices) == 0:
                        continue
                    delta = chunk.choices[0].delta

                    # Handle native OpenAI tool calling
                    if hasattr(delta, "tool_calls") and delta.tool_calls:
                        for tc in delta.tool_calls:
                            if tc.id:
                                current_tool_call["id"] = tc.id
                            if tc.function and tc.function.name:
                                current_tool_call["name"] += tc.function.name
                            if tc.function and tc.function.arguments:
                                current_tool_call["arguments"] += tc.function.arguments

                    # Regular token delta
                    if delta and delta.content:
                        token = delta.content
                        full_assistant_message += token
                        token_payload = json.dumps({"type": "token", "token": token})
                        yield f"data: {token_payload}\n\n"

                # Check if native tool was invoked
                if current_tool_call["name"]:
                    tool_calls_detected.append(current_tool_call)

                # ReAct fallback check in text output (e.g. Action: web_search \n Action Input: {...})
                if not tool_calls_detected and "Action:" in full_assistant_message and "Action Input:" in full_assistant_message:
                    try:
                        lines = full_assistant_message.splitlines()
                        act_name = ""
                        act_input_str = ""
                        for line in lines:
                            if line.strip().startswith("Action:"):
                                act_name = line.replace("Action:", "").strip()
                            elif line.strip().startswith("Action Input:"):
                                act_input_str = line.replace("Action Input:", "").strip()
                        if act_name:
                            tool_calls_detected.append({
                                "id": f"call_react_{turn}",
                                "name": act_name,
                                "arguments": act_input_str or "{}"
                            })
                    except Exception as pe:
                        logger.debug(f"ReAct parse notice: {pe}")

                # If no tools called, we are done
                if not tool_calls_detected:
                    yield f"data: {json.dumps({'type': 'done', 'model': target_model})}\n\n"
                    return

                # Execute discovered tools
                for tc in tool_calls_detected:
                    fn_name = tc["name"]
                    try:
                        fn_args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                    except Exception:
                        fn_args = {"query": tc["arguments"]} if "search" in fn_name else {}

                    # Notify frontend that tool execution started
                    tool_call_payload = json.dumps({
                        "type": "tool_call",
                        "name": fn_name,
                        "args": fn_args
                    })
                    yield f"data: {tool_call_payload}\n\n"

                    # Execute tool locally or via MCP
                    tool_output = await AgentTools.dispatch_tool(fn_name, fn_args)

                    # Notify frontend of tool output
                    tool_res_payload = json.dumps({
                        "type": "tool_result",
                        "name": fn_name,
                        "result": tool_output[:1200] if len(tool_output) > 1200 else tool_output
                    })
                    yield f"data: {tool_res_payload}\n\n"

                    # Append to conversation messages for next LLM iteration
                    messages.append({
                        "role": "assistant",
                        "content": f"[Invoked tool {fn_name} with arguments: {json.dumps(fn_args)}]"
                    })
                    messages.append({
                        "role": "user",
                        "content": f"[Tool Observation from {fn_name}]:\n{tool_output}\n\nPlease synthesize this tool observation and continue answering the user's question."
                    })

            except Exception as e:
                logger.error(f"Error during LLM stream processing: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': f'Communication Error: {str(e)}'})}\n\n"
                return

        # End of turns
        yield f"data: {json.dumps({'type': 'done', 'model': target_model})}\n\n"

    async def generate_response(
        self,
        prompt: str,
        history: List[ChatMessage],
        use_memory: bool = True,
        temperature: Optional[float] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Non-streaming generation for API consumers."""
        target_model = model or settings.LLM_MODEL
        target_temp = temperature if temperature is not None else settings.AGENT_TEMPERATURE

        sources: List[SourceCitation] = []
        user_content = prompt

        if use_memory:
            user_content, sources = self._prepare_rag_context(prompt)

        system_content = SYSTEM_PROMPT_TEMPLATE.format(agent_name=settings.AGENT_NAME)
        messages = [{"role": "system", "content": system_content}]

        for msg in history[-8:]:
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": user_content})

        response = await self.client.chat.completions.create(
            model=target_model,
            messages=messages,
            temperature=target_temp
        )

        reply_text = response.choices[0].message.content if response.choices else ""
        return {
            "reply": reply_text,
            "sources": [s.model_dump() for s in sources],
            "model_used": target_model
        }
