"""
Browser Agent Tools
Tools that wrap BrowserService for ReAct agents to call during analyze-and-fix workflows.
"""

import os
import base64
import logging
from typing import Dict, Any, Optional

from .config import SCREENSHOTS_DIR, VISION_MODEL

logger = logging.getLogger(__name__)


def browser_open_url(url: str) -> str:
    """
    Open a URL in headless Chromium browser and start capturing console/network errors.
    Also starts live screenshot streaming if an interactive session context is available.
    
    Args:
        url: The URL to open (e.g. http://localhost:5173, http://localhost:8080)
    
    Returns:
        Summary of page load result including console error count and network error count.
    """
    try:
        from .browser_service import get_browser_service
        browser = get_browser_service()
        
        result = browser.launch(url)
        if isinstance(result, str):
            return f"Error: Failed to open browser at {url}: {result}"
        if not isinstance(result, dict):
            result = {}
        
        if result.get("status") == "error":
            return f"Error: Failed to open browser at {url}: {result.get('error', 'Unknown error')}"
        
        # Start live streaming if interactive context is available
        from .session_context import current_agent_context
        ctx = current_agent_context.get()
        if ctx and "queue" in ctx and "loop" in ctx:
            browser.start_live_streaming(ctx["queue"], ctx["loop"], interval=0.5)
        
        summary = (
            f"Browser opened successfully.\n"
            f"- URL: {result.get('url', url)}\n"
            f"- Page Title: {result.get('title', 'N/A')}\n"
            f"- Console Errors: {result.get('console_errors', 0)}\n"
            f"- Console Warnings: {result.get('console_warnings', 0)}\n"
            f"- Network Errors: {result.get('network_errors', 0)}\n"
            f"- Page Crashes: {result.get('page_crashes', 0)}"
        )
        
        return summary
    except ImportError:
        return "Error: Playwright is not installed. Run: pip install playwright && playwright install chromium"
    except Exception as e:
        return f"Error opening browser: {str(e)}"


def browser_get_console_errors() -> str:
    """
    Get all captured console errors and warnings from the currently open browser session.
    
    Returns:
        Formatted report of all console errors, warnings, and uncaught exceptions.
    """
    try:
        from .browser_service import get_browser_service
        browser = get_browser_service()
        
        console_report = browser.get_console_errors()
        network_report = browser.get_network_errors()
        
        combined = f"{console_report}\n\n{network_report}"
        return combined
    except Exception as e:
        return f"Error getting console errors: {str(e)}"


def browser_take_screenshot(name: str = "screenshot", full_page: bool = False) -> str:
    """
    Take a screenshot of the current browser viewport and save it.
    Streams the screenshot to the frontend as a screenshot_taken event.
    
    Args:
        name: Name for the screenshot file (without extension)
        full_page: If True, captures the entire scrollable page
    
    Returns:
        Path to the saved screenshot file.
    """
    try:
        from .browser_service import get_browser_service
        browser = get_browser_service()
        
        # Sanitize name
        safe_name = "".join(c for c in name if c.isalnum() or c in ('_', '-')).strip() or "screenshot"
        output_path = os.path.join(SCREENSHOTS_DIR, f"{safe_name}.png")
        
        # Save screenshot
        browser.save_screenshot(output_path, full_page=full_page)
        
        # Stream screenshot event to frontend
        from .session_context import current_agent_context
        ctx = current_agent_context.get()
        if ctx and "queue" in ctx and "loop" in ctx:
            # Read the file and encode as base64 for the event
            with open(output_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
            
            ctx["loop"].call_soon_threadsafe(
                ctx["queue"].put_nowait,
                {
                    "type": "screenshot_taken",
                    "name": safe_name,
                    "path": f"_screenshots/{safe_name}.png",
                    "url": f"/api/screenshots/{safe_name}.png",
                    "image_base64": f"data:image/png;base64,{img_b64}",
                    "caption": f"Screenshot: {safe_name}",
                    "done": False
                }
            )
        
        return f"Screenshot saved: {output_path}\nAccessible at: /api/screenshots/{safe_name}.png"
    except Exception as e:
        return f"Error taking screenshot: {str(e)}"


def browser_vision_audit(prompt: str = "") -> str:
    """
    Take a screenshot of the current browser viewport and analyze it with the 
    Gemma4:26b vision model for UI quality, layout bugs, and styling issues.
    
    Args:
        prompt: Optional custom prompt for the vision model. If empty, uses default UI audit prompt.
    
    Returns:
        Vision model's structured UI audit report.
    """
    try:
        from .browser_service import get_browser_service
        from .vision_service import analyze_screenshot_bytes
        
        browser = get_browser_service()
        
        # Take screenshot as raw bytes
        screenshot_bytes = browser.take_screenshot(full_page=False)
        
        # Also save it for reference
        audit_path = os.path.join(SCREENSHOTS_DIR, "vision_audit.png")
        with open(audit_path, "wb") as f:
            f.write(screenshot_bytes)
        
        # Send to vision model
        vision_result = analyze_screenshot_bytes(
            image_bytes=screenshot_bytes,
            prompt=prompt if prompt else None,
            model_name=VISION_MODEL
        )
        
        # Stream the audit screenshot to frontend
        from .session_context import current_agent_context
        ctx = current_agent_context.get()
        if ctx and "queue" in ctx and "loop" in ctx:
            img_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            ctx["loop"].call_soon_threadsafe(
                ctx["queue"].put_nowait,
                {
                    "type": "screenshot_taken",
                    "name": "vision_audit",
                    "path": "_screenshots/vision_audit.png",
                    "url": "/api/screenshots/vision_audit.png",
                    "image_base64": f"data:image/png;base64,{img_b64}",
                    "caption": "Vision UI Audit Screenshot (analyzed by Gemma4:26b)",
                    "done": False
                }
            )
        
        if isinstance(vision_result, str):
            return f"### 👁️ Gemma4:26b Vision UI Audit\n\n{vision_result}"
        if not isinstance(vision_result, dict):
            vision_result = {}
            
        report = vision_result.get("report", "No vision report generated.")
        has_defects = vision_result.get("has_visual_defects", False)
        
        result = f"### 👁️ Gemma4:26b Vision UI Audit\n\n{report}"
        if has_defects:
            result += "\n\n⚠️ VISUAL DEFECTS DETECTED — Code fixes recommended."
        else:
            result += "\n\n✅ No critical visual defects detected."
        
        return result
    except Exception as e:
        return f"Error during vision audit: {str(e)}"


def browser_close() -> str:
    """
    Close the browser session and cleanup all resources.
    Stops live screenshot streaming.
    
    Returns:
        Confirmation message.
    """
    try:
        from .browser_service import close_browser_service
        close_browser_service()
        return "Browser session closed successfully."
    except Exception as e:
        return f"Error closing browser: {str(e)}"
