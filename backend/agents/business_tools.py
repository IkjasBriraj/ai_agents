"""
Business Tools
Agent tools wrapping presentation_service and excel_service for PowerPoint slide generation (.pptx & HTML Reveal.js)
and styled Excel workbook creation (.xlsx with formulas & charts).
"""

import os
import json
import logging
from typing import Dict, Any, Optional

from .config import DOCUMENTS_DIR, AGENT_WORKSPACE_DIR
from .session_context import current_agent_context

logger = logging.getLogger(__name__)


def generate_presentation(
    title: str = "Presentation",
    subtitle: str = "",
    slides_json: str = "",
    theme_color: str = "#1E3A8A",
    filename: str = "presentation"
) -> str:
    """
    Generate a PowerPoint presentation (.pptx) AND an interactive HTML presentation (.html).
    
    Args:
        title: Title of the presentation
        subtitle: Subtitle or tagline
        slides_json: JSON string representing slides list (type, title, bullets, metrics, table)
        theme_color: Brand primary hex color (e.g. #1E3A8A, #0F172A)
        filename: Base filename without extension (e.g. "pitch_deck", "q3_forecast")
    """
    try:
        from .presentation_service import create_powerpoint_deck, create_html_presentation

        # Clean filename
        safe_name = "".join(c for c in filename if c.isalnum() or c in ('_', '-')).strip() or "presentation"
        pptx_path = os.path.join(DOCUMENTS_DIR, f"{safe_name}.pptx")
        html_path = os.path.join(DOCUMENTS_DIR, f"{safe_name}.html")

        # Parse slides JSON
        slides = []
        if slides_json:
            try:
                slides = json.loads(slides_json)
            except Exception:
                try:
                    import ast
                    slides = ast.literal_eval(slides_json)
                except Exception:
                    slides = []

        if not slides or not isinstance(slides, list):
            slides = [
                {
                    "type": "title",
                    "title": title,
                    "subtitle": subtitle or "Executive Presentation Deck"
                },
                {
                    "type": "content",
                    "title": "Executive Summary & Market Opportunity",
                    "bullets": [
                        "Key Strategic Objectives & Core Value Proposition",
                        "Target Audience & Industry Growth Trends",
                        "Competitive Advantage & Differentiation"
                    ]
                },
                {
                    "type": "metrics",
                    "title": "Key Financial & Growth Metrics",
                    "metrics": [
                        {"label": "Target Revenue", "value": "$1.5M"},
                        {"label": "Gross Margin", "value": "65%"},
                        {"label": "Payback Period", "value": "8 Months"}
                    ]
                },
                {
                    "type": "content",
                    "title": "Strategic Roadmap & Next Steps",
                    "bullets": [
                        "Phase 1: Core Setup & Infrastructure Deployment",
                        "Phase 2: Product Launch & Customer Acquisition",
                        "Phase 3: Operational Scaling & Partnership Network"
                    ]
                }
            ]

        # Strict mandate: Enforce minimum 4 slides and maximum 30 slides
        if len(slides) > 30:
            slides = slides[:30]
        elif len(slides) < 4:
            fallback_slides = [
                {
                    "type": "title",
                    "title": title,
                    "subtitle": subtitle or "Executive Presentation Deck"
                },
                {
                    "type": "content",
                    "title": "Executive Summary & Market Analysis",
                    "bullets": [
                        "Key Strategic Objectives and Market Opportunity",
                        "Target Demographic and Customer Acquisition Strategy",
                        "Competitive Landscape and Growth Drivers"
                    ]
                },
                {
                    "type": "metrics",
                    "title": "Key Performance Metrics",
                    "metrics": [
                        {"label": "Projected Growth", "value": "150%"},
                        {"label": "Target Return", "value": "3.5x"},
                        {"label": "Efficiency", "value": "92%"}
                    ]
                },
                {
                    "type": "content",
                    "title": "Strategic Roadmap & Execution Plan",
                    "bullets": [
                        "Phase 1: Core Setup and Infrastructure Deployment",
                        "Phase 2: Product Launch and Market Penetration",
                        "Phase 3: Scale Operations and Expand Reach"
                    ]
                }
            ]
            for s in fallback_slides:
                if len(slides) >= 4:
                    break
                # Only append fallback slide if title doesn't already exist
                if not any(existing.get("title") == s.get("title") for existing in slides):
                    slides.append(s)

        spec = {
            "title": title,
            "subtitle": subtitle,
            "author": "Business Agent AI",
            "theme_color": theme_color,
            "slides": slides
        }

        # Build PPTX
        pptx_res = create_powerpoint_deck(spec, pptx_path)
        # Build HTML Reveal.js
        html_res = create_html_presentation(spec, html_path)

        pptx_url = f"/api/documents/{safe_name}.pptx"
        html_url = f"/api/documents/{safe_name}.html"

        # Stream document event to frontend
        ctx = current_agent_context.get()
        if ctx and "queue" in ctx and "loop" in ctx:
            ctx["loop"].call_soon_threadsafe(
                ctx["queue"].put_nowait,
                {
                    "type": "terminal_output",
                    "content": f"[Presentation Deck Generated]: {safe_name}.pptx ({len(slides)} slides) -- Interactive preview: {safe_name}.html",
                    "done": False
                }
            )

        report = [
            f"### [Presentation Deck Generated Successfully]",
            f"- **Title**: {title}",
            f"- **Slides Count**: {len(slides)}",
            f"- **PowerPoint File (.pptx)**: `{pptx_path}`",
            f"- **Download URL (.pptx)**: `{pptx_url}`",
            f"- **Interactive HTML Slide Deck**: `{html_path}`",
            f"- **Interactive Preview URL (.html)**: `{html_url}`"
        ]

        return "\n".join(report)
    except Exception as e:
        return f"Error generating presentation: {str(e)}"


def generate_excel_sheet(
    title: str = "Financial Spreadsheet",
    sheets_json: str = "",
    theme_color: str = "1E3A8A",
    filename: str = "spreadsheet"
) -> str:
    """
    Generate a styled Excel workbook (.xlsx) with formatting, formulas (SUM, AVERAGE), and charts.
    
    Args:
        title: Title of the workbook
        sheets_json: JSON string specifying sheets list (name, headers, data, chart)
        theme_color: Header fill color hex (e.g. "1E3A8A", "0F172A")
        filename: Base filename without extension (e.g. "financial_forecast", "budget_model")
    """
    try:
        from .excel_service import create_excel_workbook

        safe_name = "".join(c for c in filename if c.isalnum() or c in ('_', '-')).strip() or "spreadsheet"
        xlsx_path = os.path.join(DOCUMENTS_DIR, f"{safe_name}.xlsx")

        sheets = []
        if sheets_json:
            try:
                sheets = json.loads(sheets_json)
            except Exception:
                try:
                    import ast
                    sheets = ast.literal_eval(sheets_json)
                except Exception:
                    sheets = []

        if not sheets or not isinstance(sheets, list):
            sheets = [{
                "name": "Financial Overview",
                "title": title,
                "headers": ["Quarter", "Revenue ($)", "Expenses ($)", "Net Profit ($)"],
                "data": [
                    ["Q1 2026", 120000, 75000, "=B4-C4"],
                    ["Q2 2026", 160000, 85000, "=B5-C5"],
                    ["Q3 2026", 210000, 95000, "=B6-C6"],
                    ["Q4 2026", 280000, 110000, "=B7-C7"],
                    ["Total", "=SUM(B4:B7)", "=SUM(C4:C7)", "=SUM(D4:D7)"]
                ],
                "chart": {
                    "type": "column",
                    "title": "Quarterly Financial Performance"
                }
            }]

        spec = {
            "title": title,
            "theme_color": theme_color,
            "sheets": sheets
        }

        res = create_excel_workbook(spec, xlsx_path)

        if res.get("status") == "error":
            return f"Error creating Excel file: {res.get('error')}"

        xlsx_url = f"/api/documents/{safe_name}.xlsx"

        # Stream output event
        ctx = current_agent_context.get()
        if ctx and "queue" in ctx and "loop" in ctx:
            ctx["loop"].call_soon_threadsafe(
                ctx["queue"].put_nowait,
                {
                    "type": "terminal_output",
                    "content": f"[Excel Workbook Generated]: {safe_name}.xlsx ({len(sheets)} worksheets with formulas & charts)",
                    "done": False
                }
            )

        report = [
            f"### [Excel Workbook Generated Successfully]",
            f"- **Title**: {title}",
            f"- **Worksheets ({len(sheets)})**: {', '.join([s.get('name', 'Sheet') for s in sheets])}",
            f"- **File Path**: `{xlsx_path}`",
            f"- **Download URL (.xlsx)**: `{xlsx_url}`"
        ]

        return "\n".join(report)
    except Exception as e:
        return f"Error generating Excel sheet: {str(e)}"


def read_excel_sheet(filename_or_path: str) -> str:
    """Read data, worksheets, and cells from an Excel workbook (.xlsx)."""
    try:
        from .excel_service import read_excel_workbook

        file_path = filename_or_path
        if not os.path.isabs(file_path):
            file_path = os.path.join(DOCUMENTS_DIR, filename_or_path if filename_or_path.endswith(".xlsx") else f"{filename_or_path}.xlsx")
            if not os.path.exists(file_path):
                file_path = os.path.join(AGENT_WORKSPACE_DIR, filename_or_path)

        res = read_excel_workbook(file_path)

        if res.get("status") == "error":
            return f"Error reading Excel file: {res.get('error')}"

        output = [f"### [Excel Workbook Content]: {os.path.basename(file_path)}"]
        sheets = res.get("sheets", {})

        for s_name, rows in sheets.items():
            output.append(f"\n#### Worksheet: '{s_name}' ({len(rows)} rows)")
            if rows:
                headers = rows[0]
                output.append("| " + " | ".join(str(c) for c in headers) + " |")
                output.append("| " + " | ".join(["---"] * len(headers)) + " |")
                for r in rows[1:20]:
                    output.append("| " + " | ".join(str(c) for c in r) + " |")
                if len(rows) > 20:
                    output.append(f"*... {len(rows)-20} more rows.*")

        return "\n".join(output)
    except Exception as e:
        return f"Error reading Excel file: {str(e)}"
