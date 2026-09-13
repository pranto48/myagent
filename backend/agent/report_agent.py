# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 3.0.0
# Report Generation Agent — AI-Powered Enterprise Report Builder
# ==============================================================================

import os
import json
import uuid
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import AsyncOpenAI
from config import settings
from memory.vector_store import VectorMemoryStore

logger = logging.getLogger("myagent.report_agent")


REPORT_SYSTEM_PROMPT = """You are an expert Enterprise Report Generator AI for {agent_name}.
Your task is to generate structured, professional business reports in Markdown format EXCLUSIVELY based on internal company data and records.

STRICT DATA SOURCE & INTEGRITY RULES:
1. STRICT COMPANY DATA REQUIREMENT: You must ONLY use the provided internal company data and documents. DO NOT use or introduce data, benchmarks, or information from external/other companies.
2. If internal company data for certain sections is missing, DO NOT fabricate metrics or guess facts. Instead, clearly designate that section as "[কোম্পানি ডেটা পেন্ডিং: নথি বা তথ্য আপলোড প্রয়োজন]" and outline the exact data requirements.
3. Always generate reports in Bangla (বাংলা) unless explicitly requested in English.
4. Use proper Markdown: headings (##, ###), tables, bullet points, bold text.
5. Include an Executive Summary (সারসংক্ষেপ) at the top.
6. Include a "তথ্য সূত্র" (Data Sources) section at the end citing the internal company documents used.
7. Be data-driven, precise, and professional.
8. For analytical reports, include numerical tables when data is available.
9. End every report with "পরবর্তী পদক্ষেপ" (Next Actions) recommendations.

Copyright footer: "© 2026 IT support BD | তৈরি: Arif | MyAgent v3.0.0"
"""

REPORT_TEMPLATES = {
    "executive_summary": {
        "name": "এক্সিকিউটিভ সামারি",
        "icon": "📊",
        "prompt_prefix": "নিচের তথ্যের উপর ভিত্তি করে একটি পেশাদার এক্সিকিউটিভ সামারি রিপোর্ট তৈরি করুন। রিপোর্টে মূল KPI, সাফল্য, চ্যালেঞ্জ এবং সুপারিশ অন্তর্ভুক্ত করুন।"
    },
    "data_analysis": {
        "name": "ডেটা বিশ্লেষণ রিপোর্ট",
        "icon": "📈",
        "prompt_prefix": "নিচের ডেটার উপর ভিত্তি করে একটি বিস্তারিত ডেটা বিশ্লেষণ রিপোর্ট তৈরি করুন। ট্রেন্ড, প্যাটার্ন, পরিসংখ্যান এবং গ্রাফযোগ্য তথ্য সহ।"
    },
    "kpi_report": {
        "name": "KPI পারফরম্যান্স রিপোর্ট",
        "icon": "🎯",
        "prompt_prefix": "নিচের তথ্য থেকে একটি KPI পারফরম্যান্স রিপোর্ট তৈরি করুন। প্রতিটি সূচকের লক্ষ্যমাত্রা বনাম অর্জন, প্রবণতা এবং উন্নতির সুযোগ বিশ্লেষণ করুন।"
    },
    "incident_report": {
        "name": "ইনসিডেন্ট রিপোর্ট",
        "icon": "🚨",
        "prompt_prefix": "নিচের ঘটনার বিবরণ থেকে একটি পেশাদার ইনসিডেন্ট রিপোর্ট তৈরি করুন। ঘটনার সারসংক্ষেপ, মূল কারণ বিশ্লেষণ, প্রভাব এবং প্রতিকার পরিকল্পনা সহ।"
    },
    "meeting_minutes": {
        "name": "মিটিং মিনিটস",
        "icon": "📝",
        "prompt_prefix": "নিচের তথ্য থেকে একটি পেশাদার মিটিং মিনিটস ডকুমেন্ট তৈরি করুন। সিদ্ধান্ত, অ্যাকশন আইটেম এবং দায়িত্বপ্রাপ্ত ব্যক্তিদের তালিকাসহ।"
    },
    "company_policy": {
        "name": "কোম্পানি পলিসি ডকুমেন্ট",
        "icon": "📋",
        "prompt_prefix": "নিচের তথ্যের ভিত্তিতে একটি পেশাদার কোম্পানি পলিসি ডকুমেন্ট তৈরি করুন। উদ্দেশ্য, নিয়মাবলী, ব্যতিক্রম এবং বাস্তবায়নের বিবরণ সহ।"
    },
    "custom": {
        "name": "কাস্টম রিপোর্ট",
        "icon": "✨",
        "prompt_prefix": "নিচের নির্দেশনা অনুযায়ী একটি পেশাদার রিপোর্ট তৈরি করুন:"
    }
}


class ReportAgent:
    """AI-powered enterprise report generation agent."""

    def __init__(self):
        self.vector_store = VectorMemoryStore()
        self._init_client()
        self._init_report_db()

    def _init_client(self):
        base_url = settings.LLM_BASE_URL.strip()
        if not base_url.endswith("/v1") and "/v1/" not in base_url:
            base_url = base_url.rstrip("/") + "/v1"
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=settings.LLM_API_KEY or "not-needed",
            timeout=180.0
        )

    def _init_report_db(self):
        """Initialize SQLite database for storing generated reports."""
        os.makedirs(settings.DATA_DIR, exist_ok=True)
        db_path = os.path.join(settings.DATA_DIR, "reports.db")
        conn = sqlite3.connect(db_path) if os.path.exists(db_path) else sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                report_type TEXT NOT NULL,
                topic TEXT,
                content TEXT NOT NULL,
                sources TEXT DEFAULT '[]',
                created_by TEXT DEFAULT 'admin',
                created_at TEXT NOT NULL,
                word_count INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def _get_db(self):
        import sqlite3 as _sqlite3
        db_path = os.path.join(settings.DATA_DIR, "reports.db")
        conn = _sqlite3.connect(db_path)
        conn.row_factory = _sqlite3.Row
        return conn

    async def generate_report(
        self,
        report_type: str,
        topic: str,
        additional_context: str = "",
        created_by: str = "admin"
    ) -> Dict[str, Any]:
        """
        Generates a professional AI-powered report.
        1. Retrieves relevant company knowledge from vector memory.
        2. Builds an augmented prompt with the template.
        3. Streams LLM response and saves to database.
        """
        template = REPORT_TEMPLATES.get(report_type, REPORT_TEMPLATES["custom"])
        report_id = f"rpt_{uuid.uuid4().hex[:10]}"

        # 1. Retrieve relevant context from company memory
        memory_hits = self.vector_store.super_fast_search(query=topic, top_k=6, user_role="admin")
        context_blocks = []
        sources_used = []

        for hit in memory_hits:
            content = str(hit.get("content", "")).strip()
            source = str(hit.get("source", "Document"))
            score = float(hit.get("score", 0))

            if content and score > 0.4 and "????" not in content:
                context_blocks.append(f"[{source}]: {content[:500]}")
                sources_used.append({"source": source, "score": round(score, 3)})

        # 2. Build prompt
        if context_blocks:
            rag_context = "\n\n".join(context_blocks)
        else:
            rag_context = (
                "⚠️ সতর্কতা: কোম্পানির অভ্যন্তরীণ নলেজ বেস থেকে এই বিষয়ের কোনো রেকর্ড পাওয়া যায়নি।\n"
                "কঠোর নির্দেশ: কাল্পনিক তথ্য বা অন্য কোনো কোম্পানির তথ্য ব্যবহার করবেন না। রিপোর্টে স্পষ্টভাবে উল্লেখ করুন যে কোম্পানির ডেটাবেজে এই তথ্যটি এখনো অন্তর্ভুক্ত নেই এবং কোন কোন ফাইল বা ডেটা পয়েন্ট প্রয়োজন।"
            )

        user_prompt = f"""
{template['prompt_prefix']}

**বিষয়:** {topic}

**কোম্পানি নলেজ বেস থেকে প্রাসঙ্গিক তথ্য:**
{rag_context}

{f"**অতিরিক্ত নির্দেশনা / প্রেক্ষাপট:**{additional_context}" if additional_context else ""}

**তারিখ:** {datetime.now().strftime("%d %B %Y")}

অনুগ্রহ করে একটি সম্পূর্ণ, পেশাদার এবং বিস্তারিত {template['name']} তৈরি করুন।
রিপোর্টটি অবশ্যই প্রাতিষ্ঠানিক মানের হতে হবে এবং সঠিক Markdown ফরম্যাটে লিখতে হবে।
"""

        # 3. Generate with LLM
        system_msg = REPORT_SYSTEM_PROMPT.format(agent_name=settings.AGENT_NAME)

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=4096
            )
            report_content = response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Report generation LLM error: {e}")
            report_content = f"# {template['name']}: {topic}\n\n**⚠️ LLM সার্ভার সংযোগ ব্যর্থ।**\n\nঅনুগ্রহ করে LM Studio সার্ভার চালু করুন (`{settings.LLM_BASE_URL}`) এবং পুনরায় চেষ্টা করুন।\n\n**তথ্য সূত্র (মেমোরি থেকে রিট্রিভ করা):**\n{rag_context}"

        # 4. Build full report with header
        title = f"{template['icon']} {template['name']}: {topic}"
        timestamp = datetime.now().strftime("%d %B %Y, %H:%M")
        header = f"---\n**রিপোর্ট আইডি:** `{report_id}` | **তৈরি:** {timestamp} | **প্রস্তুতকারী:** {created_by}\n\n---\n\n"
        full_content = header + report_content

        word_count = len(full_content.split())

        # 5. Save to database
        import json as _json
        conn = self._get_db()
        conn.execute("""
            INSERT INTO reports (id, title, report_type, topic, content, sources, created_by, created_at, word_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_id, title, report_type, topic,
            full_content, _json.dumps(sources_used),
            created_by, datetime.now().isoformat(), word_count
        ))
        conn.commit()
        conn.close()

        # 6. Also index the report into company memory
        try:
            self.vector_store.add_note(
                title=title,
                content=full_content[:3000],
                category="generated_report",
                security_level="INTERNAL"
            )
        except Exception:
            pass

        return {
            "success": True,
            "report_id": report_id,
            "title": title,
            "report_type": report_type,
            "content": full_content,
            "sources_used": sources_used,
            "word_count": word_count,
            "created_at": datetime.now().isoformat()
        }

    def list_reports(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns list of all generated reports."""
        import json as _json
        conn = self._get_db()
        cursor = conn.execute("""
            SELECT id, title, report_type, topic, word_count, created_by, created_at
            FROM reports
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()

        return [{
            "id": r["id"],
            "title": r["title"],
            "report_type": r["report_type"],
            "topic": r["topic"],
            "word_count": r["word_count"],
            "created_by": r["created_by"],
            "created_at": r["created_at"]
        } for r in rows]

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single report by ID."""
        import json as _json
        conn = self._get_db()
        cursor = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "id": row["id"],
            "title": row["title"],
            "report_type": row["report_type"],
            "topic": row["topic"],
            "content": row["content"],
            "sources": _json.loads(row["sources"] or "[]"),
            "word_count": row["word_count"],
            "created_by": row["created_by"],
            "created_at": row["created_at"]
        }

    def delete_report(self, report_id: str) -> bool:
        """Deletes a report by ID."""
        conn = self._get_db()
        cursor = conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted


import sqlite3  # ensure import at module level
