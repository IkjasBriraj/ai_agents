import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from agents.tool_calling_loop import ToolCallingLoop

class TestToolCallingLoop(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MagicMock()
        self.mock_llm.bind_tools.return_value = self.mock_llm
        
        self.mock_tool = MagicMock()
        self.mock_tool.name = "mock_tool"
        self.mock_tool.invoke.return_value = "Tool result"
        
        self.loop = ToolCallingLoop(
            llm=self.mock_llm,
            tools=[self.mock_tool],
            system_prompt="System Prompt",
            max_steps=5
        )

    def test_state_initialization(self):
        self.assertTrue(self.loop.supports_native_tools())
        self.assertEqual(len(self.loop.tool_map), 1)
        self.assertIn("mock_tool", self.loop.tool_map)
        
    def test_should_continue_end_final_response(self):
        state = {"final_response": "Done"}
        self.assertEqual(self.loop._should_continue(state), "end")
        
    def test_should_continue_max_steps(self):
        state = {"step_count": 5, "max_steps": 5}
        self.assertEqual(self.loop._should_continue(state), "end")
        
    def test_should_continue_execute_tools(self):
        msg = AIMessage(content="", tool_calls=[{"name": "mock_tool", "args": {}, "id": "123"}])
        state = {"messages": [msg], "step_count": 1}
        self.assertEqual(self.loop._should_continue(state), "execute_tools")
        
    def test_should_continue_no_tools(self):
        msg = AIMessage(content="Hello")
        state = {"messages": [msg], "step_count": 1}
        self.assertEqual(self.loop._should_continue(state), "end")
        
    def test_duplicate_tool_call_detection(self):
        tool_call = [{"name": "mock_tool", "args": {"a": 1}, "id": "1"}]
        msg = AIMessage(content="", tool_calls=tool_call)
        
        state = {
            "messages": [msg, msg, msg],
            "step_count": 3,
            "max_steps": 10
        }
        self.assertEqual(self.loop._should_continue(state), "end")
        
    def test_invoke_llm_max_steps(self):
        state = {"step_count": 5, "max_steps": 5}
        result = self.loop._invoke_llm(state)
        self.assertIn("final_response", result)
        self.assertEqual(result["final_response"], "Max steps exceeded. Forcing exit.")
        
    def test_execute_tools_success(self):
        msg = AIMessage(content="", tool_calls=[{"name": "mock_tool", "args": {}, "id": "123"}])
        state = {"messages": [msg], "tools_executed": []}
        
        result = self.loop._execute_tools(state)
        self.assertIn("messages", result)
        self.assertEqual(len(result["messages"]), 1)
        self.assertIsInstance(result["messages"][0], ToolMessage)
        self.assertEqual(result["messages"][0].content, "Tool result")
        self.assertIn("mock_tool", result["tools_executed"])
        
    def test_execute_tools_failure(self):
        self.mock_tool.invoke.side_effect = Exception("Tool failed")
        
        msg = AIMessage(content="", tool_calls=[{"name": "mock_tool", "args": {}, "id": "123"}])
        state = {"messages": [msg], "tools_executed": []}
        
        result = self.loop._execute_tools(state)
        self.assertIn("messages", result)
        self.assertEqual(len(result["messages"]), 1)
        self.assertIsInstance(result["messages"][0], ToolMessage)
        self.assertIn("Error executing tool mock_tool: Tool failed", result["messages"][0].content)

if __name__ == "__main__":
    unittest.main()
