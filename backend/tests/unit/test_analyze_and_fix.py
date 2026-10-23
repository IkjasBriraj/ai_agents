import os
import json
import pytest
from unittest.mock import MagicMock, patch
from agents.tools import get_analysis_agent_tools
from agents.specialized_agents import AnalysisAgent
from agents.orchestrator import OrchestratorAgent

def test_analysis_agent_tools_expanded():
    tools = get_analysis_agent_tools()
    tool_names = [t.name for t in tools]
    assert "search_symbols" in tool_names
    assert "get_file_outline" in tool_names
    assert "query_codebase" in tool_names
    assert "edit_file" in tool_names
    assert "batch_verify_and_repair_files" in tool_names

def test_analysis_agent_config_permissions():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "agents", "agents_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    analysis_tools = cfg["agent_tools"]["analysis"]
    for expected in ["search_symbols", "get_file_outline", "query_codebase", "edit_file", "batch_verify_and_repair_files"]:
        assert expected in analysis_tools

def test_analysis_agent_prompt_has_architect_rules():
    agent = AnalysisAgent()
    prompt = agent.system_prompt
    assert "Lead Codebase Architect" in prompt
    assert "ROOT CAUSE" in prompt
    assert "CROSS-FILE IMPACT" in prompt
    assert "DISCOVER" in prompt

@patch("agents.orchestrator.create_specialized_agent")
def test_analyze_and_fix_generates_walkthrough_and_file(mock_create_agent, tmp_path):
    mock_analysis = MagicMock()
    mock_analysis.process.return_value = {
        "result": "ROOT CAUSE ANALYSIS:\nThe function calculate_tax had an off-by-one index error.\n\nAFFECTED FILES:\n- src/tax.py\n\nSURGICAL FIX SPECIFICATIONS:\nUpdate index logic."
    }
    mock_code = MagicMock()
    mock_code.process.return_value = {
        "result": "Successfully updated tax calculation logic in src/tax.py"
    }

    def agent_factory(agent_type, *args, **kwargs):
        if agent_type == "analysis":
            return mock_analysis
        elif agent_type == "code":
            return mock_code
        return MagicMock()

    mock_create_agent.side_effect = agent_factory

    orch = OrchestratorAgent()
    with patch("agents.config.AGENT_WORKSPACE_DIR", str(tmp_path)):
        result = orch._analyze_and_fix(
            user_request="fix off-by-one bug in src/tax.py",
            context={"thinking_level": "high"}
        )

        assert "# 🔍 Codebase Diagnostics & Fix Walkthrough" in result
        assert "## 📌 Executive Summary" in result
        assert "## 🔎 Root Cause Analysis" in result
        assert "off-by-one index error" in result
        assert "## 📂 Files Analyzed vs. Modified" in result
        assert "## 🛠️ Step-by-Step Changes Walkthrough" in result
        assert "## 🧪 Verification & Quality Checks" in result
        assert "## 🚀 How to Test & Next Steps" in result

        walkthrough_file = tmp_path / "WALKTHROUGH.md"
        assert walkthrough_file.exists()
        saved_content = walkthrough_file.read_text(encoding="utf-8")
        assert saved_content == result
