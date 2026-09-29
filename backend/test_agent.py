# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.0.0
"""
Automated Verification and Test Suite for MyAgent.
Tests: Config, Document Chunking, Excel Parsing, SQLite Multi-Session Store, JWT Auth.
"""

import os
import sys
import asyncio
import unittest

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from memory.document_loader import DocumentProcessor
from memory.chat_session_store import ChatSessionStore
from routers.auth import create_access_token, verify_token

class TestMyAgentSystem(unittest.TestCase):

    def test_01_configuration(self):
        """Verifies updated port 3399 and admin credentials."""
        self.assertEqual(settings.WEB_PORT, 3399)
        self.assertEqual(settings.ADMIN_USERNAME, "admin")
        self.assertEqual(settings.ADMIN_PASSWORD, "Aa987654")
        print("✅ [Pass] Port 3399 and Admin Credentials validated.")

    def test_02_jwt_authentication(self):
        """Verifies JWT token creation and validation for admin."""
        token = create_access_token(settings.ADMIN_USERNAME)
        self.assertIsNotNone(token)
        payload = verify_token(token)
        self.assertEqual(payload["sub"], "admin")
        self.assertEqual(payload["role"], "admin")
        print("✅ [Pass] JWT Authentication and token verification passed.")

    def test_03_text_chunking(self):
        """Tests sliding window recursive text chunker."""
        sample_text = (
            "কোম্পানির অফিস সময় সকাল ৯টা থেকে সন্ধ্যা ৬টা পর্যন্ত। "
            "সকল কর্মকর্তা কর্মচারীদের সময়মতো উপস্থিত থাকতে হবে। "
            "জরুরি প্রয়োজনে এইচআর ডিপার্টমেন্টে যোগাযোগ করতে হবে। "
        ) * 10
        chunks = DocumentProcessor.chunk_text(sample_text, chunk_size=200, overlap=50)
        self.assertTrue(len(chunks) > 1)
        self.assertTrue(all(len(c) > 0 for c in chunks))
        print(f"✅ [Pass] Text chunker generated {len(chunks)} overlapping chunks.")

    def test_04_sqlite_chat_sessions(self):
        """Tests asynchronous SQLite multi-session chat storage."""
        async def run_session_test():
            # Setup test db
            test_session = await ChatSessionStore.create_session("টেস্ট কথোপকথন")
            session_id = test_session["id"]
            self.assertTrue(session_id.startswith("session_"))

            # Add messages
            await ChatSessionStore.add_message(session_id, "user", "সেলস ডাটা কি?")
            await ChatSessionStore.add_message(
                session_id,
                "assistant",
                "২০২৪ সালের মোট সেলস ৫ কোটি টাকা।",
                sources=[{"source": "Sales.xlsx", "page": 1, "score": 0.95}]
            )

            # Retrieve
            messages = await ChatSessionStore.get_session_messages(session_id)
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0]["role"], "user")
            self.assertEqual(messages[1]["role"], "assistant")
            self.assertEqual(len(messages[1]["sources"]), 1)

            # Cleanup
            await ChatSessionStore.delete_session(session_id)

        asyncio.run(run_session_test())
        print("✅ [Pass] SQLite persistent multi-session chat storage validated.")

    def test_05_autonomous_tools(self):
        """Tests autonomous tool capabilities: save_company_memory, fs_write_file, visual_chart_generator."""
        from agent.tools import AgentTools

        # Test chart generator
        chart = AgentTools.visual_chart_generator("bar", "Q1 Sales", ["Jan", "Feb", "Mar"], [100, 250, 180])
        self.assertIn("Q1 Sales", chart)
        self.assertIn("Feb", chart)

        # Test fs write & read
        w_res = AgentTools.fs_write_file("test_auto.txt", "Autonomous Agent Test Content")
        self.assertIn("test_auto.txt", w_res)
        r_res = AgentTools.fs_read_file("reports/test_auto.txt")
        self.assertIn("Autonomous Agent Test Content", r_res)

        # Test memory persistence
        mem_res = AgentTools.save_company_memory(
            title="Office Working Hours",
            content="Official office hours are 9:00 AM to 6:00 PM Sunday through Thursday.",
            category="policy",
            tags=["office", "hours", "policy"]
        )
        self.assertIn("Successfully saved", mem_res)
        print("✅ [Pass] Autonomous tools (save_company_memory, charts, fs) validated.")

    def test_06_multi_syntax_tool_parser(self):
        """Tests robust parsing of multiple text tool calling syntaxes."""
        from agent.core_agent import CompanyAIAgent

        # 1. XML JSON tag
        sample_tag = '<thought>Need to check policy</thought><tool_call>{"name": "query_company_memory", "arguments": {"query": "vacation leave"}}</tool_call>'
        calls = CompanyAIAgent._extract_text_tool_calls(sample_tag, 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["name"], "query_company_memory")

        # 2. Markdown JSON block
        sample_md = '```json\n{"action": "python_runner", "action_input": {"code": "2 + 2"}}\n```'
        calls_md = CompanyAIAgent._extract_text_tool_calls(sample_md, 1)
        self.assertEqual(len(calls_md), 1)
        self.assertEqual(calls_md[0]["name"], "python_runner")

        # 3. Action format
        sample_act = 'Action: fs_read_file\nAction Input: {"filepath": "report.md"}'
        calls_act = CompanyAIAgent._extract_text_tool_calls(sample_act, 2)
        self.assertEqual(len(calls_act), 1)
        self.assertEqual(calls_act[0]["name"], "fs_read_file")
        print("✅ [Pass] Multi-syntax tool call parser validated for all 3 formats.")

    def test_07_all_tools_schema(self):
        """Ensures all tools have standard valid OpenAI function schemas."""
        from agent.tools import AgentTools
        schemas = AgentTools.get_openai_tools_schema()
        tool_names = [s["function"]["name"] for s in schemas]

        required = [
            "query_company_memory", "save_company_memory", "web_search", "web_scrape",
            "python_runner", "analyze_big_data", "generate_data_report", "read_pdf_document",
            "read_word_document", "read_excel_spreadsheet", "read_image_ocr", "fs_list_files",
            "fs_read_file", "fs_write_file", "sqlite_query", "smart_data_summarizer",
            "cross_document_comparator", "visual_chart_generator", "system_info"
        ]
        for req in required:
            self.assertIn(req, tool_names, f"Tool '{req}' is missing from OpenAI tool schema!")
        print(f"✅ [Pass] All {len(required)} tool schemas registered and validated.")

if __name__ == "__main__":
    unittest.main()
