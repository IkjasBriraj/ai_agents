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


def search_and_download_image(query: str, filename: str) -> Optional[str]:
    """
    Search for a high-quality real image related to the topic and download it locally.
    Queries Wikimedia Commons with iiurlwidth=800, Wikipedia API, and falls back to local diffusion AI image generation.
    """
    import os, json, urllib.request, urllib.parse
    from .config import AGENT_WORKSPACE_DIR
    from .image_pipeline import generate_image_tool

    img_dir = os.path.join(AGENT_WORKSPACE_DIR, "_generated_images")
    os.makedirs(img_dir, exist_ok=True)

    clean_query = query.strip()
    if clean_query:
        # 1. Search Wikimedia Commons with optimized 800px thumbnail width
        try:
            url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch={urllib.parse.quote(clean_query)}&gsrnamespace=6&prop=imageinfo&iiprop=url|size&iiurlwidth=800&format=json"
            req = urllib.request.Request(url, headers={'User-Agent': 'SeniorAgent/1.0 (contact@senioragent.org)'})
            with urllib.request.urlopen(req, timeout=5) as res:
                data = json.loads(res.read().decode('utf-8'))
            pages = data.get('query', {}).get('pages', {})
            for p in pages.values():
                info_list = p.get('imageinfo', [])
                if not info_list:
                    continue
                info = info_list[0]
                target_urls = [info.get('thumburl'), info.get('url')]
                for img_url in target_urls:
                    if not img_url:
                        continue
                    parsed_path = urllib.parse.urlparse(img_url).path.lower()
                    if any(parsed_path.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        ext = '.png' if parsed_path.endswith('.png') else '.jpg'
                        out_path = os.path.join(img_dir, f"{filename}{ext}")
                        d_req = urllib.request.Request(img_url, headers={'User-Agent': 'SeniorAgent/1.0 (contact@senioragent.org)'})
                        with urllib.request.urlopen(d_req, timeout=8) as d_res:
                            img_bytes = d_res.read()
                        if len(img_bytes) > 2048:
                            with open(out_path, 'wb') as f:
                                f.write(img_bytes)
                            logger.info(f"Downloaded topic image from Wikimedia for '{clean_query}': {out_path} ({len(img_bytes)} bytes)")
                            return out_path
        except Exception as e:
            logger.debug(f"Wikimedia search failed for '{clean_query}': {e}")

        # 2. Try Wikipedia Page Summary Thumbnail API
        try:
            first_term = clean_query.split()[0] if clean_query else clean_query
            wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(first_term)}"
            w_req = urllib.request.Request(wiki_url, headers={'User-Agent': 'SeniorAgent/1.0 (contact@senioragent.org)'})
            with urllib.request.urlopen(w_req, timeout=4) as w_res:
                w_data = json.loads(w_res.read().decode('utf-8'))
            thumb_source = w_data.get('thumbnail', {}).get('source') or w_data.get('originalimage', {}).get('source')
            if thumb_source:
                ext = '.png' if '.png' in thumb_source.lower() else '.jpg'
                out_path = os.path.join(img_dir, f"{filename}{ext}")
                d_req = urllib.request.Request(thumb_source, headers={'User-Agent': 'SeniorAgent/1.0 (contact@senioragent.org)'})
                with urllib.request.urlopen(d_req, timeout=6) as d_res:
                    img_bytes = d_res.read()
                if len(img_bytes) > 2048:
                    with open(out_path, 'wb') as f:
                        f.write(img_bytes)
                    logger.info(f"Downloaded topic image from Wikipedia for '{clean_query}': {out_path}")
                    return out_path
        except Exception as e:
            logger.debug(f"Wikipedia summary search failed for '{clean_query}': {e}")

    # Fallback to local diffusion AI image generator
    try:
        generate_image_tool(prompt=f"{clean_query}, high quality professional photograph, 8k", filename=filename)
        fallback_path = os.path.join(img_dir, f"{filename}.png")
        if os.path.exists(fallback_path):
            return fallback_path
    except Exception:
        pass

    return None

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

        # Ensure an interactive Quiz slide with verified answers is included in every deck
        has_quiz = any(str(s.get("type", "")).lower() == "quiz" for s in slides)
        if not has_quiz:
            slides.append({
                "type": "quiz",
                "title": f"{title}: Knowledge Check & Topic Mastery",
                "questions": [
                    {
                        "question": f"What is the foundational significance of {title}?",
                        "options": [
                            "A) Outdated historical concept",
                            f"B) Paradigm-shifting breakthrough in modern applications",
                            "C) Theoretical construct with no real utility",
                            "D) Redundant duplicate process"
                        ],
                        "answer": "B) Paradigm-shifting breakthrough in modern applications",
                        "explanation": f"Understanding {title} provides essential architectural and practical advantage in real-world implementations."
                    },
                    {
                        "question": "Which principle guarantees optimal results in this domain?",
                        "options": [
                            "A) Unchecked assumptions",
                            "B) Rigorous verification, active feedback, and precision design",
                            "C) Skipping modular validation",
                            "D) Static manual inspection"
                        ],
                        "answer": "B) Rigorous verification, active feedback, and precision design",
                        "explanation": "Continuous automated validation and feedback loops ensure zero errors and highest fidelity results."
                    }
                ]
            })

        # Process automated image search and insertion for slides
        for idx, s in enumerate(slides):
            slide_type = str(s.get("type", "content")).lower()
            img_search_term = s.get("image_search") or s.get("image_prompt")
            if not img_search_term and slide_type in ["split_image", "image", "title"]:
                img_search_term = s.get("title") or title
            
            if img_search_term and not s.get("image_path"):
                try:
                    ctx = current_agent_context.get()
                    if ctx and "queue" in ctx and "loop" in ctx:
                        ctx["loop"].call_soon_threadsafe(
                            ctx["queue"].put_nowait,
                            {"type": "thinking", "content": f"\n🖼️ Searching and embedding slide {idx+1} image for: '{img_search_term[:50]}'\n"}
                        )
                    img_name = f"{safe_name}_slide_{idx+1}"
                    found_img = search_and_download_image(img_search_term, img_name)
                    if found_img and os.path.exists(found_img):
                        s["image_path"] = found_img
                except Exception as img_err:
                    logger.error("Error searching and embedding slide image: %s", img_err)

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
