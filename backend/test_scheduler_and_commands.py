import os
os.environ["TESTING"] = "true"

import unittest
import json
import asyncio
import threading
import time
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from main import app
from database.db import SessionLocal
from database.models import ScheduledTaskModel
from agents.config_store import save_config, load_config, CONFIG_FILE_PATH
from agents.session_context import current_agent_context
from agents.tools import execute_terminal_command, schedule_agent_task


class TestSchedulerAndCommands(unittest.TestCase):
    """Integration and unit tests for the background scheduler and interactive command execution"""

    def setUp(self):
        self.client = TestClient(app)
        self.loop = asyncio.new_event_loop()
        
        # Start event loop in background thread
        self.loop_thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.loop_thread.start()
        
        # Backup config
        self.config_existed = os.path.exists(CONFIG_FILE_PATH)
        self.original_config = None
        if self.config_existed:
            try:
                with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                    self.original_config = json.load(f)
            except Exception:
                pass
        
        # Reset config with empty allowed lists
        save_config({
            "agent_tools": {
                "code": ["execute_code", "generate_code", "file_operation", "create_project", "analyze_code", "execute_terminal", "schedule_task"]
            },
            "allowed_paths": [],
            "allowed_commands": []
        })

        # Clear database scheduled tasks
        self.session = SessionLocal()
        self.session.query(ScheduledTaskModel).delete()
        self.session.commit()

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
        
        # Clear db
        self.session.query(ScheduledTaskModel).delete()
        self.session.commit()
        self.session.close()

        # Stop loop
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.loop_thread.join(timeout=2.0)
        self.loop.close()

    def test_create_and_get_scheduled_tasks(self):
        """Verifies ScheduledTask CRUD endpoints"""
        # Create a task
        payload = {
            "name": "Test Loop Task",
            "prompt": "Check something every 5 minutes",
            "interval_minutes": 5,
            "delay_minutes": 2
        }
        
        response = self.client.post("/api/multi-agent/scheduler/tasks", json=payload)
        self.assertEqual(response.status_code, 200)
        resp_data = response.json()
        self.assertEqual(resp_data["status"], "success")
        self.assertEqual(resp_data["task"]["name"], payload["name"])
        self.assertEqual(resp_data["task"]["interval_minutes"], payload["interval_minutes"])
        
        task_id = resp_data["task"]["id"]
        
        # Get tasks list
        response = self.client.get("/api/multi-agent/scheduler/tasks")
        self.assertEqual(response.status_code, 200)
        tasks = response.json()["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["id"], task_id)
        self.assertEqual(tasks[0]["status"], "active")

        # Toggle task (active -> paused)
        response = self.client.post(f"/api/multi-agent/scheduler/tasks/{task_id}/toggle")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["new_status"], "paused")

        # Toggle task (paused -> active)
        response = self.client.post(f"/api/multi-agent/scheduler/tasks/{task_id}/toggle")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["new_status"], "active")

        # Trigger immediate run (sets run_at to now)
        response = self.client.post(f"/api/multi-agent/scheduler/tasks/{task_id}/run")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

        # Delete task
        response = self.client.delete(f"/api/multi-agent/scheduler/tasks/{task_id}")
        self.assertEqual(response.status_code, 200)
        
        # Verify empty
        response = self.client.get("/api/multi-agent/scheduler/tasks")
        self.assertEqual(len(response.json()["tasks"]), 0)

    def test_command_permission_grant_flow(self):
        """Verifies execute_terminal_command prompts for approval when not whitelisted, and runs on approval"""
        session_id = "test-terminal-session"
        test_command = "echo hello_world_test"
        
        loop = self.loop
        queue = asyncio.Queue()
        execution_result = {}
        
        def run_command_thread():
            token = current_agent_context.set({
                "session_id": session_id,
                "queue": queue,
                "loop": loop
            })
            try:
                # This should request permission and wait
                output = execute_terminal_command(test_command)
                execution_result["output"] = output
            except Exception as e:
                execution_result["error"] = str(e)
            finally:
                current_agent_context.reset(token)

        thread = threading.Thread(target=run_command_thread)
        thread.start()
        
        # Wait for request to hit the queue
        time.sleep(0.5)
        
        self.assertFalse(queue.empty())
        event = queue.get_nowait()
        self.assertEqual(event["type"], "permission_request")
        self.assertEqual(event["permission_type"], "command")
        self.assertEqual(event["command"], test_command)
        
        # Approve the command via API
        response = self.client.post("/api/multi-agent/permission/command/respond", json={
            "session_id": session_id,
            "command": test_command,
            "granted": True
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["resolved"])
        self.assertTrue(response.json()["granted"])
        
        # Wait for execution thread to finish
        thread.join(timeout=5.0)
        
        # Verify it ran successfully and returned output
        self.assertIn("output", execution_result)
        self.assertIn("hello_world_test", execution_result["output"])
        
        # Verify it was added to allowed commands
        config = load_config()
        self.assertIn(test_command, config.get("allowed_commands", []))

    def test_unrestricted_command_execution(self):
        """Verifies execute_terminal_command runs directly without asking when context is unrestricted (scheduled)"""
        test_command = "echo unrestricted_output_test"
        
        # Run with unrestricted context
        token = current_agent_context.set({
            "scheduled": True,
            "unrestricted": True
        })
        try:
            output = execute_terminal_command(test_command)
            self.assertIn("unrestricted_output_test", output)
        finally:
            current_agent_context.reset(token)


if __name__ == '__main__':
    unittest.main()
