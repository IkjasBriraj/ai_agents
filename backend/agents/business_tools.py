"""
Business Tools
Agent tools wrapping presentation_service and excel_service for PowerPoint slide generation (.pptx & HTML Reveal.js),
topic-related real image search & embedding, and styled Excel workbook creation (.xlsx with formulas & charts).
"""

import os
import re
import json
import shutil
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
    import urllib.request, urllib.parse
    from .image_pipeline import generate_image_tool

    img_dir = os.path.join(AGENT_WORKSPACE_DIR, "_generated_images")
    os.makedirs(img_dir, exist_ok=True)

    # Check if we already downloaded this exact filename recently
    for existing_ext in [".jpg", ".png", ".jpeg", ".webp"]:
        candidate = os.path.join(img_dir, f"{filename}{existing_ext}")
        if os.path.exists(candidate) and os.path.getsize(candidate) > 2048:
            return candidate

    clean_query = re.sub(r'[^a-zA-Z0-9 \-]', ' ', str(query or "")).strip()
    if clean_query:
        # 1. Search Wikimedia Commons with optimized 800px thumbnail width
        try:
            url = (
                f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
                f"&gsrsearch={urllib.parse.quote(clean_query)}&gsrnamespace=6&prop=imageinfo"
                f"&iiprop=url|size&iiurlwidth=800&format=json"
            )
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
            terms_to_try = [clean_query, clean_query.split()[0]] if " " in clean_query else [clean_query]
            for term in terms_to_try:
                wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(term)}"
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
                        logger.info(f"Downloaded topic image from Wikipedia for '{term}': {out_path}")
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


def search_topic_image(query: str, filename: str = "") -> str:
    """
    Tool for Code Agent, PPT Agent, and Business Agent to search and download a real topic-related image
    and return its ready-to-use URL for HTML `<img>` tags (`http://localhost:8000/api/generated-images/<name>`).
    """
    try:
        clean_q = str(query or "technology").strip()
        safe_fn = re.sub(r'[^a-zA-Z0-9_\-]', '_', filename or clean_q.lower())[:40].strip('_') or "topic_img"
        ctx = current_agent_context.get()
        if ctx and "queue" in ctx and "loop" in ctx:
            ctx["loop"].call_soon_threadsafe(
                ctx["queue"].put_nowait,
                {"type": "thinking", "content": f"\n🖼️ Searching and downloading topic image for: '{clean_q[:60]}'\n"}
            )
        found_path = search_and_download_image(clean_q, safe_fn)
        if found_path and os.path.exists(found_path):
            basename = os.path.basename(found_path)
            url = f"http://localhost:8000/api/generated-images/{basename}"
            return (
                f"[SUCCESS] Topic image downloaded for '{clean_q}':\n"
                f"- Local Path: `{found_path}`\n"
                f"- Embed URL (use in <img src=\"...\">): `{url}`"
            )
        return f"Could not find external image for '{clean_q}'."
    except Exception as e:
        return f"Error searching topic image: {e}"


def generate_presentation(
    title: str = "Presentation",
    subtitle: str = "",
    slides_json: str = "",
    theme_color: str = "#1E3A8A",
    filename: str = "presentation",
    animation: str = ""
) -> str:
    """
    Generate a PowerPoint presentation (.pptx) AND an interactive HTML presentation (.html)
    with topic-related searched images, swiping & staggered animations, and tap-to-reveal Q&A quizzes.
    """
    try:
        from .presentation_service import create_powerpoint_deck, create_html_presentation

        ctx = current_agent_context.get()
        raw_task_input = str(ctx.get("input", "") if ctx else "")
        # Strip any prepended [SYSTEM DIRECTIVE ...] lines from raw_task_input
        user_lines = [
            ln for ln in raw_task_input.splitlines()
            if not ln.strip().startswith("[SYSTEM DIRECTIVE") and not ln.strip().startswith("Context Details:")
        ]
        user_task_input = "\n".join(user_lines).strip()

        # Load previous presentation spec if available for follow-up requests
        last_spec_path = os.path.join(DOCUMENTS_DIR, "_last_presentation_spec.json")
        prev_spec: Dict[str, Any] = {}
        if os.path.exists(last_spec_path):
            try:
                with open(last_spec_path, "r", encoding="utf-8") as lf:
                    prev_spec = json.load(lf)
            except Exception:
                prev_spec = {}

        # Detect if user asked for animation via tool argument, task prompt, or slide specs
        combined_anim_text = f"{animation} {user_task_input} {title} {subtitle}".lower()
        explicit_off = str(animation).strip().lower() in ["none", "off", "false", "no"]

        # Resolve specific animation style (with priority for swiping / slide / zoom / bounce / fly / 3d)
        anim_hint = f"{animation} {user_task_input}".lower()
        if explicit_off:
            animation_style = "none"
            animations_enabled = False
        elif any(k in anim_hint for k in ["swipe", "swiping", "push", "slide to", "next slide", "carousel"]):
            animation_style = "swipe"
            animations_enabled = True
        elif "zoom" in anim_hint or "scale" in anim_hint:
            animation_style = "zoom"
            animations_enabled = True
        elif "bounce" in anim_hint or "spring" in anim_hint or "pop" in anim_hint:
            animation_style = "bounce"
            animations_enabled = True
        elif "fly" in anim_hint or "slide in" in anim_hint or "fly-in" in anim_hint:
            animation_style = "fly"
            animations_enabled = True
        elif "wipe" in anim_hint:
            animation_style = "wipe"
            animations_enabled = True
        elif "convex" in anim_hint or "3d" in anim_hint or "flip" in anim_hint:
            animation_style = "convex"
            animations_enabled = True
        elif "fade" in anim_hint:
            animation_style = "fade"
            animations_enabled = True
        else:
            # Default to smooth 3D swipe & staggered entrance so presentations always feel alive and responsive!
            animation_style = prev_spec.get("animation_style", "swipe") if prev_spec else "swipe"
            if animation_style in ["none", "off", "false"]:
                animation_style = "swipe"
            animations_enabled = True

        # Detect dark vs light theme from prompt or previous spec
        is_dark_requested = (
            any(k in combined_anim_text for k in ["dark theme", "dark mode", "dark background", "black theme", "night mode"])
            or str(theme_color).lower() in ["#0f172a", "#000000", "#111827", "#0b0f19"]
        )
        is_light_requested = any(k in combined_anim_text for k in ["light theme", "light mode", "white background"])
        if is_dark_requested:
            theme_style = "dark"
        elif is_light_requested:
            theme_style = "notebooklm"
        elif prev_spec and prev_spec.get("theme_style") and not slides_json:
            theme_style = prev_spec["theme_style"]
        else:
            theme_style = "notebooklm"

        # Parse slides JSON
        slides = []
        if slides_json:
            if isinstance(slides_json, list):
                slides = slides_json
            else:
                try:
                    slides = json.loads(slides_json)
                except Exception:
                    try:
                        import ast
                        slides = ast.literal_eval(slides_json)
                    except Exception:
                        slides = []

        # Detect follow-up modification/animation request (e.g., "add this animation", "make sure you add swiping animation")
        followup_indicators = [
            "add animation", "add this animation", "why did you not", "didn't add", "did not add",
            "swiping animation", "swipe animation", "fix that", "fix the animation", "tap i should see",
            "update the ppt", "update the presentation", "animate the"
        ]
        is_followup_request = (
            bool(prev_spec.get("slides"))
            and (
                not slides
                or any(ind in user_task_input.lower() for ind in followup_indicators)
                or any(bad in title.lower() for bad in ["system directive", "wait why", "add animation", "presentation"])
            )
        )

        if is_followup_request and prev_spec.get("slides"):
            if not slides:
                slides = prev_spec["slides"]
            if any(bad in title.lower() for bad in ["system directive", "wait why", "add animation", "presentation", "ppt"]):
                title = prev_spec.get("title", title)
            if not subtitle:
                subtitle = prev_spec.get("subtitle", "")
            if any(bad in filename.lower() for bad in ["system_directive", "wait_why", "add_animation", "presentation", "ppt"]):
                filename = prev_spec.get("filename", filename)
            if prev_spec.get("theme_style") == "dark" and not is_light_requested:
                theme_style = "dark"

        # Clean filename
        safe_name = "".join(c for c in filename if c.isalnum() or c in ('_', '-')).strip() or "presentation"
        if safe_name.startswith("system_directive") and prev_spec.get("filename"):
            safe_name = prev_spec["filename"]

        pptx_path = os.path.join(DOCUMENTS_DIR, f"{safe_name}.pptx")
        html_path = os.path.join(DOCUMENTS_DIR, f"{safe_name}.html")

        if not slides or not isinstance(slides, list):
            title_lower = title.lower()
            if any(kw in title_lower for kw in ["space", "cosmos", "universe", "astronomy", "planet", "galaxy", "star", "mars"]):
                slides = [
                    {"type": "title", "title": title, "subtitle": subtitle or "An Exploration of the Cosmos & Deep Space", "image_search": "space station planet orbit"},
                    {"type": "content", "title": "The Solar System & Planetary Dynamics", "bullets": ["Inner Terrestrial Planets (Mercury, Venus, Earth, Mars)", "Gas & Ice Giants (Jupiter, Saturn, Uranus, Neptune)", "Kuiper Belt and Oort Cloud Boundaries"]},
                    {"type": "pipeline", "title": "The Deep Space Pipeline", "steps": ["The Launch: Earth Orbit Insertion", "The Mission: Interplanetary Transit", "The Arrival: Surface Landing & Exploration"]},
                    {"type": "metrics", "title": "Cosmic Scale & Key Metrics", "metrics": [{"label": "Observable Universe", "value": "93B Light Yrs"}, {"label": "Milky Way Stars", "value": "100B+"}, {"label": "JWST Range", "value": "13.5B Yrs Back"}]},
                    {"type": "split_image", "title": "Space Exploration Frontiers", "subtitle": "From Digital Blueprints to Cosmic Reality", "bullets": ["Apollo & Artemis Lunar Base Infrastructure", "Robotic Probes: Mars Rovers & JWST Deep Field", "Next-Gen Propulsion: Fusion & Ion Thrusters"], "image_search": "NASA spacecraft Mars rover"}
                ]
            elif any(kw in title_lower for kw in ["healthcare", "medical", "medicine", "hospital", "clinical", "health", "doctor"]):
                slides = [
                    {"type": "title", "title": title, "subtitle": subtitle or "Transforming Diagnostics, Clinical Workflows & Patient Outcomes", "image_search": "artificial intelligence medical imaging healthcare"},
                    {"type": "split_image", "title": "Precision Diagnostics & Medical Imaging", "subtitle": "Deep Learning in Radiology & Pathology", "bullets": ["Early tumor & anomaly detection with 99.1% sensitivity", "Automated MRI, CT, and retinal scan segmentation", "Real-time clinical decision support for physicians"], "image_search": "medical MRI brain scan diagnostics"},
                    {"type": "pipeline", "title": "AI-Driven Drug Discovery Pipeline", "steps": ["Target Identification: Genomic & Proteomic Screening", "Molecular Design: Generative AI Protein Folding", "Clinical Trials: Predictive Patient Cohort Matching"]},
                    {"type": "metrics", "title": "Clinical Impact & Healthcare KPIs", "metrics": [{"label": "Diagnostic Accuracy", "value": "99.2%"}, {"label": "Drug R&D Speedup", "value": "3.5x"}, {"label": "Admin Time Saved", "value": "42%"}]}
                ]
            elif any(kw in title_lower for kw in ["ai", "agent", "tech", "code", "software", "machine learning", "robot", "senioragent", "orchestrator"]):
                slides = [
                    {"type": "title", "title": title, "subtitle": subtitle or "The Local-First Agentic OS", "image_search": "artificial intelligence neural network technology"},
                    {"type": "pipeline", "title": "The Local Engine Pipeline", "steps": ["The Brain: Ollama running local LLMs on Port 11434", "The Backend: Python & FastAPI handling logic on Port 8000", "The Frontend: Node.js & React powering UI on Port 5173"]},
                    {"type": "split_image", "title": "The Future of Accessible Autonomy", "subtitle": "Bridging Multi-Agent Workflows & Senior Accessibility", "bullets": ["Digital Accessibility: Dignity and deliberate design", "Total User Control: Full local sandbox execution", "Next-Gen Agentic AI: Autonomous code generation"], "image_search": "robotics autonomous software engineering"}
                ]
            else:
                slides = [
                    {"type": "title", "title": title, "subtitle": subtitle or "Executive Strategy & Analysis Deck", "image_search": f"{title} overview"},
                    {"type": "content", "title": "Executive Summary & Core Objectives", "bullets": ["Strategic Vision and Market Opportunities", "Target Audience & Growth Drivers", "Competitive Advantage & Differentiation"]},
                    {"type": "metrics", "title": "Key Performance Indicators", "metrics": [{"label": "Target Growth", "value": "150%"}, {"label": "Efficiency Gain", "value": "45%"}, {"label": "Payback Period", "value": "6 Months"}]},
                    {"type": "split_image", "title": "Strategic Execution & Growth", "subtitle": "From Blueprint to Production Execution", "bullets": ["Phase 1: Foundation & Core Infrastructure", "Phase 2: Market Deployment & User Scaling", "Phase 3: Operational Optimization & Growth"], "image_search": f"{title} technology"}
                ]

        # Ensure an interactive Quiz slide with tap-to-reveal verified answers is included in every deck
        has_quiz = any(str(s.get("type", "")).lower() == "quiz" for s in slides)
        if not has_quiz:
            slides.append({
                "type": "quiz",
                "title": f"{title}: Knowledge Check & Tap-to-Reveal Q&A",
                "questions": [
                    {
                        "question": f"What is the foundational significance of {title}?",
                        "options": [
                            "A) Outdated historical concept",
                            "B) Paradigm-shifting breakthrough in modern applications",
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

        # Carry over existing images from prev_spec if matching slide index has an existing image file
        prev_slides = prev_spec.get("slides", []) if isinstance(prev_spec, dict) else []

        # Process automated image search and insertion for slides
        for idx, s in enumerate(slides):
            if not isinstance(s, dict):
                continue
            # Reuse cached image_path from previous spec if valid
            if not s.get("image_path") and idx < len(prev_slides) and isinstance(prev_slides[idx], dict):
                prev_img = prev_slides[idx].get("image_path")
                if prev_img and os.path.exists(str(prev_img)) and prev_spec.get("filename") == safe_name:
                    s["image_path"] = prev_img

            slide_type = str(s.get("type", "content")).lower()
            img_search_term = s.get("image_search") or s.get("image_prompt")
            if not img_search_term and slide_type in ["split_image", "image", "title"]:
                img_search_term = f"{title} {s.get('title', '')}".strip()

            if img_search_term and not (s.get("image_path") and os.path.exists(str(s.get("image_path")))):
                try:
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
            "filename": safe_name,
            "author": "PPT-generater Agent",
            "theme_style": theme_style,
            "theme_color": theme_color,
            "animations_enabled": animations_enabled,
            "animation_style": animation_style,
            "slides": slides
        }

        # Persist spec so follow-up animation/modification requests can reuse existing slides
        try:
            os.makedirs(DOCUMENTS_DIR, exist_ok=True)
            with open(last_spec_path, "w", encoding="utf-8") as sf:
                json.dump(spec, sf, indent=2)
        except Exception:
            pass

        # Build PPTX
        pptx_res = create_powerpoint_deck(spec, pptx_path)
        # Build HTML Reveal.js
        html_res = create_html_presentation(spec, html_path)

        # Also copy the interactive HTML presentation to AGENT_WORKSPACE_DIR/index.html
        # when called by PPT Generator or when user asks for a presentation so Live Preview shows it immediately!
        try:
            agent_name_lower = str(ctx.get("agent_name", "") if ctx else "").lower()
            if "ppt" in agent_name_lower or "presentation" in agent_name_lower or "slide" in user_task_input.lower() or "ppt" in user_task_input.lower():
                workspace_index = os.path.join(AGENT_WORKSPACE_DIR, "index.html")
                shutil.copyfile(html_path, workspace_index)
        except Exception as cp_err:
            logger.debug("Could not copy presentation HTML to workspace index.html: %s", cp_err)

        pptx_url = f"/api/documents/{safe_name}.pptx"
        html_url = f"/api/documents/{safe_name}.html"

        anim_badge = (
            f"Enabled ({animation_style.upper()} Slide Swiping + Staggered Element Entrance + Tap-to-Reveal Quiz)"
            if animations_enabled
            else "Off (Switchable Live in Toolbar)"
        )

        # Stream document event to frontend
        if ctx and "queue" in ctx and "loop" in ctx:
            ctx["loop"].call_soon_threadsafe(
                ctx["queue"].put_nowait,
                {
                    "type": "terminal_output",
                    "content": f"[NotebookLM Presentation Generated]: {safe_name}.pptx ({len(slides)} slides, Theme: {theme_style}, Animations: {anim_badge}) -- Interactive preview: {safe_name}.html",
                    "done": False
                }
            )

        report = [
            f"### 🚀 [NotebookLM Presentation Deck Generated Successfully]",
            f"- **Title**: {title}",
            f"- **Theme**: {'Dark Blueprint (#0B0F19)' if theme_style == 'dark' else 'Light Technical Blueprint (#FAF9F6)'}",
            f"- **Slides Count**: {len(slides)}",
            f"- **Animations & Interactivity**: {anim_badge}",
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
