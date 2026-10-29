"""
Presentation Service — NotebookLM Technical Blueprint & Visual Slide Engine
Generates professional PowerPoint presentations (.pptx) and interactive animated HTML slide decks (Reveal.js)
from structured JSON slide specifications, supporting embedded real images, process pipelines, 
blueprint diagrams, metrics KPIs, custom slide/element swiping & entrance animations, dark/light themes,
and interactive topic quizzes with tap-to-reveal answers.
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
    # Fallback to served API URL with explicit backend origin so srcDoc iframes resolve it
    filename = os.path.basename(str_path)
    return f"http://localhost:8000/api/generated-images/{filename}"


def _build_pptx_transition_xml(style: str = "swipe") -> str:
    """Build OpenXML <p:transition> element string for the given animation/transition style."""
    s = (style or "swipe").lower().strip()
    if s in ["none", "off", "false"]:
        return ""
    if "swipe" in s or "push" in s or "slide" in s or "carousel" in s:
        inner = '<p:push dir="l"/>'
    elif "zoom" in s or "scale" in s or "bounce" in s or "pop" in s:
        inner = '<p:zoom dir="in"/>'
    elif "wipe" in s:
        inner = '<p:wipe dir="l"/>'
    elif "split" in s:
        inner = '<p:split orient="horz" dir="out"/>'
    elif "wheel" in s or "spin" in s:
        inner = '<p:wheel spokes="4"/>'
    elif "fly" in s or "cover" in s or "convex" in s or "3d" in s or "flip" in s:
        inner = '<p:cover dir="l"/>'
    elif "pull" in s or "concave" in s:
        inner = '<p:pull dir="l"/>'
    else:
        inner = '<p:fade thruBlk="0"/>'

    return (
        f'<p:transition xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        f'spd="med" advClick="1">{inner}</p:transition>'
    )


def _build_pptx_timing_xml(
    shape_ids: List[int],
    style: str = "swipe",
    click_shape_ids: Optional[List[int]] = None
) -> str:
    """
    Build valid OpenXML <p:timing> element that animates each shape in `shape_ids`
    sequentially (staggered entrance animation on slide load) and animates `click_shape_ids`
    on click/tap (e.g. Tap-to-Reveal Quiz Answers).
    """
    if not shape_ids and not click_shape_ids:
        return ""

    s = (style or "swipe").lower().strip()
    if "swipe" in s or "fly" in s or "slide" in s or "push" in s:
        preset_id = 2       # Fly In
        preset_subtype = 8  # From Right (matches horizontal swipe!)
        filter_str = "slide(fromRight)"
    elif "wipe" in s:
        preset_id = 22      # Wipe
        preset_subtype = 4  # From Bottom
        filter_str = "wipe(up)"
    elif "zoom" in s or "bounce" in s or "pop" in s:
        preset_id = 53      # Zoom / Grow
        preset_subtype = 0
        filter_str = "fade"
    else:
        preset_id = 10      # Fade
        preset_subtype = 0
        filter_str = "fade"

    par_nodes = []
    bld_nodes = []
    ctn_id = 3  # 1 is root tmRoot, 2 is mainSeq

    # 1. Auto-entrance shapes (play automatically when slide appears)
    for idx, spid in enumerate(shape_ids):
        outer_id = ctn_id
        inner_id = ctn_id + 1
        set_id = ctn_id + 2
        anim_id = ctn_id + 3
        ctn_id += 4

        node_type = "withEffect" if idx == 0 else "afterEffect"
        delay_ms = "100" if idx == 0 else "180"

        par_nodes.append(f"""
                  <p:par>
                    <p:cTn id="{outer_id}" fill="hold">
                      <p:stCondLst>
                        <p:cond delay="{delay_ms}"/>
                      </p:stCondLst>
                      <p:childTnLst>
                        <p:par>
                          <p:cTn id="{inner_id}" presetID="{preset_id}" presetClass="entr" presetSubtype="{preset_subtype}" fill="hold" nodeType="{node_type}">
                            <p:stCondLst>
                              <p:cond delay="0"/>
                            </p:stCondLst>
                            <p:childTnLst>
                              <p:set>
                                <p:cBhvr>
                                  <p:cTn id="{set_id}" dur="1" fill="hold">
                                    <p:stCondLst>
                                      <p:cond delay="0"/>
                                    </p:stCondLst>
                                  </p:cTn>
                                  <p:tgtEl>
                                    <p:spTgt spid="{spid}"/>
                                  </p:tgtEl>
                                  <p:attrNameLst>
                                    <p:attrName>style.visibility</p:attrName>
                                  </p:attrNameLst>
                                </p:cBhvr>
                                <p:to>
                                  <p:strVal val="visible"/>
                                </p:to>
                              </p:set>
                              <p:animEffect transition="in" filter="{filter_str}">
                                <p:cBhvr>
                                  <p:cTn id="{anim_id}" dur="450"/>
                                  <p:tgtEl>
                                    <p:spTgt spid="{spid}"/>
                                  </p:tgtEl>
                                </p:cBhvr>
                              </p:animEffect>
                            </p:childTnLst>
                          </p:cTn>
                        </p:par>
                      </p:childTnLst>
                    </p:cTn>
                  </p:par>""")
        bld_nodes.append(f'<p:bldP spid="{spid}" grpId="0" animBg="1"/>')

    # 2. Click-to-reveal shapes (play when user taps/clicks on the slide, e.g. Quiz Answer Key)
    click_groups = []
    for spid in (click_shape_ids or []):
        grp_id = ctn_id
        outer_id = ctn_id + 1
        inner_id = ctn_id + 2
        set_id = ctn_id + 3
        anim_id = ctn_id + 4
        ctn_id += 5

        click_groups.append(f"""
                <p:par>
                  <p:cTn id="{grp_id}" fill="hold">
                    <p:stCondLst>
                      <p:cond delay="indefinite"/>
                    </p:stCondLst>
                    <p:childTnLst>
                      <p:par>
                        <p:cTn id="{outer_id}" fill="hold">
                          <p:stCondLst>
                            <p:cond delay="0"/>
                          </p:stCondLst>
                          <p:childTnLst>
                            <p:par>
                              <p:cTn id="{inner_id}" presetID="10" presetClass="entr" presetSubtype="0" fill="hold" nodeType="clickEffect">
                                <p:stCondLst>
                                  <p:cond delay="0"/>
                                </p:stCondLst>
                                <p:childTnLst>
                                  <p:set>
                                    <p:cBhvr>
                                      <p:cTn id="{set_id}" dur="1" fill="hold">
                                        <p:stCondLst>
                                          <p:cond delay="0"/>
                                        </p:stCondLst>
                                      </p:cTn>
                                      <p:tgtEl>
                                        <p:spTgt spid="{spid}"/>
                                      </p:tgtEl>
                                      <p:attrNameLst>
                                        <p:attrName>style.visibility</p:attrName>
                                      </p:attrNameLst>
                                    </p:cBhvr>
                                    <p:to>
                                      <p:strVal val="visible"/>
                                    </p:to>
                                  </p:set>
                                  <p:animEffect transition="in" filter="fade">
                                    <p:cBhvr>
                                      <p:cTn id="{anim_id}" dur="500"/>
                                      <p:tgtEl>
                                        <p:spTgt spid="{spid}"/>
                                      </p:tgtEl>
                                    </p:cBhvr>
                                  </p:animEffect>
                                </p:childTnLst>
                              </p:cTn>
                            </p:par>
                          </p:childTnLst>
                        </p:cTn>
                      </p:par>
                    </p:childTnLst>
                  </p:cTn>
                </p:par>""")
        bld_nodes.append(f'<p:bldP spid="{spid}" grpId="0" animBg="1"/>')

    auto_group_id = ctn_id
    return f"""<p:timing xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
      <p:tnLst>
        <p:par>
          <p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">
            <p:childTnLst>
              <p:seq concurrent="1" nextAc="seek">
                <p:cTn id="2" dur="indefinite" nodeType="mainSeq">
                  <p:childTnLst>
                    <p:par>
                      <p:cTn id="{auto_group_id}" fill="hold">
                        <p:stCondLst>
                          <p:cond delay="0"/>
                        </p:stCondLst>
                        <p:childTnLst>{"".join(par_nodes)}
                        </p:childTnLst>
                      </p:cTn>
                    </p:par>{"".join(click_groups)}
                  </p:childTnLst>
                </p:cTn>
                <p:prevCondLst>
                  <p:cond evt="onPrev" delay="0">
                    <p:tgtEl>
                      <p:sldTgt/>
                    </p:tgtEl>
                  </p:cond>
                </p:prevCondLst>
                <p:nextCondLst>
                  <p:cond evt="onNext" delay="0">
                    <p:tgtEl>
                      <p:sldTgt/>
                    </p:tgtEl>
                  </p:cond>
                </p:nextCondLst>
              </p:seq>
            </p:childTnLst>
          </p:cTn>
        </p:par>
      </p:tnLst>
      <p:bldLst>
        {"".join(bld_nodes)}
      </p:bldLst>
    </p:timing>"""


def _is_dark_theme(spec: Dict[str, Any]) -> bool:
    """Detect if the presentation specification requests a dark theme."""
    theme_style = str(spec.get("theme_style", "")).lower()
    theme_color = str(spec.get("theme_color", "")).lower()
    if any(k in theme_style for k in ["dark", "void", "night", "black", "cyber", "neon"]):
        return True
    if spec.get("dark_mode") is True:
        return True
    if theme_color in ["#0f172a", "#000000", "#0a0a0a", "#111827", "#0b0f19", "#1e1b4b"]:
        return True
    return False


def create_powerpoint_deck(spec: Dict[str, Any], output_path: str) -> Dict[str, Any]:
    """
    Build a high-end, executive-grade PowerPoint presentation (.pptx) in NotebookLM Technical Blueprint Style
    from a JSON slide specification, complete with native slide transitions, shape entrance animations,
    and click-to-reveal interactive quiz slides.
    """
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.oxml import parse_xml

        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        title = spec.get("title", "Presentation")
        is_dark = _is_dark_theme(spec)
        animations_enabled = bool(spec.get("animations_enabled", True))
        deck_anim_style = str(spec.get("animation_style", "swipe")).lower()

        if is_dark:
            bg_color = RGBColor(15, 23, 42)          # Dark Navy Blueprint #0F172A
            header_color = RGBColor(248, 250, 252)   # Crisp White #F8FAFC
            subtitle_color = RGBColor(148, 163, 184) # Slate Gray
            card_color = RGBColor(30, 41, 59)        # Card Fill #1E293B
            card_border = RGBColor(99, 102, 241)     # Indigo Accent #6366F1
            text_main = RGBColor(241, 245, 249)
            accent_blue = RGBColor(96, 165, 250)
            emerald_green = RGBColor(52, 211, 153)
            code_bg = RGBColor(15, 23, 42)
            code_fg = RGBColor(148, 163, 184)
        else:
            # NotebookLM Technical Blueprint Style (Light Paper #FAF9F6)
            bg_color = RGBColor(250, 249, 246)       # Off-white Blueprint #FAF9F6
            header_color = RGBColor(17, 24, 39)      # Dark Charcoal #111827
            subtitle_color = RGBColor(75, 85, 99)    # Slate #4B5563
            card_color = RGBColor(255, 255, 255)     # Pure White Card #FFFFFF
            card_border = RGBColor(209, 213, 219)    # Tech Border #D1D5DB
            text_main = RGBColor(17, 24, 39)
            accent_blue = RGBColor(79, 70, 229)      # Indigo Accent #4F46E5
            emerald_green = RGBColor(16, 185, 129)
            code_bg = RGBColor(241, 245, 249)
            code_fg = RGBColor(51, 65, 85)

        slides_data = spec.get("slides", [])
        blank_slide_layout = prs.slide_layouts[6]

        for i, s in enumerate(slides_data):
            slide_type = str(s.get("type", "content")).lower()
            image_path = s.get("image_path") or s.get("image_url")
            slide = prs.slides.add_slide(blank_slide_layout)
            animated_shape_ids: List[int] = []
            click_reveal_shape_ids: List[int] = []

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

            # Speaker Notes
            notes_text = s.get("notes") or s.get("explanation") or ""

            if slide_type == "title" or i == 0:
                if image_path and os.path.exists(str(image_path)):
                    try:
                        pic = slide.shapes.add_picture(str(image_path), Inches(0.6), Inches(0.6), Inches(5.8), Inches(6.3))
                        animated_shape_ids.append(pic.shape_id)
                    except Exception as ie:
                        logger.error("Error embedding title image: %s", ie)

                    txBox = slide.shapes.add_textbox(Inches(6.7), Inches(1.2), Inches(5.8), Inches(5.0))
                    animated_shape_ids.append(txBox.shape_id)
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
                    animated_shape_ids.append(txBox.shape_id)
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
                txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(5.8), Inches(6.0))
                animated_shape_ids.append(txBox.shape_id)
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

                if image_path and os.path.exists(str(image_path)):
                    try:
                        img_border = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(6.8), Inches(0.8), Inches(5.8), Inches(5.8))
                        img_border.fill.background()
                        img_border.line.color.rgb = card_border
                        img_border.line.width = Pt(1.5)
                        pic = slide.shapes.add_picture(str(image_path), Inches(6.9), Inches(0.9), Inches(5.6), Inches(5.6))
                        animated_shape_ids.append(img_border.shape_id)
                        animated_shape_ids.append(pic.shape_id)
                    except Exception as ie:
                        logger.error("Error adding picture to PPTX slide: %s", ie)

            elif slide_type in ["process", "pipeline"]:
                txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.733), Inches(1.0))
                animated_shape_ids.append(txBox.shape_id)
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
                animated_shape_ids.append(arrow.shape_id)

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
                    animated_shape_ids.append(node_box.shape_id)

                    ntf = node_box.text_frame
                    ntf.word_wrap = True
                    np1 = ntf.paragraphs[0]
                    np1.text = f"Step {step_idx+1}: {step_text.split(':')[0] if ':' in step_text else step_text}"
                    np1.font.size = Pt(18)
                    np1.font.bold = True
                    np1.font.color.rgb = header_color

                    code_box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left_pos, Inches(4.5), col_width - Inches(0.3), Inches(2.0))
                    code_box.fill.solid()
                    code_box.fill.fore_color.rgb = code_bg
                    code_box.line.color.rgb = card_border
                    code_box.line.width = Pt(1)
                    animated_shape_ids.append(code_box.shape_id)

                    ctf = code_box.text_frame
                    ctf.word_wrap = True
                    cp1 = ctf.paragraphs[0]
                    cp1.text = step_text.split(':')[1] if ':' in step_text else f"// Execution Config {step_idx+1}"
                    cp1.font.size = Pt(13)
                    cp1.font.color.rgb = code_fg

            elif slide_type == "quiz":
                txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.733), Inches(1.0))
                animated_shape_ids.append(txBox.shape_id)
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

                left_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.7), Inches(6.8), Inches(5.1))
                left_box.fill.solid()
                left_box.fill.fore_color.rgb = card_color
                left_box.line.color.rgb = card_border
                left_box.line.width = Pt(1.5)
                animated_shape_ids.append(left_box.shape_id)

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

                # Right side: Answer Key & Explanation Card (Revealed on Click/Tap in PowerPoint!)
                right_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.9), Inches(1.7), Inches(4.6), Inches(5.1))
                right_box.fill.solid()
                right_box.fill.fore_color.rgb = card_color
                right_box.line.color.rgb = emerald_green
                right_box.line.width = Pt(2.0)
                click_reveal_shape_ids.append(right_box.shape_id)

                rtf = right_box.text_frame
                rtf.word_wrap = True
                rp0 = rtf.paragraphs[0]
                rp0.text = "👆 TAP / CLICK REVEALED ANSWER KEY"
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
                txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.733), Inches(1.0))
                animated_shape_ids.append(txBox.shape_id)
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
                        animated_shape_ids.append(card.shape_id)

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
                        animated_shape_ids.append(card_b.shape_id)

                        btf = card_b.text_frame
                        btf.word_wrap = True
                        bp = btf.paragraphs[0]
                        bp.text = f"•   {b_text}"
                        bp.font.size = Pt(16)
                        bp.font.color.rgb = text_main

            # Apply Native PowerPoint Slide Transition & Shape Entrance Animations (in strict OpenXML order: transition then timing)
            slide_anim = str(s.get("animation") or s.get("transition") or deck_anim_style or "swipe").lower()
            try:
                transition_xml_str = _build_pptx_transition_xml(slide_anim if animations_enabled else "fade")
                if transition_xml_str:
                    slide.element.append(parse_xml(transition_xml_str))
            except Exception as tr_err:
                logger.debug("Transition XML skipped: %s", tr_err)

            if animations_enabled and (animated_shape_ids or click_reveal_shape_ids):
                try:
                    timing_xml_str = _build_pptx_timing_xml(animated_shape_ids, slide_anim, click_reveal_shape_ids)
                    if timing_xml_str:
                        slide.element.append(parse_xml(timing_xml_str))
                except Exception as tm_err:
                    logger.debug("Timing XML skipped: %s", tm_err)

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
            "animations_enabled": animations_enabled,
            "animation_style": deck_anim_style,
            "message": f"Successfully created PowerPoint presentation at '{output_path}'"
        }
    except Exception as e:
        logger.error("Error creating PowerPoint deck: %s", e)
        return {"status": "error", "error": str(e)}


def create_html_presentation(spec: Dict[str, Any], output_path: str) -> Dict[str, Any]:
    """
    Build an executive, animated HTML Reveal.js presentation with 3D swipe/push transitions,
    mouse drag-to-swipe & touch swiping gestures, staggered CSS keyframe entrance animations,
    embedded Base64 images, dark/light blueprint theme toggle, and tap-anywhere-to-reveal quiz answers.
    """
    try:
        title = spec.get("title", "Executive Presentation")
        subtitle = spec.get("subtitle", "Technical Blueprint Deck")
        author = spec.get("author", "PPT-generater Agent")
        slides_data = spec.get("slides", [])
        animations_enabled = bool(spec.get("animations_enabled", True))
        deck_anim_style = str(spec.get("animation_style", "swipe")).lower()
        is_dark = _is_dark_theme(spec)

        # Normalize deck_anim_style for CSS class and Reveal transition
        if "swipe" in deck_anim_style or "push" in deck_anim_style or "slide" in deck_anim_style:
            norm_anim = "swipe"
            reveal_transition = "slide"
        elif "zoom" in deck_anim_style or "scale" in deck_anim_style:
            norm_anim = "zoom"
            reveal_transition = "zoom"
        elif "bounce" in deck_anim_style or "spring" in deck_anim_style or "pop" in deck_anim_style:
            norm_anim = "bounce"
            reveal_transition = "convex"
        elif "convex" in deck_anim_style or "3d" in deck_anim_style or "flip" in deck_anim_style:
            norm_anim = "convex"
            reveal_transition = "convex"
        elif "fly" in deck_anim_style or "wipe" in deck_anim_style:
            norm_anim = "fly"
            reveal_transition = "slide"
        elif "fade" in deck_anim_style:
            norm_anim = "fade"
            reveal_transition = "fade"
        else:
            norm_anim = "swipe"
            reveal_transition = "slide"

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
            slide_transition = str(s.get("transition") or s.get("animation") or reveal_transition).lower()
            if "swipe" in slide_transition or "push" in slide_transition:
                slide_transition = "slide"
            elif slide_transition not in ["none", "fade", "slide", "convex", "concave", "zoom"]:
                slide_transition = reveal_transition

            if stype == "title" or i == 0:
                if img_data_uri:
                    slide_html = f"""
                    <section class="title-slide split-title" data-transition="{slide_transition}">
                        <div class="left-col anim-item anim-left" style="--anim-order: 1;">
                            <div class="blueprint-frame">
                                <img src="{img_data_uri}" alt="{stitle}" class="title-diagram-img" />
                            </div>
                        </div>
                        <div class="right-col anim-item anim-right" style="--anim-order: 2;">
                            <div class="tech-badge">PRESENTATION ARCHITECT // SLIDE 01</div>
                            <h1 class="slide-main-title">{stitle}</h1>
                            <h3 class="slide-subtitle">{ssub or subtitle}</h3>
                            <div class="swipe-hint-pill">👆 Swipe Left/Right, Drag with Mouse, or Use Arrow Keys to Navigate</div>
                            <div class="title-footer">Prepared by <strong>{author}</strong> | Interactive Animated Slide Suite</div>
                        </div>
                    </section>
                    """
                else:
                    slide_html = f"""
                    <section class="title-slide" data-transition="{slide_transition}">
                        <div class="tech-badge anim-item anim-up" style="--anim-order: 1;">PRESENTATION ARCHITECT // SLIDE 01</div>
                        <h1 class="slide-main-title anim-item anim-up" style="--anim-order: 2;">{stitle}</h1>
                        <h3 class="slide-subtitle anim-item anim-up" style="--anim-order: 3;">{ssub or subtitle}</h3>
                        <div class="swipe-hint-pill anim-item anim-up" style="--anim-order: 4;">👆 Swipe Left/Right, Drag with Mouse, or Use Arrow Keys to Navigate</div>
                        <div class="title-footer anim-item anim-up" style="--anim-order: 5;">Prepared by <strong>{author}</strong> | Interactive Animated Slide Suite</div>
                    </section>
                    """
            elif stype in ["split_image", "image"] or (img_data_uri and stype != "quiz"):
                b_items = "".join([
                    f'<div class="bullet-card anim-item anim-up" style="--anim-order: {idx+2};" onclick="this.classList.toggle(\'tapped-card\')"><span>✦</span> {b}</div>'
                    for idx, b in enumerate(bullets[:4])
                ])
                slide_html = f"""
                <section class="split-slide-container" data-transition="{slide_transition}">
                    <div class="split-left">
                        <h2 class="slide-header anim-item anim-up" style="--anim-order: 1;">{stitle}</h2>
                        {f'<p class="slide-subhead anim-item anim-up" style="--anim-order: 1;">{ssub}</p>' if ssub else ''}
                        <div class="bullets-wrapper">{b_items}</div>
                    </div>
                    <div class="split-right">
                        <div class="blueprint-image-box anim-item anim-zoom" style="--anim-order: 2;">
                            <img src="{img_data_uri}" alt="{stitle}" class="blueprint-img" />
                            <div class="image-annotation-overlay">TOPIC-MATCHED VISUAL</div>
                        </div>
                    </div>
                </section>
                """
            elif stype in ["process", "pipeline"]:
                steps = s.get("steps") or bullets or ["Phase 1: Architecture", "Phase 2: Execution", "Phase 3: Verification"]
                nodes_html = []
                for idx, st in enumerate(steps[:3]):
                    s_title = st.split(':')[0] if ':' in st else st
                    s_code = st.split(':')[1] if ':' in st else f"// Step {idx+1} Verified"
                    nodes_html.append(f"""
                    <div class="pipeline-node anim-item anim-up" style="--anim-order: {idx+2};" onclick="this.classList.toggle('tapped-card')">
                        <div class="node-title">Step {idx+1}: {s_title}</div>
                        <div class="code-callout-box">
                            <code>{s_code}</code>
                        </div>
                    </div>
                    """)
                slide_html = f"""
                <section class="pipeline-slide" data-transition="{slide_transition}">
                    <h2 class="slide-header anim-item anim-up" style="--anim-order: 1;">{stitle}</h2>
                    <div class="pipeline-connector-line anim-item anim-line" style="--anim-order: 1;"></div>
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
                        is_corr = opt.strip() == q_ans.strip() or (len(q_ans) >= 2 and opt.strip().startswith(q_ans.strip()[:2])) if q_ans else (o_idx == 1)
                        options_html.append(f"""
                        <button class="quiz-btn" data-correct="{str(is_corr).lower()}" onclick="event.stopPropagation(); checkQuizAnswer(this, {str(is_corr).lower()}, '{q_id}')">
                            <span class="opt-label">{opt}</span>
                        </button>
                        """)

                    q_blocks.append(f"""
                    <div class="quiz-card anim-item anim-up" style="--anim-order: {q_idx+2};" id="{q_id}" onclick="revealQuizCardAnswer('{q_id}')">
                        <div class="quiz-tap-badge">👆 Tap Card or Option to Reveal Answer</div>
                        <div class="quiz-q-title">Q{q_idx+1}: {q.get('question', '')}</div>
                        <div class="quiz-options-list">
                            {"".join(options_html)}
                        </div>
                        <div class="quiz-explanation-box" id="{q_id}_exp" style="display:none;">
                            <div class="exp-title">✓ Verified Answer: {q_ans}</div>
                            <div class="exp-body">💡 {q_exp}</div>
                        </div>
                    </div>
                    """)

                slide_html = f"""
                <section class="quiz-slide" data-transition="{slide_transition}">
                    <div class="tech-badge anim-item anim-up" style="--anim-order: 1;">🎯 INTERACTIVE Q&A // TAP TO REVEAL ANSWERS</div>
                    <h2 class="slide-header anim-item anim-up" style="--anim-order: 1;">{stitle}</h2>
                    <div class="quiz-grid">
                        {"".join(q_blocks)}
                    </div>
                    <div class="quiz-controls-bar anim-item anim-up" style="--anim-order: 4;">
                        <button class="toggle-all-btn" onclick="toggleAllQuizAnswers()">
                            <span>👆 Tap Here to Reveal / Hide All Answers & Explanations</span>
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
                        <div class="metric-card anim-item anim-zoom" style="--anim-order: {m_idx+2};" onclick="this.classList.toggle('tapped-card')">
                            <div class="metric-label">{m.get("label", "Metric")}</div>
                            <div class="metric-value">{m.get("value", "0")}</div>
                        </div>
                        """)
                    cards_html = f'<div class="metrics-grid">{"".join(cards)}</div>'

                bullets_html = ""
                if bullets:
                    b_items = "".join([
                        f'<div class="bullet-card anim-item anim-up" style="--anim-order: {idx+2};" onclick="this.classList.toggle(\'tapped-card\')"><span>✦</span> {b}</div>'
                        for idx, b in enumerate(bullets[:5])
                    ])
                    bullets_html = f'<div class="bullets-wrapper">{b_items}</div>'

                slide_html = f"""
                <section data-transition="{slide_transition}">
                    <h2 class="slide-header anim-item anim-up" style="--anim-order: 1;">{stitle}</h2>
                    {cards_html}
                    {bullets_html}
                    {f'<aside class="notes">{notes_text}</aside>' if notes_text else ''}
                </section>
                """

            html_slides.append(slide_html)

        theme_class = "theme-dark" if is_dark else "theme-light"
        body_anim_class = f"{theme_class} animations-active anim-style-{norm_anim}" if animations_enabled else f"{theme_class} animations-active anim-style-swipe"

        reveal_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/reveal.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-blueprint: #FAF9F6;
            --text-dark: #111827;
            --text-sub: #4B5563;
            --accent-indigo: #4F46E5;
            --accent-cyan: #06B6D4;
            --border-tech: #D1D5DB;
            --card-bg: #FFFFFF;
            --code-bg: #F3F4F6;
            --code-fg: #1F2937;
            --emerald: #10B981;
            --grid-line: rgba(209, 213, 219, 0.45);
        }}
        body.theme-dark {{
            --bg-blueprint: #0B0F19;
            --text-dark: #F8FAFC;
            --text-sub: #94A3B8;
            --accent-indigo: #6366F1;
            --accent-cyan: #22D3EE;
            --border-tech: #1E293B;
            --card-bg: #111827;
            --code-bg: #0F172A;
            --code-fg: #E2E8F0;
            --emerald: #34D399;
            --grid-line: rgba(99, 102, 241, 0.12);
        }}
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            background: var(--bg-blueprint);
            color: var(--text-dark);
            user-select: none;
            -webkit-user-select: none;
            overflow: hidden;
        }}
        .reveal {{
            font-family: 'Inter', sans-serif;
            background: var(--bg-blueprint);
            color: var(--text-dark);
            cursor: grab;
        }}
        .reveal:active {{
            cursor: grabbing;
        }}
        .reveal::before {{
            content: "";
            position: fixed;
            inset: 0;
            background-size: 32px 32px;
            background-image: linear-gradient(to right, var(--grid-line) 1px, transparent 1px),
                              linear-gradient(to bottom, var(--grid-line) 1px, transparent 1px);
            pointer-events: none;
        }}
        .title-slide {{ text-align: left; padding: 36px; }}
        .split-title {{ display: flex; gap: 40px; align-items: center; }}
        .left-col {{ flex: 1; }}
        .right-col {{ flex: 1.2; }}
        .tech-badge {{ display: inline-block; padding: 6px 14px; background: rgba(99, 102, 241, 0.14); border: 1px solid var(--accent-indigo); border-radius: 6px; font-size: 0.72em; font-weight: 700; color: var(--accent-indigo); letter-spacing: 1.5px; margin-bottom: 18px; }}
        .slide-main-title {{ font-family: 'Outfit', sans-serif; font-size: 2.9em !important; font-weight: 800; color: var(--text-dark); margin: 0 0 12px 0 !important; line-height: 1.12 !important; }}
        .slide-subtitle {{ font-size: 1.3em !important; color: var(--text-sub); font-weight: 400; margin-top: 10px !important; }}
        .swipe-hint-pill {{ display: inline-flex; align-items: center; gap: 8px; margin-top: 22px; padding: 8px 16px; border-radius: 999px; background: rgba(99, 102, 241, 0.12); border: 1px dashed var(--accent-indigo); color: var(--accent-indigo); font-size: 0.75em; font-weight: 600; }}
        .title-footer {{ font-size: 0.8em; color: var(--text-sub); margin-top: 32px; border-top: 1px solid var(--border-tech); padding-top: 14px; }}
        .slide-header {{ font-family: 'Outfit', sans-serif; text-align: left; font-size: 2.1em !important; font-weight: 800; color: var(--text-dark); margin: 0 0 22px 0 !important; border-bottom: 2px solid var(--border-tech); padding-bottom: 12px; }}
        .slide-subhead {{ text-align: left; font-size: 1.05em; color: var(--text-sub); margin-top: -10px; margin-bottom: 16px; }}
        .split-slide-container {{ display: flex; gap: 35px; align-items: center; text-align: left; }}
        .split-left {{ flex: 1.1; }}
        .split-right {{ flex: 1.2; }}
        .blueprint-image-box {{ position: relative; border: 2px solid var(--border-tech); border-radius: 14px; padding: 8px; background: var(--card-bg); box-shadow: 0 12px 32px rgba(0,0,0,0.14); transition: transform 0.35s ease; }}
        .blueprint-image-box:hover {{ transform: scale(1.02); }}
        .blueprint-img {{ width: 100%; height: 410px; object-fit: cover; border-radius: 10px; display: block; }}
        .title-diagram-img {{ width: 100%; height: 430px; object-fit: cover; border-radius: 10px; display: block; }}
        .blueprint-frame {{ border: 2px solid var(--border-tech); border-radius: 14px; padding: 8px; background: var(--card-bg); box-shadow: 0 12px 32px rgba(0,0,0,0.14); }}
        .image-annotation-overlay {{ position: absolute; bottom: 16px; left: 16px; background: rgba(15, 23, 42, 0.88); color: #FFFFFF; padding: 5px 12px; font-size: 0.65em; font-weight: 700; border-radius: 6px; letter-spacing: 1px; border: 1px solid rgba(99,102,241,0.4); }}
        .pipeline-slide {{ text-align: left; }}
        .pipeline-connector-line {{ height: 6px; background: linear-gradient(90deg, var(--accent-indigo), var(--accent-cyan), var(--accent-indigo)); background-size: 200% 100%; animation: gradientFlow 3s linear infinite; margin: 28px 0; border-radius: 3px; position: relative; }}
        .pipeline-nodes-wrapper {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
        .pipeline-node {{ background: var(--card-bg); border: 1px solid var(--border-tech); border-radius: 12px; padding: 20px; box-shadow: 0 6px 18px rgba(0,0,0,0.08); transition: all 0.25s ease; cursor: pointer; }}
        .pipeline-node:hover, .pipeline-node.tapped-card {{ transform: translateY(-5px); border-color: var(--accent-indigo); box-shadow: 0 12px 26px rgba(99,102,241,0.18); }}
        .node-title {{ font-family: 'Outfit', sans-serif; font-weight: 700; font-size: 1.1em; color: var(--text-dark); margin-bottom: 12px; }}
        .code-callout-box {{ background: var(--code-bg); border: 1px solid var(--border-tech); border-radius: 8px; padding: 12px; font-family: monospace; font-size: 0.85em; color: var(--code-fg); }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 22px 0; }}
        .metric-card {{ background: var(--card-bg); border: 1px solid var(--border-tech); border-radius: 12px; padding: 24px; text-align: left; box-shadow: 0 6px 18px rgba(0,0,0,0.08); transition: all 0.25s ease; cursor: pointer; }}
        .metric-card:hover, .metric-card.tapped-card {{ transform: translateY(-5px) scale(1.02); border-color: var(--accent-indigo); }}
        .metric-label {{ font-size: 0.75em; text-transform: uppercase; color: var(--text-sub); letter-spacing: 1px; font-weight: 700; }}
        .metric-value {{ font-family: 'Outfit', sans-serif; font-size: 2.5em; font-weight: 800; color: var(--accent-indigo); margin: 8px 0 0 0; }}
        .bullets-wrapper {{ display: flex; flex-direction: column; gap: 12px; text-align: left; margin-top: 14px; }}
        .bullet-card {{ background: var(--card-bg); border: 1px solid var(--border-tech); border-left: 4px solid var(--accent-indigo); border-radius: 10px; padding: 15px 20px; font-size: 1.05em; color: var(--text-dark); box-shadow: 0 4px 12px rgba(0,0,0,0.06); transition: all 0.22s ease; cursor: pointer; }}
        .bullet-card:hover, .bullet-card.tapped-card {{ transform: translateX(8px); border-color: var(--accent-indigo); box-shadow: 0 8px 20px rgba(99,102,241,0.16); }}
        .bullet-card span {{ color: var(--accent-indigo); margin-right: 8px; font-weight: bold; }}

        /* Keyframe Animations: 3D Swipe, Fade-Up, Zoom, Bounce, Fly-In */
        @keyframes pptSwipeIn {{
            0% {{ opacity: 0; transform: perspective(900px) translateX(90px) rotateY(-14deg) scale(0.94); }}
            100% {{ opacity: 1; transform: perspective(900px) translateX(0) rotateY(0deg) scale(1); }}
        }}
        @keyframes pptFadeUp {{
            0% {{ opacity: 0; transform: translateY(32px); }}
            100% {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes pptZoomIn {{
            0% {{ opacity: 0; transform: scale(0.82); }}
            100% {{ opacity: 1; transform: scale(1); }}
        }}
        @keyframes pptFlyLeft {{
            0% {{ opacity: 0; transform: translateX(-64px); }}
            100% {{ opacity: 1; transform: translateX(0); }}
        }}
        @keyframes pptFlyRight {{
            0% {{ opacity: 0; transform: translateX(64px); }}
            100% {{ opacity: 1; transform: translateX(0); }}
        }}
        @keyframes pptBounceIn {{
            0% {{ opacity: 0; transform: scale(0.72) translateY(35px); }}
            60% {{ opacity: 1; transform: scale(1.05) translateY(-7px); }}
            80% {{ transform: scale(0.98) translateY(2px); }}
            100% {{ opacity: 1; transform: scale(1) translateY(0); }}
        }}
        @keyframes pptConvexFlip {{
            0% {{ opacity: 0; transform: perspective(1000px) rotateX(25deg) translateY(30px); }}
            100% {{ opacity: 1; transform: perspective(1000px) rotateX(0deg) translateY(0); }}
        }}
        @keyframes pptLineExpand {{
            0% {{ transform: scaleX(0); transform-origin: left; opacity: 0.3; }}
            100% {{ transform: scaleX(1); transform-origin: left; opacity: 1; }}
        }}
        @keyframes answerRevealAnim {{
            0% {{ opacity: 0; transform: translateY(-10px) scale(0.97); }}
            100% {{ opacity: 1; transform: translateY(0) scale(1); }}
        }}
        @keyframes gradientFlow {{
            0% {{ background-position: 0% 50%; }}
            100% {{ background-position: 200% 50%; }}
        }}

        /* Active Slide Staggered Element Animations */
        body.animations-active .reveal .slides section.present .anim-item {{
            animation-duration: 0.68s;
            animation-fill-mode: both;
            animation-timing-function: cubic-bezier(0.22, 1, 0.36, 1);
            animation-delay: calc(var(--anim-order, 1) * 0.12s);
        }}
        body.animations-active .reveal .slides section.present .anim-up {{ animation-name: pptFadeUp; }}
        body.animations-active .reveal .slides section.present .anim-zoom {{ animation-name: pptZoomIn; }}
        body.animations-active .reveal .slides section.present .anim-left {{ animation-name: pptFlyLeft; }}
        body.animations-active .reveal .slides section.present .anim-right {{ animation-name: pptFlyRight; }}
        body.animations-active .reveal .slides section.present .anim-line {{ animation-name: pptLineExpand; }}

        /* Deck-Wide Animation Style Overrides */
        body.animations-active.anim-style-swipe .reveal .slides section.present .anim-item {{
            animation-name: pptSwipeIn;
            animation-duration: 0.72s;
        }}
        body.animations-active.anim-style-zoom .reveal .slides section.present .anim-item {{
            animation-name: pptZoomIn;
        }}
        body.animations-active.anim-style-bounce .reveal .slides section.present .anim-item {{
            animation-name: pptBounceIn;
            animation-duration: 0.78s;
        }}
        body.animations-active.anim-style-fly .reveal .slides section.present .anim-item {{
            animation-name: pptFlyRight;
        }}
        body.animations-active.anim-style-convex .reveal .slides section.present .anim-item {{
            animation-name: pptConvexFlip;
        }}

        /* Custom Swipe Feedback Toast */
        .swipe-toast {{
            position: fixed;
            top: 18px;
            right: 20px;
            z-index: 45;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(8px);
            color: #F8FAFC;
            padding: 6px 14px;
            border-radius: 999px;
            border: 1px solid rgba(99, 102, 241, 0.5);
            font-family: 'Inter', sans-serif;
            font-size: 11px;
            font-weight: 600;
            pointer-events: none;
            opacity: 0;
            transform: translateY(-8px);
            transition: opacity 0.25s ease, transform 0.25s ease;
        }}
        .swipe-toast.show {{
            opacity: 1;
            transform: translateY(0);
        }}

        /* Interactive Animation & Swipe Navigation Toolbar */
        .ppt-anim-toolbar {{
            position: fixed;
            bottom: 14px;
            left: 16px;
            z-index: 45;
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(15, 23, 42, 0.92);
            backdrop-filter: blur(10px);
            color: #F9FAFB;
            padding: 7px 14px;
            border-radius: 999px;
            border: 1px solid rgba(99, 102, 241, 0.45);
            font-family: 'Inter', sans-serif;
            font-size: 12px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        }}
        .ppt-anim-toolbar select, .ppt-anim-toolbar button {{
            background: rgba(255,255,255,0.1);
            color: #FFFFFF;
            border: 1px solid rgba(255,255,255,0.22);
            border-radius: 999px;
            padding: 4px 11px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            outline: none;
            transition: all 0.18s ease;
        }}
        .ppt-anim-toolbar select option {{
            background: #0F172A;
            color: #FFFFFF;
        }}
        .ppt-anim-toolbar button:hover {{
            background: var(--accent-indigo);
            border-color: var(--accent-indigo);
            transform: translateY(-1px);
        }}
        .ppt-anim-toolbar .nav-pill {{
            background: rgba(99, 102, 241, 0.25);
            border-color: rgba(99, 102, 241, 0.6);
        }}

        /* Interactive Quiz & Tap-to-Reveal Styles */
        .quiz-slide {{ text-align: left; padding: 16px; }}
        .quiz-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 22px; margin-top: 12px; }}
        .quiz-card {{
            position: relative;
            background: var(--card-bg);
            border: 2px solid var(--border-tech);
            border-radius: 14px;
            padding: 20px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.08);
            text-align: left;
            cursor: pointer;
            transition: all 0.25s ease;
        }}
        .quiz-card:hover {{
            border-color: var(--accent-indigo);
            transform: translateY(-3px);
            box-shadow: 0 12px 28px rgba(99, 102, 241, 0.18);
        }}
        .quiz-tap-badge {{
            display: inline-block;
            font-size: 0.68em;
            font-weight: 700;
            color: var(--accent-indigo);
            background: rgba(99, 102, 241, 0.12);
            padding: 3px 10px;
            border-radius: 999px;
            margin-bottom: 10px;
        }}
        .quiz-q-title {{ font-family: 'Outfit', sans-serif; font-size: 1.12em; font-weight: 700; color: var(--text-dark); margin-bottom: 14px; line-height: 1.35; }}
        .quiz-options-list {{ display: flex; flex-direction: column; gap: 8px; }}
        .quiz-btn {{
            background: var(--code-bg);
            border: 1px solid var(--border-tech);
            border-radius: 8px;
            padding: 10px 14px;
            text-align: left;
            font-size: 0.88em;
            font-family: 'Inter', sans-serif;
            color: var(--text-dark);
            cursor: pointer;
            transition: all 0.2s;
        }}
        .quiz-btn:hover {{ background: rgba(99, 102, 241, 0.15); border-color: var(--accent-indigo); }}
        .quiz-btn.correct {{ background: rgba(16, 185, 129, 0.2) !important; border-color: #10B981 !important; color: var(--emerald) !important; font-weight: 700; }}
        .quiz-btn.wrong {{ background: rgba(239, 68, 68, 0.18) !important; border-color: #EF4444 !important; color: #F87171 !important; opacity: 0.8; }}
        .quiz-explanation-box {{
            margin-top: 14px;
            padding: 12px 14px;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.45);
            border-radius: 10px;
            font-size: 0.84em;
            animation: answerRevealAnim 0.35s cubic-bezier(0.22, 1, 0.36, 1) both;
        }}
        .exp-title {{ font-weight: 700; color: var(--emerald); margin-bottom: 4px; }}
        .exp-body {{ color: var(--text-dark); line-height: 1.45; }}
        .quiz-controls-bar {{ margin-top: 20px; text-align: center; }}
        .toggle-all-btn {{
            background: var(--accent-indigo);
            color: #FFFFFF;
            border: none;
            padding: 10px 24px;
            border-radius: 999px;
            font-size: 0.88em;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s;
            box-shadow: 0 6px 18px rgba(99, 102, 241, 0.35);
        }}
        .toggle-all-btn:hover {{ transform: scale(1.03); filter: brightness(1.1); }}
    </style>
</head>
<body class="{body_anim_class}">
    <div id="swipeToast" class="swipe-toast">✨ Swiped Slide</div>

    <div class="reveal">
        <div class="slides">
            {"".join(html_slides)}
        </div>
    </div>

    <div class="ppt-anim-toolbar">
        <button class="nav-pill" onclick="swipePrevSlide()" title="Swipe to Previous Slide">⬅ Swipe Prev</button>
        <button class="nav-pill" onclick="swipeNextSlide()" title="Swipe to Next Slide">Swipe Next ➡</button>
        <span>✨ Animation:</span>
        <select id="pptAnimSelect" onchange="changePptAnimation(this.value)">
            <option value="swipe" {"selected" if norm_anim == "swipe" else ""}>3D Swipe / Slide</option>
            <option value="fade" {"selected" if norm_anim == "fade" else ""}>Smooth Fade-Up</option>
            <option value="zoom" {"selected" if norm_anim == "zoom" else ""}>Dynamic Zoom</option>
            <option value="bounce" {"selected" if norm_anim == "bounce" else ""}>Spring Bounce</option>
            <option value="fly" {"selected" if norm_anim == "fly" else ""}>Slide Fly-In</option>
            <option value="convex" {"selected" if norm_anim == "convex" else ""}>3D Convex Flip</option>
            <option value="off" {"selected" if deck_anim_style in ["none", "off", "false"] else ""}>Off</option>
        </select>
        <button onclick="replaySlideAnimation()">↻ Replay</button>
        <button onclick="toggleDeckTheme()" id="themeBtn">{"☀️ Light" if is_dark else "🌙 Dark"}</button>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/reveal.min.js"></script>
    <script>
        Reveal.initialize({{
            controls: true,
            progress: true,
            center: false,
            hash: false,
            history: false,
            touch: true,
            keyboard: true,
            overview: true,
            transition: '{reveal_transition}',
            transitionSpeed: 'default',
            backgroundTransition: 'fade',
            slideNumber: 'c/t'
        }});

        function showSwipeToast(msg) {{
            const t = document.getElementById('swipeToast');
            if (!t) return;
            t.textContent = msg;
            t.classList.add('show');
            clearTimeout(window._swipeToastTimer);
            window._swipeToastTimer = setTimeout(() => t.classList.remove('show'), 950);
        }}

        function swipeNextSlide() {{
            Reveal.next();
            showSwipeToast('➡ Swiped to Next Slide');
        }}

        function swipePrevSlide() {{
            Reveal.prev();
            showSwipeToast('⬅ Swiped to Previous Slide');
        }}

        // Desktop Mouse Drag-to-Swipe & Trackpad Horizontal Gesture Engine
        (function initSwipeGestures() {{
            let startX = null;
            let startY = null;
            let isDragging = false;

            document.addEventListener('pointerdown', (e) => {{
                if (e.target.closest('button, select, a, input, .ppt-anim-toolbar')) return;
                startX = e.clientX;
                startY = e.clientY;
                isDragging = true;
            }});

            document.addEventListener('pointerup', (e) => {{
                if (!isDragging || startX === null) return;
                const dx = e.clientX - startX;
                const dy = e.clientY - startY;
                isDragging = false;
                startX = null;
                if (Math.abs(dx) > 55 && Math.abs(dx) > Math.abs(dy) * 1.3) {{
                    if (dx < 0) {{
                        swipeNextSlide();
                    }} else {{
                        swipePrevSlide();
                    }}
                }}
            }});

            // Horizontal trackpad two-finger swipe support
            let lastWheelTime = 0;
            document.addEventListener('wheel', (e) => {{
                const now = Date.now();
                if (now - lastWheelTime < 650) return;
                if (Math.abs(e.deltaX) > 40 && Math.abs(e.deltaX) > Math.abs(e.deltaY) * 1.4) {{
                    lastWheelTime = now;
                    if (e.deltaX > 0) swipeNextSlide();
                    else swipePrevSlide();
                }}
            }}, {{ passive: true }});
        }})();

        function replaySlideAnimation() {{
            const currentSlide = Reveal.getCurrentSlide();
            if (!currentSlide) return;
            const items = currentSlide.querySelectorAll('.anim-item');
            items.forEach(el => {{
                el.style.animation = 'none';
                void el.offsetHeight;
                el.style.animation = '';
            }});
        }}

        function changePptAnimation(style) {{
            document.body.classList.remove(
                'anim-style-swipe', 'anim-style-fade', 'anim-style-zoom',
                'anim-style-bounce', 'anim-style-fly', 'anim-style-convex'
            );
            if (style === 'off') {{
                document.body.classList.remove('animations-active');
                Reveal.configure({{ transition: 'none' }});
            }} else {{
                document.body.classList.add('animations-active', 'anim-style-' + style);
                const trMap = {{
                    swipe: 'slide',
                    fade: 'fade',
                    zoom: 'zoom',
                    bounce: 'convex',
                    fly: 'slide',
                    convex: 'convex'
                }};
                Reveal.configure({{ transition: trMap[style] || 'slide' }});
                replaySlideAnimation();
                showSwipeToast('✨ Animation: ' + style.toUpperCase());
            }}
        }}

        function toggleDeckTheme() {{
            const isDark = document.body.classList.toggle('theme-dark');
            document.body.classList.toggle('theme-light', !isDark);
            const btn = document.getElementById('themeBtn');
            if (btn) btn.textContent = isDark ? '☀️ Light' : '🌙 Dark';
        }}

        Reveal.on('slidechanged', () => {{
            replaySlideAnimation();
        }});

        function checkQuizAnswer(btn, isCorrect, cardId) {{
            const card = document.getElementById(cardId);
            if (!card) return;
            const buttons = card.querySelectorAll('.quiz-btn');
            buttons.forEach(b => {{
                b.classList.remove('correct', 'wrong');
                if (b.getAttribute('data-correct') === 'true') {{
                    b.classList.add('correct');
                }}
            }});
            if (!isCorrect) {{
                btn.classList.add('wrong');
            }}
            const exp = document.getElementById(cardId + '_exp');
            if (exp) exp.style.display = 'block';
        }}

        function revealQuizCardAnswer(cardId) {{
            const card = document.getElementById(cardId);
            if (!card) return;
            const exp = document.getElementById(cardId + '_exp');
            const isHidden = !exp || exp.style.display === 'none';
            if (exp) exp.style.display = isHidden ? 'block' : 'none';
            const buttons = card.querySelectorAll('.quiz-btn');
            buttons.forEach(b => {{
                if (isHidden && b.getAttribute('data-correct') === 'true') {{
                    b.classList.add('correct');
                }} else if (!isHidden) {{
                    b.classList.remove('correct', 'wrong');
                }}
            }});
        }}

        let allAnswersVisible = false;
        function toggleAllQuizAnswers() {{
            allAnswersVisible = !allAnswersVisible;
            document.querySelectorAll('.quiz-card').forEach(card => {{
                const exp = card.querySelector('.quiz-explanation-box');
                if (exp) exp.style.display = allAnswersVisible ? 'block' : 'none';
                card.querySelectorAll('.quiz-btn').forEach(b => {{
                    if (allAnswersVisible && b.getAttribute('data-correct') === 'true') {{
                        b.classList.add('correct');
                    }} else if (!allAnswersVisible) {{
                        b.classList.remove('correct', 'wrong');
                    }}
                }});
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
            "animations_enabled": animations_enabled,
            "animation_style": norm_anim,
            "message": f"Successfully created animated interactive HTML presentation at '{output_path}'"
        }
    except Exception as e:
        logger.error("Error creating HTML presentation: %s", e)
        return {"status": "error", "error": str(e)}
