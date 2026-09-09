"""
Browser Automation Service using Playwright
Provides headless Chromium browser control for the Analyze & Fix Agent.
Captures console errors, network failures, takes screenshots, and streams live browser view.
"""

import os
import time
import base64
import asyncio
import logging
import threading
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class BrowserService:
    """
    Headless Chromium browser automation via Playwright.
    Captures JS console errors, network failures, takes screenshots,
    and optionally streams live browser screenshots to the frontend.
    """

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._page = None
        self._console_logs: List[Dict[str, Any]] = []
        self._page_errors: List[str] = []
        self._network_errors: List[Dict[str, Any]] = []
        self._current_url: str = ""
        self._live_streaming = False
        self._queue = None
        self._loop = None
        self._lock = threading.Lock()

    def launch(self, url: str, wait_time: float = 1.5) -> Dict[str, Any]:
        """
        Launch headless Chromium, navigate to URL, and start capturing console/network errors.
        
        Args:
            url: The URL to navigate to
            wait_time: Seconds to wait after page load for async JS to settle
            
        Returns:
            Dict with page title, console error count, network error count
        """
        try:
            from playwright.sync_api import sync_playwright

            # Clear previous session data
            self._console_logs = []
            self._page_errors = []
            self._network_errors = []

            if self._playwright is None:
                self._playwright = sync_playwright().start()
                self._browser = self._playwright.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
                )
                self._page = self._browser.new_page(viewport={"width": 1280, "height": 720})

                # Attach console listener
                self._page.on("console", self._on_console_message)
                
                # Attach page error listener (uncaught exceptions)
                self._page.on("pageerror", self._on_page_error)
                
                # Attach network error listeners
                self._page.on("response", self._on_response)
                self._page.on("requestfailed", self._on_request_failed)

            # Navigate using domcontentloaded with a resilient 10s timeout to prevent hanging on CDNs
            try:
                self._page.goto(url, wait_until="domcontentloaded", timeout=10000)
            except Exception as nav_err:
                logger.warning("Browser navigation warning for %s: %s", url, nav_err)

            self._current_url = url

            # Wait briefly for rendering to settle
            if wait_time > 0:
                time.sleep(wait_time)

            title = ""
            try:
                title = self._page.title()
            except Exception:
                pass

            # Push live viewport frame to frontend if streaming is active
            self.emit_live_frame()

            return {
                "status": "success",
                "url": url,
                "title": title,
                "console_errors": len([l for l in self._console_logs if l["type"] == "error"]),
                "console_warnings": len([l for l in self._console_logs if l["type"] == "warning"]),
                "network_errors": len(self._network_errors),
                "page_crashes": len(self._page_errors)
            }
        except Exception as e:
            logger.error("BrowserService.launch failed: %s", e)
            return {
                "status": "error",
                "error": str(e),
                "url": url
            }

    def _on_console_message(self, msg):
        """Capture browser console messages"""
        try:
            location = msg.location if hasattr(msg, 'location') and msg.location else {}
            self._console_logs.append({
                "type": msg.type,
                "text": msg.text,
                "url": location.get("url", "") if isinstance(location, dict) else "",
                "line": location.get("lineNumber", 0) if isinstance(location, dict) else 0,
                "column": location.get("columnNumber", 0) if isinstance(location, dict) else 0
            })
        except Exception as e:
            logger.debug("Error capturing console message: %s", e)

    def _on_page_error(self, error):
        """Capture uncaught page errors / exceptions"""
        self._page_errors.append(str(error))

    def _on_response(self, response):
        """Capture HTTP responses with error status codes"""
        try:
            if response.status >= 400:
                self._network_errors.append({
                    "type": "http_error",
                    "status": response.status,
                    "url": response.url,
                    "status_text": response.status_text if hasattr(response, 'status_text') else ""
                })
        except Exception:
            pass

    def _on_request_failed(self, request):
        """Capture completely failed network requests"""
        try:
            self._network_errors.append({
                "type": "request_failed",
                "url": request.url,
                "failure": request.failure if hasattr(request, 'failure') else "Unknown failure",
                "resource_type": request.resource_type if hasattr(request, 'resource_type') else ""
            })
        except Exception:
            pass

    def get_console_errors(self) -> str:
        """Get all captured console errors/warnings as a formatted report string."""
        errors = [l for l in self._console_logs if l["type"] in ("error", "warning")]
        crashes = self._page_errors

        if not errors and not crashes:
            return "No console errors or warnings detected. Browser console is clean."

        lines = [f"### Browser Console Errors Report ({len(errors)} errors, {len(crashes)} crashes)"]
        
        for i, err in enumerate(errors, 1):
            err_type = "❌ ERROR" if err["type"] == "error" else "⚠️ WARNING"
            location = f" (at {err['url']}:{err['line']})" if err.get("url") else ""
            lines.append(f"{i}. [{err_type}] {err['text']}{location}")

        for i, crash in enumerate(crashes, 1):
            lines.append(f"💥 UNCAUGHT EXCEPTION #{i}: {crash}")

        return "\n".join(lines)

    def get_network_errors(self) -> str:
        """Get all captured network errors as a formatted report string."""
        if not self._network_errors:
            return "No network errors detected. All resources loaded successfully."

        lines = [f"### Network Errors Report ({len(self._network_errors)} failures)"]
        
        for i, err in enumerate(self._network_errors, 1):
            if err["type"] == "http_error":
                lines.append(f"{i}. [HTTP {err['status']}] {err['url']}")
            else:
                lines.append(f"{i}. [REQUEST FAILED] {err['url']} — {err.get('failure', 'Unknown')}")

        return "\n".join(lines)

    def take_screenshot(self, full_page: bool = False) -> bytes:
        """Take a PNG screenshot of the current browser viewport."""
        if not self._page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        with self._lock:
            return self._page.screenshot(full_page=full_page, type="png")

    def save_screenshot(self, output_path: str, full_page: bool = False) -> str:
        """Take a screenshot, save it to disk, and broadcast live view. Returns the saved file path."""
        screenshot_bytes = self.take_screenshot(full_page=full_page)
        dir_path = os.path.dirname(output_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(screenshot_bytes)
        self.emit_live_frame()
        return output_path

    def get_page_title(self) -> str:
        """Get the current page title."""
        if not self._page:
            return ""
        try:
            with self._lock:
                return self._page.title()
        except Exception:
            return ""

    def get_current_url(self) -> str:
        """Get the current page URL."""
        return self._current_url

    def emit_live_frame(self):
        """
        Safely capture the current browser viewport and push to the frontend SSE queue.
        Called on the main Playwright thread to strictly avoid cross-thread greenlet deadlocks.
        """
        if not self._live_streaming or not self._page or not self._queue or not self._loop:
            return
        try:
            with self._lock:
                screenshot_bytes = self._page.screenshot(type="png")
            b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            self._loop.call_soon_threadsafe(
                self._queue.put_nowait,
                {
                    "type": "browser_live",
                    "image_base64": f"data:image/png;base64,{b64}",
                    "url": self._current_url,
                    "done": False
                }
            )
        except Exception as e:
            logger.debug("emit_live_frame error: %s", e)

    def start_live_streaming(self, queue, loop, interval: float = 0.5):
        """
        Start live streaming browser screenshots to the frontend via SSE queue.
        Screenshots are broadcast synchronously on the Playwright thread during events and actions.
        """
        self._live_streaming = True
        self._queue = queue
        self._loop = loop
        # Immediately emit the initial viewport state
        self.emit_live_frame()

    def stop_live_streaming(self):
        """Stop the live screenshot streaming and signal completion."""
        if self._live_streaming and self._queue and self._loop:
            try:
                self._loop.call_soon_threadsafe(
                    self._queue.put_nowait,
                    {
                        "type": "browser_live",
                        "image_base64": "",
                        "url": self._current_url,
                        "done": True
                    }
                )
            except Exception:
                pass
        self._live_streaming = False
        self._queue = None
        self._loop = None

    def reload_page(self):
        """Reload the current page with resilient domcontentloaded timeout."""
        if self._page:
            # Clear previous errors before reload
            self._console_logs = []
            self._page_errors = []
            self._network_errors = []
            try:
                self._page.reload(wait_until="domcontentloaded", timeout=10000)
            except Exception as e:
                logger.warning("Browser reload warning: %s", e)
            time.sleep(1.0)
            self.emit_live_frame()

    def close(self):
        """Close browser and cleanup all resources."""
        self.stop_live_streaming()
        try:
            if self._page:
                self._page.close()
                self._page = None
        except Exception:
            pass
        try:
            if self._browser:
                self._browser.close()
                self._browser = None
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
        except Exception:
            pass

    def __del__(self):
        self.close()


# Singleton instance for the current session
_active_browser: Optional[BrowserService] = None


def get_browser_service() -> BrowserService:
    """Get or create the active browser service singleton."""
    global _active_browser
    if _active_browser is None:
        _active_browser = BrowserService()
    return _active_browser


def close_browser_service():
    """Close and reset the active browser service singleton."""
    global _active_browser
    if _active_browser is not None:
        _active_browser.close()
        _active_browser = None
