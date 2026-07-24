"""
Unit tests for Business Agent and CSV Sheet Operation tool
"""

import os
import pytest
from agents.specialized_agents import BusinessAgent, SPECIALIZED_AGENTS, create_specialized_agent
from agents.tools import csv_sheet_operation, get_business_agent_tools, get_tools_by_names, AGENT_TOOLS
from agents.orchestrator import OrchestratorAgent
from agents.config import get_workspace_path, ALLOWED_EXTENSIONS


def test_specialized_agents_registry():
    assert "business" in SPECIALIZED_AGENTS
    assert SPECIALIZED_AGENTS["business"] == BusinessAgent


def test_business_agent_instantiation():
    agent = create_specialized_agent("business")
    assert agent is not None
    assert isinstance(agent, BusinessAgent)
    assert agent.name == "Business Agent"
    assert agent.agent_type == "business"
    tool_names = [t.name for t in agent.tools]
    assert "csv_sheet_operation" in tool_names
    assert "file_operation" in tool_names


def test_csv_allowed_extension():
    assert ".csv" in ALLOWED_EXTENSIONS


def test_csv_sheet_operation_write_read_append():
    rel_path = "unit_test_financials.csv"
    abs_path = get_workspace_path(rel_path)

    # Ensure clean starting state
    if os.path.exists(abs_path):
        os.remove(abs_path)

    try:
        # Write
        data_write = [
            ["Metric", "2025", "2026"],
            ["ARR", "$1,000,000", "$2,500,000"],
            ["Margin", "70%", "78%"]
        ]
        write_res = csv_sheet_operation("write", rel_path, data_write)
        assert "[SUCCESS]" in write_res
        assert os.path.exists(abs_path)

        # Append
        data_append = [
            ["EBITDA", "$200,000", "$600,000"]
        ]
        append_res = csv_sheet_operation("append", rel_path, data_append)
        assert "[SUCCESS]" in append_res

        # Read
        read_res = csv_sheet_operation("read", rel_path)
        assert "unit_test_financials.csv" in read_res
        assert "Metric" in read_res
        assert "ARR" in read_res
        assert "EBITDA" in read_res

    finally:
        if os.path.exists(abs_path):
            os.remove(abs_path)


def test_csv_sheet_operation_invalid():
    res = csv_sheet_operation("invalid_op", "test.csv")
    assert "Error: Unknown operation" in res


def test_get_tools_by_names():
    tools = get_tools_by_names(["csv_sheet_operation"])
    assert len(tools) == 1
    assert tools[0].name == "csv_sheet_operation"


def test_orchestrator_routing_business():
    orchestrator = OrchestratorAgent()
    state = {
        "user_request": "Create a 2026 financial forecast spreadsheet in CSV format",
        "messages": [],
        "session_id": "test_session"
    }
    res_state = orchestrator._analyze_request(state)
    assert res_state["selected_agent"] == "business"
