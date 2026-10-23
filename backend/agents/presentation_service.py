"""
Presentation Service — NotebookLM Technical Blueprint & Visual Slide Engine
Generates professional PowerPoint presentations (.pptx) and interactive animated HTML slide decks (Reveal.js)
from structured JSON slide specifications, supporting embedded real images, process pipelines, 
blueprint diagrams, metrics KPIs, and interactive topic quizzes with revealable answers.
"""

import os
import json
import base64
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def get_image_data_uri(image_path: Optional[str]) -> str:
    """Convert local image path into a self-contained base64 data URI for 100% reliable HTML browser rendering."""
    if not image_path:
        return ""
    str_path = str(image_path).strip()
    if str_path.startswith("data:") or str_path.startswith("http://") or str_path.startswith("https://"):
        return str_path
    if os.path.exists(str_path):
        try:
            ext = os.path.splitext(str_path)[1].lower().replace('.', '') or 'jpeg'
            if ext == 'jpg':
                ext = 'jpeg'
            with open(str_path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            return f"data:image/{ext};base64,{b64}"
        except Exception as e:
            logger.error("Error creating base64 data URI for %s: %s", str_path, e)
    # Fallback to served API URL if available
    filename = os.path.basename(str_path)
    return f"/api/generated-images/{filename}"


def create_powerpoint_deck(spec: Dict[str, Any], output_path: str) -> Dict[str, Any]:
    """
    Build a high-end, executive-grade PowerPoint presentation (.pptx) in NotebookLM Technical Blueprint Style
    from a JSON slide specification, complete with native slide fade transitions and interactive quiz slides.
    """
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.oxml import parse_xml

        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        title = spec.get("title", "Presentation")
        theme_style = str(spec.get("theme_style", "notebooklm")).lower()

        if theme_style in ["dark", "dark_blueprint", "void"]:
            bg_color = RGBColor(15, 23, 42)          # Dark Navy Blueprint #0F172A
            header_color = RGBColor(248, 250, 252)   # Crisp White #F8FAFC
            subtitle_color = RGBColor(148, 163, 184) # Slate Gray
            card_color = RGBColor(30, 41, 59)        # Card Fill #1E293B
            card_border = RGBColor(79, 70, 229)      # Indigo Accent #4F46E5
            text_main = RGBColor(241, 245, 249)
            accent_blue = RGBColor(96, 165, 250)
            emerald_green = RGBColor(52, 211, 153)
        else:
            # NotebookLM Technical Blueprint Style (Light Paper #FAF9F6)
            bg_color = RGBColor(250, 249, 246)       # Off-white Blueprint #FAF9F6
            header_color = RGBColor(17, 24, 39)      # Dark Charcoal #111827
            subtitle_color = RGBColor(75, 85, 99)    # Slate #4B5563
            card_color = RGBColor(255, 255, 255)     # Pure White Card #FFFFFF
            card_border = RGBColor(209, 213, 219)   # Tech Border #D1D5DB
            text_main = RGBColor(17, 24, 39)
            accent_blue = RGBColor(79, 70, 229)      # Indigo Accent #4F46E5
            emerald_green = RGBColor(16, 185, 129)

        slides_data = spec.get("slides", [])
        blank_slide_layout = prs.slide_layouts[6]

        for i, s in enumerate(slides_data):
            slide_type = str(s.get("type", "content")).lower()
            image_path = s.get("image_path") or s.get("image_url")
            slide = prs.slides.add_slide(blank_slide_layout)

            # Slide Blueprint Canvas Background
            bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
            bg.fill.solid()
            bg.fill.fore_color.rgb = bg_color
            bg.line.fill.background()

            # Technical Grid Outer Frame
            frame = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.4), Inches(0.4), Inches(12.533), Inches(6.7))
            frame.fill.background()
            frame.line.color.rgb = card_border
            frame.line.width = Pt(1.5)

            # Add Native Slide Fade Transition (PowerPoint Animation)
            try:
                transition_xml = parse_xml(
                    '<p:transition xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" spd="med"><p:fade/></p:transition>'
                )
                slide.element.append(transition_xml)
            except Exception:
                pass

            # Speaker Notes
            notes_text = s.get("notes") or s.get("explanation") or ""

            if slide_type == "title" or i == 0:
                # Title Slide: NotebookLM Split Blueprint Layout
                if image_path and os.path.exists(str(image_path)):
                    try:
                        slide.shapes.add_picture(str(image_path), Inches(0.6), Inches(0.6), Inches(5.8), Inches(6.3))
                    except Exception as ie:
                        logger.error("Error embedding title image: %s", ie)

                    txBox = slide.shapes.add_textbox(Inches(6.7), Inches(1.2), Inches(5.8), Inches(5.0))
                    tf = txBox.text_frame
                    tf.word_wrap = True

                    p0 = tf.paragraphs[0]
                    p0.text = "SYSTEM ROOT // AGENT OS"
                    p0.font.size = Pt(12)
                    p0.font.bold = True
                    p0.font.color.rgb = accent_blue

                    p1 = tf.add_paragraph()
                    p1.text = s.get("title", title)
                    p1.font.size = Pt(40)
                    p1.font.bold = True
                    p1.font.color.rgb = header_color
                    p1.space_before = Pt(16)

                    subtitle_str = s.get("subtitle") or spec.get("subtitle", "")
                    if subtitle_str:
                        p2 = tf.add_paragraph()
                        p2.text = subtitle_str
                        p2.font.size = Pt(18)
                        p2.font.color.rgb = subtitle_color
                        p2.space_before = Pt(14)
                else:
                    txBox = slide.shapes.add_textbox(Inches(1.2), Inches(1.8), Inches(10.9), Inches(4.0))
                    tf = txBox.text_frame
                    tf.word_wrap = True

                    p0 = tf.paragraphs[0]
                    p0.text = "SYSTEM ROOT // AGENT OS"
                    p0.font.size = Pt(14)
                    p0.font.bold = True
                    p0.font.color.rgb = accent_blue

                    p1 = tf.add_paragraph()
                    p1.text = s.get("title", title)
                    p1.font.size = Pt(46)
                    p1.font.bold = True
                    p1.font.color.rgb = header_color
                    p1.space_before = Pt(16)

                    subtitle_str = s.get("subtitle") or spec.get("subtitle", "")
                    if subtitle_str:
                        p2 = tf.add_paragraph()
                        p2.text = subtitle_str
                        p2.font.size = Pt(20)
                        p2.font.color.rgb = subtitle_color
                        p2.space_before = Pt(14)

            elif slide_type in ["split_image", "image"] or (image_path and os.path.exists(str(image_path)) and slide_type != "quiz"):
                # Split Image Slide Layout (Text Left / Image Right)
                txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(5.8), Inches(6.0))
                tf = txBox.text_frame
                tf.word_wrap = True

                p = tf.paragraphs[0]
                p.text = s.get("title", f"Slide {i+1}")
                p.font.size = Pt(34)
                p.font.bold = True
                p.font.color.rgb = header_color

                subtitle_text = s.get("subtitle", "")
                if subtitle_text:
                    p2 = tf.add_paragraph()
                    p2.text = subtitle_text
                    p2.font.size = Pt(17)
                    p2.font.color.rgb = subtitle_color
                    p2.space_before = Pt(10)

                bullets = s.get("bullets", [])
                for b_text in bullets[:4]:
                    bp = tf.add_paragraph()
                    bp.text = f"•  {b_text}"
                    bp.font.size = Pt(15)
                    bp.font.color.rgb = text_main
                    bp.space_before = Pt(12)

                # Embed Image on Right Half
                if image_path and os.path.exists(str(image_path)):
                    try:
                        img_border = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(6.8), Inches(0.8), Inches(5.8), Inches(5.8))
                        img_border.fill.background()
                        img_border.line.color.rgb = card_border
                        img_border.line.width = Pt(1.5)
                        slide.shapes.add_picture(str(image_path), Inches(6.9), Inches(0.9), Inches(5.6), Inches(5.6))
                    except Exception as ie:
                        logger.error("Error adding picture to PPTX slide: %s", ie)

            elif slide_type in ["process", "pipeline"]:
                # Process Pipeline Layout (Horizontal Node Timeline)
                txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.733), Inches(1.0))
                tf = txBox.text_frame
                tf.word_wrap = True
                p = tf.paragraphs[0]
                p.text = s.get("title", "The Engine Pipeline")
                p.font.size = Pt(32)
                p.font.bold = True
                p.font.color.rgb = header_color

                arrow = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(1.2), Inches(2.2), Inches(10.8), Inches(0.3))
                arrow.fill.solid()
                arrow.fill.fore_color.rgb = accent_blue
                arrow.line.fill.background()

                steps = s.get("steps") or s.get("bullets") or ["Phase 1: Architecture", "Phase 2: Execution", "Phase 3: Verification"]
                num_steps = min(len(steps), 3)
                col_width = Inches(11.733 / num_steps)

                for step_idx, step_text in enumerate(steps[:3]):
                    left_pos = Inches(0.8 + step_idx * (11.733 / num_steps))
                    node_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left_pos, Inches(2.8), col_width - Inches(0.3), Inches(1.5))
                    node_box.fill.solid()
                    node_box.fill.fore_color.rgb = card_color
                    node_box.line.color.rgb = card_border
                    node_box.line.width = Pt(1.5)

                    ntf = node_box.text_frame
                    ntf.word_wrap = True
                    np1 = ntf.paragraphs[0]
                    np1.text = f"Step {step_idx+1}: {step_text.split(':')[0] if ':' in step_text else step_text}"
                    np1.font.size = Pt(18)
                    np1.font.bold = True
                    np1.font.color.rgb = header_color

                    code_box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left_pos, Inches(4.5), col_width - Inches(0.3), Inches(2.0))
                    code_box.fill.solid()
                    code_box.fill.fore_color.rgb = RGBColor(241, 245, 249)
                    code_box.line.color.rgb = card_border
                    code_box.line.width = Pt(1)

                    ctf = code_box.text_frame
                    ctf.word_wrap = True
                    cp1 = ctf.paragraphs[0]
                    cp1.text = step_text.split(':')[1] if ':' in step_text else f"// Execution Config {step_idx+1}"
                    cp1.font.size = Pt(13)
                    cp1.font.color.rgb = RGBColor(51, 65, 85)

            elif slide_type == "quiz":
                # Dedicated Interactive Quiz & Knowledge Check Slide
                txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.733), Inches(1.0))
                tf = txBox.text_frame
                tf.word_wrap = True
                p = tf.paragraphs[0]
                p.text = f"🎯 {s.get('title', 'Topic Mastery & Knowledge Check Quiz')}"
                p.font.size = Pt(30)
                p.font.bold = True
                p.font.color.rgb = header_color

                questions = s.get("questions") or [
                    {
                        "question": "What is the primary breakthrough concept introduced in this topic?",
                        "options": ["A) Classical linear processing", "B) Next-generation distributed intelligence", "C) Static database caching", "D) Unverified script execution"],
                        "answer": "B) Next-generation distributed intelligence",
                        "explanation": "Next-gen distributed architectures fundamentally change execution efficiency and scalability."
                    },
                    {
                        "question": "Which metric provides the strongest verification signal?",
                        "options": ["A) Line count alone", "B) Automated end-to-end verification and error feedback", "C) Random sampling", "D) Manual terminal review"],
                        "answer": "B) Automated end-to-end verification and error feedback",
                        "explanation": "Automated runtime feedback and visual checks ensure zero syntax and runtime regressions."
                    }
                ]

                # Left side: Questions Box
                left_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.7), Inches(6.8), Inches(5.1))
                left_box.fill.solid()
                left_box.fill.fore_color.rgb = card_color
                left_box.line.color.rgb = card_border
                left_box.line.width = Pt(1.5)

                ltf = left_box.text_frame
                ltf.word_wrap = True

                for q_idx, q in enumerate(questions[:2]):
                    qp = ltf.paragraphs[0] if q_idx == 0 else ltf.add_paragraph()
                    qp.text = f"Q{q_idx+1}: {q.get('question', '')}"
                    qp.font.size = Pt(16)
                    qp.font.bold = True
                    qp.font.color.rgb = header_color
                    if q_idx > 0:
                        qp.space_before = Pt(16)

                    opts = q.get("options", [])
                    for opt in opts[:4]:
                        op = ltf.add_paragraph()
                        op.text = f"   {opt}"
                        op.font.size = Pt(13)
                        op.font.color.rgb = text_main
                        op.space_before = Pt(4)

                # Right side: Answer Key & Explanation Card
                right_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.9), Inches(1.7), Inches(4.6), Inches(5.1))
                right_box.fill.solid()
                right_box.fill.fore_color.rgb = card_color
                right_box.line.color.rgb = emerald_green
                right_box.line.width = Pt(2.0)

                rtf = right_box.text_frame
                rtf.word_wrap = True
                rp0 = rtf.paragraphs[0]
                rp0.text = "VERIFIED ANSWER KEY"
                rp0.font.size = Pt(13)
                rp0.font.bold = True
                rp0.font.color.rgb = emerald_green

                notes_lines = ["--- SLIDE QUIZ ANSWER KEY ---"]
                for q_idx, q in enumerate(questions[:2]):
                    ans_p = rtf.add_paragraph()
                    ans_p.text = f"✓ Q{q_idx+1} Answer: {q.get('answer', 'Option B')}"
                    ans_p.font.size = Pt(14)
                    ans_p.font.bold = True
                    ans_p.font.color.rgb = header_color
                    ans_p.space_before = Pt(14)

                    exp_p = rtf.add_paragraph()
                    exp_p.text = f"💡 {q.get('explanation', 'Core principle verified by domain specifications.')}"
                    exp_p.font.size = Pt(12)
                    exp_p.font.color.rgb = subtitle_color
                    exp_p.space_before = Pt(4)

                    notes_lines.append(f"Q{q_idx+1}: {q.get('question', '')}\nAnswer: {q.get('answer', '')}\nExplanation: {q.get('explanation', '')}\n")

                notes_text = "\n".join(notes_lines)

            else:
                # Standard Content & Metrics Slide
                txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.733), Inches(1.0))
                tf = txBox.text_frame
                tf.word_wrap = True
                p = tf.paragraphs[0]
                p.text = s.get("title", f"Slide {i+1}")
                p.font.size = Pt(28)
                p.font.bold = True
                p.font.color.rgb = header_color

                bullets = s.get("bullets", [])
                metrics = s.get("metrics", [])

                if metrics:
                    num_metrics = min(len(metrics), 4)
                    card_w = Inches(11.733 / max(num_metrics, 1) - 0.25)
                    for m_idx, m in enumerate(metrics[:4]):
                        left_pos = Inches(0.8 + m_idx * (11.733 / num_metrics))
                        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left_pos, Inches(1.8), card_w, Inches(2.0))
                        card.fill.solid()
                        card.fill.fore_color.rgb = card_color
                        card.line.color.rgb = card_border
                        card.line.width = Pt(1.5)

                        ctf = card.text_frame
                        ctf.word_wrap = True
                        cp1 = ctf.paragraphs[0]
                        cp1.text = str(m.get("label", "Metric")).upper()
                        cp1.font.size = Pt(11)
                        cp1.font.bold = True
                        cp1.font.color.rgb = subtitle_color

                        cp2 = ctf.add_paragraph()
                        cp2.text = str(m.get("value", "0"))
                        cp2.font.size = Pt(30)
                        cp2.font.bold = True
                        cp2.font.color.rgb = accent_blue

                if bullets:
                    top_pos = Inches(4.0) if metrics else Inches(1.8)
                    for b_idx, b_text in enumerate(bullets[:5]):
                        c_top = top_pos + Inches(b_idx * 1.0)
                        card_b = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), c_top, Inches(11.733), Inches(0.85))
                        card_b.fill.solid()
                        card_b.fill.fore_color.rgb = card_color
                        card_b.line.color.rgb = card_border
                        card_b.line.width = Pt(1)

                        btf = card_b.text_frame
                        btf.word_wrap = True
                        bp = btf.paragraphs[0]
                        bp.text = f"•   {b_text}"
                        bp.font.size = Pt(16)
                        bp.font.color.rgb = text_main

            # Write speaker notes if present
            if notes_text:
                try:
                    notes_slide = slide.notes_slide
                    tf_notes = notes_slide.notes_text_frame
                    tf_notes.text = notes_text
                except Exception:
                    pass

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        prs.save(output_path)
        return {
            "status": "success",
            "file_path": output_path,
            "slides_count": len(slides_data),
            "message": f"Successfully created PowerPoint presentation at '{output_path}'"
        }
    except Exception as e:
        logger.error("Error creating PowerPoint deck: %s", e)
        return {"status": "error", "error": str(e)}


def create_html_presentation(spec: Dict[str, Any], output_path: str) -> Dict[str, Any]:
    """
    Build an executive, animated HTML Reveal.js presentation with smooth transitions,
    embedded Base64 images, interactive quiz slides with instant answer checking, and clean technical styling.
    """
    try:
        title = spec.get("title", "Executive Presentation")
        subtitle = spec.get("subtitle", "Technical Blueprint Deck")
        author = spec.get("author", "PPT-generater Agent")
        slides_data = spec.get("slides", [])

        html_slides = []
        for i, s in enumerate(slides_data):
            stype = str(s.get("type", "content")).lower()
            stitle = s.get("title", f"Slide {i+1}")
            ssub = s.get("subtitle", "")
            bullets = s.get("bullets", [])
            metrics = s.get("metrics", [])
            image_path = s.get("image_path") or s.get("image_url")
            img_data_uri = get_image_data_uri(image_path)
            notes_text = s.get("notes") or s.get("explanation") or ""

            if stype == "title" or i == 0:
                if img_data_uri:
                    slide_html = f"""
                    <section class="title-slide split-title" data-transition="zoom">
                        <div class="left-col fragment fade-right">
                            <div class="blueprint-frame">
                                <img src="{img_data_uri}" alt="{stitle}" class="title-diagram-img" />
                            </div>
                        </div>
                        <div class="right-col fragment fade-left">
                            <div class="tech-badge">PRESENTATION ARCHITECT // SLIDE DECK</div>
                            <h1 class="slide-main-title">{stitle}</h1>
                            <h3 class="slide-subtitle">{ssub or subtitle}</h3>
                            <div class="title-footer">Prepared by <strong>{author}</strong> | Interactive Slide Suite</div>
                        </div>
                    </section>
                    """
                else:
                    slide_html = f"""
                    <section class="title-slide" data-transition="zoom">
                        <div class="tech-badge">PRESENTATION ARCHITECT // SLIDE DECK</div>
                        <h1 class="slide-main-title">{stitle}</h1>
                        <h3 class="slide-subtitle">{ssub or subtitle}</h3>
                        <div class="title-footer">Prepared by <strong>{author}</strong> | Interactive Slide Suite</div>
                    </section>
                    """
            elif stype in ["split_image", "image"] or (img_data_uri and stype != "quiz"):
                b_items = "".join([f'<div class="bullet-card fragment fade-up" data-fragment-index="{idx+1}"><span>✦</span> {b}</div>' for idx, b in enumerate(bullets[:4])])
                slide_html = f"""
                <section class="split-slide-container" data-transition="slide">
                    <div class="split-left">
                        <h2 class="slide-header">{stitle}</h2>
                        {f'<p class="slide-subhead">{ssub}</p>' if ssub else ''}
                        <div class="bullets-wrapper">{b_items}</div>
                    </div>
                    <div class="split-right">
                        <div class="blueprint-image-box fragment zoom-in" data-fragment-index="1">
                            <img src="{img_data_uri}" alt="{stitle}" class="blueprint-img" />
                            <div class="image-annotation-overlay">HIGH-RES VISUAL ASSET</div>
                        </div>
                    </div>
                </section>
                """
            elif stype in ["process", "pipeline"]:
                steps = s.get("steps") or bullets or ["Phase 1: Architecture", "Phase 2: Execution", "Phase 3: Verification"]
                nodes_html = []
                for idx, st in enumerate(steps[:3]):
                    s_title = st.split(':')[0] if ':' in st else st
                    s_code = st.split(':')[1] if ':' in st else f"// Config {idx+1}"
                    nodes_html.append(f"""
                    <div class="pipeline-node fragment fade-up" data-fragment-index="{idx+1}">
                        <div class="node-title">Step {idx+1}: {s_title}</div>
                        <div class="code-callout-box">
                            <code>{s_code}</code>
                        </div>
                    </div>
                    """)
                slide_html = f"""
                <section class="pipeline-slide" data-transition="slide">
                    <h2 class="slide-header">{stitle}</h2>
                    <div class="pipeline-connector-line"></div>
                    <div class="pipeline-nodes-wrapper">{"".join(nodes_html)}</div>
                </section>
                """
            elif stype == "quiz":
                questions = s.get("questions") or [
                    {
                        "question": "What is the primary breakthrough concept introduced in this topic?",
                        "options": ["A) Classical linear processing", "B) Next-generation distributed intelligence", "C) Static database caching", "D) Unverified script execution"],
                        "answer": "B) Next-generation distributed intelligence",
                        "explanation": "Next-gen distributed architectures fundamentally change execution efficiency and scalability."
                    },
                    {
                        "question": "Which metric provides the strongest verification signal?",
                        "options": ["A) Line count alone", "B) Automated end-to-end verification and error feedback", "C) Random sampling", "D) Manual terminal review"],
                        "answer": "B) Automated end-to-end verification and error feedback",
                        "explanation": "Automated runtime feedback and visual checks ensure zero syntax and runtime regressions."
                    }
                ]

                q_blocks = []
                notes_lines = ["--- SLIDE QUIZ ANSWER KEY ---"]
                for q_idx, q in enumerate(questions[:2]):
                    q_id = f"quiz_q_{i}_{q_idx}"
                    q_ans = q.get("answer", "")
                    q_exp = q.get("explanation", "Verified topic concept.")
                    notes_lines.append(f"Q{q_idx+1}: {q.get('question','')}\nAnswer: {q_ans}\nWhy: {q_exp}\n")

                    options_html = []
                    for o_idx, opt in enumerate(q.get("options", [])):
                        is_corr = opt.strip() == q_ans.strip() or opt.startswith(q_ans[:2]) if q_ans else (o_idx == 1)
                        options_html.append(f"""
                        <button class="quiz-btn" onclick="checkQuizAnswer(this, {str(is_corr).lower()}, '{q_id}')">
                            <span class="opt-label">{opt}</span>
                        </button>
                        """)

                    q_blocks.append(f"""
                    <div class="quiz-card fragment fade-up" id="{q_id}">
                        <div class="quiz-q-title">Q{q_idx+1}: {q.get('question', '')}</div>
                        <div class="quiz-options-list">
                            {"".join(options_html)}
                        </div>
                        <div class="quiz-explanation-box" id="{q_id}_exp" style="display:none;">
                            <div class="exp-title">✓ Verified Answer: {q_ans}</div>
                            <div class="exp-body">{q_exp}</div>
                        </div>
                    </div>
                    """)

                slide_html = f"""
                <section class="quiz-slide" data-transition="convex">
                    <div class="tech-badge">🎯 INTERACTIVE KNOWLEDGE CHECK // TOPIC QUIZ</div>
                    <h2 class="slide-header">{stitle}</h2>
                    <div class="quiz-grid">
                        {"".join(q_blocks)}
                    </div>
                    <div class="quiz-controls-bar">
                        <button class="toggle-all-btn" onclick="toggleAllQuizAnswers()">
                            <span>👁️ Toggle Show All Answers & Explanations</span>
                        </button>
                    </div>
                    <aside class="notes">
                        {"<br/>".join(notes_lines)}
                    </aside>
                </section>
                """
            else:
                cards_html = ""
                if metrics:
                    cards = []
                    for m_idx, m in enumerate(metrics[:4]):
                        cards.append(f"""
                        <div class="metric-card fragment zoom-in" data-fragment-index="{m_idx+1}">
                            <div class="metric-label">{m.get("label", "Metric")}</div>
                            <div class="metric-value">{m.get("value", "0")}</div>
                        </div>
                        """)
                    cards_html = f'<div class="metrics-grid">{"".join(cards)}</div>'

                bullets_html = ""
                if bullets:
                    b_items = "".join([f'<div class="bullet-card fragment fade-up" data-fragment-index="{idx+1}"><span>✦</span> {b}</div>' for idx, b in enumerate(bullets[:5])])
                    bullets_html = f'<div class="bullets-wrapper">{b_items}</div>'

                slide_html = f"""
                <section data-transition="slide">
                    <h2 class="slide-header">{stitle}</h2>
                    {cards_html}
                    {bullets_html}
                    {f'<aside class="notes">{notes_text}</aside>' if notes_text else ''}
                </section>
                """

            html_slides.append(slide_html)

        reveal_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/reveal.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/theme/dracula.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-blueprint: #FAF9F6;
            --text-dark: #111827;
            --text-sub: #4B5563;
            --accent-indigo: #4F46E5;
            --border-tech: #D1D5DB;
            --card-bg: #FFFFFF;
            --emerald: #10B981;
        }}
        .reveal {{ font-family: 'Inter', sans-serif; background: var(--bg-blueprint); color: var(--text-dark); }}
        .reveal::before {{
            content: "";
            position: fixed;
            inset: 0;
            background-size: 30px 30px;
            background-image: linear-gradient(to right, rgba(209, 213, 219, 0.4) 1px, transparent 1px),
                              linear-gradient(to bottom, rgba(209, 213, 219, 0.4) 1px, transparent 1px);
            pointer-events: none;
        }}
        .title-slide {{ text-align: left; padding: 40px; }}
        .split-title {{ display: flex; gap: 40px; align-items: center; }}
        .left-col {{ flex: 1; }}
        .right-col {{ flex: 1.2; }}
        .tech-badge {{ display: inline-block; padding: 6px 14px; background: rgba(79, 70, 229, 0.1); border: 1px solid var(--accent-indigo); border-radius: 6px; font-size: 0.75em; font-weight: 700; color: var(--accent-indigo); letter-spacing: 1.5px; margin-bottom: 20px; }}
        .slide-main-title {{ font-family: 'Outfit', sans-serif; font-size: 3.2em !important; font-weight: 800; color: var(--text-dark); margin-bottom: 10px !important; line-height: 1.1 !important; }}
        .slide-subtitle {{ font-size: 1.4em !important; color: var(--text-sub); font-weight: 400; margin-top: 10px !important; }}
        .title-footer {{ font-size: 0.85em; color: #6B7280; margin-top: 40px; border-top: 1px solid var(--border-tech); padding-top: 15px; }}
        .slide-header {{ font-family: 'Outfit', sans-serif; text-align: left; font-size: 2.2em !important; font-weight: 800; color: var(--text-dark); margin-bottom: 25px !important; border-bottom: 2px solid var(--border-tech); padding-bottom: 12px; }}
        .split-slide-container {{ display: flex; gap: 35px; align-items: center; text-align: left; }}
        .split-left {{ flex: 1.1; }}
        .split-right {{ flex: 1.2; }}
        .blueprint-image-box {{ position: relative; border: 2px solid var(--border-tech); border-radius: 12px; padding: 8px; background: #FFFFFF; box-shadow: 0 10px 30px rgba(0,0,0,0.08); transition: transform 0.3s ease; }}
        .blueprint-image-box:hover {{ transform: scale(1.02); }}
        .blueprint-img {{ width: 100%; height: 420px; object-fit: cover; border-radius: 8px; display: block; }}
        .title-diagram-img {{ width: 100%; height: 440px; object-fit: cover; border-radius: 8px; display: block; }}
        .blueprint-frame {{ border: 2px solid var(--border-tech); border-radius: 12px; padding: 8px; background: #FFFFFF; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }}
        .image-annotation-overlay {{ position: absolute; bottom: 16px; left: 16px; background: rgba(17, 24, 39, 0.85); color: #FFFFFF; padding: 4px 10px; font-size: 0.65em; font-weight: 700; border-radius: 4px; letter-spacing: 1px; }}
        .pipeline-slide {{ text-align: left; }}
        .pipeline-connector-line {{ height: 6px; background: var(--accent-indigo); margin: 30px 0; border-radius: 3px; position: relative; }}
        .pipeline-nodes-wrapper {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
        .pipeline-node {{ background: #FFFFFF; border: 1px solid var(--border-tech); border-radius: 10px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
        .node-title {{ font-family: 'Outfit', sans-serif; font-weight: 700; font-size: 1.1em; color: var(--text-dark); margin-bottom: 12px; }}
        .code-callout-box {{ background: #F3F4F6; border: 1px solid #E5E7EB; border-radius: 6px; padding: 12px; font-family: monospace; font-size: 0.85em; color: #1F2937; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 25px 0; }}
        .metric-card {{ background: #FFFFFF; border: 1px solid var(--border-tech); border-radius: 12px; padding: 24px; text-align: left; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
        .metric-label {{ font-size: 0.75em; text-transform: uppercase; color: var(--text-sub); letter-spacing: 1px; font-weight: 700; }}
        .metric-value {{ font-family: 'Outfit', sans-serif; font-size: 2.5em; font-weight: 800; color: var(--accent-indigo); margin: 8px 0 0 0; }}
        .bullets-wrapper {{ display: flex; flex-direction: column; gap: 12px; text-align: left; margin-top: 15px; }}
        .bullet-card {{ background: #FFFFFF; border: 1px solid var(--border-tech); border-left: 4px solid var(--accent-indigo); border-radius: 8px; padding: 16px 20px; font-size: 1.1em; color: var(--text-dark); box-shadow: 0 2px 8px rgba(0,0,0,0.04); }}
        .bullet-card span {{ color: var(--accent-indigo); margin-right: 8px; }}

        /* Interactive Quiz Slide Styles */
        .quiz-slide {{ text-align: left; padding: 20px; }}
        .quiz-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 24px; margin-top: 15px; }}
        .quiz-card {{ background: #FFFFFF; border: 2px solid var(--border-tech); border-radius: 12px; padding: 20px; box-shadow: 0 4px 16px rgba(0,0,0,0.06); text-align: left; }}
        .quiz-q-title {{ font-family: 'Outfit', sans-serif; font-size: 1.15em; font-weight: 700; color: var(--text-dark); margin-bottom: 15px; line-height: 1.3; }}
        .quiz-options-list {{ display: flex; flex-direction: column; gap: 8px; }}
        .quiz-btn {{ background: #F9FAFB; border: 1px solid #D1D5DB; border-radius: 8px; padding: 10px 14px; text-align: left; font-size: 0.9em; font-family: 'Inter', sans-serif; color: #1F2937; cursor: pointer; transition: all 0.2s; }}
        .quiz-btn:hover {{ background: #EEF2FF; border-color: var(--accent-indigo); }}
        .quiz-btn.correct {{ background: #ECFDF5 !important; border-color: #10B981 !important; color: #065F46 !important; font-weight: 700; }}
        .quiz-btn.wrong {{ background: #FEF2F2 !important; border-color: #EF4444 !important; color: #991B1B !important; opacity: 0.7; }}
        .quiz-explanation-box {{ margin-top: 14px; padding: 12px; background: #F0FDF4; border: 1px solid #86EFAC; border-radius: 8px; font-size: 0.85em; }}
        .exp-title {{ font-weight: 700; color: #166534; margin-bottom: 4px; }}
        .exp-body {{ color: #1F2937; line-height: 1.4; }}
        .quiz-controls-bar {{ margin-top: 24px; text-align: center; }}
        .toggle-all-btn {{ background: #111827; color: #FFFFFF; border: 1px solid #374151; padding: 10px 24px; border-radius: 20px; font-size: 0.9em; font-weight: 600; cursor: pointer; transition: all 0.2s; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
        .toggle-all-btn:hover {{ background: var(--accent-indigo); }}
    </style>
</head>
<body>
    <div class="reveal">
        <div class="slides">
            {"".join(html_slides)}
        </div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/reveal.min.js"></script>
    <script>
        Reveal.initialize({{
            controls: true,
            progress: true,
            center: false,
            hash: true,
            transition: 'slide',
            backgroundTransition: 'fade',
            slideNumber: 'c/t'
        }});

        function checkQuizAnswer(btn, isCorrect, cardId) {{
            const card = document.getElementById(cardId);
            if (!card) return;
            const buttons = card.querySelectorAll('.quiz-btn');
            buttons.forEach(b => b.classList.remove('correct', 'wrong'));
            if (isCorrect) {{
                btn.classList.add('correct');
            }} else {{
                btn.classList.add('wrong');
            }}
            const exp = document.getElementById(cardId + '_exp');
            if (exp) exp.style.display = 'block';
        }}

        let allAnswersVisible = false;
        function toggleAllQuizAnswers() {{
            allAnswersVisible = !allAnswersVisible;
            document.querySelectorAll('.quiz-explanation-box').forEach(el => {{
                el.style.display = allAnswersVisible ? 'block' : 'none';
            }});
        }}
    </script>
</body>
</html>"""

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(reveal_template)

        return {
            "status": "success",
            "file_path": output_path,
            "slides_count": len(slides_data),
            "message": f"Successfully created animated interactive HTML presentation at '{output_path}'"
        }
    except Exception as e:
        logger.error("Error creating HTML presentation: %s", e)
        return {"status": "error", "error": str(e)}
