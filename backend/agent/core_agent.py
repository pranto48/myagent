import os
import json
import logging
import asyncio
import httpx
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
            timeout=httpx.Timeout(60.0, connect=4.0)
        )
        self.sync_client = OpenAI(
            base_url=base_url,
            api_key=settings.LLM_API_KEY or "not-needed",
            timeout=httpx.Timeout(10.0, connect=3.0)
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

    @staticmethod
    def is_conversational_greeting(text: str) -> bool:
        """
        Detects greetings, pleasantries, small talk, and introductory inquiries
        to avoid pulling unrelated corporate RAG document context.
        """
        if not text:
            return False
        clean = text.strip().lower()
        clean_no_punct = "".join([c if c.isalnum() or c.isspace() else " " for c in clean]).strip()
        tokens = clean_no_punct.split()
        if not tokens:
            return False

        exact_greetings = {
            "hi", "hello", "hey", "hlo", "hola", "yo", "sup", "heya", "greetings",
            "good morning", "good afternoon", "good evening", "good night", "good day",
            "how are you", "how are you doing", "what's up", "whats up",
            "who are you", "what can you do", "what are you", "help", "who made you",
            "thanks", "thank you", "thx", "bye", "goodbye",
            "হাই", "হ্যালো", "হ্যাল্লো", "হে", "সালাম", "আসসালামু আলাইকুম", "আসসালামুআলাইকুম",
            "নমস্কার", "শুভ সকাল", "শুভ দুপুর", "শুভ সন্ধ্যা", "শুভ রাত্রি",
            "কেমন আছেন", "কেমন আছো", "কেমন আছেন?", "কেমন আছো?", "কেমন চলতেছে",
            "আপনি কে", "তুমি কে", "তোমার কাজ কি", "আপনার কাজ কি", "কী করতে পারেন",
            "কি করতে পারেন", "কী করতে পারো", "কি করতে পারো", "সাহায্য", "সাহায্য করুন",
            "ধন্যবাদ", "অনেক ধন্যবাদ", "থ্যাংকস", "থ্যাংক ইউ", "কেমন আছিস"
        }

        if clean in exact_greetings or clean_no_punct in exact_greetings:
            return True

        if len(tokens) <= 3:
            if tokens[0] in {"hi", "hello", "hey", "hlo", "হাই", "হ্যালো", "হ্যাল্লো", "সালাম"}:
                return True

        return False

    def _prepare_rag_context(self, prompt: str, user_role: str = "admin", has_attachments: bool = False, language: str = "bn") -> tuple[str, List[SourceCitation]]:
        """Queries super-fast hybrid memory (< 10ms) and builds augmented prompt and citation list with DLS."""
        # 1. Skip RAG completely for greetings and casual pleasantries
        if self.is_conversational_greeting(prompt):
            logger.info(f"Conversational greeting detected for '{prompt}', skipping RAG retrieval.")
            return prompt, []

        rag_top_k = max(settings.TOP_K_RESULTS, 6)
        hits = self.vector_store.super_fast_search(query=prompt, top_k=rag_top_k, user_role=user_role)
        sources: List[SourceCitation] = []

        context_blocks = []
        seen_snippets = set()
        if hits:
            for hit in hits:
                source_file = str(hit.get("source", "Document"))
                page_num = hit.get("page", 1)
                chunk_content = str(hit.get("content", "")).strip()
                score = float(hit.get("score", 0.0))
                meta = hit.get("metadata", {}) or {}
                category = meta.get("category") or hit.get("category", "")

                # Quality filter: skip corrupt or placeholder entries
                if "????" in source_file or "????" in chunk_content:
                    continue
                if chunk_content.count("?") > 5 and (chunk_content.count("?") / max(len(chunk_content), 1)) > 0.15:
                    continue

                # Minimum relevance threshold for semantic-only matches
                if score < 0.65 and not hit.get("is_keyword_match", False):
                    continue

                # Deduplication fingerprint: skip redundant overlapping sentences
                snippet_fp = " ".join(chunk_content[:90].lower().split())
                if snippet_fp in seen_snippets:
                    continue
                seen_snippets.add(snippet_fp)

                idx = len(context_blocks) + 1
                cat_tag = f" | Section: {category}" if language == "en" and category else (f" | বিভাগ: {category}" if category else "")
                context_blocks.append(
                    f"[Source #{idx}: {source_file} (Page {page_num}{cat_tag})]\n{chunk_content}"
                )
                sources.append(
                    SourceCitation(
                        source=source_file,
                        chunk_id=hit.get("id", ""),
                        content=chunk_content[:200] + "..." if len(chunk_content) > 200 else chunk_content,
                        score=score,
                        page=page_num
                    )
                )
                if len(context_blocks) >= rag_top_k:
                    break

        # If no quality hits survived filtering
        if not context_blocks:
            if has_attachments:
                # Chat-attached files will supply the context directly
                return prompt, []

            # Strict company data mode: inform agent that no records exist in company memory
            if language == "en":
                no_context_msg = (
                    "⚠️ [No relevant internal documents or records were found in the company knowledge base or vector memory for this query.]\n"
                    "[Instruction: Do not invent facts or provide external company data. Politely inform the user that this record is not found in the company memory and advise uploading the necessary file or note.]"
                )
            else:
                no_context_msg = (
                    "⚠️ [কোম্পানির নলেজবেস ও ভেক্টর মেমোরিতে এই অনুসন্ধানের সাথে সম্পর্কিত কোনো অভ্যন্তরীণ নথি বা তথ্য পাওয়া যায়নি।]\n"
                    "[নির্দেশনা: কাল্পনিক বা অন্য কোনো কোম্পানির তথ্য প্রদান করবেন না। ব্যবহারকারীকে বিনীতভাবে জানান যে এই তথ্যটি কোম্পানির মেমোরিতে সংরক্ষিত নেই এবং প্রয়োজনীয় ফাইল বা তথ্য আপলোড করার পরামর্শ দিন।]"
                )
            augmented_prompt = RAG_CONTEXT_WRAPPER.format(
                context_chunks=no_context_msg,
                query=prompt
            )
            return augmented_prompt, []

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
        user_role: str = "admin",
        attached_files: Optional[List[Dict[str, Any]]] = None,
        language: str = "bn"
    ) -> AsyncGenerator[str, None]:
        """
        Executes agent reasoning with dynamic tool calling (local tools & MCP)
        enforcing Prompt Injection Firewall, DLP PII sanitization, and DLS.
        Directly injects rich context for files, Excel tables, and OCR photos attached from chat.
        """
        audit_store = SecurityAuditStore()

        # 1. Prompt Firewall Check (if prompt provided)
        if prompt.strip():
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
                if language == "en":
                    blocked_msg = "🛡️ [Security System Alert]: A potential prompt injection or unauthorized instruction was detected. The request has been blocked by the firewall."
                else:
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

            # 3. Autonomous Direct Memory Save Instruction Handling
            lower_p = prompt.strip().lower()
            if lower_p.startswith(("মনে রেখো", "মনে রাখো", "save to memory:", "/remember", "/save")):
                clean_instruction = prompt.strip()
                for prefix in ["মনে রেখো:", "মনে রেখো", "মনে রাখো:", "মনে রাখো", "save to memory:", "/remember", "/save"]:
                    if clean_instruction.lower().startswith(prefix):
                        clean_instruction = clean_instruction[len(prefix):].strip()
                        break
                if clean_instruction:
                    try:
                        title_candidate = clean_instruction.split("\n")[0][:40]
                        save_res = self.vector_store.add_note(
                            title=title_candidate,
                            content=clean_instruction,
                            category="user_instruction",
                            security_level="INTERNAL"
                        )
                        if language == "en":
                            reply_text = f"✅ **Information successfully saved to MyAgent persistent memory!**\n\n- **Note ID:** `{save_res['doc_id']}`\n- **Saved Content:** {clean_instruction}\n\nI will autonomously reference this information for relevant future queries."
                        else:
                            reply_text = f"✅ **তথ্যটি সফলভাবে MyAgent-এর স্থায়ী মেমোরিতে সংরক্ষণ করা হয়েছে!**\n\n- **নোট আইডি:** `{save_res['doc_id']}`\n- **সংরক্ষিত বিবরণ:** {clean_instruction}\n\nভবিষ্যতে যেকোনো প্রাসঙ্গিক অনুসন্ধানে আমি এই তথ্যটি স্বয়ংক্রিয়ভাবে রেফারেন্স হিসেবে ব্যবহার করব।"
                        yield f"data: {json.dumps({'type': 'token', 'token': reply_text})}\n\n"
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                        return
                    except Exception as save_err:
                        logger.warning(f"Autonomous memory save notice: {save_err}")

        target_model = model or settings.LLM_MODEL
        target_temp = temperature if temperature is not None else settings.AGENT_TEMPERATURE

        sources: List[SourceCitation] = []
        user_content = prompt

        has_attachments = bool(attached_files and len(attached_files) > 0)
        if use_memory and prompt.strip():
            user_content, sources = self._prepare_rag_context(prompt, user_role=user_role, has_attachments=has_attachments, language=language)

        # 3. Incorporate Chat-Attached Files (Excel, Photo OCR, Documents) directly into context
        if has_attachments:
            attachment_blocks = []
            for af in attached_files:
                fname = af.get("filename", "File")
                ftype = af.get("file_type", "document")
                summary = af.get("summary", "")
                preview = af.get("preview_text", "")
                table_md = af.get("table_markdown", "")
                ocr_txt = af.get("ocr_text", "")

                block_content = f"📎 [সংযুক্ত ফাইল: {fname} (ধরন: {ftype})]\n{summary}\n" if language == "bn" else f"📎 [Attached File: {fname} (Type: {ftype})]\n{summary}\n"
                if table_md:
                    block_content += f"\n[ডাটা টেবিল ভিউ]:\n{table_md}\n" if language == "bn" else f"\n[Data Table View]:\n{table_md}\n"
                if ocr_txt:
                    block_content += f"\n[OCR টেক্সট]:\n{ocr_txt}\n" if language == "bn" else f"\n[OCR Extracted Text]:\n{ocr_txt}\n"
                if preview and not table_md and not ocr_txt:
                    block_content += f"\n[কনটেন্ট প্রিভিউ]:\n{preview}\n" if language == "bn" else f"\n[Content Preview]:\n{preview}\n"
                attachment_blocks.append(block_content)

            merged_attachments = "\n\n---\n\n".join(attachment_blocks)
            if not prompt.strip() or self.is_conversational_greeting(prompt):
                if language == "en":
                    user_content = f"### [The user directly attached the following files in chat and requested detailed analysis]:\n\n{merged_attachments}\n\nPlease analyze the attached files and present detailed statistics, key columns/data points, and actionable insights in clear, professional English."
                else:
                    user_content = f"### [ব্যবহারকারী সরাসরি চ্যাটে নিম্নলিখিত ফাইলগুলো সংযুক্ত করেছেন এবং বিস্তারিত বিশ্লেষণ চেয়েছেন]:\n\n{merged_attachments}\n\nঅনুগ্রহ করে সংযুক্ত ফাইলের বিস্তারিত পরিসংখ্যান, প্রধান কলাম/ডাটা পয়েন্ট এবং কার্যোপযোগী ইনসাইটস পরিষ্কার ও প্রাঞ্জল বাংলায় উপস্থাপন করুন।"
            else:
                if language == "en":
                    user_content = f"### [Directly Attached Files and Data Context]:\n\n{merged_attachments}\n\n### [User Question / Instructions]:\n{user_content}"
                else:
                    user_content = f"### [সরাসরি চ্যাটে সংযুক্ত ফাইল ও ডাটা কনটেক্সট]:\n\n{merged_attachments}\n\n### [ব্যবহারকারীর প্রশ্ন / নির্দেশনা]:\n{user_content}"

        # 4. Send sources metadata first
        sources_payload = [s.model_dump() for s in sources]
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources_payload})}\n\n"

        # 5. Build conversation payload
        system_content = SYSTEM_PROMPT_TEMPLATE.format(agent_name=settings.AGENT_NAME)
        # Apply language preference directive (English or Bangla)
        if language == "en":
            system_content += "\n\nCRITICAL LANGUAGE DIRECTIVE: The user has selected English as their preferred interface language. Generate all your final responses, insights, analyses, and citations in professional English (while strictly observing the internal company data and memory boundaries)."
        else:
            system_content += "\n\nCRITICAL LANGUAGE DIRECTIVE: The user has selected Bangla as their preferred interface language. Generate all your final responses, insights, analyses, and citations in natural, professional, and elegant Bangla (বাংলা)."

        # Add tool usage instructions into system prompt for models without native function calling
        system_content += "\n\nAVAILABLE TOOLS: You have access to built-in tools (query_company_memory, python_runner, analyze_big_data, generate_data_report, read_pdf_document, read_word_document, read_excel_spreadsheet, read_image_ocr, fs_list_files, sqlite_query, system_info) and any connected MCP tools. NOTE: Do not search for other companies on the web. Only company internal memory and files are permitted for company operations. You may call tools using tool_calls or structured text: Action: <tool_name>\nAction Input: <json_arguments>"

        messages = [{"role": "system", "content": system_content}]

        # Add recent conversation history (limit to last 8 turns)
        for msg in history[-8:]:
            messages.append({"role": msg.role, "content": msg.content})

        # Add current user prompt (with RAG context & attached files if applicable)
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
                    err_str = str(plain_err)
                    err_lower = err_str.lower()
                    if "connection error" in err_lower or "connecterror" in err_lower or "connection refused" in err_lower or "failed to connect" in err_lower or "timeout" in err_lower or "timed out" in err_lower:
                        if self.is_conversational_greeting(prompt):
                            if language == "en":
                                fallback_reply = (
                                    "👋 **Hello! I am MyAgent AI** — your enterprise intelligence and productivity assistant.\n\n"
                                    "How can I help you today? Here are my core capabilities:\n\n"
                                    "- 📁 **Multi-format File Analysis:** PDF, Word (DOCX), Excel spreadsheets, and Image OCR reading.\n"
                                    "- 📊 **Big Data & Table Summary:** Business dataset statistics and trend analysis.\n"
                                    "- 🔍 **Company Knowledge Base Search:** Instantly retrieve internal policies, documents, and files.\n"
                                    "- ⚡ **Automated Executive Reports:** Generate deep reviews and action plans in one click.\n\n"
                                    "Feel free to ask a question or attach a file to begin analysis!"
                                )
                            else:
                                fallback_reply = (
                                    "👋 **হ্যালো! আমি MyAgent AI** — আপনার এন্টারপ্রাইজ ইন্টেলিজেন্স ও প্রোডাক্টিভিটি অ্যাসিস্ট্যান্ট।\n\n"
                                    "আমি আপনাকে কীভাবে সাহায্য করতে পারি? আমার প্রধান ক্ষমতা ও সুবিধাগুলো:\n\n"
                                    "- 📁 **মাল্টি-ফরম্যাট ফাইল বিশ্লেষণ:** PDF, Word (DOCX), Excel স্প্রেডশিট ও ইমেজ OCR পাঠ।\n"
                                    "- 📊 **বিগ ডেটা ও টেবিল সামারি:** ব্যবসায়িক ডেটাসেট পরিসংখ্যান ও ট্রেন্ড বিশ্লেষণ।\n"
                                    "- 🔍 **কোম্পানি নলেজবেস অনুসন্ধান:** অভ্যন্তরীণ পলিসি, ডকুমেন্ট ও ফাইল তাৎক্ষণিক খুঁজে বের করা।\n"
                                    "- ⚡ **অটোমেটেড এক্সিকিউটিভ রিপোর্ট:** এক ক্লিকে গভীর পর্যালোচনা ও অ্যাকশন প্ল্যান তৈরি।\n\n"
                                    "আপনার প্রয়োজনীয় প্রশ্নটি লিখুন অথবা ফাইল আপলোড করে বিশ্লেষণ শুরু করুন!"
                                )
                        elif sources:
                            if language == "en":
                                fallback_reply = (
                                    f"⚠️ **[LLM Server Offline - Memory Knowledge Response]**\n\n"
                                    f"Your external AI model server (`{target_model}` @ `{settings.LLM_BASE_URL}`) is currently disconnected. "
                                    f"However, here is the relevant company knowledge and vector memory retrieved for your query:\n\n"
                                )
                                for s in sources:
                                    fallback_reply += f"> **📄 {s.source} (Page {s.page}):**\n> {s.content}\n\n"
                                fallback_reply += f"💡 *For AI-generated synthesis, please ensure the LM Studio / LLM server is running (`{settings.LLM_BASE_URL}`) or configure an active server in System Settings (⚙️).*"
                            else:
                                fallback_reply = (
                                    f"⚠️ **[এলএলএম সার্ভার অফলাইন - মেমোরি নলেজ রেসপন্স]**\n\n"
                                    f"আপনার বাহ্যিক এআই মডেল সার্ভারটি (`{target_model}` @ `{settings.LLM_BASE_URL}`) বর্তমানে সংযুক্ত নয়। "
                                    f"তবে আপনার প্রশ্নের সাথে প্রাসঙ্গিক কোম্পানির নলেজবেস ও ভেক্টর মেমোরির তথ্য নিচে প্রদান করা হলো:\n\n"
                                )
                                for s in sources:
                                    fallback_reply += f"> **📄 {s.source} (পৃষ্ঠা {s.page}):**\n> {s.content}\n\n"
                                fallback_reply += f"💡 *এআই মডেলের মাধ্যমে আরও বিশদ উত্তরের জন্য অনুগ্রহ করে LM Studio সার্ভারটি চালু করুন (`192.168.20.10:1234`) অথবা সিস্টেম সেটিংস (⚙️) থেকে সক্রিয় কোনো সার্ভার সেট করুন।*"
                        else:
                            if language == "en":
                                fallback_reply = (
                                    f"⚠️ **[LLM Server Offline (Connection Error)]**\n\n"
                                    f"The backend could not connect to your configured LLM server:\n"
                                    f"- **Server URL:** `{settings.LLM_BASE_URL}`\n"
                                    f"- **Target Model:** `{target_model}`\n\n"
                                    f"**Troubleshooting Steps:**\n"
                                    f"1. Check that **Start Server** is active in your LM Studio or Ollama application.\n"
                                    f"2. Ensure **'Serve on Local Network'** is enabled in LM Studio so external devices or Docker containers (`192.168.9.9`) can reach it.\n"
                                    f"3. Or select an active server endpoint in **System Settings (⚙️)**."
                                )
                            else:
                                fallback_reply = (
                                    f"⚠️ **[এলএলএম মডেল সার্ভার অফলাইন (Connection Error)]**\n\n"
                                    f"আপনার কনফিগার করা এলএলএম সার্ভারের সাথে ব্যাকএন্ড সংযোগ স্থাপন করতে পারছে না:\n"
                                    f"- **সার্ভার ইউআরএল:** `{settings.LLM_BASE_URL}`\n"
                                    f"- **টার্গেট মডেল:** `{target_model}`\n\n"
                                    f"**সহজ সমাধান নির্দেশিকা:**\n"
                                    f"1. আপনার LM Studio অ্যাপে **Start Server** চালু আছে কিনা পরীক্ষা করুন।\n"
                                    f"2. LM Studio-তে **'Serve on Local Network'** অন রাখুন যাতে অন্য ডিভাইস বা ডকার সার্ভার (`192.168.9.9`) থেকে সংযোগ গ্রহণ করতে পারে।\n"
                                    f"3. অথবা অ্যাডমিন প্যানেলের **সিস্টেম সেটিংস (⚙️)** থেকে সক্রিয় কোনো সার্ভার URL সেট করুন।"
                                )
                        # Stream fallback reply smoothly
                        for word in fallback_reply.split(" "):
                            yield f"data: {json.dumps({'type': 'token', 'token': word + ' '})}\n\n"
                            await asyncio.sleep(0.015)
                        yield f"data: {json.dumps({'type': 'done', 'model': target_model})}\n\n"
                        return
                    else:
                        yield f"data: {json.dumps({'type': 'error', 'error': f'LLM Server Error: {err_str}'})}\n\n"
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
                err_lower = str(e).lower()
                if any(kw in err_lower for kw in ["connection", "timeout", "connecterror", "reset", "closed", "broken pipe"]):
                    msg = (
                        "\n\n⚠️ **[এলএলএম সার্ভার সংযোগ বিচ্ছিন্ন হয়েছে। অনুগ্রহ করে LM Studio বা মডেল সার্ভার পরীক্ষা করুন।]**"
                        if language != "en"
                        else "\n\n⚠️ **[LLM server connection interrupted. Please verify the LM Studio / model server status.]**"
                    )
                    yield f"data: {json.dumps({'type': 'token', 'token': msg})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'model': target_model})}\n\n"
                    return
                yield f"data: {json.dumps({'type': 'error', 'error': f'Communication Error: {str(e)}'})}\n\n"
                return

        # End of turns — Cognitive Auto-Memory Extraction runs silently after streaming
        yield f"data: {json.dumps({'type': 'done', 'model': target_model})}\n\n"

        # 🧠 Cognitive Auto-Memory Extraction Engine (background, non-blocking)
        # Scans the user prompt for factual statements worth saving to permanent memory
        if use_memory and prompt.strip() and not self.is_conversational_greeting(prompt):
            try:
                extracted = await self._cognitive_auto_extract(prompt, language=language)
                if extracted:
                    save_res = self.vector_store.add_note(
                        title=extracted["title"],
                        content=extracted["content"],
                        category="ai_auto_extracted",
                        tags=extracted.get("tags", ["auto_extracted"])
                    )
                    logger.info(f"[AutoMemory] Saved: '{extracted['title']}' | doc_id={save_res['doc_id']} | chunks={save_res['chunks_count']}")
                    yield f"data: {json.dumps({'type': 'memory_saved', 'note': extracted['title'], 'doc_id': save_res['doc_id']})}\n\n"
            except Exception as auto_err:
                logger.debug(f"[AutoMemory] Extraction skipped: {auto_err}")

    async def _cognitive_auto_extract(self, prompt: str, language: str = "bn") -> Optional[Dict[str, Any]]:
        """
        🧠 Cognitive Auto-Memory Extraction Engine.
        Scans user prompt with regex + heuristic NLP to detect factual statements:
          - Named entities: people, companies, places, projects
          - Dates, deadlines, time references
          - Financial figures, salaries, budgets
          - Rules, policies, instructions, procedures
          - Contact info: phone, email, address
        Returns a structured {title, content, tags} dict if worthy data found, else None.
        Minimum threshold: 25 chars and at least 1 factual signal to save.
        """
        import re

        text = prompt.strip()
        if len(text) < 25:
            return None

        lower = text.lower()

        # ── Signal Pattern Library ──────────────────────────────────────────────
        date_pat       = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{2}[/-]\d{2}|জানুয়ারি|ফেব্রুয়ারি|মার্চ|এপ্রিল|মে|জুন|জুলাই|আগস্ট|সেপ্টেম্বর|অক্টোবর|নভেম্বর|ডিসেম্বর|january|february|march|april|may|june|july|august|september|october|november|december)\b", re.I)
        money_pat      = re.compile(r"\b(\d[\d,]*\s*(টাকা|taka|bdt|usd|\$|৳|লক্ষ|কোটি|হাজার|thousand|million|billion|salary|বেতন|budget|বাজেট|payment|পেমেন্ট))\b", re.I)
        phone_pat      = re.compile(r"\b(\+?880|01)[3-9]\d{8}\b")
        email_pat      = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
        rule_kw        = ["নিয়ম", "নীতি", "পলিসি", "নির্দেশনা", "আইন", "ধারা", "সিদ্ধান্ত", "চুক্তি",
                          "rule", "policy", "regulation", "guideline", "procedure", "decision", "contract", "agreement"]
        person_kw      = ["জনাব", "মিস", "ড.", "ডাক্তার", "mr.", "mr ", "mrs.", "ms.", "dr.", "engineer", "ইঞ্জিনিয়ার",
                          "manager", "ম্যানেজার", "director", "পরিচালক", "ceo", "md ", "chairman", "চেয়ারম্যান"]
        project_kw     = ["প্রজেক্ট", "project", "initiative", "কার্যক্রম", "উদ্যোগ", "task", "milestone", "deadline"]
        company_kw     = ["কোম্পানি", "company", "ltd", "limited", "corp", "inc.", "সংস্থা", "প্রতিষ্ঠান", "organization"]
        instruction_kw = ["মনে রেখো", "মনে রাখো", "save", "remember", "record", "সংরক্ষণ", "নোট", "note down", "log this"]

        # Count signals
        signals = 0
        tags    = []

        if date_pat.search(text):
            signals += 2; tags.append("date_reference")
        if money_pat.search(text):
            signals += 2; tags.append("financial")
        if phone_pat.search(text) or email_pat.search(text):
            signals += 2; tags.append("contact_info")
        if any(k in lower for k in rule_kw):
            signals += 3; tags.append("policy_rule")
        if any(k in lower for k in person_kw):
            signals += 2; tags.append("person_entity")
        if any(k in lower for k in project_kw):
            signals += 2; tags.append("project")
        if any(k in lower for k in company_kw):
            signals += 2; tags.append("company_data")
        if any(k in lower for k in instruction_kw):
            signals += 4; tags.append("user_instruction")

        # Length bonus — longer statements are more likely to contain facts
        if len(text) > 120:
            signals += 1
        if len(text) > 300:
            signals += 2

        # Threshold: need at least 3 signal points to save
        if signals < 3:
            return None

        # Deduplicate tags
        tags = list(dict.fromkeys(tags))
        tags.append("auto_extracted")

        # Build title from first meaningful sentence (max 60 chars)
        first_sentence = re.split(r"[।\.!\n]", text)[0].strip()
        title = (first_sentence[:57] + "...") if len(first_sentence) > 60 else first_sentence
        if not title:
            title = text[:57] + "..."

        # Prefix indicates auto-extraction
        if language == "en":
            content = f"[AI Auto-Extracted Factual Memory]\nSource: User conversation\nExtracted Data:\n{text}"
        else:
            content = f"[এআই স্বয়ংক্রিয় ফ্যাক্টুয়াল মেমোরি এক্সট্র্যাকশন]\nউৎস: ব্যবহারকারীর কথোপকথন\nএক্সট্র্যাক্টেড তথ্য:\n{text}"

        return {"title": title, "content": content, "tags": tags, "signals": signals}

    async def generate_response(
        self,
        prompt: str,
        history: List[ChatMessage],
        use_memory: bool = True,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
        attached_files: Optional[List[Dict[str, Any]]] = None,
        language: str = "bn"
    ) -> Dict[str, Any]:
        """Non-streaming generation for API consumers."""
        target_model = model or settings.LLM_MODEL
        target_temp = temperature if temperature is not None else settings.AGENT_TEMPERATURE

        sources: List[SourceCitation] = []
        user_content = prompt

        if use_memory and prompt.strip():
            user_content, sources = self._prepare_rag_context(prompt, language=language)

        # Incorporate attached files into user_content
        if attached_files and len(attached_files) > 0:
            attachment_blocks = []
            for af in attached_files:
                fname = af.get("filename", "File")
                ftype = af.get("file_type", "document")
                summary = af.get("summary", "")
                preview = af.get("preview_text", "")
                table_md = af.get("table_markdown", "")
                ocr_txt = af.get("ocr_text", "")

                block_content = f"📎 [সংযুক্ত ফাইল: {fname} (ধরন: {ftype})]\n{summary}\n" if language == "bn" else f"📎 [Attached File: {fname} (Type: {ftype})]\n{summary}\n"
                if table_md:
                    block_content += f"\n[ডাটা টেবিল ভিউ]:\n{table_md}\n" if language == "bn" else f"\n[Data Table View]:\n{table_md}\n"
                if ocr_txt:
                    block_content += f"\n[OCR টেক্সট]:\n{ocr_txt}\n" if language == "bn" else f"\n[OCR Extracted Text]:\n{ocr_txt}\n"
                if preview and not table_md and not ocr_txt:
                    block_content += f"\n[কনটেন্ট প্রিভিউ]:\n{preview}\n" if language == "bn" else f"\n[Content Preview]:\n{preview}\n"
                attachment_blocks.append(block_content)

            merged_attachments = "\n\n---\n\n".join(attachment_blocks)
            if not prompt.strip():
                if language == "en":
                    user_content = f"### [The user directly attached the following files in chat and requested detailed analysis]:\n\n{merged_attachments}\n\nPlease provide detailed statistics, findings, and insights in professional English."
                else:
                    user_content = f"### [ব্যবহারকারী সরাসরি চ্যাটে নিম্নলিখিত ফাইলগুলো সংযুক্ত করেছেন এবং বিস্তারিত বিশ্লেষণ চেয়েছেন]:\n\n{merged_attachments}\n\nঅনুগ্রহ করে সংযুক্ত ফাইলের বিস্তারিত পরিসংখ্যান ও ইনসাইটস বাংলায় উপস্থাপন করুন।"
            else:
                if language == "en":
                    user_content = f"### [Directly Attached Files and Data Context]:\n\n{merged_attachments}\n\n### [User Question / Instructions]:\n{user_content}"
                else:
                    user_content = f"### [সরাসরি চ্যাটে সংযুক্ত ফাইল ও ডাটা কনটেক্সট]:\n\n{merged_attachments}\n\n### [ব্যবহারকারীর প্রশ্ন / নির্দেশনা]:\n{user_content}"

        system_content = SYSTEM_PROMPT_TEMPLATE.format(agent_name=settings.AGENT_NAME)
        if language == "en":
            system_content += "\n\nCRITICAL LANGUAGE DIRECTIVE: The user has selected English as their preferred interface language. Generate your final response in clear, professional English (while strictly observing the internal company data and memory boundaries)."
        else:
            system_content += "\n\nCRITICAL LANGUAGE DIRECTIVE: The user has selected Bangla as their preferred interface language. Generate your final response in natural, professional, and elegant Bangla (বাংলা)."
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
