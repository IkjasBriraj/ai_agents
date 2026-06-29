import unittest
import os
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from agents.config import is_safe_path, AGENT_WORKSPACE_DIR
from agents.config_store import save_config, load_config, CONFIG_FILE_PATH
from agents.tools import get_tools_for_agent


class TestAgentSecurityAndConfig(unittest.TestCase):
    """Unit and integration tests for path whitelisting and tool filtering"""

    def setUp(self):
        self.client = TestClient(app)
        # Backup the original config file if it exists
        self.config_existed = os.path.exists(CONFIG_FILE_PATH)
        self.original_config = None
        if self.config_existed:
            try:
                with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                    self.original_config = json.load(f)
            except Exception:
                pass
        
        # Reset global config store cache
        from agents import config_store
        config_store._current_config = None

    def tearDown(self):
        # Restore the original config
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
                
        # Reset global config store cache
        from agents import config_store
        config_store._current_config = None

    def test_default_workspace_fallback_is_safe(self):
        """When whitelist is empty, only workspace directory is safe"""
        # Set empty whitelist
        save_config({
            "agent_tools": {},
            "allowed_paths": []
        })
        
        # Inside workspace should be safe
        safe_file = os.path.join(AGENT_WORKSPACE_DIR, "test.py")
        self.assertTrue(is_safe_path(safe_file))
        
        # Outside workspace should NOT be safe
        unsafe_file = r"C:\Windows\System32\cmd.exe"
        self.assertFalse(is_safe_path(unsafe_file))
        
        # Another user directory should NOT be safe
        self.assertFalse(is_safe_path(r"C:\Users\ADMIN\Desktop\unauthorized.txt"))

    def test_custom_whitelist_path_restrictions(self):
        """When whitelist is set, only whitelisted paths are safe, others blocked"""
        whitelisted_dir = r"C:\Users\ADMIN\.gemini\antigravity\scratch\allowed_dir"
        whitelisted_file = r"C:\Users\ADMIN\.gemini\antigravity\scratch\allowed_file.py"
        
        save_config({
            "agent_tools": {},
            "allowed_paths": [whitelisted_dir, whitelisted_file]
        })
        
        # Whitelisted file should be safe
        self.assertTrue(is_safe_path(whitelisted_file))
        
        # File inside whitelisted directory should be safe
        inner_file = os.path.join(whitelisted_dir, "app.py")
        self.assertTrue(is_safe_path(inner_file))
        
        # Un-whitelisted file outside should NOT be safe, even if it's in default workspace!
        default_workspace_file = os.path.join(AGENT_WORKSPACE_DIR, "test.py")
        self.assertFalse(is_safe_path(default_workspace_file))

    def test_tool_toggle_filtering(self):
        """Disabled tools should be filtered out by get_tools_for_agent"""
        # Enable only file_operation for code agent
        save_config({
            "agent_tools": {
                "code": ["file_operation"]
            },
            "allowed_paths": []
        })
        
        code_tools = get_tools_for_agent("code")
        tool_names = [t.name for t in code_tools]
        
        self.assertIn("file_operation", tool_names)
        self.assertNotIn("execute_code", tool_names)
        self.assertNotIn("generate_code", tool_names)

    def test_config_api_endpoints(self):
        """Verify endpoints to get and update config"""
        # GET config
        response = self.client.get("/api/multi-agent/config")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("config", data)
        self.assertIn("all_tools", data)
        
        # POST config
        test_config = {
            "agent_tools": {
                "code": ["file_operation", "execute_code"],
                "research": ["web_search"],
                "analysis": []
            },
            "allowed_paths": [r"C:\Users\ADMIN\.gemini\antigravity\scratch\api_test"]
        }
        
        post_response = self.client.post("/api/multi-agent/config", json=test_config)
        self.assertEqual(post_response.status_code, 200)
        post_data = post_response.json()
        self.assertEqual(post_data["status"], "success")
        
        # Fetch config again to confirm updates persisted
        get_response = self.client.get("/api/multi-agent/config")
        get_data = get_response.json()["config"]
        
        self.assertEqual(get_data["agent_tools"]["code"], ["file_operation", "execute_code"])
        self.assertEqual(get_data["agent_tools"]["research"], ["web_search"])
        self.assertEqual(get_data["agent_tools"]["analysis"], [])
        # The store returns absolute normalized paths
        normalized_expected = [os.path.abspath(r"C:\Users\ADMIN\.gemini\antigravity\scratch\api_test")]
        self.assertEqual(get_data["allowed_paths"], normalized_expected)


if __name__ == "__main__":
    unittest.main()
