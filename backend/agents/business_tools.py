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
            title_lower = title.lower()
            if any(kw in title_lower for kw in ["space", "cosmos", "universe", "astronomy", "planet", "galaxy", "star", "mars"]):
                slides = [
                    {"type": "title", "title": title, "subtitle": subtitle or "An Exploration of the Cosmos & Deep Space", "image_prompt": "A futuristic blueprint schematic of a space station orbiting a blue gas giant planet, 8k"},
                    {"type": "content", "title": "The Solar System & Planetary Dynamics", "bullets": ["Inner Terrestrial Planets (Mercury, Venus, Earth, Mars)", "Gas & Ice Giants (Jupiter, Saturn, Uranus, Neptune)", "Kuiper Belt and Oort Cloud Boundaries"]},
                    {"type": "pipeline", "title": "The Deep Space Pipeline", "steps": ["The Launch: Earth Orbit Insertion", "The Mission: Interplanetary Transit", "The Arrival: Surface Landing & Exploration"]},
                    {"type": "metrics", "title": "Cosmic Scale & Key Metrics", "metrics": [{"label": "Observable Universe", "value": "93B Light Yrs"}, {"label": "Milky Way Stars", "value": "100B+"}, {"label": "JWST Range", "value": "13.5B Yrs Back"}]},
                    {"type": "split_image", "title": "Space Exploration Frontiers", "subtitle": "From Digital Blueprints to Cosmic Reality", "bullets": ["Apollo & Artemis Lunar Base Infrastructure", "Robotic Probes: Mars Rovers & JWST Deep Field", "Next-Gen Propulsion: Fusion & Ion Thrusters"], "image_prompt": "A high-tech 3D printer extruding a blue geometric spacecraft model with technical blueprint callouts, photorealistic 8k"}
                ]
            elif any(kw in title_lower for kw in ["ai", "agent", "tech", "code", "software", "machine learning", "robot", "senioragent", "orchestrator"]):
                slides = [
                    {"type": "title", "title": title, "subtitle": subtitle or "The Local-First Agentic OS", "image_prompt": "A technical blueprint diagram showing system root folder tree connected to modular UI wireframes, blueprint style 8k"},
                    {"type": "pipeline", "title": "The Local Engine Pipeline", "steps": ["The Brain: Ollama running local LLMs on Port 11434", "The Backend: Python & FastAPI handling logic on Port 8000", "The Frontend: Node.js & React powering UI on Port 5173"]},
                    {"type": "split_image", "title": "The Future of Accessible Autonomy", "subtitle": "Bridging Multi-Agent Workflows & Senior Accessibility", "bullets": ["Digital Accessibility: Dignity and deliberate design", "Total User Control: Full local sandbox execution", "Next-Gen Agentic AI: Autonomous code generation"], "image_prompt": "A 3D hexagonal blue pillar labeled SeniorAgent flanked by digital accessibility boxes and agentic AI tree diagram, blueprint 8k"}
                ]
            else:
                slides = [
                    {"type": "title", "title": title, "subtitle": subtitle or "Executive Strategy & Analysis Deck", "image_prompt": "A modern technical blueprint graphic showing interconnected business strategy nodes and analytics charts, 8k"},
                    {"type": "content", "title": "Executive Summary & Core Objectives", "bullets": ["Strategic Vision and Market Opportunities", "Target Audience & Growth Drivers", "Competitive Advantage & Differentiation"]},
                    {"type": "metrics", "title": "Key Performance Indicators", "metrics": [{"label": "Target Growth", "value": "150%"}, {"label": "Efficiency Gain", "value": "45%"}, {"label": "Payback Period", "value": "6 Months"}]},
                    {"type": "split_image", "title": "Strategic Execution & Growth", "subtitle": "From Blueprint to Production Execution", "bullets": ["Phase 1: Foundation & Core Infrastructure", "Phase 2: Market Deployment & User Scaling", "Phase 3: Operational Optimization & Growth"], "image_prompt": "A high-tech robotic arm 3D printing a precision mechanical gear on a blueprint grid with technical callout annotations, 8k"}
                ]

        # Process automated image generation for slides with image_prompt specifications
        from .image_pipeline import generate_image_tool
        for idx, s in enumerate(slides):
            img_prompt = s.get("image_prompt")
            if img_prompt and not s.get("image_path"):
                try:
                    # Stream progress notification
                    ctx = current_agent_context.get()
                    if ctx and "queue" in ctx and "loop" in ctx:
                        ctx["loop"].call_soon_threadsafe(
                            ctx["queue"].put_nowait,
                            {"type": "thinking", "content": f"\n🎨 Generating slide {idx+1} image: '{img_prompt[:60]}...'...\n"}
                        )
                    img_name = f"{safe_name}_slide_{idx+1}"
                    img_res = generate_image_tool(prompt=img_prompt, filename=img_name)
                    
                    # Extract saved image path
                    generated_img_path = os.path.join(AGENT_WORKSPACE_DIR, "_generated_images", f"{img_name}.png")
                    if os.path.exists(generated_img_path):
                        s["image_path"] = generated_img_path
                except Exception as img_err:
                    logger.error("Error generating slide image: %s", img_err)

        spec = {
            "title": title,
            "subtitle": subtitle,
            "author": "Business Agent AI",
            "theme_style": "notebooklm",
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
                    "content": f"[NotebookLM Presentation Generated]: {safe_name}.pptx ({len(slides)} slides) -- Interactive preview: {safe_name}.html",
                    "done": False
                }
            )

        report = [
            f"### 🚀 [NotebookLM Presentation Deck Generated Successfully]",
            f"- **Title**: {title}",
            f"- **Style**: NotebookLM Technical Blueprint Layout",
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
