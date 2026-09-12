import os
import uuid
import re
from typing import List, Dict, Any, Tuple
from pathlib import Path
from pypdf import PdfReader
from docx import Document as DocxDocument
from config import settings

class DocumentProcessor:
    """Extracts text from various file formats and generates semantic chunks with metadata."""

    @staticmethod
    def extract_text(file_path: str) -> List[Tuple[str, int]]:
        """
        Extracts text from file.
        Returns a list of tuples: (text_content, page_number)
        For non-paged documents, page_number is 1.
        """
        path = Path(file_path)
        ext = path.suffix.lower()
        extracted_pages: List[Tuple[str, int]] = []

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

        elif ext in [".xlsx", ".xls"]:
            try:
                from openpyxl import load_workbook
                wb = load_workbook(file_path, data_only=True, read_only=True)
                sheets_text = []
                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    rows_data = []
                    headers = []
                    for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
                        clean_row = [str(cell).strip() if cell is not None else "" for cell in row]
                        if not any(clean_row):
                            continue
                        if not headers:
                            headers = clean_row
                            rows_data.append(f"[Worksheet: {sheet_name}] Headers: " + " | ".join(headers))
                        else:
                            row_pairs = []
                            for i in range(min(len(headers), len(clean_row))):
                                if clean_row[i]:
                                    h_name = headers[i] if i < len(headers) and headers[i] else f"Col_{i+1}"
                                    row_pairs.append(f"{h_name}: {clean_row[i]}")
                            if row_pairs:
                                rows_data.append(f"[Sheet: {sheet_name}, Row {row_idx + 1}]: " + ", ".join(row_pairs))
                            else:
                                rows_data.append(f"[Sheet: {sheet_name}, Row {row_idx + 1}]: " + " | ".join(clean_row))
                    if rows_data:
                        sheets_text.append("\n".join(rows_data))
                wb.close()
                if sheets_text:
                    extracted_pages.append(("\n\n".join(sheets_text), 1))
            except Exception as e:
                raise ValueError(f"Failed to read Excel file: {str(e)}")

        elif ext in [".txt", ".md", ".json", ".csv", ".tsv", ".yaml", ".yml", ".log"]:
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                    if content.strip():
                        extracted_pages.append((content.strip(), 1))
            except Exception as e:
                raise ValueError(f"Failed to read text file: {str(e)}")
        else:
            # Fallback text attempt
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

            # Try to break at a natural sentence boundary (. ! ? \n)
            slice_zone = text[start:end]
            punctuation_match = list(re.finditer(r'(\. |\n\n|\n|\? |! )', slice_zone))
            if punctuation_match and len(punctuation_match) > 0:
                last_punct = punctuation_match[-1]
                actual_end = start + last_punct.end()
            else:
                # Fallback to last whitespace
                last_space = slice_zone.rfind(' ')
                if last_space != -1 and last_space > (chunk_size // 2):
                    actual_end = start + last_space
                else:
                    actual_end = end

            chunk_content = text[start:actual_end].strip()
            if chunk_content:
                chunks.append(chunk_content)

            # Advance with overlap
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
