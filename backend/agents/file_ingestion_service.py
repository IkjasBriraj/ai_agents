"""
File Ingestion Service for 'Drop-on-the-Orb' Workflows
Handles multi-modal drag-and-drop file ingestion: receipts, PDFs, spreadsheets, and code.
Automatically bridges receipts to Excel spreadsheets via excel_service.
"""

import os
import re
import json
import logging
import base64
from typing import Dict, Any, Optional

from .config import AGENT_WORKSPACE_DIR, get_workspace_path, VISION_MODEL
from .business_tools import generate_excel_sheet

logger = logging.getLogger(__name__)

class FileIngestionService:
    """Processes dropped files and extracts actionable intelligence."""

    def __init__(self, workspace_dir: str = AGENT_WORKSPACE_DIR):
        self.workspace_dir = workspace_dir

    def save_uploaded_file(self, filename: str, content_bytes: bytes) -> str:
        """Save dropped file into workspace under 'uploads' or root directory."""
        clean_filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)
        upload_dir = os.path.join(self.workspace_dir, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        target_path = os.path.join(upload_dir, clean_filename)

        with open(target_path, "wb") as f:
            f.write(content_bytes)

        return target_path

    def process_dropped_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze file type and extract text, structured tables, or receipts."""
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        filename = os.path.basename(file_path)
        rel_path = os.path.relpath(file_path, self.workspace_dir)
        ext = os.path.splitext(filename)[1].lower()
        size_bytes = os.path.getsize(file_path)

        # 1. Image / Receipt / Invoice
        if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
            return self._process_image(file_path, filename, rel_path, size_bytes)

        # 2. PDF Document
        elif ext == ".pdf":
            return self._process_pdf(file_path, filename, rel_path, size_bytes)

        # 3. CSV Spreadsheet
        elif ext == ".csv":
            return self._process_csv(file_path, filename, rel_path, size_bytes)

        # 4. Excel Workbook
        elif ext in [".xlsx", ".xls"]:
            return {
                "status": "success",
                "file_type": "spreadsheet",
                "filename": filename,
                "rel_path": rel_path,
                "size_bytes": size_bytes,
                "summary": f"Excel Workbook '{filename}' ({size_bytes // 1024} KB).",
                "suggested_prompt": f"Please inspect and summarize the data in spreadsheet '{rel_path}'."
            }

        # 5. Code & Text Files
        elif ext in [".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json", ".md", ".txt"]:
            return self._process_text_code(file_path, filename, rel_path, size_bytes, ext)

        return {
            "status": "success",
            "file_type": "general",
            "filename": filename,
            "rel_path": rel_path,
            "size_bytes": size_bytes,
            "summary": f"Uploaded file '{filename}'.",
            "suggested_prompt": f"I've uploaded '{rel_path}'. Please analyze its contents."
        }

    def _process_image(self, file_path: str, filename: str, rel_path: str, size_bytes: int) -> Dict[str, Any]:
        """Process images using local vision model to detect receipts or documents."""
        try:
            with open(file_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

            import httpx
            vision_prompt = (
                "Analyze this image. If it is a receipt or invoice, extract: "
                "Vendor, Date, Total, and line items (Item, Price, Quantity) formatted as a JSON object: "
                '{"is_receipt": true, "vendor": "...", "date": "...", "total": 0.0, "items": [{"item": "...", "price": 0.0, "qty": 1}]}. '
                "Otherwise, describe the image and extract all visible text."
            )

            res = httpx.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": VISION_MODEL,
                    "prompt": vision_prompt,
                    "images": [img_b64],
                    "stream": False
                },
                timeout=45.0
            )

            if res.status_code == 200:
                resp_text = res.json().get("response", "")
                
                # Check for receipt JSON
                json_match = re.search(r'(\{[\s\S]*\})', resp_text)
                if json_match:
                    try:
                        receipt_data = json.loads(json_match.group(1))
                        if receipt_data.get("is_receipt"):
                            # Auto-create Excel sheet
                            excel_info = self.convert_receipt_to_excel(receipt_data, filename)
                            return {
                                "status": "success",
                                "file_type": "receipt",
                                "filename": filename,
                                "rel_path": rel_path,
                                "size_bytes": size_bytes,
                                "summary": f"🧾 Receipt from {receipt_data.get('vendor', 'Unknown Vendor')} (Total: {receipt_data.get('total', 'N/A')}).",
                                "extracted_data": receipt_data,
                                "excel_generated": excel_info,
                                "suggested_prompt": f"I've uploaded receipt '{filename}'. Please review the extracted expenses and verify the generated spreadsheet."
                            }
                    except Exception:
                        pass

                return {
                    "status": "success",
                    "file_type": "image",
                    "filename": filename,
                    "rel_path": rel_path,
                    "size_bytes": size_bytes,
                    "summary": f"🖼️ Image Analysis: {resp_text[:180]}...",
                    "suggested_prompt": f"I uploaded '{filename}'. Here is the visual description: {resp_text[:120]}... What should we do with it?"
                }
        except Exception as e:
            logger.debug(f"Local vision processing skipped: {e}")

        return {
            "status": "success",
            "file_type": "image",
            "filename": filename,
            "rel_path": rel_path,
            "size_bytes": size_bytes,
            "summary": f"Image '{filename}' uploaded ({size_bytes // 1024} KB).",
            "suggested_prompt": f"I uploaded image '{rel_path}'. Please inspect and extract text from it."
        }

    def convert_receipt_to_excel(self, receipt_data: Dict[str, Any], origin_filename: str) -> str:
        """Create a styled Excel spreadsheet from extracted receipt items."""
        vendor = receipt_data.get("vendor", "Expense Report")
        date = receipt_data.get("date", "N/A")
        items = receipt_data.get("items", [])
        
        headers = ["Item Description", "Quantity", "Unit Price", "Total Amount"]
        rows = []
        for idx, it in enumerate(items, 2):
            name = it.get("item", f"Item {idx-1}")
            qty = it.get("qty", 1)
            price = it.get("price", 0.0)
            rows.append([name, qty, price, f"=B{idx}*C{idx}"])

        if not rows:
            rows.append(["Receipt Total", 1, receipt_data.get("total", 0.0), receipt_data.get("total", 0.0)])

        sheet_spec = {
            "name": "Expenses",
            "headers": headers,
            "rows": rows,
            "summary_row": {
                "label": "Grand Total",
                "formula": f"=SUM(D2:D{len(rows)+1})"
            }
        }

        out_name = f"receipt_{os.path.splitext(origin_filename)[0]}"
        try:
            return generate_excel_sheet(
                title=f"Receipt: {vendor} ({date})",
                sheets_json=json.dumps([sheet_spec]),
                theme_color="0D9488",
                filename=out_name
            )
        except Exception as e:
            logger.error(f"Failed to auto-generate excel from receipt: {e}")
            return f"Excel generation error: {e}"

    def _process_pdf(self, file_path: str, filename: str, rel_path: str, size_bytes: int) -> Dict[str, Any]:
        """Extract text and metadata from PDF files."""
        text_preview = ""
        total_pages = 1
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            total_pages = len(reader.pages)
            first_pages = [reader.pages[i].extract_text() or "" for i in range(min(3, total_pages))]
            text_preview = "\n".join(first_pages).strip()
        except Exception as e:
            text_preview = f"PDF text preview unavailable ({e})"

        summary = f"📄 PDF Document '{filename}' ({total_pages} pages, {size_bytes // 1024} KB)."
        return {
            "status": "success",
            "file_type": "pdf",
            "filename": filename,
            "rel_path": rel_path,
            "total_pages": total_pages,
            "size_bytes": size_bytes,
            "preview": text_preview[:400] + ("..." if len(text_preview) > 400 else ""),
            "summary": summary,
            "suggested_prompt": f"Please read and provide a senior-friendly summary of the PDF '{rel_path}'."
        }

    def _process_csv(self, file_path: str, filename: str, rel_path: str, size_bytes: int) -> Dict[str, Any]:
        """Process CSV files and provide column overview."""
        import csv
        row_count = 0
        headers = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                for i, row in enumerate(reader):
                    if i == 0:
                        headers = row
                    row_count += 1
        except Exception:
            pass

        return {
            "status": "success",
            "file_type": "csv",
            "filename": filename,
            "rel_path": rel_path,
            "size_bytes": size_bytes,
            "headers": headers,
            "row_count": max(0, row_count - 1),
            "summary": f"📊 CSV Spreadsheet '{filename}' ({max(0, row_count-1)} rows, {len(headers)} columns: {', '.join(headers[:4])}).",
            "suggested_prompt": f"I've uploaded CSV '{rel_path}'. Please analyze the trends and calculate key summaries."
        }

    def _process_text_code(self, file_path: str, filename: str, rel_path: str, size_bytes: int, ext: str) -> Dict[str, Any]:
        """Preview and analyze code or text files."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(500)
            lines = content.count("\n")
        except Exception:
            content = ""
            lines = 0

        type_label = "Source Code" if ext in [".py", ".js", ".ts", ".html", ".css"] else "Document"
        return {
            "status": "success",
            "file_type": "code" if ext in [".py", ".js", ".ts", ".html", ".css"] else "text",
            "filename": filename,
            "rel_path": rel_path,
            "size_bytes": size_bytes,
            "preview": content[:250],
            "summary": f"💻 {type_label} '{filename}' ({size_bytes // 1024} KB).",
            "suggested_prompt": f"I uploaded '{rel_path}'. Please review the code, check for any bugs, and suggest improvements."
        }

# Singleton instance
file_ingestion = FileIngestionService()
