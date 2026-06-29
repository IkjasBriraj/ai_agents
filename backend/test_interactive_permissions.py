import os
os.environ["TESTING"] = "true"

import unittest
import json
import asyncio
import threading
import time
from fastapi.testclient import TestClient

from main import app
from agents.config_store import save_config, load_config, CONFIG_FILE_PATH
from agents.session_context import current_agent_context
from agents.tools import check_and_request_permission


class TestInteractivePermissions(unittest.TestCase):
    """Integration tests for the interactive path whitelisting permission request flow"""

    def setUp(self):
        self.client = TestClient(app)
        self.loop = asyncio.new_event_loop()
        
        # Start event loop in background thread
        self.loop_thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.loop_thread.start()
        
        # Backup the original config file if it exists
        self.config_existed = os.path.exists(CONFIG_FILE_PATH)
        self.original_config = None
        if self.config_existed:
            try:
                with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                    self.original_config = json.load(f)
            except Exception:
                pass
        
        # Reset allowed paths config
        save_config({
            "agent_tools": {},
            "allowed_paths": []
        })

    def tearDown(self):
        # Restore config
        if self.config_existed and self.original_config is not None:
            try:
                with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
                    json.dump(self.original_config, f, indent=2)
            except Exception:
                pass
        elif os.path.exists(CONFIG_FILE_PATH):
            try:
                os.remove(CONFIG_FILE_PATH)
            except Exception:
                pass
        
        # Stop and close loop
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.loop_thread.join(timeout=2.0)
        self.loop.close()

    def test_permission_grant_flow(self):
        """Verifies that an unsafe path blocks, triggers a queue request, and resumes when approved"""
        session_id = "test-session-123"
        target_path = os.path.abspath(r"D:\learning\code\external_test_folder\document.txt")
        
        # Setup mock queue and running loop
        loop = self.loop
        queue = asyncio.Queue()
        
        # We run the check in a separate thread since it blocks waiting for permission
        permission_result = {}
        
        def run_tool_thread():
            # In thread, we must set the context variable so the tool knows the session details
            token = current_agent_context.set({
                "session_id": session_id,
                "queue": queue,
                "loop": loop
            })
            try:
                granted = check_and_request_permission(target_path)
                permission_result["granted"] = granted
            except Exception as e:
                permission_result["error"] = str(e)
            finally:
                current_agent_context.reset(token)

        thread = threading.Thread(target=run_tool_thread)
        thread.start()
        
        # Give the thread a moment to start and block
        time.sleep(0.5)
        
        # Verify that a permission_request event was put in the queue
        self.assertFalse(queue.empty())
        event = queue.get_nowait()
        self.assertEqual(event["type"], "permission_request")
        self.assertEqual(event["path"], target_path)
        self.assertEqual(event["session_id"], session_id)
        
        # Submit approval through the FastAPI TestClient
        response = self.client.post("/api/multi-agent/permission/respond", json={
            "session_id": session_id,
            "path": target_path,
            "granted": True
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["granted"], True)
        
        # Wait for the thread to finish blocking
        thread.join(timeout=5.0)
        
        # Verify result was granted
        self.assertTrue(permission_result.get("granted"))
        
        # Verify path was persisted to configuration allowed_paths
        config = load_config()
        self.assertIn(target_path, config["allowed_paths"])

    def test_permission_deny_flow(self):
        """Verifies that an unsafe path blocks, triggers a queue request, and returns False when denied"""
        session_id = "test-session-456"
        target_path = os.path.abspath(r"D:\learning\code\another_folder\refused.txt")
        
        loop = self.loop
        queue = asyncio.Queue()
        
        permission_result = {}
        
        def run_tool_thread():
            token = current_agent_context.set({
                "session_id": session_id,
                "queue": queue,
                "loop": loop
            })
            try:
                granted = check_and_request_permission(target_path)
                permission_result["granted"] = granted
            except Exception as e:
                permission_result["error"] = str(e)
            finally:
                current_agent_context.reset(token)

        thread = threading.Thread(target=run_tool_thread)
        thread.start()
        
        time.sleep(0.5)
        
        # Submit denial through FastAPI TestClient
        response = self.client.post("/api/multi-agent/permission/respond", json={
            "session_id": session_id,
            "path": target_path,
            "granted": False
        })
        self.assertEqual(response.status_code, 200)
        
        thread.join(timeout=5.0)
        
        # Verify result was denied
        self.assertFalse(permission_result.get("granted"))
        
        # Verify path was NOT persisted to configuration
        config = load_config()
        self.assertNotIn(target_path, config["allowed_paths"])


if __name__ == "__main__":
    unittest.main()
