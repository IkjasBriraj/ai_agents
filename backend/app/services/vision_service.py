"""
Vision Service for Multimodal Model Analysis (Gemma4:26b / Ollama Vision)
Analyzes app UI screenshots for visual bugs, alignment issues, poor styling, and render errors.
"""

import os
import base64
import logging
import httpx
from typing import Optional, Dict, Any, Union

logger = logging.getLogger(__name__)

DEFAULT_VISION_MODEL = os.environ.get("VISION_MODEL", "gemma4:26b")
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

def encode_image_to_base64(image_input: Union[str, bytes]) -> Optional[str]:
    """Convert an image file path or raw bytes to a base64 encoded string."""
    try:
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                logger.error("Image file not found: %s", image_input)
                return None
            with open(image_input, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        elif isinstance(image_input, bytes):
            return base64.b64encode(image_input).decode("utf-8")
    except Exception as e:
        logger.error("Error encoding image to base64: %s", e)
        return None
    return None

DEFAULT_UI_AUDIT_PROMPT = """You are a Senior UI/UX & Quality Assurance Vision Inspector.
Analyze this web application UI screenshot in detail and evaluate:

1. **Visual Errors & Broken Layouts**: Are there misaligned elements, overlapping text, cut-off buttons, or unrendered components?
2. **Error Badges / Popups**: Are there visible error messages, 404 badges, or red console alerts?
3. **Styling & Aesthetics**: Is the color palette readable and high-contrast? Is spacing/padding consistent? Does it feel premium?
4. **Actionable Code Fix Instructions**: If there are visual or styling flaws, state EXACTLY what CSS/HTML/React layout changes the Code Agent should make to fix them.

Format your response clearly with:
- **VISUAL AUDIT SCORE**: (1 to 10)
- **VISUAL DEFECTS FOUND**: (List defects or "None")
- **CODE/CSS FIX INSTRUCTIONS**: (Actionable steps for Code Agent)"""

def analyze_ui_screenshot_with_vision(
    image_input: Union[str, bytes],
    prompt: Optional[str] = None,
    model_name: str = DEFAULT_VISION_MODEL,
    ollama_base_url: str = DEFAULT_OLLAMA_URL
) -> Dict[str, Any]:
    """
    Send a UI screenshot to the Vision-capable model (e.g. gemma4:26b) via Ollama API.
    Audits visual aesthetics, layout bugs, console error popups, color contrast, and styling defects.
    """
    base64_img = encode_image_to_base64(image_input)
    if not base64_img:
        return {
            "status": "error",
            "error": "Failed to encode screenshot image.",
            "report": "⚠️ Could not encode screenshot for vision analysis."
        }

    final_prompt = prompt or DEFAULT_UI_AUDIT_PROMPT

    url = f"{ollama_base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": final_prompt,
                "images": [base64_img]
            }
        ],
        "stream": False
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                msg = data.get("message") if isinstance(data, dict) else {}
                content = msg.get("content", "") if isinstance(msg, dict) else str(msg or "")
                return {
                    "status": "success",
                    "model": model_name,
                    "report": content,
                    "has_visual_defects": "DEFECTS FOUND" in content.upper() and "NONE" not in content.upper().split("DEFECTS FOUND")[1][:30] if "DEFECTS FOUND" in content.upper() else False
                }
            else:
                logger.warning("Ollama Vision API returned HTTP %d: %s", response.status_code, response.text)
                # Fallback check if model lacks vision or model name differs
                return {
                    "status": "error",
                    "error": f"Ollama API HTTP {response.status_code}: {response.text}",
                    "report": f"⚠️ Vision analysis returned status {response.status_code}. (Model: {model_name})"
                }
    except Exception as e:
        logger.error("Vision service exception: %s", e)
        return {
            "status": "error",
            "error": str(e),
            "report": f"⚠️ Vision service error: {str(e)}"
        }


def analyze_screenshot_bytes(
    image_bytes: bytes,
    prompt: Optional[str] = None,
    model_name: str = DEFAULT_VISION_MODEL,
    ollama_base_url: str = DEFAULT_OLLAMA_URL
) -> Dict[str, Any]:
    """
    Convenience function: analyze raw screenshot bytes (e.g. from Playwright) 
    directly with the vision model. No file I/O needed.
    """
    return analyze_ui_screenshot_with_vision(
        image_input=image_bytes,
        prompt=prompt,
        model_name=model_name,
        ollama_base_url=ollama_base_url
    )
