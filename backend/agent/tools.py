# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.0.0
import os
import sys
import math
import time
import json
import sqlite3
import logging
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
    async def dispatch_tool(cls, tool_name: str, args: Dict[str, Any]) -> str:
        """Dynamically dispatches a tool call by name and executes it."""
        try:
            if tool_name == "query_company_memory":
                q = args.get("query", "")
                k = int(args.get("top_k", 4))
                hits = cls.query_company_memory(query=q, top_k=k)
                return json.dumps(hits, ensure_ascii=False, indent=2)

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

            else:
                # Check dynamic MCP manager
                from mcp.manager import MCPManager
                return await MCPManager.call_tool(tool_name, args)
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

