# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.1.0
import os
import re
import sys
import math
import time
import json
import asyncio
import sqlite3
import logging
import subprocess
from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup
from memory.vector_store import VectorStore as VectorMemoryStore
from config import settings

logger = logging.getLogger(__name__)

class AgentTools:
    """
    Built-in Open Source & Local Toolbox for Autonomous AI Agent:
      - Python Sandbox (safe arithmetic & data calculations)
      - DuckDuckGo Instant Web Search
      - BeautifulSoup4 Web Page Scraper
      - Big Data Analyzer (Pandas CSV/TSV aggregations & distributions)
      - PDF Reader (pypdf)
      - Word Reader (python-docx)
      - Excel Reader (openpyxl)
      - Photo OCR Reader (Pillow & pytesseract)
      - Local File System Operator
      - SQLite Query Engine
      - System & Container Diagnostics
      - Super Fast Hybrid Company Memory (with Document-Level Security & DLP)
    """

    @staticmethod
    def query_company_memory(query: str, top_k: int = 4, user_role: str = "admin") -> List[Dict[str, Any]]:
        """Tool to retrieve semantic and keyword matches from company hybrid memory (< 10ms)."""
        store = VectorMemoryStore()
        return store.super_fast_search(query=query, top_k=top_k, user_role=user_role)

    @staticmethod
    def save_company_memory(
        title: str,
        content: str,
        category: str = "general",
        tags: Optional[List[str]] = None,
        security_level: str = "INTERNAL"
    ) -> str:
        """Autonomously persists a key fact, rule, guideline, or finding into the company hybrid vector memory."""
        try:
            store = VectorMemoryStore()
            res = store.add_note(
                title=title,
                content=content,
                category=category,
                tags=tags or ["autonomous_save"],
                security_level=security_level
            )
            return f"Successfully saved to company persistent memory. Note ID: {res.get('doc_id')}, Chunks indexed: {res.get('chunks_count')}"
        except Exception as e:
            return f"Error saving to company memory: {str(e)}"

    @staticmethod
    async def web_search(query: str) -> str:
        """Autonomous live web search using DuckDuckGo Instant Answers with resilient HTML fallback."""
        try:
            url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    abstract = data.get("AbstractText", "")
                    if abstract:
                        return f"[ওয়েব সার্চ ফলাফল]: {abstract}"
                    related = [t.get("Text", "") for t in data.get("RelatedTopics", []) if "Text" in t]
                    if related:
                        return f"[ওয়েব সার্চ ফলাফল]: {related[0]}"
            
            # Resilient HTML fallback search
            html_url = "https://html.duckduckgo.com/html/"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            async with httpx.AsyncClient(timeout=8.0, headers=headers) as client:
                resp = await client.post(html_url, data={"q": query})
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    results = []
                    for r in soup.select(".result__body")[:4]:
                        snippet = r.select_one(".result__snippet")
                        title = r.select_one(".result__title")
                        if snippet and snippet.text.strip():
                            t_text = title.text.strip() if title else "Source"
                            results.append(f"- **{t_text}**: {snippet.text.strip()}")
                    if results:
                        return f"=== [ওয়েব সার্চ ফলাফল: {query}] ===\n" + "\n".join(results)
            return f"DuckDuckGo-তে '{query}' সম্পর্কে কোনো সরাসরি উত্তর পাওয়া যায়নি।"
        except Exception as e:
            return f"Web search service error: {str(e)}"

    @staticmethod
    async def web_scrape(url: str, max_chars: int = 3500) -> str:
        """Fetches public webpage content and extracts clean, readable text using BeautifulSoup."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 MyAgent/2.1.0"
            }
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=headers) as client:
                res = await client.get(url)
                if res.status_code != 200:
                    return f"Webpage returned status {res.status_code}."

                soup = BeautifulSoup(res.text, "html.parser")
                # Strip script and style tags
                for script in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                    script.extract()

                text = soup.get_text(separator="\n")
                # Collapse whitespace
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                clean_text = "\n".join(lines)

                if len(clean_text) > max_chars:
                    return f"[Webpage Snippet: {url}]\n" + clean_text[:max_chars] + f"\n... [Truncated {len(clean_text) - max_chars} characters]"
                return f"[Webpage Content: {url}]\n" + clean_text
        except Exception as e:
            return f"Web scrape error for {url}: {str(e)}"

    @staticmethod
    def python_runner(code: str) -> str:
        """
        Executes Python code or mathematical expressions in a constrained execution sandbox.
        Equipped with standard data science modules: pandas, numpy, datetime, statistics, re, math.
        """
        import io
        import re
        import csv
        import datetime
        import statistics
        import collections
        import itertools
        import contextlib

        def load_dataset(filename_or_path: str):
            """Helper to load any CSV, TSV, or Excel file into a pandas DataFrame."""
            import pandas as pd
            target = filename_or_path
            if not os.path.isabs(target):
                for d in [settings.DATA_DIR, os.path.join(settings.DATA_DIR, "documents"), os.path.join(settings.DATA_DIR, "uploads"), os.path.join(settings.DATA_DIR, "reports")]:
                    cand = os.path.join(d, filename_or_path)
                    if os.path.exists(cand):
                        target = cand
                        break
            if not os.path.exists(target):
                raise FileNotFoundError(f"Dataset '{filename_or_path}' not found in data directories.")
            ext = os.path.splitext(target)[1].lower()
            if ext in [".xlsx", ".xls"]:
                return pd.read_excel(target)
            elif ext == ".tsv":
                return pd.read_csv(target, sep="\t")
            elif ext == ".json":
                return pd.read_json(target)
            return pd.read_csv(target)

        stdout_capture = io.StringIO()
        safe_globals = {
            "math": math,
            "json": json,
            "time": time,
            "re": re,
            "csv": csv,
            "datetime": datetime,
            "statistics": statistics,
            "collections": collections,
            "itertools": itertools,
            "load_dataset": load_dataset,
            "len": len,
            "range": range,
            "min": min,
            "max": max,
            "sum": sum,
            "round": round,
            "abs": abs,
            "sorted": sorted,
            "enumerate": enumerate,
            "zip": zip,
            "list": list,
            "dict": dict,
            "set": set,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "print": print
        }

        # Inject pandas and numpy if available
        try:
            import pandas as pd
            safe_globals["pd"] = pd
            safe_globals["pandas"] = pd
        except Exception:
            pass

        try:
            import numpy as np
            safe_globals["np"] = np
            safe_globals["numpy"] = np
        except Exception:
            pass

        # Try evaluating as an expression first
        try:
            expr_res = eval(code.strip(), safe_globals)
            if expr_res is not None:
                return f"[Result]: {expr_res}"
        except Exception:
            pass

        # Execute as statements and capture stdout
        try:
            with contextlib.redirect_stdout(stdout_capture):
                exec(code, safe_globals)
            output = stdout_capture.getvalue().strip()
            return f"[Output]:\n{output}" if output else "[Code executed successfully with no stdout output]"
        except Exception as e:
            return f"Python Execution Error: {type(e).__name__}: {str(e)}"

    @staticmethod
    def calculate(expression: str) -> str:
        """Safely evaluates basic mathematical calculations."""
        return AgentTools.python_runner(expression)

    @staticmethod
    def analyze_big_data(
        filepath: str,
        query_type: str = "summary",
        group_by: Optional[str] = None,
        aggregate_col: Optional[str] = None,
        agg_func: Optional[str] = "sum"
    ) -> str:
        """
        Big Data tabular analysis tool for CSV, TSV, Excel, or JSON datasets using Pandas.
        query_type options: 'summary', 'head', 'columns', 'statistics', 'nulls', 'groupby', 'correlation'.
        """
        try:
            import pandas as pd
            target_path = filepath
            if not os.path.isabs(target_path):
                # Search inside data directory
                for root_dir in [settings.DATA_DIR, os.path.join(settings.DATA_DIR, "documents"), os.path.join(settings.DATA_DIR, "uploads"), os.path.join(settings.DATA_DIR, "reports")]:
                    candidate = os.path.join(root_dir, filepath)
                    if os.path.exists(candidate):
                        target_path = candidate
                        break

            if not os.path.exists(target_path):
                return f"Dataset file '{filepath}' not found."

            if target_path.endswith(".csv"):
                df = pd.read_csv(target_path)
            elif target_path.endswith(".tsv"):
                df = pd.read_csv(target_path, sep="\t")
            elif target_path.endswith((".xlsx", ".xls")):
                df = pd.read_excel(target_path)
            elif target_path.endswith(".json"):
                df = pd.read_json(target_path)
            else:
                return f"Unsupported tabular format for '{filepath}'."

            if query_type == "summary":
                rows, cols = df.shape
                col_names = list(df.columns)
                num_cols = df.select_dtypes(include=["number"]).columns.tolist()
                stats_str = df.describe().to_string() if len(num_cols) > 0 else "No numerical columns"
                return (
                    f"=== ডাটাসেট বিশ্লেষণ: {os.path.basename(target_path)} ===\n"
                    f"মোট সারি (Rows): {rows}, মোট কলাম (Columns): {cols}\n"
                    f"কলামসমূহ: {', '.join(col_names)}\n\n"
                    f"নমুনা ডাটা (Top 3):\n{df.head(3).to_string()}\n\n"
                    f"পরিসংখ্যান (Summary Stats):\n{stats_str}"
                )
            elif query_type == "head":
                return f"Top 10 Rows of {os.path.basename(target_path)}:\n" + df.head(10).to_string()
            elif query_type == "columns":
                return f"Columns in {os.path.basename(target_path)}:\n" + "\n".join([f"- {c} ({df[c].dtype})" for c in df.columns])
            elif query_type == "nulls":
                null_counts = df.isnull().sum()
                return f"Missing/Null Values:\n" + null_counts[null_counts > 0].to_string()
            elif query_type == "groupby":
                grp_col = group_by or df.columns[0]
                if grp_col not in df.columns:
                    return f"Group column '{grp_col}' not found. Available: {', '.join(df.columns)}"
                if aggregate_col and aggregate_col in df.columns:
                    fn = agg_func if agg_func in ["sum", "mean", "count", "min", "max"] else "sum"
                    res_df = df.groupby(grp_col)[aggregate_col].agg([fn, "count"]).reset_index()
                else:
                    res_df = df.groupby(grp_col).size().reset_index(name="count")
                return f"=== গ্রুপ বিশ্লেষণ ({grp_col}) ===\n" + res_df.head(20).to_string()
            elif query_type == "correlation":
                num_df = df.select_dtypes(include=["number"])
                if num_df.shape[1] > 1:
                    return f"=== পারস্পরিক সম্পর্ক ম্যাট্রিক্স (Correlation Matrix) ===\n" + num_df.corr().round(3).to_string()
                return "অনুরোধটি সম্পন্ন করা যায়নি: পারস্পরিক সম্পর্কের জন্য পর্যাপ্ত সংখ্যাবাচক কলাম (Numeric Columns) নেই।"
            else:
                return df.head(5).to_string()
        except Exception as e:
            return f"Big Data analysis error: {str(e)}"

    @staticmethod
    def generate_data_report(title: str, report_markdown: str, filename: Optional[str] = None) -> str:
        """
        Saves a structured executive intelligence or data report into the reports volume
        so the user can review and download it directly.
        """
        try:
            reports_dir = os.path.join(settings.DATA_DIR, "reports")
            os.makedirs(reports_dir, exist_ok=True)
            safe_filename = filename or f"report_{int(time.time())}.md"
            if not safe_filename.endswith((".md", ".txt", ".csv")):
                safe_filename += ".md"
            target_file = os.path.join(reports_dir, os.path.basename(safe_filename))
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n*Generated by MyAgent Enterprise Productivity Engine*\n*Date: {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                f.write(report_markdown)
            return f"✅ এক্সিকিউটিভ রিপোর্ট সফলভাবে তৈরি ও সংরক্ষিত হয়েছে: reports/{os.path.basename(target_file)} (আকার: {len(report_markdown)} অক্ষর)"
        except Exception as e:
            return f"Error generating report: {str(e)}"

    @staticmethod
    def read_pdf_document(filepath: str, max_pages: int = 15) -> str:
        """Reads and extracts structured text from PDF documents page by page."""
        try:
            import pypdf
            target_path = filepath
            if not os.path.isabs(target_path):
                for d in [settings.DATA_DIR, os.path.join(settings.DATA_DIR, "documents"), os.path.join(settings.DATA_DIR, "uploads")]:
                    if os.path.exists(os.path.join(d, filepath)):
                        target_path = os.path.join(d, filepath)
                        break

            if not os.path.exists(target_path):
                return f"PDF file '{filepath}' not found."

            reader = pypdf.PdfReader(target_path)
            total_pages = len(reader.pages)
            content_parts = []
            for i, page in enumerate(reader.pages[:max_pages], 1):
                t = page.extract_text() or ""
                if t.strip():
                    content_parts.append(f"--- [পৃষ্ঠা {i} / {total_pages}] ---\n{t.strip()}")

            return f"=== PDF ডকুমেন্ট: {os.path.basename(target_path)} (মোট পৃষ্ঠা: {total_pages}) ===\n" + "\n\n".join(content_parts)
        except Exception as e:
            return f"PDF reading error: {str(e)}"

    @staticmethod
    def read_word_document(filepath: str) -> str:
        """Reads and extracts paragraphs and tables from Word (.docx) documents."""
        try:
            import docx
            target_path = filepath
            if not os.path.isabs(target_path):
                for d in [settings.DATA_DIR, os.path.join(settings.DATA_DIR, "documents"), os.path.join(settings.DATA_DIR, "uploads")]:
                    if os.path.exists(os.path.join(d, filepath)):
                        target_path = os.path.join(d, filepath)
                        break

            if not os.path.exists(target_path):
                return f"Word document '{filepath}' not found."

            doc = docx.Document(target_path)
            text_blocks = []
            for p in doc.paragraphs:
                if p.text.strip():
                    text_blocks.append(p.text.strip())

            table_blocks = []
            for t_idx, table in enumerate(doc.tables, 1):
                rows_data = []
                for row in table.rows:
                    rows_data.append(" | ".join([cell.text.strip() for cell in row.cells]))
                if rows_data:
                    table_blocks.append(f"[টেবিল {t_idx}]:\n" + "\n".join(rows_data))

            combined = "\n\n".join(text_blocks)
            if table_blocks:
                combined += "\n\n=== সংলগ্ন টেবিলসমূহ ===\n" + "\n\n".join(table_blocks)

            return f"=== Word ডকুমেন্ট: {os.path.basename(target_path)} ===\n" + combined
        except Exception as e:
            return f"Word document reading error: {str(e)}"

    @staticmethod
    def read_excel_spreadsheet(filepath: str, sheet_name: Optional[str] = None, max_rows: int = 50) -> str:
        """Reads sheets, columns, and rows from Excel (.xlsx / .xls) spreadsheets."""
        try:
            import openpyxl
            target_path = filepath
            if not os.path.isabs(target_path):
                for d in [settings.DATA_DIR, os.path.join(settings.DATA_DIR, "documents"), os.path.join(settings.DATA_DIR, "uploads")]:
                    if os.path.exists(os.path.join(d, filepath)):
                        target_path = os.path.join(d, filepath)
                        break

            if not os.path.exists(target_path):
                return f"Excel file '{filepath}' not found."

            wb = openpyxl.load_workbook(target_path, data_only=True)
            sheet = wb[sheet_name] if sheet_name and sheet_name in wb.sheetnames else wb.active

            rows = list(sheet.iter_rows(values_only=True))
            if not rows:
                return f"Excel sheet '{sheet.title}' is empty."

            headers = [str(h) if h is not None else f"Col_{idx}" for idx, h in enumerate(rows[0], 1)]
            row_texts = []
            for r_idx, row in enumerate(rows[1:max_rows+1], 2):
                entries = [f"{headers[i]}: {val}" for i, val in enumerate(row) if val is not None and str(val).strip()]
                if entries:
                    row_texts.append(f"Row {r_idx} -> " + ", ".join(entries))

            return (
                f"=== Excel ফাইল: {os.path.basename(target_path)} | শিট: '{sheet.title}' ===\n"
                f"শিটসমূহ: {', '.join(wb.sheetnames)}\n"
                f"কলাম হেডার: {', '.join(headers)}\n\n"
                f"ডাটা রেকর্ডস (শীর্ষ {len(row_texts)} সারি):\n" + "\n".join(row_texts)
            )
        except Exception as e:
            return f"Excel reading error: {str(e)}"

    @staticmethod
    def read_image_ocr(filepath: str) -> str:
        """Reads text from photos/images (.png, .jpg, .webp) using Pillow and OCR."""
        try:
            from PIL import Image
            import pytesseract
            target_path = filepath
            if not os.path.isabs(target_path):
                for d in [settings.DATA_DIR, os.path.join(settings.DATA_DIR, "documents"), os.path.join(settings.DATA_DIR, "uploads")]:
                    if os.path.exists(os.path.join(d, filepath)):
                        target_path = os.path.join(d, filepath)
                        break

            if not os.path.exists(target_path):
                return f"Image file '{filepath}' not found."

            img = Image.open(target_path)
            extracted_text = pytesseract.image_to_string(img)
            if extracted_text and extracted_text.strip():
                return f"=== ফটো/ছবি OCR ফলাফল: {os.path.basename(target_path)} ===\n" + extracted_text.strip()
            else:
                return f"ছবি '{os.path.basename(target_path)}' ({img.size[0]}x{img.size[1]} {img.format}) থেকে কোনো টেক্সট শনাক্ত করা যায়নি।"
        except Exception as e:
            return f"Photo OCR error: {str(e)}"

    @staticmethod
    def fs_list_files(directory: str = "") -> str:
        """Lists files and folders in the internal data storage directory."""
        try:
            base = settings.DATA_DIR
            target = os.path.join(base, directory.strip("/")) if directory else base
            if not os.path.exists(target):
                return f"Directory '{directory}' does not exist."

            entries = []
            for item in os.listdir(target):
                full = os.path.join(target, item)
                is_dir = os.path.isdir(full)
                size_kb = round(os.path.getsize(full) / 1024, 1) if not is_dir else "-"
                mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(full)))
                entries.append(f"{'[DIR]' if is_dir else '[FILE]'} {item} ({size_kb} KB, {mtime})")

            return f"=== ফাইল তালিকা: {target} ===\n" + "\n".join(entries)
        except Exception as e:
            return f"File system list error: {str(e)}"

    @staticmethod
    def fs_read_file(filepath: str, max_chars: int = 5000) -> str:
        """Reads text, markdown, json, or code file contents from data storage."""
        try:
            if "sealed_vault" in (filepath or "").lower():
                return "Security Block: 'sealed_vault.db' is an AI-Sealed AES-256-GCM credential vault. AI models are prohibited from accessing it."
            target_path = filepath
            if not os.path.isabs(target_path):
                for d in [settings.DATA_DIR, os.path.join(settings.DATA_DIR, "documents"), os.path.join(settings.DATA_DIR, "uploads")]:
                    if os.path.exists(os.path.join(d, filepath)):
                        target_path = os.path.join(d, filepath)
                        break

            if not os.path.exists(target_path):
                return f"File '{filepath}' not found."

            with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(max_chars)
            return f"=== ফাইল কনটেন্ট: {os.path.basename(target_path)} ===\n" + content
        except Exception as e:
            return f"File read error: {str(e)}"

    @staticmethod
    def fs_write_file(filepath: str, content: str) -> str:
        """Writes AI analysis notes or reports to the reports folder."""
        try:
            reports_dir = os.path.join(settings.DATA_DIR, "reports")
            os.makedirs(reports_dir, exist_ok=True)
            filename = os.path.basename(filepath)
            dest = os.path.join(reports_dir, filename)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(content)
            return f"সফলভাবে সংরক্ষিত হয়েছে: {dest} ({len(content)} অক্ষর)"
        except Exception as e:
            return f"File write error: {str(e)}"

    @staticmethod
    def sqlite_query(query: str, db_name: str = "chat_history.db") -> str:
        """Executes safe read-only SQL queries against SQLite databases."""
        try:
            if "sealed_vault" in (db_name or "").lower() or "mcp_sealed_device_vault" in (query or "").lower():
                return "Security Block: 'sealed_vault.db' is an AI-Sealed AES-256-GCM credential vault. AI models cannot query or access this table."
            q_lower = query.strip().lower()
            if not q_lower.startswith("select") and not q_lower.startswith("pragma") and not q_lower.startswith("explain"):
                return "Security Error: Only SELECT or PRAGMA read queries are permitted."

            db_path = os.path.join(settings.DATA_DIR, db_name)
            if not os.path.exists(db_path):
                return f"Database '{db_name}' not found."

            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query)
                rows = cursor.fetchall()
                if not rows:
                    return "Query returned 0 rows."
                col_names = [col[0] for col in cursor.description]
                result_lines = [" | ".join(col_names)]
                result_lines.append("-" * 40)
                for r in rows[:50]:
                    result_lines.append(" | ".join([str(r[c]) for c in col_names]))
                return f"=== SQL ফলাফল ({len(rows)} সারি) ===\n" + "\n".join(result_lines)
        except Exception as e:
            return f"SQLite Query Error: {str(e)}"

    @staticmethod
    def system_info() -> str:
        """Returns container diagnostics: uptime, memory, disk, and CPU load."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage(settings.DATA_DIR)
            cpu = psutil.cpu_percent(interval=0.2)
            boot_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(psutil.boot_time()))
            return (
                f"=== সিস্টেম ও ডকার ডায়াগনস্টিকস ===\n"
                f"CPU ব্যবহার: {cpu}%\n"
                f"র‍্যাম ব্যবহার: {mem.percent}% (ব্যবহৃত: {round(mem.used/(1024**3), 2)} GB / মোট: {round(mem.total/(1024**3), 2)} GB)\n"
                f"ডিস্ক স্পেস: {disk.percent}% (ফ্রি: {round(disk.free/(1024**3), 2)} GB / মোট: {round(disk.total/(1024**3), 2)} GB)\n"
                f"সিস্টেম বুট টাইম: {boot_time}\n"
                f"ডাটা ডিরেক্টরি: {settings.DATA_DIR}"
            )
        except Exception as e:
            return f"System info error: {str(e)}"

    @staticmethod
    def smart_data_summarizer(filepath: str) -> str:
        """
        Deep automated statistical profiler for tabular data (CSV, TSV, Excel, JSON).
        Returns dataset dimensions, column types, null counts, numeric statistics, and top categories.
        """
        try:
            import pandas as pd
            target_path = filepath
            if not os.path.isabs(target_path):
                for root_dir in [settings.DATA_DIR, os.path.join(settings.DATA_DIR, "documents"), os.path.join(settings.DATA_DIR, "uploads"), os.path.join(settings.DATA_DIR, "reports")]:
                    cand = os.path.join(root_dir, filepath)
                    if os.path.exists(cand):
                        target_path = cand
                        break
            if not os.path.exists(target_path):
                return f"Dataset file '{filepath}' not found in data directories."

            ext = os.path.splitext(target_path)[1].lower()
            if ext in [".xlsx", ".xls"]:
                df = pd.read_excel(target_path)
            elif ext == ".tsv":
                df = pd.read_csv(target_path, sep="\t")
            elif ext == ".json":
                df = pd.read_json(target_path)
            else:
                df = pd.read_csv(target_path)

            rows, cols = df.shape
            mem_mb = round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2)
            null_count = int(df.isnull().sum().sum())
            null_pct = round((null_count / max(rows * cols, 1)) * 100, 2)

            res = [
                f"=== 📊 স্মার্ট ডাটা প্রোফাইল: {os.path.basename(target_path)} ===",
                f"- মোট সারি (Rows): {rows:,}",
                f"- মোট কলাম (Columns): {cols}",
                f"- মেমোরি ব্যবহার: {mem_mb} MB",
                f"- মোট মিসিং মান (Nulls): {null_count:,} ({null_pct}%)\n",
                "### কলাম বিবরণ ও পরিসংখ্যান:"
            ]

            num_cols = df.select_dtypes(include=["number"]).columns.tolist()
            cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
            date_cols = df.select_dtypes(include=["datetime"]).columns.tolist()

            if num_cols:
                res.append("\n**📈 সংখ্যাবাচক কলাম (Numeric KPIs):**")
                stats_df = df[num_cols].describe().T[["min", "mean", "50%", "max"]].rename(columns={"50%": "median"}).round(2)
                res.append(stats_df.to_markdown())

            if cat_cols:
                res.append("\n**🏷️ ক্যাটাগরিক্যাল কলাম (Categories & Top Values):**")
                for c in cat_cols[:8]:
                    n_uniq = df[c].nunique()
                    top_vals = df[c].value_counts().head(3).to_dict()
                    top_str = ", ".join([f"{k} ({v})" for k, v in top_vals.items()])
                    res.append(f"- **{c}** ({n_uniq} unique): {top_str}")

            if date_cols:
                res.append("\n**📅 তারিখ কলাম (Date Ranges):**")
                for c in date_cols:
                    res.append(f"- **{c}**: {df[c].min()} থেকে {df[c].max()}")

            return "\n".join(res)
        except Exception as e:
            return f"Error profiling dataset: {str(e)}"

    @staticmethod
    def cross_document_comparator(doc1_path: str, doc2_path: str, topic: Optional[str] = None) -> str:
        """
        Cross-examines and compares two corporate documents, policies, or datasets.
        Identifies structural differences, size, key overlapping topics, and differences.
        """
        try:
            def extract_text(path: str) -> str:
                ext = os.path.splitext(path)[1].lower()
                if ext == ".pdf":
                    return AgentTools.read_pdf_document(path, max_pages=20)
                elif ext in [".docx", ".doc"]:
                    return AgentTools.read_word_document(path)
                elif ext in [".xlsx", ".xls"]:
                    return AgentTools.read_excel_spreadsheet(path, max_rows=50)
                else:
                    return AgentTools.fs_read_file(path, max_chars=10000)

            t1 = extract_text(doc1_path)
            t2 = extract_text(doc2_path)

            b1 = os.path.basename(doc1_path)
            b2 = os.path.basename(doc2_path)

            lines1 = [l.strip() for l in t1.splitlines() if l.strip() and not l.startswith("===")]
            lines2 = [l.strip() for l in t2.splitlines() if l.strip() and not l.startswith("===")]

            if topic:
                topic_lower = topic.lower()
                lines1 = [l for l in lines1 if topic_lower in l.lower()]
                lines2 = [l for l in lines2 if topic_lower in l.lower()]

            res = [
                f"=== 📑 ক্রস-ডকুমেন্ট তুলনামূলক বিশ্লেষণ ===",
                f"- **ডকুমেন্ট ১:** {b1} ({len(lines1)} প্রাসঙ্গিক লাইন)",
                f"- **ডকুমেন্ট ২:** {b2} ({len(lines2)} প্রাসঙ্গিক লাইন)",
            ]
            if topic:
                res.append(f"- **নির্দিষ্ট অনুসন্ধান বিষয়:** `{topic}`\n")

            res.append(f"\n### 🔹 {b1} থেকে শীর্ষ অংশ:")
            res.append("\n".join(lines1[:6]) if lines1 else "কোনো প্রাসঙ্গিক তথ্য পাওয়া যায়নি।")

            res.append(f"\n### 🔹 {b2} থেকে শীর্ষ অংশ:")
            res.append("\n".join(lines2[:6]) if lines2 else "কোনো প্রাসঙ্গিক তথ্য পাওয়া যায়নি।")

            return "\n".join(res)
        except Exception as e:
            return f"Cross document comparison error: {str(e)}"

    @staticmethod
    def visual_chart_generator(
        chart_type: str,
        title: str,
        data_labels: List[str],
        data_values: List[float],
        max_bar_width: int = 25
    ) -> str:
        """
        Generates beautiful text-based Unicode/ASCII visualizations for chat responses.
        Supported chart_types: 'bar' (horizontal bar chart), 'gauge' (progress gauges), 'sparkline' (trendline).
        """
        try:
            if not data_labels or not data_values or len(data_labels) != len(data_values):
                return "ত্রুটি: চার্টের জন্য data_labels এবং data_values একই দৈর্ঘ্যের হতে হবে।"

            lines = [f"📊 **{title}**\n```"]
            max_val = max(data_values) if data_values and max(data_values) > 0 else 1.0
            max_lbl_len = max(len(str(lbl)) for lbl in data_labels)

            if chart_type in ["bar", "horizontal_bar"]:
                for lbl, val in zip(data_labels, data_values):
                    ratio = max(0.0, float(val)) / max_val
                    bar_len = int(round(ratio * max_bar_width))
                    bar_str = "█" * bar_len + "░" * (max_bar_width - bar_len)
                    lines.append(f"{str(lbl).ljust(max_lbl_len)} | {bar_str} {val}")

            elif chart_type in ["gauge", "progress"]:
                for lbl, val in zip(data_labels, data_values):
                    pct = min(100.0, max(0.0, float(val)))
                    gauge_len = int(round((pct / 100.0) * max_bar_width))
                    gauge_str = "▓" * gauge_len + "░" * (max_bar_width - gauge_len)
                    lines.append(f"{str(lbl).ljust(max_lbl_len)} | {gauge_str} {pct:.1f}%")

            elif chart_type in ["sparkline", "trend"]:
                ticks = [" ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
                min_val = min(data_values)
                val_range = max(max_val - min_val, 1e-6)
                spark = "".join([ticks[min(7, int(((v - min_val) / val_range) * 7))] for v in data_values])
                lines.append(f"Trend: [{spark}] (Min: {min_val}, Max: {max_val})")
                for lbl, val in zip(data_labels, data_values):
                    lines.append(f"  • {lbl}: {val}")

            else:
                for lbl, val in zip(data_labels, data_values):
                    lines.append(f"{str(lbl).ljust(max_lbl_len)} : {val}")

            lines.append("```")
            return "\n".join(lines)
        except Exception as e:
            return f"Chart generator error: {str(e)}"

    @classmethod
    async def delegate_to_subagent(cls, subagent_id: str, task: str) -> str:
        """Dispatches work to a specialized subagent and returns synthesized results."""
        from agent.subagents.work_engine import SubAgentWorkEngine
        try:
            res = await SubAgentWorkEngine.execute_subagent_task(
                agent_id=subagent_id,
                task_instruction=task
            )
            return json.dumps({
                "agent_id": subagent_id,
                "agent_name": res.get("agent_name"),
                "status": "COMPLETED",
                "tool_summary": res.get("tool_summary"),
                "findings": res.get("output")
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"agent_id": subagent_id, "error": str(e)})

    @classmethod
    async def execute_subagent_swarm(cls, goal: str) -> str:
        """Coordinates a multi-agent swarm mission across qualified subagents to accomplish a user goal."""
        from agent.subagents.work_engine import SubAgentWorkEngine
        try:
            res = await SubAgentWorkEngine.orchestrate_swarm_mission(goal=goal)
            return json.dumps({
                "mission_id": res.get("mission_id"),
                "agents_engaged": res.get("agents_engaged"),
                "total_duration_ms": res.get("total_duration_ms"),
                "executive_summary": res.get("executive_summary")
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"goal": goal, "error": str(e)})

    @staticmethod
    async def ping_network_diagnostics(target: str, ping_type: str = "icmp", port: Optional[int] = None, count: int = 3) -> str:
        """
        Autonomous Sub-Agent tool to test ping connectivity and measure latency from the
        Agent Server (192.168.9.9) to another IP address or hostname.
        """
        try:
            from agent.subagents.ping_agent import NetworkPingSubAgent
            res = await NetworkPingSubAgent.ping_target(target=target, ping_type=ping_type, port=port, count=count)
            status_emoji = "🟢" if res.get("status") == "ONLINE" else ("🟡" if res.get("status") == "DEGRADED" else "🔴")
            lines = [
                f"### {status_emoji} নেটওয়ার্ক পিং ও স্টেটাস রিপোর্ট ({res.get('status')})",
                f"- **সার্ভার উৎস আইপি (Source IP):** `{res.get('source_server_ip', '192.168.9.9')}`",
                f"- **টার্গেট আইপি (Target IP):** `{res.get('target_ip')}` ({res.get('target_name', 'Host')})",
                f"- **টেস্টিং মেথড:** `{res.get('method', 'ICMP')}`",
                f"- **কানেকশন স্টেটাস:** `{res.get('status')}`",
                f"- **গড় লেটেন্সি (Avg Latency):** `{res.get('latency_ms', 'N/A')} ms`",
                f"- **প্যাকেট লস (Packet Loss):** `{res.get('packet_loss', 0)}%`"
            ]
            if res.get("min_ms") is not None and res.get("max_ms") is not None:
                lines.append(f"- **ন্যূনতম / সর্বোচ্চ লেটেন্সি:** `{res.get('min_ms')} ms` / `{res.get('max_ms')} ms`")
            if res.get("raw_output"):
                lines.append(f"\n```text\n{res.get('raw_output')}\n```")
            return "\n".join(lines)
        except Exception as e:
            return f"Ping diagnostics error: {str(e)}"

    @staticmethod
    async def save_project_info(
        project_name: str,
        description: str,
        display_name: Optional[str] = None,
        tech_stack: Optional[str] = None,
        architecture_blueprint: Optional[str] = None,
        urls: Optional[str] = None
    ) -> str:
        """Creates or updates high-level project information, tech stack, and architecture blueprint."""
        from memory.project_store import ProjectMemoryStore
        res = await ProjectMemoryStore.save_project_info(
            name=project_name,
            display_name=display_name,
            description=description,
            tech_stack=tech_stack,
            architecture_blueprint=architecture_blueprint,
            urls=urls
        )
        return json.dumps({
            "success": True,
            "message": f"Project information for '{project_name}' successfully saved.",
            "project": res
        }, ensure_ascii=False, indent=2)

    @staticmethod
    async def get_project_info(project_name: str) -> str:
        """Retrieves project overview, tech stack, architecture blueprint, and memory count."""
        from memory.project_store import ProjectMemoryStore
        data = await ProjectMemoryStore.get_project_info(project_name)
        if not data:
            return f"No project registered with name '{project_name}'. You can register it using save_project_info."
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    async def list_all_projects() -> str:
        """Lists all registered projects with memory counts and last updated status."""
        from memory.project_store import ProjectMemoryStore
        projects = await ProjectMemoryStore.list_projects()
        return json.dumps({
            "total_projects": len(projects),
            "projects": projects
        }, ensure_ascii=False, indent=2)

    @staticmethod
    async def save_project_memory(
        project_name: str,
        key: str,
        content: str,
        title: Optional[str] = None,
        category: str = "general",
        context: str = "production",
        tags: Optional[List[str]] = None,
        security_level: str = "INTERNAL"
    ) -> str:
        """Saves a hierarchical per-project memory item indexed by project -> category -> context -> key."""
        from memory.project_store import ProjectMemoryStore
        res = await ProjectMemoryStore.save_memory(
            project_name=project_name,
            key=key,
            content=content,
            title=title,
            category=category,
            context=context,
            tags=tags,
            security_level=security_level
        )
        return json.dumps(res, ensure_ascii=False, indent=2)

    @staticmethod
    async def get_project_memory(project_name: str, key: str) -> str:
        """Direct fast retrieval (<1ms) of a saved memory by project name and exact key."""
        from memory.project_store import ProjectMemoryStore
        mem = await ProjectMemoryStore.get_memory(project_name, key)
        if not mem:
            return f"No memory found for project '{project_name}' with key '{key}'."
        return json.dumps(mem, ensure_ascii=False, indent=2)

    @staticmethod
    async def search_project_memory(
        project_name: Optional[str] = None,
        category: Optional[str] = None,
        context: Optional[str] = None,
        query: Optional[str] = None
    ) -> str:
        """Searches across project memories by project name, category, context, or keyword."""
        from memory.project_store import ProjectMemoryStore
        mems = await ProjectMemoryStore.search_memories(
            project_name=project_name,
            category=category,
            context=context,
            query=query,
            limit=30
        )
        return json.dumps({
            "count": len(mems),
            "memories": mems
        }, ensure_ascii=False, indent=2)

    @staticmethod
    def enhance_prompt(prompt: str, mode: str = "developer", target_audience: str = "ai_agent") -> str:
        """
        Transforms any rough or brief prompt into an elite, highly structured,
        constraint-hardened prompt following industry best practices.
        """
        clean_p = prompt.strip()
        modes_config = {
            "developer": {
                "role": "Senior Principal Software Engineer & Systems Architect",
                "focus": "Production-grade code, strict error handling, modularity, optimal Big-O complexity, and zero technical debt.",
                "format": "Executable code blocks with exact file paths, dependency lists, edge-case handling, and verification test commands."
            },
            "architect": {
                "role": "Chief Enterprise Solutions & Cloud Infrastructure Architect",
                "focus": "Scalability, high availability, Docker/containerization, zero-trust security, and low-latency data pipelines.",
                "format": "Mermaid architecture diagrams, service boundaries, schema blueprints, failure recovery workflows, and deployment plans."
            },
            "analysis": {
                "role": "Lead Data Scientist & Quantitative Intelligence Analyst",
                "focus": "Statistical accuracy, anomaly detection, distribution metrics, correlations, and executive KPI synthesis.",
                "format": "Structured Markdown comparison tables, percentile breakdowns, trend diagnostics, and data-driven recommendations."
            },
            "executive": {
                "role": "Chief Technology Officer (CTO) & Strategic Technical Advisor",
                "focus": "ROI, risk mitigation, engineering velocity, cross-team alignment, and clear business impact.",
                "format": "Executive brief summary, priority matrix, timeline milestones, and critical risk callouts."
            },
            "concise": {
                "role": "Ultra-Direct Precision Engineering Assistant",
                "focus": "Zero fluff, highest signal-to-noise ratio, immediate actionable output.",
                "format": "Bulleted atomic commands, minimal diffs, and verified facts."
            }
        }
        cfg = modes_config.get(mode.lower(), modes_config["developer"])

        return (
            f"### ✨ [ENHANCED MASTER PROMPT — {mode.upper()} MODE]\n\n"
            f"**1. ROLE & EXPERT PERSONA:**\n"
            f"Act as a **{cfg['role']}**. Prioritize {cfg['focus']}\n\n"
            f"**2. OPERATIONAL CONTEXT & TARGET:**\n"
            f"- **Target Consumer:** `{target_audience}`\n"
            f"- **Core Intent:** {clean_p}\n\n"
            f"**3. EXECUTION CONSTRAINTS & GUARDRAILS:**\n"
            f"- **Step-by-Step Reasoning:** Deconstruct prerequisites, hidden dependencies, and edge cases before implementation.\n"
            f"- **Zero Hallucination:** Only reference real APIs, validated file paths, and verified schemas.\n"
            f"- **Production Completeness:** Provide complete, runnable implementations — never omit error handling or leave placeholder stubs.\n"
            f"- **Security Hardening:** Avoid hardcoded secrets, SQL injection risks, XSS, or unsafe shell evaluations.\n\n"
            f"**4. REQUIRED OUTPUT SPECIFICATION:**\n"
            f"{cfg['format']}\n\n"
            f"**5. REFINED TASK DIRECTIVE:**\n"
            f"```text\n{clean_p}\n```\n\n"
            f"Execute this directive thoroughly with clear verification proof."
        )

    @staticmethod
    async def network_port_scan(target: str, ports: Optional[List[int]] = None, timeout_sec: float = 0.8) -> str:
        """
        Asynchronously probes TCP ports on a target IP address or hostname from the Docker server
        to discover open listening services, measure TCP handshake latency, and identify risks.
        """
        default_ports = [21, 22, 53, 80, 443, 1433, 3306, 3389, 3399, 5432, 6379, 8000, 8008, 8080, 8443, 9000, 27017]
        target_ports = ports if ports and len(ports) > 0 else default_ports
        service_map = {
            21: "FTP", 22: "SSH", 53: "DNS", 80: "HTTP", 443: "HTTPS",
            1433: "MSSQL", 3306: "MySQL", 3389: "RDP", 3399: "MyAgent Web (Nginx)",
            5432: "PostgreSQL", 6379: "Redis", 8000: "FastAPI / Uvicorn",
            8008: "MyAgent Backend API", 8080: "HTTP Alt", 8443: "HTTPS Alt",
            9000: "Portainer / Admin", 27017: "MongoDB"
        }

        async def probe_port(p: int):
            t0 = time.perf_counter()
            try:
                conn = asyncio.open_connection(target, p)
                reader, writer = await asyncio.wait_for(conn, timeout=timeout_sec)
                lat = round((time.perf_counter() - t0) * 1000, 2)
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
                return (p, True, lat)
            except Exception:
                return (p, False, 0.0)

        results = await asyncio.gather(*[probe_port(int(p)) for p in target_ports[:30]])
        open_ports = [r for r in results if r[1]]
        closed_count = len(results) - len(open_ports)

        lines = [
            f"### 🔭 নেটওয়ার্ক TCP পোর্ট ও সার্ভিস স্ক্যান রিপোর্ট: `{target}`",
            f"- **উৎস সার্ভার (Source):** Docker Container (`192.168.9.9`)",
            f"- **মোট স্ক্যানকৃত পোর্ট:** `{len(results)}` | 🟢 **খোলা পোর্ট (Open):** `{len(open_ports)}` | 🔴 **বন্ধ/ফিল্টার্ড:** `{closed_count}`",
            "",
            "| পোর্ট (Port) | স্টেটাস (Status) | সার্ভিস (Service) | ল্যাটেন্সি (Latency) |",
            "| :--- | :--- | :--- | :--- |"
        ]
        for p, is_open, lat in open_ports:
            svc = service_map.get(p, "Custom TCP Service")
            lines.append(f"| **{p}** | 🟢 OPEN | {svc} | `{lat} ms` |")

        if not open_ports:
            lines.append("| — | 🔴 ALL CLOSED / FILTERED | No responsive TCP ports detected | — |")

        return "\n".join(lines)

    @staticmethod
    def sqlite_schema_inspector(db_name: str = "chat_history.db", table_name: Optional[str] = None, explain_sql: Optional[str] = None) -> str:
        """
        Inspects SQLite database tables, columns, row counts, indexes,
        or explains a SQL query execution plan (EXPLAIN QUERY PLAN).
        """
        if "sealed_vault" in (db_name or "").lower() or "mcp_sealed_device_vault" in (table_name or "").lower():
            return "Security Block: 'sealed_vault.db' is an AI-Sealed AES-256-GCM credential vault. AI models cannot inspect this database."
        db_path = os.path.join(settings.DATA_DIR, os.path.basename(db_name))
        if not os.path.exists(db_path):
            db_path = os.path.join("./data", os.path.basename(db_name))
        if not os.path.exists(db_path):
            return f"Database file '{db_name}' not found in data storage."

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            if explain_sql:
                if not explain_sql.strip().lower().startswith("select"):
                    return "Security block: EXPLAIN QUERY PLAN only accepts SELECT statements."
                cur.execute(f"EXPLAIN QUERY PLAN {explain_sql}")
                plan_rows = [dict(r) for r in cur.fetchall()]
                conn.close()
                return f"### ⚡ SQL Execution Plan (`{db_name}`)\n```json\n{json.dumps(plan_rows, indent=2)}\n```"

            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            tables = [r["name"] for r in cur.fetchall()]

            if table_name:
                if table_name not in tables:
                    conn.close()
                    return f"Table '{table_name}' does not exist in '{db_name}'. Available tables: {', '.join(tables)}"
                cur.execute(f"PRAGMA table_info({table_name})")
                cols = [dict(r) for r in cur.fetchall()]
                cur.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
                row_cnt = cur.fetchone()["cnt"]
                cur.execute(f"PRAGMA index_list({table_name})")
                idxs = [dict(r) for r in cur.fetchall()]
                conn.close()
                return json.dumps({
                    "database": db_name,
                    "table": table_name,
                    "row_count": row_cnt,
                    "columns": cols,
                    "indexes": idxs
                }, indent=2, ensure_ascii=False)

            overview = []
            for t in tables:
                try:
                    cur.execute(f"SELECT COUNT(*) as cnt FROM {t}")
                    cnt = cur.fetchone()["cnt"]
                except Exception:
                    cnt = -1
                overview.append({"table": t, "rows": cnt})
            conn.close()
            return f"### 🗄️ Database Schema Overview: `{db_name}`\n" + json.dumps(overview, indent=2)
        except Exception as e:
            return f"Database schema inspection error: {str(e)}"

    @staticmethod
    def code_quality_and_security_audit(code: str, language: str = "python") -> str:
        """
        Audits source code snippets for security risks (hardcoded keys, SQL injection, eval/exec,
        shell injection), missing error handling, and code quality best practices.
        """
        findings = []
        lines = code.splitlines()

        secret_patterns = [
            (r"(api[_-]?key|secret|password|token)\s*=\s*['\"][A-Za-z0-9_\-]{8,}['\"]", "CRITICAL: Potential hardcoded credential or API secret detected."),
            (r"sk-[a-zA-Z0-9]{20,}", "CRITICAL: Exposed OpenAI/OpenRouter style secret key detected.")
        ]
        vuln_patterns = [
            (r"\beval\s*\(", "HIGH: Use of `eval()` allows arbitrary code execution."),
            (r"\bexec\s*\(", "HIGH: Use of `exec()` allows arbitrary code execution."),
            (r"subprocess\.(run|Popen|call).*shell\s*=\s*True", "HIGH: `shell=True` in subprocess introduces command injection risk."),
            (r"f['\"]SELECT\s+.*\{.*\}", "HIGH: String-interpolated SQL query introduces SQL injection vulnerability. Use parameterized queries (`?`)."),
            (r"except\s*:", "MEDIUM: Bare `except:` catches SystemExit/KeyboardInterrupt silently; catch `Exception` explicitly."),
            (r"TODO|FIXME|HACK", "LOW: Unresolved technical debt marker (TODO/FIXME) present.")
        ]

        for idx, line in enumerate(lines, 1):
            for pat, msg in secret_patterns + vuln_patterns:
                if re.search(pat, line, re.IGNORECASE):
                    findings.append(f"- **Line {idx}:** {msg}\n  `{line.strip()[:100]}`")

        loc = len(lines)
        non_empty = len([l for l in lines if l.strip()])
        score = max(0, 100 - (len(findings) * 15))

        report = [
            f"### 🛡️ কোড কোয়ালিটি ও সিকিউরিটি অডিট রিপোর্ট ({language.upper()})",
            f"- **মোট লাইন:** `{loc}` (কার্যকর লাইন: `{non_empty}`)",
            f"- **সিকিউরিটি ও কোয়ালিটি স্কোর:** `{score}/100`",
            ""
        ]
        if findings:
            report.append("#### ⚠️ শনাক্তকৃত ঝুঁকি ও পরামর্শসমূহ:")
            report.extend(findings)
        else:
            report.append("✅ **চমৎকার!** কোনো স্পষ্ট হার্ডকোডেড সিক্রেট বা সিকিউরিটি ঝুঁকি পাওয়া যায়নি।")

        return "\n".join(report)

    @staticmethod
    def git_repo_inspector(max_commits: int = 5) -> str:
        """
        Inspects local Git workspace branch, latest commit history, uncommitted changes,
        and remote origin tracking URL.
        """
        try:
            def run_git(cmd_args):
                res = subprocess.run(
                    ["git"] + cmd_args,
                    capture_output=True, text=True, timeout=5
                )
                return res.stdout.strip() if res.returncode == 0 else f"(Git info unavailable: {res.stderr.strip()})"

            branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
            status = run_git(["status", "--short"])
            commits = run_git(["log", f"-n{max_commits}", "--oneline", "--decorate"])
            remote = run_git(["remote", "get-url", "origin"])

            return (
                f"### 🌿 গিট রিপোজিটরি ইন্সপেক্টর\n"
                f"- **রিমোট অরিজিন:** `{remote}`\n"
                f"- **বর্তমান ব্রাঞ্চ:** `{branch}`\n\n"
                f"**সাম্প্রতিক কমিটস (Top {max_commits}):**\n```text\n{commits}\n```\n"
                f"**অপরিবর্তিত/আনকমিটেড ফাইলস:**\n```text\n{status or 'Working tree clean'}\n```"
            )
        except Exception as e:
            return f"Git inspection note: {str(e)}"

    @staticmethod
    def generate_task_breakdown(goal: str, sprint_hours: int = 4) -> str:
        """
        Decomposes a high-level feature or engineering goal into structured,
        time-boxed sprint phases with priorities and verification checklists.
        """
        clean_goal = goal.strip()
        return (
            f"### 📅 স্ট্রাকচার্ড স্প্রিন্ট ও টাস্ক ব্রেকডাউন প্ল্যান ({sprint_hours}h Box)\n\n"
            f"**🎯 মূল লক্ষ্য (Goal):** {clean_goal}\n\n"
            f"| ধাপ (Phase) | সময় বরাদ্দ | অ্যাকশন আইটেম (Actionable Deliverables) | যাচাইকরণ (Verification Criteria) |\n"
            f"| :--- | :--- | :--- | :--- |\n"
            f"| **Phase 1: Discovery & Design** | 20% (~{round(sprint_hours*0.2, 1)}h) | প্রজেক্টের বিদ্যমান আর্কিটেকচার ও ডেটাবেজ স্কিমা বিশ্লেষণ (`get_project_info`) | আর্কিটেকচার ব্লুপ্রিন্ট ও স্কিমা ডায়াগ্রাম নিশ্চিত করা |\n"
            f"| **Phase 2: Core Implementation** | 50% (~{round(sprint_hours*0.5, 1)}h) | ব্যাকএন্ড API লজিক, টুল ডিসপ্যাচার এবং ইউনিট মডিউল তৈরি | সিনট্যাক্স কম্পাইল ও লজিক্যাল এন্ডপয়েন্ট টেস্ট |\n"
            f"| **Phase 3: Integration & UI** | 20% (~{round(sprint_hours*0.2, 1)}h) | ফ্রন্টএন্ড UI কানেক্টিভিটি এবং এরর হ্যান্ডলিং যুক্ত করা | ব্রাউজার ও API-তে সম্পূর্ণ ইউজার ফ্লো টেস্ট |\n"
            f"| **Phase 4: Audit & Deployment** | 10% (~{round(sprint_hours*0.1, 1)}h) | সিকিউরিটি অডিট, মেমোরিতে সেভ (`save_project_memory`) ও ডিপ্লয়মেন্ট | লাইভ সার্ভারে HTTP 200 ও স্ট্যাটাস ভেরিফিকেশন |"
        )

    @staticmethod
    async def list_available_skills(category: Optional[str] = None) -> str:
        """
        Lists all active domain skills stored in MyAgent's Operations Hub (ops_skills),
        optionally filtered by domain category.
        """
        try:
            from routers.ops_router import get_ops_db
            db = await get_ops_db()
            try:
                sql = "SELECT id, name, description, category, icon, triggers, is_toolset FROM ops_skills WHERE is_enabled = 1"
                params = []
                if category:
                    sql += " AND LOWER(category) LIKE ?"
                    params.append(f"%{category.strip().lower()}%")
                sql += " ORDER BY category, name"
                async with db.execute(sql, params) as cursor:
                    rows = await cursor.fetchall()
                    skills = [dict(r) for r in rows]
                    return json.dumps({
                        "total_active_skills": len(skills),
                        "category_filter": category or "ALL",
                        "skills": skills
                    }, ensure_ascii=False, indent=2)
            finally:
                await db.close()
        except Exception as e:
            return f"Failed to load skills library: {str(e)}"

    @staticmethod
    async def invoke_agent_skill(skill_name: str, task_context: str = "") -> str:
        """
        Retrieves full expert instructions, architecture rules, and trigger patterns
        for a specific skill from MyAgent Skills Library and prepares an execution directive.
        """
        try:
            from routers.ops_router import get_ops_db
            db = await get_ops_db()
            try:
                clean_s = skill_name.strip().lower()
                async with db.execute(
                    "SELECT * FROM ops_skills WHERE LOWER(name) = ? OR LOWER(id) = ? LIMIT 1",
                    (clean_s, clean_s)
                ) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        async with db.execute(
                            "SELECT * FROM ops_skills WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ? LIMIT 1",
                            (f"%{clean_s}%", f"%{clean_s}%")
                        ) as cursor2:
                            row = await cursor2.fetchone()
                    if not row:
                        return f"Skill '{skill_name}' not found in Skills Library. Call list_available_skills first."
                    skill = dict(row)
            finally:
                await db.close()

            return (
                f"### {skill.get('icon', '✨')} [SKILL ACTIVATED: {skill['name']}]\n"
                f"- **ক্যাটাগরি:** `{skill.get('category')}` | **সক্রিয় অবস্থা:** `{'ENABLED' if skill.get('is_enabled') else 'DISABLED'}`\n"
                f"- **বিবরণ:** {skill.get('description')}\n\n"
                f"#### 📋 এক্সিকিউশন গাইডলাইন ও নিয়মাবলী (Skill Instructions):\n"
                f"{skill.get('instructions')}\n\n"
                f"#### 🎯 প্রয়োগকৃত টাস্ক কনটেক্সট (Target Task):\n"
                f"{task_context or 'Apply this skill strictly to the current operational task.'}"
            )
        except Exception as e:
            return f"Skill invocation error: {str(e)}"

    @staticmethod
    async def create_daily_agent_task(
        task_name: str,
        daily_instruction: str,
        daily_time: str = "09:00",
        frequency: str = "daily",
        model: Optional[str] = None,
        project_name: Optional[str] = None,
        save_report: bool = True,
        save_memory: bool = False,
        post_to_chat: bool = True
    ) -> str:
        """Creates and activates an n8n-style daily autonomous agent workflow."""
        try:
            from workflows.store import WorkflowStore
            await WorkflowStore.init_tables_and_seed()
            wf = await WorkflowStore.build_quick_daily_workflow(
                name=task_name.strip() or "Daily AI Agent Task",
                instruction=daily_instruction.strip(),
                daily_time=daily_time,
                frequency=frequency,
                timezone_str="Asia/Dhaka",
                model=model or "",
                project_name=project_name or "",
                save_report=save_report,
                save_memory=save_memory,
                post_to_chat=post_to_chat
            )
            return json.dumps({
                "success": True,
                "workflow_id": wf["id"],
                "name": wf["name"],
                "schedule_expr": wf["schedule_expr"],
                "next_run": wf["next_run"],
                "timezone": wf["timezone"],
                "nodes_count": len(wf.get("nodes", [])),
                "message": f"Daily autonomous workflow '{wf['name']}' scheduled successfully."
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"Failed to create daily workflow: {str(e)}"

    @staticmethod
    async def list_workflows() -> str:
        """Lists all configured n8n-style autonomous workflows with schedule and stats."""
        try:
            from workflows.store import WorkflowStore
            await WorkflowStore.init_tables_and_seed()
            wfs = await WorkflowStore.list_workflows()
            summary = [
                {
                    "id": w["id"],
                    "name": w["name"],
                    "trigger_type": w["trigger_type"],
                    "schedule": w["schedule_expr"],
                    "is_enabled": w["is_enabled"],
                    "next_run": w.get("next_run"),
                    "last_run": w.get("last_run"),
                    "last_status": w.get("last_status"),
                    "run_count": w.get("run_count", 0),
                    "nodes_count": len(w.get("nodes", []))
                }
                for w in wfs
            ]
            return json.dumps({"total_workflows": len(summary), "workflows": summary}, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"Failed to list workflows: {str(e)}"

    @staticmethod
    async def run_workflow_now(workflow_id: str) -> str:
        """Executes a workflow DAG immediately via WorkflowEngine."""
        try:
            from workflows.engine import workflow_engine
            res = await workflow_engine.execute_workflow(workflow_id=workflow_id.strip(), trigger_source="mcp")
            return json.dumps({
                "success": res.get("success"),
                "run_id": res.get("run_id"),
                "status": res.get("status"),
                "duration_ms": res.get("duration_ms"),
                "final_output": res.get("final_output", "")[:2500],
                "steps": [
                    {"node_id": nr["node_id"], "title": nr["title"], "status": nr["status"], "ms": nr["duration_ms"]}
                    for nr in res.get("node_results", [])
                ]
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"Workflow execution error: {str(e)}"

    @staticmethod
    async def architect_workflow_from_goal(
        goal: str,
        name: Optional[str] = None,
        daily_time: str = "09:00",
        frequency: str = "daily",
        project_name: Optional[str] = None
    ) -> str:
        """Designs a complete multi-node branched n8n workflow DAG automatically from any natural-language goal."""
        try:
            from workflows.store import WorkflowStore
            await WorkflowStore.init_tables_and_seed()
            wf = await WorkflowStore.architect_workflow_from_goal(
                goal=goal,
                name=name or "",
                daily_time=daily_time or "09:00",
                frequency=frequency or "daily",
                timezone_str="Asia/Dhaka",
                project_name=project_name or "",
                auto_enable=True
            )
            return json.dumps({
                "success": True,
                "workflow_id": wf["id"],
                "name": wf["name"],
                "schedule_expr": wf["schedule_expr"],
                "next_run": wf["next_run"],
                "nodes_count": len(wf.get("nodes", [])),
                "edges_count": len(wf.get("edges", []))
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"Workflow architect error: {str(e)}"

    @staticmethod
    async def get_workflows_status_report() -> str:
        """Returns comprehensive WORKFLOWS (Auto) live status, schedules, and latest execution traces."""
        try:
            from workflows.store import WorkflowStore
            await WorkflowStore.init_tables_and_seed()
            digest = await WorkflowStore.build_workflows_status_report(max_workflows=12, max_runs=8)
            return digest.get("report_text", "") or json.dumps(digest, ensure_ascii=False)
        except Exception as e:
            return f"Failed to inspect workflows status: {str(e)}"

    @classmethod
    async def dispatch_tool(cls, tool_name: str, args: Dict[str, Any]) -> str:
        """Dynamically dispatches a tool call by name and executes it."""
        try:
            if tool_name == "query_company_memory":
                q = args.get("query", "")
                k = int(args.get("top_k", 4))
                hits = cls.query_company_memory(query=q, top_k=k)
                return json.dumps(hits, ensure_ascii=False, indent=2)

            elif tool_name == "save_company_memory":
                tags_input = args.get("tags", [])
                if isinstance(tags_input, str):
                    tags_input = [t.strip() for t in tags_input.split(",") if t.strip()]
                return cls.save_company_memory(
                    title=args.get("title", "Autonomous Saved Memory"),
                    content=args.get("content", ""),
                    category=args.get("category", "general"),
                    tags=tags_input,
                    security_level=args.get("security_level", "INTERNAL")
                )

            elif tool_name == "web_search":
                return await cls.web_search(args.get("query", ""))

            elif tool_name == "web_scrape":
                return await cls.web_scrape(args.get("url", ""))

            elif tool_name == "python_runner":
                return cls.python_runner(args.get("code", ""))

            elif tool_name == "calculate":
                return cls.calculate(args.get("expression", ""))

            elif tool_name == "analyze_big_data":
                return cls.analyze_big_data(
                    args.get("filepath", ""),
                    args.get("query_type", "summary"),
                    args.get("group_by"),
                    args.get("aggregate_col"),
                    args.get("agg_func", "sum")
                )

            elif tool_name == "smart_data_summarizer":
                return cls.smart_data_summarizer(args.get("filepath", ""))

            elif tool_name == "cross_document_comparator":
                return cls.cross_document_comparator(
                    args.get("doc1_path", ""),
                    args.get("doc2_path", ""),
                    args.get("topic")
                )

            elif tool_name == "visual_chart_generator":
                labels = args.get("data_labels", [])
                vals = [float(v) for v in args.get("data_values", [])]
                width = int(args.get("max_bar_width", 25))
                return cls.visual_chart_generator(
                    args.get("chart_type", "bar"),
                    args.get("title", "Visual Chart"),
                    labels,
                    vals,
                    width
                )

            elif tool_name == "generate_data_report":
                return cls.generate_data_report(
                    args.get("title", "Executive Report"),
                    args.get("report_markdown", ""),
                    args.get("filename")
                )

            elif tool_name == "read_pdf_document":
                return cls.read_pdf_document(args.get("filepath", ""), int(args.get("max_pages", 15)))

            elif tool_name == "read_word_document":
                return cls.read_word_document(args.get("filepath", ""))

            elif tool_name == "read_excel_spreadsheet":
                return cls.read_excel_spreadsheet(args.get("filepath", ""), args.get("sheet_name"), int(args.get("max_rows", 50)))

            elif tool_name == "read_image_ocr":
                return cls.read_image_ocr(args.get("filepath", ""))

            elif tool_name == "fs_list_files":
                return cls.fs_list_files(args.get("directory", ""))

            elif tool_name == "fs_read_file":
                return cls.fs_read_file(args.get("filepath", ""), int(args.get("max_chars", 5000)))

            elif tool_name == "fs_write_file":
                return cls.fs_write_file(args.get("filepath", ""), args.get("content", ""))

            elif tool_name == "sqlite_query":
                return cls.sqlite_query(args.get("query", ""), args.get("db_name", "chat_history.db"))

            elif tool_name == "system_info":
                return cls.system_info()

            elif tool_name == "delegate_to_subagent":
                return await cls.delegate_to_subagent(
                    subagent_id=args.get("subagent_id", "task_planner_agent"),
                    task=args.get("task", "")
                )
            elif tool_name == "execute_subagent_swarm":
                return await cls.execute_subagent_swarm(goal=args.get("goal", ""))
            elif tool_name == "ping_network_diagnostics":
                return await cls.ping_network_diagnostics(
                    target=args.get("target") or args.get("ip") or "192.168.9.1",
                    ping_type=args.get("ping_type", "icmp"),
                    port=int(args["port"]) if args.get("port") else None,
                    count=int(args.get("count", 3))
                )
            elif tool_name == "save_project_info":
                return await cls.save_project_info(
                    project_name=args.get("project_name", "myagent"),
                    description=args.get("description", ""),
                    display_name=args.get("display_name"),
                    tech_stack=args.get("tech_stack"),
                    architecture_blueprint=args.get("architecture_blueprint"),
                    urls=args.get("urls")
                )
            elif tool_name == "get_project_info":
                return await cls.get_project_info(project_name=args.get("project_name", "myagent"))
            elif tool_name == "list_all_projects":
                return await cls.list_all_projects()
            elif tool_name == "save_project_memory":
                return await cls.save_project_memory(
                    project_name=args.get("project_name", "myagent"),
                    key=args.get("key", "note"),
                    content=args.get("content", ""),
                    title=args.get("title"),
                    category=args.get("category", "general"),
                    context=args.get("context", "production"),
                    tags=args.get("tags"),
                    security_level=args.get("security_level", "INTERNAL")
                )
            elif tool_name == "get_project_memory":
                return await cls.get_project_memory(
                    project_name=args.get("project_name", "myagent"),
                    key=args.get("key", "")
                )
            elif tool_name == "search_project_memory":
                return await cls.search_project_memory(
                    project_name=args.get("project_name"),
                    category=args.get("category"),
                    context=args.get("context"),
                    query=args.get("query")
                )
            elif tool_name == "enhance_prompt":
                return cls.enhance_prompt(
                    prompt=args.get("prompt", ""),
                    mode=args.get("mode", "developer"),
                    target_audience=args.get("target_audience", "ai_agent")
                )
            elif tool_name == "network_port_scan":
                return await cls.network_port_scan(
                    target=args.get("target", "192.168.9.9"),
                    ports=args.get("ports"),
                    timeout_sec=float(args.get("timeout_sec", 0.8))
                )
            elif tool_name == "sqlite_schema_inspector":
                return cls.sqlite_schema_inspector(
                    db_name=args.get("db_name", "chat_history.db"),
                    table_name=args.get("table_name"),
                    explain_sql=args.get("explain_sql")
                )
            elif tool_name == "code_quality_and_security_audit":
                return cls.code_quality_and_security_audit(
                    code=args.get("code", ""),
                    language=args.get("language", "python")
                )
            elif tool_name == "git_repo_inspector":
                return cls.git_repo_inspector(
                    max_commits=int(args.get("max_commits", 5))
                )
            elif tool_name == "generate_task_breakdown":
                return cls.generate_task_breakdown(
                    goal=args.get("goal", ""),
                    sprint_hours=int(args.get("sprint_hours", 4))
                )
            elif tool_name == "list_available_skills":
                return await cls.list_available_skills(
                    category=args.get("category")
                )
            elif tool_name == "invoke_agent_skill":
                return await cls.invoke_agent_skill(
                    skill_name=args.get("skill_name", ""),
                    task_context=args.get("task_context", "")
                )
            elif tool_name == "create_daily_agent_task":
                return await cls.create_daily_agent_task(
                    task_name=args.get("task_name", "Daily Auto Task"),
                    daily_instruction=args.get("daily_instruction", ""),
                    daily_time=args.get("daily_time", "09:00"),
                    frequency=args.get("frequency", "daily"),
                    model=args.get("model"),
                    project_name=args.get("project_name"),
                    save_report=bool(args.get("save_report", True)),
                    save_memory=bool(args.get("save_memory", False)),
                    post_to_chat=bool(args.get("post_to_chat", True))
                )
            elif tool_name == "list_workflows":
                return await cls.list_workflows()
            elif tool_name == "run_workflow_now":
                return await cls.run_workflow_now(workflow_id=args.get("workflow_id", ""))
            elif tool_name == "architect_workflow_from_goal":
                return await cls.architect_workflow_from_goal(
                    goal=args.get("goal", ""),
                    name=args.get("name"),
                    daily_time=args.get("daily_time", "09:00"),
                    frequency=args.get("frequency", "daily"),
                    project_name=args.get("project_name")
                )
            elif tool_name == "get_workflows_status_report":
                return await cls.get_workflows_status_report()
            elif tool_name == "dns_lookup_diagnostics":
                from mcp.it_admin_tools import ITAdminTools
                r_types = args.get("record_types")
                if isinstance(r_types, str):
                    r_types = [x.strip() for x in r_types.split(",") if x.strip()]
                return await ITAdminTools.dns_lookup_diagnostics(
                    domain=args.get("domain", ""),
                    record_types=r_types,
                    use_doh=bool(args.get("use_doh", True))
                )
            elif tool_name == "ssl_tls_cert_inspector":
                from mcp.it_admin_tools import ITAdminTools
                return await ITAdminTools.ssl_tls_cert_inspector(
                    host=args.get("host", ""),
                    port=int(args.get("port", 443)),
                    timeout_sec=float(args.get("timeout_sec", 5.0))
                )
            elif tool_name == "http_endpoint_health_check":
                from mcp.it_admin_tools import ITAdminTools
                return await ITAdminTools.http_endpoint_health_check(
                    url=args.get("url", ""),
                    method=args.get("method", "GET"),
                    expected_status=int(args.get("expected_status", 200)),
                    timeout_sec=float(args.get("timeout_sec", 8.0)),
                    follow_redirects=bool(args.get("follow_redirects", True))
                )
            elif tool_name == "subnet_ip_calculator":
                from mcp.it_admin_tools import ITAdminTools
                return ITAdminTools.subnet_ip_calculator(cidr=args.get("cidr", ""))
            elif tool_name == "lan_subnet_discovery_scan":
                from mcp.it_admin_tools import ITAdminTools
                p_list = args.get("ports")
                if isinstance(p_list, str):
                    p_list = [int(p.strip()) for p in p_list.split(",") if p.strip().isdigit()]
                return await ITAdminTools.lan_subnet_discovery_scan(
                    subnet=args.get("subnet", "192.168.9.0/24"),
                    ports=p_list,
                    max_hosts=int(args.get("max_hosts", 32)),
                    start_offset=int(args.get("start_offset", 0)),
                    timeout_sec=float(args.get("timeout_sec", 0.45))
                )
            elif tool_name == "server_process_and_ports_audit":
                from mcp.it_admin_tools import ITAdminTools
                return await ITAdminTools.server_process_and_ports_audit(
                    top_n=int(args.get("top_n", 12)),
                    sort_by=args.get("sort_by", "memory"),
                    include_connections=bool(args.get("include_connections", True))
                )
            elif tool_name == "system_logs_inspector":
                from mcp.it_admin_tools import ITAdminTools
                return await ITAdminTools.system_logs_inspector(
                    log_source=args.get("log_source", "all"),
                    keyword=args.get("keyword"),
                    level=args.get("level", "ALL"),
                    tail_lines=int(args.get("tail_lines", 30))
                )
            elif tool_name == "network_traceroute_or_path":
                from mcp.it_admin_tools import ITAdminTools
                return await ITAdminTools.network_traceroute_or_path(
                    target=args.get("target", ""),
                    max_hops=int(args.get("max_hops", 12)),
                    timeout_sec=float(args.get("timeout_sec", 1.5))
                )
            elif tool_name == "it_security_utility":
                from mcp.it_admin_tools import ITAdminTools
                return ITAdminTools.it_security_utility(
                    action=args.get("action", "generate_password"),
                    value=args.get("value"),
                    length=int(args.get("length", 20)),
                    hash_alg=args.get("hash_alg", "sha256")
                )
            elif tool_name == "cron_schedule_and_maintenance_planner":
                from mcp.it_admin_tools import ITAdminTools
                return ITAdminTools.cron_schedule_and_maintenance_planner(
                    expression=args.get("expression", "0 3 * * *"),
                    count=int(args.get("count", 5))
                )
            elif tool_name == "save_sealed_device_credential":
                from mcp.sealed_vault import SealedDeviceVault
                saved = await SealedDeviceVault.save_device_credential(
                    device_name=args.get("device_name", ""),
                    host=args.get("host", ""),
                    username=args.get("username", ""),
                    password=args.get("password", ""),
                    device_type=args.get("device_type", "router"),
                    protocol=args.get("protocol", "http"),
                    port=int(args["port"]) if args.get("port") else None,
                    enable_secret=args.get("enable_secret", ""),
                    notes=args.get("notes", ""),
                    created_by="mcp_sealed_input"
                )
                return json.dumps({
                    "sealed": True,
                    "message": "Device login sealed with AES-256-GCM. AI models CANNOT retrieve the plaintext password.",
                    "device": saved
                }, ensure_ascii=False, indent=2)
            elif tool_name == "list_sealed_device_inventory":
                from mcp.sealed_vault import SealedDeviceVault
                items = await SealedDeviceVault.list_devices_safe(query=args.get("query"))
                return json.dumps({
                    "ai_access_policy": "ZERO-AI-LEAK (Only masked metadata is visible; plaintext passwords are blocked for all AI models)",
                    "total_devices": len(items),
                    "devices": items
                }, ensure_ascii=False, indent=2)
            elif tool_name == "verify_sealed_device_status":
                from mcp.sealed_vault import SealedDeviceVault
                res = await SealedDeviceVault.verify_device_with_sealed_credential(
                    device_or_host=args.get("device_or_host", "")
                )
                return json.dumps(res, ensure_ascii=False, indent=2)

            else:
                # Check dynamic MCP manager
                from mcp.manager import MCPManager
                return await MCPManager.call_tool(tool_name, args, server_id=args.get("_mcp_server_id"))
        except Exception as e:
            logger.error(f"Error dispatching tool {tool_name}: {e}")
            return f"Error executing tool '{tool_name}': {str(e)}"

    @classmethod
    def get_openai_tools_schema(cls) -> List[Dict[str, Any]]:
        """Returns standard OpenAI Function Calling tool definitions for all built-in tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "ping_network_diagnostics",
                    "description": "Network Sub-Agent: Pings and checks latency/status from Agent Server (192.168.9.9) to another IP address or domain.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target": {"type": "string", "description": "Target IP address or domain (e.g. 192.168.9.5, 192.168.9.1, 8.8.8.8)"},
                            "ping_type": {"type": "string", "enum": ["icmp", "tcp"], "description": "Type of ping: 'icmp' or 'tcp' port probe"},
                            "port": {"type": "integer", "description": "TCP port if ping_type is tcp (e.g. 80, 443, 3399, 445)"},
                            "count": {"type": "integer", "description": "Number of ping packets to send (default 3)"}
                        },
                        "required": ["target"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_project_info",
                    "description": "Stores or updates project metadata, description, tech stack, and architecture blueprint.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_name": {"type": "string", "description": "Unique project identifier (e.g. 48_otnarp, ampshop, myagent, arifmahmud.com)"},
                            "description": {"type": "string", "description": "High-level summary of the project's purpose and functionality"},
                            "display_name": {"type": "string", "description": "Human-readable project title"},
                            "tech_stack": {"type": "string", "description": "Technologies used (frontend, backend, database, docker, ports)"},
                            "architecture_blueprint": {"type": "string", "description": "Architectural structure, components, data flows, and build steps"},
                            "urls": {"type": "string", "description": "Live URLs, repository links, or API docs"}
                        },
                        "required": ["project_name", "description"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_project_info",
                    "description": "Retrieves comprehensive architectural overview, tech stack, and memory statistics for a specific project.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_name": {"type": "string", "description": "Target project identifier (e.g. 48_otnarp, ampshop, myagent)"}
                        },
                        "required": ["project_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_all_projects",
                    "description": "Lists all registered projects in the system along with their description and total memory counts.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_project_memory",
                    "description": "Persists key architectural facts, credentials, API endpoints, or database schemas tagged hierarchically by Project -> Category -> Context -> Key.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_name": {"type": "string", "description": "Project identifier (e.g. 48_otnarp, ampshop, myagent)"},
                            "key": {"type": "string", "description": "Logical specific key (e.g. admin_credentials, firebase_config, redis_port, db_schema)"},
                            "content": {"type": "string", "description": "Detailed text content of the fact, configuration, or credentials to remember"},
                            "title": {"type": "string", "description": "Brief descriptive title"},
                            "category": {"type": "string", "enum": ["auth", "database", "deployment", "credentials", "architecture", "api", "notes", "general"], "description": "Tag Level 2: Core category"},
                            "context": {"type": "string", "enum": ["production", "local", "staging", "admin", "test"], "description": "Tag Level 3: Environment or role context"},
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Search tags"
                            },
                            "security_level": {"type": "string", "enum": ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"], "description": "Security classification"}
                        },
                        "required": ["project_name", "key", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_project_memory",
                    "description": "Ultra-fast direct retrieval of a specific project memory fact by exact project name and key.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_name": {"type": "string", "description": "Project identifier"},
                            "key": {"type": "string", "description": "Exact key name to retrieve"}
                        },
                        "required": ["project_name", "key"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_project_memory",
                    "description": "Searches and filters saved memories across projects by project name, category, context, or keywords.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_name": {"type": "string", "description": "Optional project filter"},
                            "category": {"type": "string", "description": "Optional category filter (e.g. auth, database, deployment, credentials)"},
                            "context": {"type": "string", "description": "Optional context filter (e.g. production, local)"},
                            "query": {"type": "string", "description": "Keyword search across memory keys, titles, content, and tags"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "enhance_prompt",
                    "description": "Prompt Engineering Optimizer: Transforms rough instructions into elite, multi-layered, constraint-hardened AI prompts tailored to developer, architect, analysis, executive, or concise mode.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string", "description": "Raw user prompt or goal to enhance"},
                            "mode": {"type": "string", "enum": ["developer", "architect", "analysis", "executive", "concise"], "description": "Optimization persona/mode (default: developer)"},
                            "target_audience": {"type": "string", "description": "Target AI or reader e.g. ai_agent, claude, cursor"}
                        },
                        "required": ["prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "network_port_scan",
                    "description": "Asynchronously scans TCP ports on a target server IP from the Docker container (192.168.9.9) to detect open listening services and latency.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target": {"type": "string", "description": "Target IP or hostname (e.g. 192.168.9.9, 192.168.9.5, 192.168.9.1)"},
                            "ports": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "Optional custom list of port numbers (defaults to common service ports: 21, 22, 80, 443, 3306, 3399, 5432, 6379, 8000, 8080)"
                            },
                            "timeout_sec": {"type": "number", "description": "Socket connection timeout in seconds (default 0.8)"}
                        },
                        "required": ["target"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "sqlite_schema_inspector",
                    "description": "Inspects internal SQLite database schemas, table row counts, indexes, or executes EXPLAIN QUERY PLAN for SQL optimization.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "db_name": {"type": "string", "description": "Database filename (e.g. chat_history.db, ops.db, security_audit.db)"},
                            "table_name": {"type": "string", "description": "Optional specific table name to inspect columns and indexes"},
                            "explain_sql": {"type": "string", "description": "Optional SELECT query to analyze via EXPLAIN QUERY PLAN"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "code_quality_and_security_audit",
                    "description": "Static code analyzer auditing snippets for hardcoded secrets, SQL injection, eval/exec, insecure subprocesses, and code quality.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "description": "Source code string to audit"},
                            "language": {"type": "string", "description": "Programming language (e.g. python, javascript, sql, bash)"}
                        },
                        "required": ["code"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "git_repo_inspector",
                    "description": "Inspects current Git workspace branch, recent commits log, uncommitted changes, and remote tracking URL.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "max_commits": {"type": "integer", "description": "Number of recent commits to display (default 5)"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_task_breakdown",
                    "description": "Agile Sprint Planner: Decomposes complex goals into time-boxed 1h/4h milestone sprints with verification checklists.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal": {"type": "string", "description": "Feature or project goal to break down"},
                            "sprint_hours": {"type": "integer", "description": "Time box duration in hours (default 4)"}
                        },
                        "required": ["goal"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_available_skills",
                    "description": "Lists all 67+ specialized domain skills available in MyAgent's Operations Hub (Software Development, Productivity, Autonomous AI, Research, Creative).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "description": "Optional category filter (e.g. Software Development, Productivity, Autonomous AI Agents)"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "invoke_agent_skill",
                    "description": "Activates a specific domain skill from MyAgent's Skills Library (e.g. dockerfile-optimizer, prompt-engineering-optimizer, sql-query-profiler) and applies its instructions to a task.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "skill_name": {"type": "string", "description": "Exact skill name or keyword (e.g. prompt-engineering-optimizer, git-conflict-resolver, security-ast-scanner)"},
                            "task_context": {"type": "string", "description": "Specific task details to apply the skill onto"}
                        },
                        "required": ["skill_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_daily_agent_task",
                    "description": "Creates and schedules a daily n8n-style multi-node autonomous workflow so the AI agent executes the given task automatically every day (or hourly/weekly), archives reports, and posts digests.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_name": {"type": "string", "description": "Short descriptive title of the daily automated task"},
                            "daily_instruction": {"type": "string", "description": "Detailed task instructions the AI agent should execute automatically"},
                            "daily_time": {"type": "string", "description": "24-hour time HH:MM in Asia/Dhaka e.g. '09:00', '21:30' (default '09:00')"},
                            "frequency": {"type": "string", "enum": ["daily", "hourly", "every_6h", "weekly", "every_15m"], "description": "Execution frequency (default: daily)"},
                            "model": {"type": "string", "description": "Optional specific OpenRouter or local model ID"},
                            "project_name": {"type": "string", "description": "Optional project scope for memory context/saving"},
                            "save_report": {"type": "boolean", "description": "Archive output to AI Reports (default true)"},
                            "save_memory": {"type": "boolean", "description": "Persist daily summary into Project Memory (default false)"},
                            "post_to_chat": {"type": "boolean", "description": "Post daily output into chat automation digest (default true)"}
                        },
                        "required": ["task_name", "daily_instruction"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_workflows",
                    "description": "Lists all configured n8n-style automated daily workflows, their schedules, next run timestamps, and status.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "run_workflow_now",
                    "description": "Immediately triggers an n8n-style workflow by ID and returns per-node execution trace and output.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "workflow_id": {"type": "string", "description": "Target workflow ID from list_workflows"}
                        },
                        "required": ["workflow_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "architect_workflow_from_goal",
                    "description": "Automatically designs and schedules a branched multi-node n8n workflow DAG (ping/port scan/HTTP/Python/AI Agent/IF-Else/Alert/Report) from any complex goal.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal": {"type": "string", "description": "Full automation goal (servers to check, conditions, alerts, Python processing, etc.)"},
                            "name": {"type": "string", "description": "Optional workflow title"},
                            "daily_time": {"type": "string", "description": "HH:MM time in Asia/Dhaka (default 09:00)"},
                            "frequency": {"type": "string", "enum": ["daily", "hourly", "every_6h", "weekly", "every_15m"]},
                            "project_name": {"type": "string", "description": "Optional project memory context"}
                        },
                        "required": ["goal"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_company_memory",
                    "description": "Super-fast hybrid search into indexed company documents, policies, notes, and past records.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search keyword or question about company data"},
                            "top_k": {"type": "integer", "description": "Number of top chunks to retrieve (default: 4)"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_company_memory",
                    "description": "Autonomously saves a verified fact, policy, rule, credential, or finding into the company permanent hybrid memory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Concise descriptive title for the memory note"},
                            "content": {"type": "string", "description": "Full text details of the fact, rule, or information to record"},
                            "category": {"type": "string", "description": "Category tag e.g. policy, finance, operation, user_instruction, project"},
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of search keywords or entity tags"
                            },
                            "security_level": {
                                "type": "string",
                                "enum": ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"],
                                "description": "Data classification level (default: INTERNAL)"
                            }
                        },
                        "required": ["title", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Live DuckDuckGo web search for general knowledge. STRICT NOTE: Do NOT use for company data, business operations, or external companies. Company inquiries must strictly use query_company_memory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query for the web"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_scrape",
                    "description": "Fetches and cleans public web page contents using BeautifulSoup to extract text.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "Full HTTP or HTTPS URL to read"}
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "python_runner",
                    "description": "Executes Python code or mathematical formulas in a secure sandbox for statistics, calculations, or data formatting.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "description": "Python snippet or mathematical expression to evaluate"}
                        },
                        "required": ["code"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_big_data",
                    "description": "Analyzes tabular data files (CSV, TSV, Excel, JSON) using Pandas. Supports summary stats, head rows, column lists, missing nulls, group-by aggregation, and correlation matrix.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "Path or filename of the dataset (e.g. sales_2026.csv)"},
                            "query_type": {"type": "string", "enum": ["summary", "head", "columns", "nulls", "groupby", "correlation"], "description": "Type of analysis to perform"},
                            "group_by": {"type": "string", "description": "Column name to group by (for query_type='groupby')"},
                            "aggregate_col": {"type": "string", "description": "Numerical column to aggregate (for query_type='groupby')"},
                            "agg_func": {"type": "string", "enum": ["sum", "mean", "count", "min", "max"], "description": "Aggregation function"}
                        },
                        "required": ["filepath"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_data_report",
                    "description": "Compiles and writes a structured executive intelligence or analytical report file (.md) into data/reports for download.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Title of the executive report"},
                            "report_markdown": {"type": "string", "description": "Full markdown body of the report with tables and recommendations"},
                            "filename": {"type": "string", "description": "Target filename e.g. sales_summary_2026.md"}
                        },
                        "required": ["title", "report_markdown"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_pdf_document",
                    "description": "Reads and extracts text from a PDF file page by page.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "Path or filename of the PDF"}
                        },
                        "required": ["filepath"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_word_document",
                    "description": "Reads and extracts paragraphs and tables from a Word document (.docx).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "Path or filename of the Word document"}
                        },
                        "required": ["filepath"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_excel_spreadsheet",
                    "description": "Reads rows, columns, and sheets from Excel spreadsheets (.xlsx, .xls).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "Path or filename of the Excel sheet"},
                            "sheet_name": {"type": "string", "description": "Optional specific sheet name"}
                        },
                        "required": ["filepath"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_image_ocr",
                    "description": "Extracts text from images, photos, scanned documents, or screenshots using OCR.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "Path or filename of the image (.png, .jpg, .webp)"}
                        },
                        "required": ["filepath"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fs_list_files",
                    "description": "Lists stored documents and data files in the local data directory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "directory": {"type": "string", "description": "Subdirectory name (optional, defaults to root)"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fs_read_file",
                    "description": "Reads text, markdown, json, or code file contents from data storage.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "Filename or path of the file to read"},
                            "max_chars": {"type": "integer", "description": "Maximum number of characters to read (default: 5000)"}
                        },
                        "required": ["filepath"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fs_write_file",
                    "description": "Safely writes analysis notes or report files to the data/reports folder.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "Filename for the new file e.g. analysis.txt"},
                            "content": {"type": "string", "description": "Text content to write"}
                        },
                        "required": ["filepath", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "sqlite_query",
                    "description": "Executes read-only SELECT queries on internal SQLite databases.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "SQL SELECT query to execute"},
                            "db_name": {"type": "string", "description": "Database filename, default: chat_history.db"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "smart_data_summarizer",
                    "description": "Deep automated statistical profiler for tabular data (CSV, TSV, Excel, JSON). Returns dimensions, missing value ratios, numeric KPIs, and category distributions.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "Filename or path of dataset (e.g. sales.csv, accounts.xlsx)"}
                        },
                        "required": ["filepath"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "cross_document_comparator",
                    "description": "Cross-examines and compares two corporate documents, policies, or spreadsheets. Identifies structural differences, size, key overlapping topics, and differences.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "doc1_path": {"type": "string", "description": "Path or filename of first document"},
                            "doc2_path": {"type": "string", "description": "Path or filename of second document"},
                            "topic": {"type": "string", "description": "Optional specific topic or keyword to focus the comparison on"}
                        },
                        "required": ["doc1_path", "doc2_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "visual_chart_generator",
                    "description": "Generates text-based Unicode/ASCII visualizations (bar charts, gauges, trendlines) for immediate visual presentation in chat responses.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "chart_type": {"type": "string", "enum": ["bar", "gauge", "sparkline"], "description": "Type of chart: 'bar' (horizontal bar), 'gauge' (progress %), 'sparkline' (trend line)"},
                            "title": {"type": "string", "description": "Chart title"},
                            "data_labels": {"type": "array", "items": {"type": "string"}, "description": "List of category labels"},
                            "data_values": {"type": "array", "items": {"type": "number"}, "description": "List of numeric values corresponding to labels"},
                            "max_bar_width": {"type": "integer", "description": "Maximum width in characters (default 25)"}
                        },
                        "required": ["chart_type", "title", "data_labels", "data_values"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "system_info",
                    "description": "Returns Docker container runtime health: CPU load, RAM usage, and available disk space.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_workflows_status_report",
                    "description": "Returns comprehensive WORKFLOWS (Auto) live status, schedules, and latest autonomous run reports.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "dns_lookup_diagnostics",
                    "description": "IT Admin DNS & Email Audit: Resolves A, AAAA, MX, TXT, NS, CNAME, PTR records via OS DNS + DoH, and checks SPF/DMARC configuration.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "domain": {"type": "string", "description": "Domain name or IP address (e.g. itsupport.com.bd, 192.168.9.1)"},
                            "record_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "DNS record types to inspect (default: ['A', 'AAAA', 'MX', 'TXT', 'NS', 'CNAME'])"
                            },
                            "use_doh": {"type": "boolean", "description": "Also query Cloudflare/Google DNS-over-HTTPS for MX/TXT/SPF/DMARC (default: true)"}
                        },
                        "required": ["domain"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "ssl_tls_cert_inspector",
                    "description": "IT Admin SSL/TLS Inspector: Checks HTTPS/LDAPS/SMTPS certificate expiry countdown, issuer, SANs, cipher suite, SHA-256 fingerprint, and chain trust.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "host": {"type": "string", "description": "Hostname or IP address (e.g. itsupport.com.bd, google.com)"},
                            "port": {"type": "integer", "description": "TLS port number (default: 443; e.g. 465, 636, 993, 8443)"},
                            "timeout_sec": {"type": "number", "description": "Connection timeout in seconds (default: 5.0)"}
                        },
                        "required": ["host"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "http_endpoint_health_check",
                    "description": "IT Admin Endpoint Monitor: Measures HTTP/HTTPS status code, latency (ms), redirects, server headers, and OWASP security headers.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "Target HTTP/HTTPS URL (e.g. http://192.168.9.9:3399, https://itsupport.com.bd)"},
                            "method": {"type": "string", "enum": ["GET", "HEAD", "OPTIONS"], "description": "Safe read-only HTTP method (default: GET)"},
                            "expected_status": {"type": "integer", "description": "Expected HTTP status code (default: 200)"},
                            "timeout_sec": {"type": "number", "description": "Request timeout in seconds (default: 8.0)"},
                            "follow_redirects": {"type": "boolean", "description": "Follow HTTP 3xx redirects (default: true)"}
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "subnet_ip_calculator",
                    "description": "IT Admin IPv4/IPv6 Subnet Calculator: Computes network/broadcast addresses, subnet mask, wildcard mask, usable host range, total hosts, and RFC1918 scope.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cidr": {"type": "string", "description": "CIDR block or IP/Netmask (e.g. 192.168.9.0/24, 10.20.0.15/22, 172.16.1.0/255.255.255.128)"}
                        },
                        "required": ["cidr"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "lan_subnet_discovery_scan",
                    "description": "IT Admin Network Discovery: Asynchronously scans an IPv4 CIDR slice (up to 64 hosts) for live devices, reverse DNS hostnames, and open management ports (SSH, HTTP, SMB, RDP).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subnet": {"type": "string", "description": "IPv4 CIDR block to scan (default: 192.168.9.0/24)"},
                            "ports": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "TCP ports to probe per host (default: [22, 53, 80, 443, 445, 3389, 3399, 8000, 8080])"
                            },
                            "max_hosts": {"type": "integer", "description": "Number of hosts in slice to scan (1..64, default: 32)"},
                            "start_offset": {"type": "integer", "description": "Host offset in subnet to start scanning from (default: 0)"},
                            "timeout_sec": {"type": "number", "description": "Per-port probe timeout seconds (default: 0.45)"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "server_process_and_ports_audit",
                    "description": "IT Admin Host Telemetry: Audits top CPU/RAM processes, active listening TCP/UDP sockets, load average, and network interface RX/TX counters.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "top_n": {"type": "integer", "description": "Number of top processes to display (1..30, default: 12)"},
                            "sort_by": {"type": "string", "enum": ["memory", "cpu"], "description": "Sort processes by 'memory' or 'cpu' (default: memory)"},
                            "include_connections": {"type": "boolean", "description": "Include active listening TCP/UDP ports (default: true)"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "system_logs_inspector",
                    "description": "IT Admin Incident & Log Inspector: Inspects workflow execution failures, security audit logs, Telegram polling status, and container .log files with keyword/severity filters.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "log_source": {"type": "string", "enum": ["all", "workflows", "security", "telegram", "files"], "description": "Log subsystem to inspect (default: all)"},
                            "keyword": {"type": "string", "description": "Optional case-insensitive filter keyword"},
                            "level": {"type": "string", "enum": ["ALL", "ERROR", "WARNING", "FAILED", "SUCCESS"], "description": "Severity/status filter (default: ALL)"},
                            "tail_lines": {"type": "integer", "description": "Max entries to return per source (default: 30)"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "network_traceroute_or_path",
                    "description": "IT Admin Routing Path Trace: Safely traces hop-by-hop network routers, reverse DNS, and per-hop RTT latency to a target IP or hostname.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target": {"type": "string", "description": "Destination IP or hostname (e.g. 8.8.8.8, 192.168.9.1, google.com)"},
                            "max_hops": {"type": "integer", "description": "Maximum TTL hops to probe (1..25, default: 12)"},
                            "timeout_sec": {"type": "number", "description": "Timeout per hop in seconds (default: 1.5)"}
                        },
                        "required": ["target"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "it_security_utility",
                    "description": "IT Admin Security Utility: Generates high-entropy passwords or API/JWT tokens, calculates SHA/MD5 digests, audits password strength, or decodes JWT claims and expiry.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["generate_password", "generate_api_token", "hash_text", "check_password_strength", "inspect_jwt"],
                                "description": "Security utility action to perform"
                            },
                            "value": {"type": "string", "description": "Input string for hash_text, check_password_strength, or inspect_jwt"},
                            "length": {"type": "integer", "description": "Character/byte length for generated passwords/tokens (default: 20)"},
                            "hash_alg": {"type": "string", "enum": ["md5", "sha1", "sha256", "sha512"], "description": "Hash algorithm for hash_text (default: sha256)"}
                        },
                        "required": ["action"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "cron_schedule_and_maintenance_planner",
                    "description": "IT Admin Maintenance Scheduler: Validates 5-field cron expressions or aliases (@daily, @every_15m), explains them in English/Bangla, and lists next N Asia/Dhaka execution windows.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string", "description": "5-field cron expression or alias (e.g. '0 3 * * 1-5', '*/15 * * * *', '@daily')"},
                            "count": {"type": "integer", "description": "Number of upcoming maintenance runs to calculate (1..20, default: 5)"}
                        },
                        "required": ["expression"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_sealed_device_credential",
                    "description": "Zero-AI-Leak Device Vault: Encrypts and stores router/switch/firewall/server login credentials with AES-256-GCM. Once sealed, NO AI model or MCP client can ever read back the plaintext username/password.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "device_name": {"type": "string", "description": "Friendly device label (e.g. 'Office Core MikroTik Router')"},
                            "host": {"type": "string", "description": "Router/device IP address or hostname (e.g. 192.168.9.1)"},
                            "username": {"type": "string", "description": "Login username (immediately AES-256-GCM encrypted & sealed)"},
                            "password": {"type": "string", "description": "Login password (immediately AES-256-GCM encrypted & sealed)"},
                            "device_type": {"type": "string", "enum": ["router", "mikrotik", "switch", "firewall", "server", "nas", "ap", "other"], "description": "Device category (default: router)"},
                            "protocol": {"type": "string", "enum": ["http", "https", "ssh", "winbox", "routeros_rest", "routeros_api", "rdp", "telnet", "snmp"], "description": "Management protocol (default: http)"},
                            "port": {"type": "integer", "description": "Management port (auto-defaults by protocol e.g. 80/443/22/8291)"},
                            "enable_secret": {"type": "string", "description": "Optional enable password, PIN, or API secret"},
                            "notes": {"type": "string", "description": "Non-secret location/VLAN notes"}
                        },
                        "required": ["host", "username", "password"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_sealed_device_inventory",
                    "description": "AI-Blind Vault Inventory: Lists saved routers/devices with masked usernames and redacted password indicators ONLY. Plaintext credentials are strictly hidden from all AI models.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Optional search filter by device name, IP, or type"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "verify_sealed_device_status",
                    "description": "Blind MCP Proxy Check: Tests reachability/HTTP auth against a sealed router/device internally in backend memory without ever exposing plaintext credentials to the AI model.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "device_or_host": {"type": "string", "description": "Vault ID, device IP (e.g. 192.168.9.1), or device name"}
                        },
                        "required": ["device_or_host"]
                    }
                }
            }
        ]

    @classmethod
    async def get_all_tools_schema(cls) -> List[Dict[str, Any]]:
        """Returns standard OpenAI Function Calling tool definitions for all built-in tools AND active MCP servers."""
        schemas = list(cls.get_openai_tools_schema())
        try:
            from mcp.store import MCPStore
            servers = await MCPStore.list_servers()
            for s in servers:
                if not s.get("is_enabled", True):
                    continue
                for t in s.get("tools_cache", []):
                    t_name = t.get("name")
                    if not t_name:
                        continue
                    if any(existing.get("function", {}).get("name") == t_name for existing in schemas):
                        continue
                    schemas.append({
                        "type": "function",
                        "function": {
                            "name": t_name,
                            "description": f"[MCP: {s.get('name')}] {t.get('description', '')}",
                            "parameters": t.get("inputSchema", {"type": "object", "properties": {}})
                        }
                    })
        except Exception as e:
            logger.warning(f"Failed to append dynamic MCP tools schema: {e}")
        return schemas

