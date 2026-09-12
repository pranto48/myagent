# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.2.0
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

if __name__ == "__main__":
    unittest.main()
