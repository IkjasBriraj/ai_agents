"""
Verification tests for Agent Memory functionality.
Tests both Custom User Agents memory and Coordinated Multi-Agent memory.
"""

import sys
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from langchain_core.messages import HumanMessage, AIMessage

# Import memory components
from agents.memory import MultiAgentMemory, multi_agent_memory
from agents.orchestrator import OrchestratorAgent
from main import app, agents_db, agent_conversations, Agent


class TestMultiAgentMemoryUnit(unittest.TestCase):
    """Unit tests for the MultiAgentMemory store class"""

    def setUp(self):
        self.memory = MultiAgentMemory()

    def test_initial_state(self):
        messages = self.memory.get_messages("session_1")
        self.assertEqual(messages, [])

    def test_add_messages(self):
        self.memory.add_message("session_1", HumanMessage(content="Hello agent"))
        self.memory.add_message("session_1", AIMessage(content="Hello human"))
        
        messages = self.memory.get_messages("session_1")
        self.assertEqual(len(messages), 2)
        self.assertIsInstance(messages[0], HumanMessage)
        self.assertEqual(messages[0].content, "Hello agent")
        self.assertIsInstance(messages[1], AIMessage)
        self.assertEqual(messages[1].content, "Hello human")

    def test_format_history(self):
        self.memory.add_message("session_1", HumanMessage(content="Hello"))
        self.memory.add_message("session_1", AIMessage(content="Hi there"))
        
        formatted = self.memory.format_history("session_1")
        expected = "User: Hello\nAssistant: Hi there"
        self.assertEqual(formatted, expected)

    def test_clear_memory(self):
        self.memory.add_message("session_1", HumanMessage(content="Hello"))
        self.memory.clear("session_1")
        self.assertEqual(self.memory.get_messages("session_1"), [])


class TestCustomAgentMemoryAPI(unittest.TestCase):
    """Integration tests for custom agent memory using TestClient and mocks"""

    def setUp(self):
        self.client = TestClient(app)
        # Setup mock agent in database
        self.agent_id = "test-agent-123"
        agents_db[self.agent_id] = Agent(
            id=self.agent_id,
            name="Test memory Agent",
            persona="A helpful assistant",
            system_prompt="You are a helpful assistant.",
            tools=[],
            base_model="llama3",
            training_data=[]
        )
        if self.agent_id in agent_conversations:
            del agent_conversations[self.agent_id]

    def tearDown(self):
        if self.agent_id in agents_db:
            del agents_db[self.agent_id]
        if self.agent_id in agent_conversations:
            del agent_conversations[self.agent_id]

    @patch("main.OllamaService.chat_stream")
    def test_custom_agent_chat_accumulates_memory(self, mock_chat_stream):
        # First chat turn mock response
        async def mock_chat_generator_1(*args, **kwargs):
            yield {"message": {"content": "Hello. I am your assistant."}, "done": False}
            yield {"done": True}

        # Second chat turn mock response
        async def mock_chat_generator_2(*args, **kwargs):
            yield {"message": {"content": "You asked about memory."}, "done": False}
            yield {"done": True}

        # First turn
        mock_chat_stream.side_effect = mock_chat_generator_1
        response = self.client.post(f"/chat/{self.agent_id}?prompt=Hello")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["response"], "Hello. I am your assistant.")
        
        # Verify history holds first turn
        self.assertIn(self.agent_id, agent_conversations)
        history = agent_conversations[self.agent_id]
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].content, "Hello")
        self.assertEqual(history[1].content, "Hello. I am your assistant.")

        # Second turn
        mock_chat_stream.side_effect = mock_chat_generator_2
        response = self.client.post(f"/chat/{self.agent_id}?prompt=What did I say?")
        self.assertEqual(response.status_code, 200)
        
        # Check that chat_stream was called with history parameter containing first turn
        # Get last call arguments
        args, kwargs = mock_chat_stream.call_args
        passed_history = args[2] if len(args) > 2 else kwargs.get("history")
        self.assertIsNotNone(passed_history)
        self.assertEqual(len(passed_history), 2)
        self.assertEqual(passed_history[0].content, "Hello")
        self.assertEqual(passed_history[1].content, "Hello. I am your assistant.")

    def test_custom_agent_clear_memory(self):
        # Populate dummy conversation
        agent_conversations[self.agent_id] = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi")
        ]
        
        # Clear
        response = self.client.post(f"/chat/{self.agent_id}/clear")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(agent_conversations[self.agent_id], [])


class TestMultiAgentMemoryAPI(unittest.TestCase):
    """Integration tests for multi-agent coordinated memory using TestClient and mocks"""

    def setUp(self):
        self.client = TestClient(app)
        self.session_id = "test-session-456"
        multi_agent_memory.clear(self.session_id)

    def tearDown(self):
        multi_agent_memory.clear(self.session_id)

    @patch("agents.orchestrator.ChatOllama.invoke")
    def test_multi_agent_general_chat_adds_memory(self, mock_llm_invoke):
        # Mock LLM response indicating "general" agent selection
        mock_selection = MagicMock()
        mock_selection.content = "general"
        
        # Mock general agent response content
        mock_response = MagicMock()
        mock_response.content = "General memory response."
        
        mock_llm_invoke.side_effect = [mock_selection, mock_response]

        payload = {
            "prompt": "Hello senior multi-agent app",
            "session_id": self.session_id,
            "stream": False
        }
        
        # Send post request
        response = self.client.post("/api/multi-agent/agents/chat", json=payload)
        self.assertEqual(response.status_code, 200)
        
        # Check messages added to multi_agent_memory
        messages = multi_agent_memory.get_messages(self.session_id)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].content, "Hello senior multi-agent app")
        self.assertEqual(messages[1].content, "General memory response.")

    @patch("agents.orchestrator.create_specialized_agent")
    @patch("agents.orchestrator.ChatOllama.invoke")
    def test_multi_agent_routing_receives_history(self, mock_llm_invoke, mock_create_agent):
        # Inject history beforehand
        multi_agent_memory.add_message(self.session_id, HumanMessage(content="Help me code."))
        multi_agent_memory.add_message(self.session_id, AIMessage(content="Sure, what code?"))

        # Setup routing mock response
        mock_selection = MagicMock()
        mock_selection.content = "code"
        mock_llm_invoke.return_value = mock_selection

        # Setup specialized agent mock
        mock_agent = MagicMock()
        mock_agent.process.return_value = "Resulting python program."
        mock_create_agent.return_value = mock_agent

        payload = {
            "prompt": "Write the code now.",
            "session_id": self.session_id,
            "stream": False
        }

        response = self.client.post("/api/multi-agent/agents/chat", json=payload)
        self.assertEqual(response.status_code, 200)

        # Verify orchestrator prompt for routing included history
        called_messages = mock_llm_invoke.call_args[0][0]
        system_msg = called_messages[0]
        self.assertIn("Conversation History:", system_msg.content)
        self.assertIn("Help me code.", system_msg.content)
        self.assertIn("Sure, what code?", system_msg.content)

        # Verify specialized agent process received history
        mock_agent.process.assert_called_once()
        passed_history = mock_agent.process.call_args[1].get("chat_history")
        self.assertEqual(len(passed_history), 2)
        self.assertEqual(passed_history[0].content, "Help me code.")
        self.assertEqual(passed_history[1].content, "Sure, what code?")

    def test_multi_agent_clear_memory(self):
        # Populate history
        multi_agent_memory.add_message(self.session_id, HumanMessage(content="Hi"))
        multi_agent_memory.add_message(self.session_id, AIMessage(content="Hello"))

        # Clear
        response = self.client.post(f"/api/multi-agent/agents/clear?session_id={self.session_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(multi_agent_memory.get_messages(self.session_id), [])


if __name__ == "__main__":
    unittest.main()
