import os
import json
import logging
import asyncio
from typing import List, Dict, Any, AsyncGenerator, Optional
from openai import AsyncOpenAI, OpenAI
from config import settings
from memory.vector_store import VectorMemoryStore
from agent.prompts import SYSTEM_PROMPT_TEMPLATE, RAG_CONTEXT_WRAPPER
from models.schemas import ChatMessage, SourceCitation

logger = logging.getLogger("myagent.agent")

class CompanyAIAgent:
    """Enterprise AI Agent for querying company knowledge and orchestrating LLM calls."""

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

    def _prepare_rag_context(self, prompt: str) -> tuple[str, List[SourceCitation]]:
        """Queries memory and builds augmented prompt and citation list."""
        hits = self.vector_store.search_memory(query=prompt, top_k=settings.TOP_K_RESULTS)
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
        model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Executes agent reasoning and streams response as SSE formatted strings.
        """
        target_model = model or settings.LLM_MODEL
        target_temp = temperature if temperature is not None else settings.AGENT_TEMPERATURE

        sources: List[SourceCitation] = []
        user_content = prompt

        if use_memory:
            user_content, sources = self._prepare_rag_context(prompt)

        # 1. Send sources metadata first
        sources_payload = [s.model_dump() for s in sources]
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources_payload})}\n\n"

        # 2. Build conversation payload
        system_content = SYSTEM_PROMPT_TEMPLATE.format(agent_name=settings.AGENT_NAME)
        messages = [{"role": "system", "content": system_content}]

        # Add recent conversation history (limit to last 8 turns)
        for msg in history[-8:]:
            messages.append({"role": msg.role, "content": msg.content})

        # Add current user prompt (with RAG context if applicable)
        messages.append({"role": "user", "content": user_content})

        try:
            stream = await self.client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=target_temp,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        token_payload = json.dumps({"type": "token", "token": delta.content})
                        yield f"data: {token_payload}\n\n"

            # 3. Send done event
            yield f"data: {json.dumps({'type': 'done', 'model': target_model})}\n\n"

        except Exception as e:
            logger.error(f"Error during LLM chat streaming: {e}")
            error_payload = json.dumps({
                "type": "error",
                "error": f"LLM Server Communication Error: {str(e)}. Please check if your LLM server ({settings.LLM_BASE_URL}) is reachable and model '{target_model}' is loaded."
            })
            yield f"data: {error_payload}\n\n"

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
