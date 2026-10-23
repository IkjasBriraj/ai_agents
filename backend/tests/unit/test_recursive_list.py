"""
Unit tests for recursive_list and grep_search tools
"""

import os
import sys
import asyncio
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from agents.tools import recursive_list, grep_search, file_operation, get_code_agent_tools, get_analysis_agent_tools
from agents.config import AGENT_WORKSPACE_DIR
from agents.specialized_agents import RobustReActParser, CodeAgent, ThreadSafeAgentCallbackHandler
from langchain_core.agents import AgentAction


class TestRecursiveListAndGrep(unittest.TestCase):
    def setUp(self):
        os.makedirs(AGENT_WORKSPACE_DIR, exist_ok=True)

    def test_recursive_list_string_path(self):
        result = recursive_list("")
        self.assertIsInstance(result, str)
        self.assertNotIn("Error in recursive_list", result)
        self.assertTrue("Found" in result or "empty" in result)

    def test_recursive_list_dict_input(self):
        result = recursive_list({"path": ""})
        self.assertIsInstance(result, str)
        self.assertNotIn("Error in recursive_list", result)
        self.assertTrue("Found" in result or "empty" in result)

    def test_recursive_list_nonexistent(self):
        result = recursive_list("nonexistent_directory_12345")
        self.assertIn("not found", result.lower())

    def test_grep_search_string_query(self):
        result = grep_search("html")
        self.assertIsInstance(result, str)
        self.assertNotIn("Error in grep_search", result)

    def test_grep_search_dict_input(self):
        result = grep_search({"query": "html", "path": ""})
        self.assertIsInstance(result, str)
        self.assertNotIn("Error in grep_search", result)

    def test_file_operation_recursive_list(self):
        result = file_operation("recursive_list", "")
        self.assertIsInstance(result, str)
        self.assertTrue("Found" in result or "empty" in result)

    def test_code_agent_has_tools(self):
        code_tools = [t.name for t in get_code_agent_tools()]
        self.assertIn("recursive_list", code_tools)
        self.assertIn("grep_search", code_tools)

        analysis_tools = [t.name for t in get_analysis_agent_tools()]
        self.assertIn("recursive_list", analysis_tools)
        self.assertIn("grep_search", analysis_tools)

    def test_code_agent_instance_tools(self):
        agent = CodeAgent()
        agent_tool_names = [t.name for t in agent.tools]
        self.assertIn("recursive_list", agent_tool_names)
        self.assertIn("grep_search", agent_tool_names)

    def test_parser_normalizes_recursive_list(self):
        parser = RobustReActParser()
        raw_text = 'Action: recursive_list\nAction Input: {"path": ""}'
        parsed = parser.parse(raw_text)
        self.assertIsInstance(parsed, AgentAction)
        self.assertEqual(parsed.tool, "recursive_list")
        self.assertEqual(parsed.tool_input, '{"path": ""}')

    def test_callback_handler_on_tool_error(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        queue = asyncio.Queue()
        handler = ThreadSafeAgentCallbackHandler(queue, loop, "code")
        handler.executed_actions.append("recursive_list")

        handler.on_tool_error(Exception("Simulated tool failure"))

        # Run loop briefly so call_soon_threadsafe callbacks are processed
        loop.run_until_complete(asyncio.sleep(0.05))

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        self.assertTrue(any(e.get("type") == "tool_end" for e in events))
        tool_end_event = next(e for e in events if e.get("type") == "tool_end")
        self.assertIn("Simulated tool failure", tool_end_event["output"])
        loop.close()


if __name__ == "__main__":
    unittest.main()
