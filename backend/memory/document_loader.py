# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 2.2.0
# ==============================================================================

import os
import uuid
import re
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path
from pypdf import PdfReader
from docx import Document as DocxDocument
from config import settings

logger = logging.getLogger("myagent.document_loader")

class DocumentProcessor:
    """
    Enterprise multi-format document parser.
    Supports: PDF, Word (DOCX), Excel (XLSX/XLS), Big Data (CSV/JSON),
    and Photo/Image reading (PNG, JPG, WEBP) with OCR.
    """

    @staticmethod
    def extract_text(file_path: str) -> List[Tuple[str, int]]:
        """
        Extracts text from file.
        Returns a list of tuples: (text_content, page_number)
        """
        path = Path(file_path)
        ext = path.suffix.lower()
        extracted_pages: List[Tuple[str, int]] = []

        # 1. PDF Document Reader
        if ext == ".pdf":
            try:
                reader = PdfReader(file_path)
                for idx, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    clean_text = text.strip()
                    if clean_text:
                        extracted_pages.append((clean_text, idx + 1))
            except Exception as e:
                raise ValueError(f"Failed to read PDF file: {str(e)}")

        # 2. Word Document Reader (DOCX)
        elif ext in [".docx", ".doc"]:
            try:
                doc = DocxDocument(file_path)
                full_text = []
                for p in doc.paragraphs:
                    if p.text.strip():
                        full_text.append(p.text.strip())
                for table in doc.tables:
                    for row in table.rows:
                        row_text = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                        if row_text:
                            full_text.append(row_text)
                extracted_pages.append(("\n\n".join(full_text), 1))
            except Exception as e:
                raise ValueError(f"Failed to read DOCX file: {str(e)}")

        # 3. Excel Spreadsheets & Big Data Table Analysis (XLSX, XLS)
        elif ext in [".xlsx", ".xls"]:
            try:
                import pandas as pd
                sheets_text = []
                sheet_names = []
                try:
                    excel_file = pd.ExcelFile(file_path)
                    sheet_names = excel_file.sheet_names
                except Exception:
                    pass

                if sheet_names:
                    for sheet_name in sheet_names:
                        try:
                            df = pd.read_excel(file_path, sheet_name=sheet_name)
                            total_rows, total_cols = df.shape
                            col_list = [str(c) for c in df.columns]
                            sheet_header = f"### [Worksheet: {sheet_name}] (মোট {total_rows}টি রেকর্ড, {total_cols}টি কলাম: {', '.join(col_list)})\n"
                            
                            # Numeric Statistics Summary
                            num_summary = ""
                            try:
                                desc = df.describe()
                                if not desc.empty:
                                    num_summary = f"\n[পরিসংখ্যানগত সারসংক্ষেপ (Numeric Summary)]:\n{desc.to_string()}\n"
                            except Exception:
                                pass

                            # Top 25 rows as clean Markdown Table
                            top_df = df.head(25)
                            try:
                                md_table = top_df.to_markdown(index=False)
                            except Exception:
                                md_table = top_df.to_string(index=False)

                            # Detailed row-by-row lines for vector search
                            row_lines = []
                            for idx, row in df.head(200).iterrows():
                                pairs = [f"{col}: {row[col]}" for col in df.columns if pd.notna(row[col])]
                                if pairs:
                                    row_lines.append(f"[সারি {idx+1}]: " + ", ".join(pairs))

                            full_sheet_doc = sheet_header + num_summary + f"\n[ডাটা টেবিল নমুনা (First {min(25, total_rows)} Rows)]:\n{md_table}\n\n" + "\n".join(row_lines)
                            sheets_text.append(full_sheet_doc)
                        except Exception as sheet_err:
                            sheets_text.append(f"[Worksheet: {sheet_name}] লোড করতে ত্রুটি: {str(sheet_err)}")

                # Fallback to openpyxl if pandas yielded no sheets
                if not sheets_text:
                    from openpyxl import load_workbook
                    wb = load_workbook(file_path, data_only=True, read_only=True)
                    for sheet_name in wb.sheetnames:
                        ws = wb[sheet_name]
                        rows_data = []
                        for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
                            clean_row = [str(cell).strip() if cell is not None else "" for cell in row]
                            if any(clean_row):
                                rows_data.append(f"[Sheet {sheet_name}, Row {row_idx+1}]: " + " | ".join(clean_row))
                        if rows_data:
                            sheets_text.append("\n".join(rows_data[:250]))
                    wb.close()

                if sheets_text:
                    extracted_pages.append(("\n\n---\n\n".join(sheets_text), 1))
                else:
                    extracted_pages.append((f"[Excel File: {path.name}] (খালি অথবা রিড করা যায়নি)", 1))
            except Exception as e:
                raise ValueError(f"Failed to read Excel file: {str(e)}")

        # 4. Photos & Images OCR Reader (PNG, JPG, JPEG, WEBP, BMP, TIFF)
        elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
            try:
                from PIL import Image
                img = Image.open(file_path)
                image_info = f"[Photo/Image File: {path.name}, Dimensions: {img.width}x{img.height}, Format: {img.format or ext[1:].upper()}, Mode: {img.mode}]"
                
                # Preprocess image for OCR
                processed_img = img
                if processed_img.mode in ("RGBA", "P"):
                    processed_img = processed_img.convert("RGB")

                # Attempt OCR with pytesseract (Bangla + English)
                ocr_text = ""
                try:
                    import pytesseract
                    try:
                        ocr_text = pytesseract.image_to_string(processed_img, lang="eng+ben").strip()
                    except Exception:
                        ocr_text = pytesseract.image_to_string(processed_img, lang="eng").strip()
                except Exception as ocr_err:
                    logger.warning(f"Tesseract OCR notice: {ocr_err}")

                if ocr_text:
                    extracted_pages.append((f"{image_info}\n\n[ফটো থেকে প্রাপ্ত টেক্সট (Optical Character Recognition - OCR)]:\n{ocr_text}", 1))
                else:
                    extracted_pages.append((f"{image_info}\n\n[ফটো বিশ্লেষণ]: এই ছবিতে কোনো মুদ্রণযোগ্য টেক্সট সরাসরি সনাক্ত হয়নি। ছবিটি সফলভাবে কোম্পানি মিডিয়া লাইব্রেরিতে সংরক্ষিত হয়েছে।", 1))
            except Exception as e:
                raise ValueError(f"Failed to read Photo/Image file: {str(e)}")

        # 5. Big Data CSV / JSON / Plaintext
        elif ext in [".csv", ".tsv"]:
            try:
                import pandas as pd
                df = pd.read_csv(file_path, nrows=5000)
                summary_lines = [
                    f"[Big Data CSV Dataset: {path.name}]",
                    f"Total Rows Analyzed: {len(df)}, Columns: {list(df.columns)}",
                    f"Numerical Summary:\n{df.describe().to_string()}",
                    "\nSample Records:"
                ]
                for idx, row in df.head(100).iterrows():
                    summary_lines.append(f"Row {idx+1}: " + ", ".join([f"{col}={row[col]}" for col in df.columns if pd.notna(row[col])]))
                extracted_pages.append(("\n".join(summary_lines), 1))
            except Exception:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    extracted_pages.append((f.read().strip(), 1))

        elif ext in [".txt", ".md", ".json", ".yaml", ".yml", ".log"]:
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                    if content.strip():
                        extracted_pages.append((content.strip(), 1))
            except Exception as e:
                raise ValueError(f"Failed to read text file: {str(e)}")
        else:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if content.strip():
                        extracted_pages.append((content.strip(), 1))
            except Exception as e:
                raise ValueError(f"Unsupported file format: {ext} ({str(e)})")

        return extracted_pages

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
        """Splits long text into overlapping chunks respecting sentence boundaries."""
        if not text:
            return []
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chunk_size
            if end >= text_len:
                chunks.append(text[start:].strip())
                break

            slice_zone = text[start:end]
            punctuation_match = list(re.finditer(r'(\. |\n\n|\n|\? |! )', slice_zone))
            if punctuation_match and len(punctuation_match) > 0:
                last_punct = punctuation_match[-1]
                actual_end = start + last_punct.end()
            else:
                last_space = slice_zone.rfind(' ')
                if last_space != -1 and last_space > (chunk_size // 2):
                    actual_end = start + last_space
                else:
                    actual_end = end

            chunk_content = text[start:actual_end].strip()
            if chunk_content:
                chunks.append(chunk_content)

            start = actual_end - overlap
            if start < 0:
                start = 0
            if start >= text_len or actual_end == text_len:
                break

        return chunks

    @classmethod
    def process_file_into_chunks(cls, file_path: str, doc_id: str, original_filename: str) -> List[Dict[str, Any]]:
        """Processes a file and returns a list of chunk dictionaries ready for vector embedding."""
        pages = cls.extract_text(file_path)
        processed_chunks = []
        chunk_idx = 0

        for page_text, page_num in pages:
            chunks = cls.chunk_text(
                page_text,
                chunk_size=settings.CHUNKING_SIZE,
                overlap=settings.CHUNKING_OVERLAP
            )
            for chunk in chunks:
                chunk_idx += 1
                chunk_id = f"{doc_id}_chunk_{chunk_idx}"
                processed_chunks.append({
                    "id": chunk_id,
                    "doc_id": doc_id,
                    "filename": original_filename,
                    "page": page_num,
                    "chunk_index": chunk_idx,
                    "content": chunk
                })

        return processed_chunks

    @classmethod
    def generate_file_quick_summary(cls, file_path: str, filename: str) -> Dict[str, Any]:
        """
        Generates a quick, rich structural summary and preview of an uploaded file
        for immediate injection into chat prompt context and UI preview.
        """
        path = Path(file_path)
        ext = path.suffix.lower()
        size_bytes = os.path.getsize(file_path) if os.path.exists(file_path) else 0

        # Human-readable size
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

        file_type = "document"
        summary = f"নথি ফাইল: {filename} ({size_str})"
        preview_text = ""
        table_markdown = ""
        ocr_text = ""

        try:
            if ext in [".xlsx", ".xls"]:
                file_type = "excel"
                import pandas as pd
                try:
                    excel_file = pd.ExcelFile(file_path)
                    sheets = excel_file.sheet_names
                    first_df = pd.read_excel(file_path, sheet_name=sheets[0])
                    rows, cols = first_df.shape
                    summary = f"Excel স্প্রেডশিট: {len(sheets)}টি শিট ({', '.join(sheets[:3])})। প্রথম শিটে {rows}টি সারি ও {cols}টি কলাম রয়েছে।"
                    try:
                        table_markdown = first_df.head(15).to_markdown(index=False)
                    except Exception:
                        table_markdown = first_df.head(15).to_string()
                    preview_text = f"কলামসমূহ: {list(first_df.columns)}\n\nনমুনা ডাটা:\n{table_markdown}"
                except Exception as e:
                    summary = f"Excel ফাইল: {filename} ({size_str})"
                    preview_text = str(e)

            elif ext in [".csv", ".tsv"]:
                file_type = "excel"
                import pandas as pd
                try:
                    df = pd.read_csv(file_path, nrows=50)
                    rows, cols = df.shape
                    summary = f"CSV ডাটা টেবিল: {cols}টি কলাম ও {rows}+ রেকর্ড।"
                    try:
                        table_markdown = df.head(15).to_markdown(index=False)
                    except Exception:
                        table_markdown = df.head(15).to_string()
                    preview_text = f"কলামসমূহ: {list(df.columns)}\n\n{table_markdown}"
                except Exception:
                    summary = f"CSV ফাইল: {filename} ({size_str})"

            elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
                file_type = "photo"
                from PIL import Image
                img = Image.open(file_path)
                summary = f"ফটো/ছবি: {img.width}x{img.height} পিক্সেল ({img.format or ext[1:].upper()})"
                try:
                    import pytesseract
                    pimg = img.convert("RGB") if img.mode in ("RGBA", "P") else img
                    try:
                        ocr_text = pytesseract.image_to_string(pimg, lang="eng+ben").strip()
                    except Exception:
                        ocr_text = pytesseract.image_to_string(pimg, lang="eng").strip()
                    if ocr_text:
                        preview_text = f"[OCR নিষ্কাশিত টেক্সট]:\n{ocr_text[:800]}"
                        summary += f" • OCR টেক্সট প্রাপ্ত ({len(ocr_text)} অক্ষর)"
                    else:
                        preview_text = "(ছবিতে কোনো সরাসরি মুদ্রণযোগ্য টেক্সট সনাক্ত হয়নি)"
                except Exception:
                    preview_text = "(OCR প্রসেসিং উপলব্ধ নয়)"

            elif ext == ".pdf":
                file_type = "pdf"
                reader = PdfReader(file_path)
                num_pages = len(reader.pages)
                summary = f"PDF ডকুমেন্ট: মোট {num_pages}টি পৃষ্ঠা ({size_str})"
                first_page_text = reader.pages[0].extract_text() if num_pages > 0 else ""
                preview_text = first_page_text[:800].strip() if first_page_text else "(খালি পৃষ্ঠা)"

            elif ext in [".docx", ".doc"]:
                file_type = "word"
                doc = DocxDocument(file_path)
                paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
                summary = f"Word ডকুমেন্ট: {len(paras)}টি অনুচ্ছেদ ({size_str})"
                preview_text = "\n".join(paras[:5])[:800]

            else:
                file_type = "text"
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    preview_text = f.read(1000).strip()
                summary = f"টেক্সট ফাইল: {filename} ({size_str})"

        except Exception as err:
            logger.warning(f"Error generating quick summary for {filename}: {err}")
            summary = f"সংযুক্ত ফাইল: {filename} ({size_str})"
            preview_text = f"প্রসেসিং নোট: {str(err)}"

        return {
            "filename": filename,
            "file_type": file_type,
            "size_bytes": size_bytes,
            "size_str": size_str,
            "summary": summary,
            "preview_text": preview_text,
            "table_markdown": table_markdown,
            "ocr_text": ocr_text
        }

