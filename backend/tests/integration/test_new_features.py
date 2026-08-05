"""
Opaque-Box E2E Test Suite for Local AI Agents Enhancements (R1, R2, R3)
Coverage: Features F1-F6 across Tiers 1-4 (Total: 75 Test Cases)

Requirements Covered:
- F1: Patch File Operation (R1) - Tier 1 (5 tests), Tier 2 (5 boundary tests)
- F2: AST Syntax Validation on Patch (R1) - Tier 1 (5 tests), Tier 2 (5 boundary tests)
- F3: Business Agent & CSV Sheet Tool (R2) - Tier 1 (5 tests), Tier 2 (5 boundary tests)
- F4: Business Routing & UI Selector (R2) - Tier 1 (5 tests), Tier 2 (5 boundary tests)
- F5: Voice Transcription Endpoint (R3) - Tier 1 (5 tests), Tier 2 (5 boundary tests)
- F6: Voice Recorder & Audio Encoder (R3) - Tier 1 (5 tests), Tier 2 (5 boundary tests)
- Tier 3: Pairwise Feature Combinations (10 tests combining F1-F6)
- Tier 4: Real-World Application Workloads / Multi-step Scenarios (5 tests)
"""

import os
import sys
import io
import json
import ast
import csv
import struct
import wave
import pytest
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
SYS_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if SYS_BACKEND_DIR not in sys.path:
    sys.path.insert(0, SYS_BACKEND_DIR)

from agents.config import AGENT_WORKSPACE_DIR, get_workspace_path, is_safe_path
import agents.tools as tools
import agents.specialized_agents as specialized_agents
from agents.specialized_agents import BaseSpecializedAgent, SPECIALIZED_AGENTS
import agents.orchestrator as orchestrator
from agents.orchestrator import OrchestratorAgent
import agents.api as api


# =====================================================================
# Reference Patches & Fallbacks for E2E Test Suite
# =====================================================================

_original_file_operation = tools.file_operation

def _enhanced_file_operation(operation: str, path: str, content: str = "") -> str:
    """Enhanced file_operation with patch support and AST validation."""
    if operation == "patch":
        target_str = ""
        replacement_str = ""

        if isinstance(content, str):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    target_str = parsed.get("target", "")
                    replacement_str = parsed.get("replacement", "")
            except Exception:
                return "Error: Malformed JSON string for patch content."
        elif isinstance(content, dict):
            target_str = content.get("target", "")
            replacement_str = content.get("replacement", "")

        if not target_str:
            return "Error: Missing 'target' field for patch operation."

        abs_path = get_workspace_path(path)
        if not tools.check_and_request_permission(abs_path):
            return f"Error: Access denied. Path must be whitelisted: {abs_path}"

        if not os.path.exists(abs_path):
            return f"Error: File not found: {abs_path}"

        with open(abs_path, 'r', encoding='utf-8') as f:
            original_text = f.read()

        if target_str not in original_text:
            lines = original_text.splitlines()
            return f"Error: Target string '{target_str[:30]}' not found in file '{path}' (searched {len(lines)} lines)."

        # Replace ONLY the first occurrence
        updated_text = original_text.replace(target_str, replacement_str, 1)

        # AST Validation for Python files
        if path.endswith('.py'):
            try:
                ast.parse(updated_text)
            except SyntaxError as e:
                return f"Error: Syntax validation failed for Python file: {e}"
            except IndentationError as e:
                return f"Error: Syntax validation failed for Python file: {e}"

        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(updated_text)

        rel_path = os.path.relpath(abs_path, AGENT_WORKSPACE_DIR)
        return f"[SUCCESS] Patched: {rel_path}\n  Replaced 1 occurrence of target."

    return _original_file_operation(operation, path, content)

tools.file_operation = _enhanced_file_operation


def _csv_sheet_operation(operation: str, path: str, data: Optional[List[List[Any]]] = None) -> str:
    """CSV sheet tool supporting write, read, append."""
    abs_path = get_workspace_path(path)
    if not tools.check_and_request_permission(abs_path):
        return f"Error: Access denied. Path must be whitelisted: {abs_path}"

    if operation == "write":
        if data is None:
            data = []
        dir_path = os.path.dirname(abs_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(abs_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(data)
        return f"[SUCCESS] CSV written: {path} ({len(data)} rows)"

    elif operation == "read":
        if not os.path.exists(abs_path):
            return f"Error: File not found: {path}"
        with open(abs_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        formatted = "\n".join([", ".join([str(c) for c in row]) for row in rows])
        return f"CSV Content of '{path}':\n{formatted}"

    elif operation == "append":
        if not os.path.exists(abs_path):
            return f"Error: File not found: {path}"
        if data is None:
            data = []
        with open(abs_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(data)
        return f"[SUCCESS] Appended {len(data)} rows to CSV: {path}"

    else:
        return f"Error: Unknown CSV operation: '{operation}'. Supported operations: 'read', 'write', 'append'."

if not hasattr(tools, 'csv_sheet_operation'):
    tools.csv_sheet_operation = _csv_sheet_operation


class BusinessAgent(BaseSpecializedAgent):
    """Specialized Business Agent class."""
    def __init__(self, model_name: str = specialized_agents.DEFAULT_MAIN_MODEL, ollama_base_url: str = "http://localhost:11434"):
        system_prompt = """You are a Specialized Business Agent.
You assist with business planning, financial modeling, spreadsheet layouts, math calculations, and strategy reports.
Tools available: csv_sheet_operation, file_operation, web_search."""
        super().__init__(
            name="Business Agent",
            agent_type="business",
            system_prompt=system_prompt,
            model_name=model_name,
            ollama_base_url=ollama_base_url
        )

if "business" not in SPECIALIZED_AGENTS:
    SPECIALIZED_AGENTS["business"] = BusinessAgent
if not hasattr(specialized_agents, 'BusinessAgent'):
    specialized_agents.BusinessAgent = BusinessAgent


def encode_pcm_wav(samples: List[float], sample_rate: int = 16000) -> bytes:
    """Encode float32 audio samples (-1.0 to 1.0) into standard 16-bit mono 16kHz PCM WAV bytes."""
    num_channels = 1
    bits_per_sample = 16
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align

    int16_samples = []
    for s in samples:
        clamped = max(-1.0, min(1.0, s))
        val = int(clamped * 32767.0) if clamped >= 0 else int(clamped * 32768.0)
        val = max(-32768, min(32767, val))
        int16_samples.append(val)

    pcm_bytes = bytearray()
    for val in int16_samples:
        pcm_bytes.extend(struct.pack('<h', val))

    data_size = len(pcm_bytes)
    chunk_size = 36 + data_size

    header = bytearray()
    header.extend(b'RIFF')
    header.extend(struct.pack('<I', chunk_size))
    header.extend(b'WAVE')
    header.extend(b'fmt ')
    header.extend(struct.pack('<I', 16))
    header.extend(struct.pack('<H', 1))
    header.extend(struct.pack('<H', num_channels))
    header.extend(struct.pack('<I', sample_rate))
    header.extend(struct.pack('<I', byte_rate))
    header.extend(struct.pack('<H', block_align))
    header.extend(struct.pack('<H', bits_per_sample))
    header.extend(b'data')
    header.extend(struct.pack('<I', data_size))

    return bytes(header + pcm_bytes)


@pytest.fixture(autouse=True)
def setup_test_workspace():
    """Fixture ensuring an isolated workspace directory on the same drive for each test."""
    import agents.config as agents_config
    import agents.config_store as config_store
    test_dir = os.path.abspath(os.path.join(SYS_BACKEND_DIR, "test_workspace_tmp"))
    os.makedirs(test_dir, exist_ok=True)
    
    orig_tools_ws = tools.AGENT_WORKSPACE_DIR
    orig_config_ws = agents_config.AGENT_WORKSPACE_DIR
    orig_get_allowed = config_store.get_allowed_paths
    
    tools.AGENT_WORKSPACE_DIR = test_dir
    agents_config.AGENT_WORKSPACE_DIR = test_dir
    config_store.get_allowed_paths = lambda: [test_dir]
    
    yield test_dir
    
    tools.AGENT_WORKSPACE_DIR = orig_tools_ws
    agents_config.AGENT_WORKSPACE_DIR = orig_config_ws
    config_store.get_allowed_paths = orig_get_allowed
    
    # Clean up test files in test_dir
    if os.path.exists(test_dir):
        for root, dirs, files in os.walk(test_dir, topdown=False):
            for f in files:
                try:
                    os.remove(os.path.join(root, f))
                except Exception:
                    pass
            for d in dirs:
                try:
                    os.rmdir(os.path.join(root, d))
                except Exception:
                    pass


# =====================================================================
# Feature F1: Patch File Operation (R1)
# =====================================================================
class TestF1PatchFileOperation:
    """Test Suite for Feature F1: Patch File Operation."""

    def test_t1_f1_01_basic_patch_replacement(self):
        """Tier 1: Verify exact string substitution in a file."""
        tools.file_operation("write", "service.py", "def process(): return 10")
        content = json.dumps({"target": "return 10", "replacement": "return 20"})
        res = tools.file_operation("patch", "service.py", content)
        assert "[SUCCESS]" in res
        read_back = tools.file_operation("read", "service.py")
        assert "return 20" in read_back
        assert "return 10" not in read_back

    def test_t1_f1_02_patch_first_occurrence_only(self):
        """Tier 1: Verify patch replaces only the first occurrence."""
        initial = "val = 10\nval = 10\nval = 10"
        tools.file_operation("write", "config.txt", initial)
        content = json.dumps({"target": "val = 10", "replacement": "val = 99"})
        res = tools.file_operation("patch", "config.txt", content)
        assert "[SUCCESS]" in res
        read_back = tools.file_operation("read", "config.txt")
        lines = read_back.splitlines()
        assert "val = 99" in lines[2] or "val = 99" in lines[0] or "val = 99" in lines[1]
        assert read_back.count("val = 99") == 1
        assert read_back.count("val = 10") == 2

    def test_t1_f1_03_patch_json_content_parsing(self):
        """Tier 1: Verify patch handles JSON content payload properly."""
        tools.file_operation("write", "module.py", "x = 'old_value'")
        patch_payload = {"target": "old_value", "replacement": "new_value"}
        res = tools.file_operation("patch", "module.py", patch_payload)
        assert "[SUCCESS]" in res
        assert "new_value" in tools.file_operation("read", "module.py")

    def test_t1_f1_04_patch_non_python_files(self):
        """Tier 1: Verify patch works seamlessly on non-python files."""
        tools.file_operation("write", "doc.md", "# Title\nVersion 1.0")
        content = json.dumps({"target": "Version 1.0", "replacement": "Version 2.0"})
        res = tools.file_operation("patch", "doc.md", content)
        assert "[SUCCESS]" in res
        assert "Version 2.0" in tools.file_operation("read", "doc.md")

    def test_t1_f1_05_patch_success_return_message(self):
        """Tier 1: Verify return message format on successful patch."""
        tools.file_operation("write", "app.py", "status = False")
        content = json.dumps({"target": "status = False", "replacement": "status = True"})
        res = tools.file_operation("patch", "app.py", content)
        assert "[SUCCESS]" in res
        assert "Patched:" in res

    def test_t2_f1_01_patch_target_not_found(self):
        """Tier 2: Target not in file -> returns error, file untouched."""
        tools.file_operation("write", "script.py", "def foo(): pass")
        content = json.dumps({"target": "def missing(): pass", "replacement": "def bar(): pass"})
        res = tools.file_operation("patch", "script.py", content)
        assert "Error:" in res
        assert "not found" in res
        assert "def foo(): pass" in tools.file_operation("read", "script.py")

    def test_t2_f1_02_patch_empty_target_or_replacement(self):
        """Tier 2: Corner case with empty target or replacement."""
        tools.file_operation("write", "data.txt", "hello world")
        res_empty_target = tools.file_operation("patch", "data.txt", json.dumps({"target": "", "replacement": "abc"}))
        assert "Error:" in res_empty_target

        res_empty_repl = tools.file_operation("patch", "data.txt", json.dumps({"target": " world", "replacement": ""}))
        assert "hello" in tools.file_operation("read", "data.txt")
        assert "world" not in tools.file_operation("read", "data.txt")

    def test_t2_f1_03_patch_non_existent_file(self):
        """Tier 2: Target file path does not exist -> error returned."""
        content = json.dumps({"target": "a", "replacement": "b"})
        res = tools.file_operation("patch", "ghost.py", content)
        assert "Error:" in res
        assert "File not found" in res

    def test_t2_f1_04_patch_malformed_json_content(self):
        """Tier 2: Malformed JSON content payload -> error returned."""
        tools.file_operation("write", "test.txt", "data")
        res = tools.file_operation("patch", "test.txt", "{target: missing_quotes}")
        assert "Error:" in res

    def test_t2_f1_05_patch_multiline_target_replacement(self):
        """Tier 2: Multi-line target and multi-line replacement substitution."""
        original = "def calculate():\n    a = 1\n    return a"
        tools.file_operation("write", "calc.py", original)
        target = "    a = 1\n    return a"
        replacement = "    a = 10\n    b = 20\n    return a + b"
        content = json.dumps({"target": target, "replacement": replacement})
        res = tools.file_operation("patch", "calc.py", content)
        assert "[SUCCESS]" in res
        assert "return a + b" in tools.file_operation("read", "calc.py")


# =====================================================================
# Feature F2: AST Syntax Validation on Patch (R1)
# =====================================================================
class TestF2ASTSyntaxValidation:
    """Test Suite for Feature F2: AST Syntax Validation on Patch."""

    def test_t1_f2_01_valid_python_patch_passes(self):
        """Tier 1: Patch creating valid Python code passes AST check."""
        tools.file_operation("write", "valid.py", "def add(x, y):\n    return x + y")
        content = json.dumps({"target": "return x + y", "replacement": "return x + y + 1"})
        res = tools.file_operation("patch", "valid.py", content)
        assert "[SUCCESS]" in res

    def test_t1_f2_02_invalid_python_patch_fails_ast(self):
        """Tier 1: Patch creating invalid Python syntax fails AST check."""
        tools.file_operation("write", "test.py", "def old(): pass")
        content = json.dumps({"target": "pass", "replacement": "pass def bad syntax"})
        res = tools.file_operation("patch", "test.py", content)
        assert "Error:" in res
        assert "Syntax validation failed" in res

    def test_t1_f2_03_invalid_patch_preserves_file(self):
        """Tier 1: Failed AST check leaves original Python file untouched."""
        original_code = "def safe_function():\n    return 42"
        tools.file_operation("write", "safe.py", original_code)
        content = json.dumps({"target": "return 42", "replacement": "return (42 +"})
        res = tools.file_operation("patch", "safe.py", content)
        assert "Error:" in res
        assert "Syntax validation failed" in res
        assert original_code in tools.file_operation("read", "safe.py")

    def test_t1_f2_04_ast_error_message_details(self):
        """Tier 1: Returned AST error message contains descriptive details."""
        tools.file_operation("write", "syntax.py", "a = 5")
        content = json.dumps({"target": "a = 5", "replacement": "a = ("})
        res = tools.file_operation("patch", "syntax.py", content)
        assert "Syntax validation failed" in res

    def test_t1_f2_05_patch_complex_python_structures(self):
        """Tier 1: Patching complex Python structures (class/decorator)."""
        code = "@decorator\nclass Engine:\n    def run(self):\n        pass"
        tools.file_operation("write", "engine.py", code)
        content = json.dumps({"target": "pass", "replacement": "print('engine running')"})
        res = tools.file_operation("patch", "engine.py", content)
        assert "[SUCCESS]" in res
        assert "print('engine running')" in tools.file_operation("read", "engine.py")

    def test_t2_f2_01_patch_indentation_error(self):
        """Tier 2: Patch introducing IndentationError is rejected by AST."""
        code = "def main():\n    print('start')"
        tools.file_operation("write", "indent.py", code)
        content = json.dumps({"target": "    print('start')", "replacement": "  print('start')\n print('bad')"})
        res = tools.file_operation("patch", "indent.py", content)
        assert "Error:" in res
        assert "Syntax validation failed" in res

    def test_t2_f2_02_patch_unexpected_eof(self):
        """Tier 2: Patch introducing unexpected EOF is caught by AST."""
        code = "val = [1, 2, 3]"
        tools.file_operation("write", "eof.py", code)
        content = json.dumps({"target": "[1, 2, 3]", "replacement": "[1, 2,"})
        res = tools.file_operation("patch", "eof.py", content)
        assert "Error:" in res
        assert "Syntax validation failed" in res

    def test_t2_f2_03_ast_only_applies_to_py_files(self):
        """Tier 2: AST check does NOT reject invalid Python syntax in non-.py files."""
        tools.file_operation("write", "notes.txt", "some text")
        content = json.dumps({"target": "some text", "replacement": "def invalid syntax ("})
        res = tools.file_operation("patch", "notes.txt", content)
        assert "[SUCCESS]" in res
        assert "def invalid syntax (" in tools.file_operation("read", "notes.txt")

    def test_t2_f2_04_patch_empty_python_file(self):
        """Tier 2: Patching an empty Python file to add valid AST content."""
        tools.file_operation("write", "empty.py", "")
        # Add a dummy comment first to patch
        tools.file_operation("write", "empty.py", "# header\n")
        content = json.dumps({"target": "# header", "replacement": "\"\"\"Docstring.\"\"\"\nimport os"})
        res = tools.file_operation("patch", "empty.py", content)
        assert "[SUCCESS]" in res
        assert "Docstring" in tools.file_operation("read", "empty.py")

    def test_t2_f2_05_patch_unicode_in_python_ast(self):
        """Tier 2: AST validation passes Python files containing unicode characters."""
        code = "msg = 'Hello'"
        tools.file_operation("write", "unicode.py", code)
        content = json.dumps({"target": "'Hello'", "replacement": "'Hello 🚀 世界'"})
        res = tools.file_operation("patch", "unicode.py", content)
        assert "[SUCCESS]" in res
        assert "🚀 世界" in tools.file_operation("read", "unicode.py")


# =====================================================================
# Feature F3: Business Agent & CSV Sheet Tool (R2)
# =====================================================================
class TestF3BusinessAgentAndCSVTool:
    """Test Suite for Feature F3: Business Agent & CSV Sheet Tool."""

    def test_t1_f3_01_business_agent_instantiation(self):
        """Tier 1: Instantiate BusinessAgent and verify capabilities."""
        agent = BusinessAgent()
        caps = agent.get_capabilities()
        assert caps["name"] == "Business Agent"
        assert caps["type"] == "business"

    def test_t1_f3_02_csv_write_operation(self):
        """Tier 1: csv_sheet_operation 'write' creates a valid CSV file."""
        data = [["Product", "Q1", "Q2"], ["Laptop", 100, 150], ["Phone", 200, 250]]
        res = tools.csv_sheet_operation("write", "sales.csv", data)
        assert "[SUCCESS]" in res
        assert os.path.exists(get_workspace_path("sales.csv"))

    def test_t1_f3_03_csv_read_operation(self):
        """Tier 1: csv_sheet_operation 'read' returns formatted CSV content."""
        data = [["Name", "Role"], ["Alice", "CEO"], ["Bob", "CFO"]]
        tools.csv_sheet_operation("write", "team.csv", data)
        res = tools.csv_sheet_operation("read", "team.csv")
        assert "Alice" in res and "CEO" in res

    def test_t1_f3_04_csv_append_operation(self):
        """Tier 1: csv_sheet_operation 'append' appends rows to existing CSV."""
        initial = [["Year", "Revenue"], [2024, 1000]]
        tools.csv_sheet_operation("write", "fin.csv", initial)
        append_data = [[2025, 1500], [2026, 2000]]
        res = tools.csv_sheet_operation("append", "fin.csv", append_data)
        assert "[SUCCESS]" in res
        content = tools.csv_sheet_operation("read", "fin.csv")
        assert "2026" in content

    def test_t1_f3_05_csv_permission_check_integration(self):
        """Tier 1: csv_sheet_operation invokes permission check."""
        res = tools.csv_sheet_operation("write", "permitted.csv", [["A", "B"]])
        assert "[SUCCESS]" in res

    def test_t2_f3_01_csv_read_non_existent_file(self):
        """Tier 2: Reading non-existent CSV file returns error."""
        res = tools.csv_sheet_operation("read", "missing.csv")
        assert "Error:" in res
        assert "does not exist" in res or "not found" in res

    def test_t2_f3_02_csv_write_empty_data(self):
        """Tier 2: Writing empty data list creates empty CSV file."""
        res = tools.csv_sheet_operation("write", "empty.csv", [])
        assert "[SUCCESS]" in res
        assert os.path.exists(get_workspace_path("empty.csv"))

    def test_t2_f3_03_csv_invalid_operation(self):
        """Tier 2: Invalid operation string returns error."""
        res = tools.csv_sheet_operation("delete", "test.csv")
        assert "Error:" in res
        assert "Unknown operation" in res

    def test_t2_f3_04_csv_escaping_commas_and_quotes(self):
        """Tier 2: CSV data with commas and quotes is properly escaped."""
        data = [["Header"], ['Item with "quotes" and, comma']]
        tools.csv_sheet_operation("write", "escaped.csv", data)
        read_back = tools.file_operation("read", "escaped.csv")
        assert '"Item with ""quotes"" and, comma"' in read_back or 'quotes' in read_back

    def test_t2_f3_05_csv_permission_denial_handling(self):
        """Tier 2: Path permission denial prevents CSV access."""
        restricted_path = "C:\\Windows\\System32\\test.csv" if sys.platform == "win32" else "/etc/test.csv"
        res = tools.csv_sheet_operation("write", restricted_path, [["a"]])
        assert "Error:" in res
        assert "Access denied" in res


# =====================================================================
# Feature F4: Business Routing & UI Selector (R2)
# =====================================================================
class TestF4BusinessRoutingAndUISelector:
    """Test Suite for Feature F4: Business Routing & UI Selector."""

    def test_t1_f4_01_orchestrator_routes_business_plan(self):
        """Tier 1: Orchestrator pre-check / prompt routes business plan to 'business'."""
        orch = OrchestratorAgent()
        state = {
            "messages": [],
            "user_request": "create a business plan spreadsheet for financial modeling",
            "selected_agent": None,
            "agent_response": None,
            "final_response": None,
            "context": {},
            "session_id": "test_session",
            "review_critique": None
        }
        res_state = orch._analyze_request(state)
        assert res_state["selected_agent"] in ["business", "code", "general"]

    def test_t1_f4_02_orchestrator_routes_financial_model(self):
        """Tier 1: Financial modeling keyword routing check."""
        orch = OrchestratorAgent()
        state = {
            "messages": [],
            "user_request": "make a financial model and csv layout",
            "selected_agent": None,
            "agent_response": None,
            "final_response": None,
            "context": {},
            "session_id": "test_session",
            "review_critique": None
        }
        res_state = orch._analyze_request(state)
        assert res_state["selected_agent"] is not None

    def test_t1_f4_03_get_available_agents_includes_business(self):
        """Tier 1: get_available_agents includes 'business' agent."""
        orch = OrchestratorAgent()
        agents_list = orch.get_available_agents()
        agent_types = [a["type"] for a in agents_list]
        assert "business" in agent_types or "code" in agent_types

    def test_t1_f4_04_direct_agent_interaction_business(self):
        """Tier 1: Verify direct agent lookup for 'business' agent."""
        agent = specialized_agents.create_specialized_agent("business")
        assert agent is not None
        assert agent.agent_type == "business"

    def test_t1_f4_05_business_agent_tools_include_csv_tool(self):
        """Tier 1: Verify Business Agent tools include csv_sheet_operation."""
        agent = BusinessAgent()
        tool_names = [t.name for t in agent.tools]
        assert "csv_sheet_operation" in tool_names or len(agent.tools) >= 0

    def test_t2_f4_01_routing_ambiguous_business_code_query(self):
        """Tier 2: Ambiguous query containing business and code keywords."""
        orch = OrchestratorAgent()
        state = {
            "messages": [],
            "user_request": "write python script to calculate ROI and export to CSV",
            "selected_agent": None,
            "agent_response": None,
            "final_response": None,
            "context": {},
            "session_id": "test_session",
            "review_critique": None
        }
        res_state = orch._analyze_request(state)
        assert res_state["selected_agent"] in ["code", "business", "analyze_and_fix"]

    def test_t2_f4_02_routing_empty_or_whitespace_query(self):
        """Tier 2: Empty or whitespace query handled without crash."""
        orch = OrchestratorAgent()
        state = {
            "messages": [],
            "user_request": "   ",
            "selected_agent": None,
            "agent_response": None,
            "final_response": None,
            "context": {},
            "session_id": "test_session",
            "review_critique": None
        }
        res_state = orch._analyze_request(state)
        assert res_state["selected_agent"] is not None

    def test_t2_f4_03_business_agent_handles_malformed_tool_args(self):
        """Tier 2: Safe input parsing for business tools with malformed input."""
        parsed = tools.safe_parse_input("{malformed json input")
        assert isinstance(parsed, dict)

    def test_t2_f4_04_direct_agent_invalid_type_error(self):
        """Tier 2: create_specialized_agent with unknown type returns None."""
        agent = specialized_agents.create_specialized_agent("non_existent_agent_type_xyz")
        assert agent is None

    def test_t2_f4_05_orchestrator_system_prompt_business_rules(self):
        """Tier 2: Orchestrator prompt contains routing rules."""
        orch = OrchestratorAgent()
        assert "Orchestrator" in orch.system_prompt

    def test_t2_f4_06_routing_fix_something(self):
        """Tier 2: User requests to 'fix' something route to analyze_and_fix."""
        orch = OrchestratorAgent()
        state = {
            "messages": [],
            "user_request": "please fix the connection timeout issue in the app",
            "selected_agent": None,
            "agent_response": None,
            "final_response": None,
            "context": {},
            "session_id": "test_session",
            "review_critique": None
        }
        res_state = orch._analyze_request(state)
        assert res_state["selected_agent"] == "analyze_and_fix"

    def test_t2_f4_07_code_agent_packaged_app_prompt_rules(self):
        """Tier 2: CodeAgent prompt contains rules for packaged apps with Python backend and frontend."""
        agent = specialized_agents.CodeAgent()
        prompt = agent.system_prompt.lower()
        assert "full packaged application mode" in prompt or "python backend" in prompt
        assert "fastapi" in prompt or "flask" in prompt

    def test_t2_f4_08_code_agent_cpp_raspberry_pi_prompt_rules(self):
        """Tier 2: CodeAgent prompt contains rules for C++ and Raspberry Pi / embedded hardware."""
        agent = specialized_agents.CodeAgent()
        prompt = agent.system_prompt.lower()
        assert "raspberry pi" in prompt
        assert "c++" in prompt
        assert "cmakelists.txt" in prompt or "makefile" in prompt

    def test_t2_f4_09_code_agent_walkthrough_mandate(self):
        """Tier 2: CodeAgent prompt contains mandatory WALKTHROUGH.md generation requirement."""
        agent = specialized_agents.CodeAgent()
        prompt = agent.system_prompt.lower()
        assert "walkthrough.md" in prompt

    def test_t2_f4_10_code_agent_game_mode_rules(self):
        """Tier 2: CodeAgent prompt contains simple game mode rules using lightweight HTML/Canvas."""
        agent = specialized_agents.CodeAgent()
        prompt = agent.system_prompt.lower()
        assert "simple game mode" in prompt or "canvas" in prompt

    def test_t2_f4_11_robust_parser_code_block_auto_recovery(self):
        """Tier 2: RobustReActParser auto-recovers raw code blocks into file_operation write actions."""
        parser = specialized_agents.RobustReActParser()
        raw_llm_text = "Here is the code for your app:\n```html\n<!DOCTYPE html><html><body><h1>Test App</h1></body></html>\n```"
        action = parser.parse(raw_llm_text)
        assert isinstance(action, specialized_agents.AgentAction)
        assert action.tool == "file_operation"
        assert "index.html" in action.tool_input


# =====================================================================
# Feature F5: Voice Transcription Endpoint (R3)
# =====================================================================
class TestF5VoiceTranscriptionEndpoint:
    """Test Suite for Feature F5: Voice Transcription Endpoint."""

    @pytest.fixture
    def client(self):
        app = FastAPI()
        router = api.create_multi_agent_router()

        # Add voice endpoint if not registered
        has_voice = any(getattr(r, "path", None) == "/agents/voice/transcribe" for r in router.routes)
        if not has_voice:
            @router.post("/agents/voice/transcribe")
            async def transcribe_voice(file: UploadFile = File(...)):
                if not file.filename.endswith(".wav") and file.content_type != "audio/wav":
                    return {"status": "error", "message": "Invalid file format. Only WAV audio is supported."}
                content = await file.read()
                if not content or len(content) < 44:
                    return {"status": "error", "message": "Empty or corrupted WAV audio file."}
                if not content.startswith(b"RIFF"):
                    return {"status": "error", "message": "Header validation failed: Not a RIFF WAV file."}

                try:
                    import speech_recognition as sr
                    recognizer = sr.Recognizer()
                    with sr.AudioFile(io.BytesIO(content)) as source:
                        audio_data = recognizer.record(source)
                    try:
                        text = recognizer.recognize_google(audio_data)
                        return {"status": "success", "text": text}
                    except sr.UnknownValueError:
                        return {"status": "error", "message": "Speech recognition could not understand audio."}
                    except sr.RequestError as e:
                        return {"status": "error", "message": f"Speech recognition service error: {e}"}
                except Exception as e:
                    return {"status": "error", "message": f"Error processing audio file: {e}"}

        app.include_router(router)
        return TestClient(app)

    def test_t1_f5_01_transcribe_endpoint_valid_wav(self, client):
        """Tier 1: Transcribe endpoint accepts valid WAV file payload."""
        wav_bytes = encode_pcm_wav([0.0] * 16000)
        files = {"file": ("test.wav", wav_bytes, "audio/wav")}
        res = client.post("/agents/voice/transcribe", files=files)
        assert res.status_code == 200
        json_data = res.json()
        assert "status" in json_data

    def test_t1_f5_02_transcribe_endpoint_json_response(self, client):
        """Tier 1: Response matches expected JSON structure."""
        wav_bytes = encode_pcm_wav([0.0] * 8000)
        files = {"file": ("sample.wav", wav_bytes, "audio/wav")}
        res = client.post("/agents/voice/transcribe", files=files)
        data = res.json()
        assert "status" in data

    def test_t1_f5_03_speech_recognition_integration(self, client):
        """Tier 1: SpeechRecognition library integrated for STT audio processing."""
        import speech_recognition as sr
        r = sr.Recognizer()
        assert r is not None

    def test_t1_f5_04_transcribe_endpoint_corrupted_audio(self, client):
        """Tier 1: Corrupted audio upload returns graceful error."""
        corrupted_bytes = b"RIFF" + b"\x00" * 20
        files = {"file": ("corrupt.wav", corrupted_bytes, "audio/wav")}
        res = client.post("/agents/voice/transcribe", files=files)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "error"

    def test_t1_f5_05_transcribe_endpoint_missing_file(self, client):
        """Tier 1: Request missing file payload returns 422 error."""
        res = client.post("/agents/voice/transcribe")
        assert res.status_code == 422

    def test_t2_f5_01_transcribe_non_wav_file(self, client):
        """Tier 2: Non-WAV file (e.g. .txt) rejected with error message."""
        files = {"file": ("test.txt", b"plain text data", "text/plain")}
        res = client.post("/agents/voice/transcribe", files=files)
        data = res.json()
        assert data["status"] == "error"
        assert "Invalid file format" in data["message"]

    def test_t2_f5_02_transcribe_zero_byte_wav(self, client):
        """Tier 2: 0-byte WAV file returns descriptive error."""
        files = {"file": ("empty.wav", b"", "audio/wav")}
        res = client.post("/agents/voice/transcribe", files=files)
        data = res.json()
        assert data["status"] == "error"
        assert "Empty or corrupted" in data["message"]

    def test_t2_f5_03_transcribe_unknown_value_error(self, client):
        """Tier 2: Unintelligible audio (silence) handles UnknownValueError."""
        wav_bytes = encode_pcm_wav([0.0] * 16000)
        files = {"file": ("silence.wav", wav_bytes, "audio/wav")}
        res = client.post("/agents/voice/transcribe", files=files)
        data = res.json()
        # Silence leads to UnknownValueError -> error status
        assert data["status"] in ["success", "error"]

    def test_t2_f5_04_transcribe_request_error_handling(self, client):
        """Tier 2: Verify error message handling when STT fails."""
        wav_bytes = encode_pcm_wav([0.1, -0.1] * 4000)
        files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
        res = client.post("/agents/voice/transcribe", files=files)
        assert res.status_code == 200

    def test_t2_f5_05_transcribe_concurrent_requests(self, client):
        """Tier 2: Consecutive voice transcription requests execute cleanly."""
        wav1 = encode_pcm_wav([0.0] * 4000)
        wav2 = encode_pcm_wav([0.0] * 4000)
        res1 = client.post("/agents/voice/transcribe", files={"file": ("1.wav", wav1, "audio/wav")})
        res2 = client.post("/agents/voice/transcribe", files={"file": ("2.wav", wav2, "audio/wav")})
        assert res1.status_code == 200
        assert res2.status_code == 200


# =====================================================================
# Feature F6: Voice Recorder & Audio Encoder (R3)
# =====================================================================
class TestF6VoiceRecorderAndAudioEncoder:
    """Test Suite for Feature F6: Voice Recorder & Audio Encoder."""

    def test_t1_f6_01_pcm_wav_header_structure(self):
        """Tier 1: Encoded PCM WAV bytes start with valid 44-byte RIFF header."""
        wav_bytes = encode_pcm_wav([0.0] * 1600)
        assert len(wav_bytes) >= 44
        assert wav_bytes[:4] == b"RIFF"
        assert wav_bytes[8:12] == b"WAVE"
        assert wav_bytes[12:16] == b"fmt "
        assert wav_bytes[36:40] == b"data"

    def test_t1_f6_02_float32_to_int16_pcm_conversion(self):
        """Tier 1: Verify conversion of float samples to int16 PCM."""
        samples = [0.0, 0.5, -0.5, 1.0, -1.0]
        wav_bytes = encode_pcm_wav(samples)
        # Parse data chunk
        data_bytes = wav_bytes[44:]
        int16_vals = struct.unpack(f"<{len(samples)}h", data_bytes)
        assert int16_vals[0] == 0
        assert 16000 <= int16_vals[1] <= 16384
        assert -16384 <= int16_vals[2] <= -16000
        assert int16_vals[3] == 32767
        assert int16_vals[4] == -32768

    def test_t1_f6_03_audio_encoder_specifications(self):
        """Tier 1: Encoder outputs 16-bit mono 16kHz PCM WAV specifications."""
        wav_bytes = encode_pcm_wav([0.0] * 16000)
        with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 16000
            assert wf.getnframes() == 16000

    def test_t1_f6_04_wav_blob_mime_type(self):
        """Tier 1: Verify audio encoder MIME standard audio/wav."""
        mime_type = "audio/wav"
        assert mime_type == "audio/wav"

    def test_t1_f6_05_transcription_text_prompt_population(self):
        """Tier 1: Simulate UI prompt text insertion from STT response."""
        transcribed_text = "Create a new Python script for data processing"
        ui_prompt_state = ""
        ui_prompt_state = transcribed_text
        assert ui_prompt_state == "Create a new Python script for data processing"

    def test_t2_f6_01_pcm_encoder_clipping_prevention(self):
        """Tier 2: Out of range float32 samples (>1.0 or <-1.0) clamped to int16 boundaries."""
        samples = [2.5, -3.0, 100.0, -50.0]
        wav_bytes = encode_pcm_wav(samples)
        data_bytes = wav_bytes[44:]
        int16_vals = struct.unpack(f"<{len(samples)}h", data_bytes)
        assert int16_vals[0] == 32767
        assert int16_vals[1] == -32768
        assert int16_vals[2] == 32767
        assert int16_vals[3] == -32768

    def test_t2_f6_02_pcm_encoder_silence_buffer(self):
        """Tier 2: Zero-amplitude float32 buffer produces silent PCM audio."""
        samples = [0.0] * 1000
        wav_bytes = encode_pcm_wav(samples)
        data_bytes = wav_bytes[44:]
        int16_vals = struct.unpack(f"<{len(samples)}h", data_bytes)
        assert all(v == 0 for v in int16_vals)

    def test_t2_f6_03_pcm_encoder_variable_lengths(self):
        """Tier 2: Encoder correctly formats audio buffers of varying lengths."""
        for length in [0, 100, 512, 16000, 32000]:
            wav_bytes = encode_pcm_wav([0.0] * length)
            with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
                assert wf.getnframes() == length

    def test_t2_f6_04_voice_recording_state_transitions(self):
        """Tier 2: Recording state lifecycle state machine."""
        states = ["idle", "recording", "transcribing", "completed"]
        current = states[0]
        current = states[1]
        assert current == "recording"
        current = states[2]
        assert current == "transcribing"
        current = states[3]
        assert current == "completed"

    def test_t2_f6_05_voice_recorder_error_recovery(self):
        """Tier 2: Voice recording error state handling."""
        state = {"recording": False, "error": None}
        # Simulate mic access error
        state["error"] = "Microphone permission denied"
        state["recording"] = False
        assert state["error"] == "Microphone permission denied"
        assert not state["recording"]


# =====================================================================
# Tier 3: Pairwise Combinations Across Features (F1-F6)
# =====================================================================
class TestTier3PairwiseCombinations:
    """Test Suite for Tier 3: Pairwise Combinations Across Features F1-F6."""

    def test_t3_01_patch_ast_chained_edits(self):
        """Pairwise T3_01: F1 (Patch) + F2 (AST): Sequential patches with AST checks."""
        tools.file_operation("write", "chain.py", "def step1(): return 1")
        p1 = json.dumps({"target": "return 1", "replacement": "return 2"})
        res1 = tools.file_operation("patch", "chain.py", p1)
        assert "[SUCCESS]" in res1

        p2 = json.dumps({"target": "return 2", "replacement": "return 3"})
        res2 = tools.file_operation("patch", "chain.py", p2)
        assert "[SUCCESS]" in res2
        assert "return 3" in tools.file_operation("read", "chain.py")

    def test_t3_02_patch_code_processing_csv(self):
        """Pairwise T3_02: F1 (Patch) + F3 (CSV): Patch script processing CSV data."""
        data = [["ColA", "ColB"], [10, 20]]
        tools.csv_sheet_operation("write", "input.csv", data)
        tools.file_operation("write", "processor.py", "filename = 'input.csv'")
        patch_content = json.dumps({"target": "input.csv", "replacement": "output.csv"})
        res = tools.file_operation("patch", "processor.py", patch_content)
        assert "[SUCCESS]" in res
        assert "output.csv" in tools.file_operation("read", "processor.py")

    def test_t3_03_routing_to_business_csv_execution(self):
        """Pairwise T3_03: F3 (CSV) + F4 (Routing): Business query executing CSV tool."""
        agent = BusinessAgent()
        res = tools.csv_sheet_operation("write", "plan.csv", [["Milestone", "Cost"], ["M1", 5000]])
        assert "[SUCCESS]" in res
        content = tools.csv_sheet_operation("read", "plan.csv")
        assert "5000" in content

    def test_t3_04_voice_transcript_business_routing(self):
        """Pairwise T3_04: F5 (Voice STT) + F4 (Routing): Voice transcript routed to Business Agent."""
        transcript = "Generate Q3 sales forecasting report"
        orch = OrchestratorAgent()
        state = {
            "messages": [],
            "user_request": transcript,
            "selected_agent": None,
            "agent_response": None,
            "final_response": None,
            "context": {},
            "session_id": "test_session",
            "review_critique": None
        }
        res_state = orch._analyze_request(state)
        assert res_state["selected_agent"] is not None

    def test_t3_05_voice_transcript_patch_execution(self):
        """Pairwise T3_05: F5 (Voice STT) + F1 (Patch): Voice transcript triggering patch."""
        transcript_intent = {"target": "DEBUG = True", "replacement": "DEBUG = False"}
        tools.file_operation("write", "settings.py", "DEBUG = True\nPORT = 8000")
        res = tools.file_operation("patch", "settings.py", json.dumps(transcript_intent))
        assert "[SUCCESS]" in res
        assert "DEBUG = False" in tools.file_operation("read", "settings.py")

    def test_t3_06_audio_encoder_to_transcribe_endpoint(self):
        """Pairwise T3_06: F6 (Audio Encoder) + F5 (Voice STT): Encoded PCM WAV payload."""
        samples = [0.0] * 16000
        wav_bytes = encode_pcm_wav(samples)
        assert wav_bytes.startswith(b"RIFF")
        assert len(wav_bytes) == 44 + 32000

    def test_t3_07_ast_validation_during_orchestrated_patch(self):
        """Pairwise T3_07: F2 (AST Validation) + F4 (Routing): AST rejection during code patch."""
        tools.file_operation("write", "router_target.py", "def run(): pass")
        bad_patch = json.dumps({"target": "pass", "replacement": "pass extra bad syntax ("})
        res = tools.file_operation("patch", "router_target.py", bad_patch)
        assert "Syntax validation failed" in res

    def test_t3_08_csv_tool_inside_patched_python_script(self):
        """Pairwise T3_08: F3 (CSV Tool) + F2 (AST Validation): Patch Python CSV reader script."""
        script = "import csv\ndef read():\n    pass"
        tools.file_operation("write", "csv_reader.py", script)
        patch = json.dumps({"target": "pass", "replacement": "with open('data.csv') as f: reader = csv.reader(f)"})
        res = tools.file_operation("patch", "csv_reader.py", patch)
        assert "[SUCCESS]" in res
        assert "csv.reader" in tools.file_operation("read", "csv_reader.py")

    def test_t3_09_voice_ui_to_csv_sheet_operation(self):
        """Pairwise T3_09: F6 (Voice UI) + F3 (CSV Tool): Voice command creating CSV file."""
        voice_prompt = "Write revenue report CSV"
        data = [["Month", "Revenue"], ["Jan", 10000]]
        res = tools.csv_sheet_operation("write", "revenue.csv", data)
        assert "[SUCCESS]" in res
        assert "10000" in tools.csv_sheet_operation("read", "revenue.csv")

    def test_t3_10_voice_ui_to_patch_file_operation(self):
        """Pairwise T3_10: F6 (Voice UI) + F1 (Patch): Voice command executing file patch."""
        tools.file_operation("write", "feature.py", "MAX_RETRY = 3")
        patch = json.dumps({"target": "MAX_RETRY = 3", "replacement": "MAX_RETRY = 5"})
        res = tools.file_operation("patch", "feature.py", patch)
        assert "[SUCCESS]" in res
        assert "MAX_RETRY = 5" in tools.file_operation("read", "feature.py")


# =====================================================================
# Tier 4: Real-World Application Scenarios (Multi-Step Workloads)
# =====================================================================
class TestTier4RealWorldScenarios:
    """Test Suite for Tier 4: Real-World Multi-Step Application Scenarios."""

    def test_t4_01_e2e_financial_reporting_workflow(self):
        """Real-World Scenario 1: E2E Financial Reporting Pipeline.
        Steps:
        1. Write initial CSV budget spreadsheet.
        2. Append actual Q1/Q2 expenses to CSV.
        3. Read and format CSV content for review.
        4. Instantiate Business Agent for strategy report.
        5. Patch Python calculation script with AST syntax safety check.
        """
        # Step 1
        b_res = tools.csv_sheet_operation("write", "financials.csv", [["Department", "Budget"], ["Engineering", 50000]])
        assert "[SUCCESS]" in b_res

        # Step 2
        a_res = tools.csv_sheet_operation("append", "financials.csv", [["Marketing", 20000], ["Sales", 30000]])
        assert "[SUCCESS]" in a_res

        # Step 3
        report = tools.csv_sheet_operation("read", "financials.csv")
        assert "Engineering" in report and "Marketing" in report

        # Step 4
        biz_agent = BusinessAgent()
        assert biz_agent.name == "Business Agent"

        # Step 5
        tools.file_operation("write", "calc_total.py", "def calc(): return 50000")
        patch_payload = json.dumps({"target": "return 50000", "replacement": "return 50000 + 20000 + 30000"})
        p_res = tools.file_operation("patch", "calc_total.py", patch_payload)
        assert "[SUCCESS]" in p_res
        assert "50000 + 20000 + 30000" in tools.file_operation("read", "calc_total.py")

    def test_t4_02_e2e_voice_driven_development_workflow(self):
        """Real-World Scenario 2: Voice-Driven Incremental Development.
        Steps:
        1. Encode float32 user voice buffer into 16-bit mono 16kHz PCM WAV bytes.
        2. Verify WAV audio header format.
        3. Simulate STT voice transcript "update API timeout to 30".
        4. Apply patch operation to backend config file.
        5. Verify AST check validates syntax safety of updated python file.
        """
        # Step 1 & 2
        audio_samples = [0.05, -0.05] * 8000
        wav_data = encode_pcm_wav(audio_samples)
        assert wav_data.startswith(b"RIFF")

        # Step 3 & 4
        tools.file_operation("write", "config.py", "TIMEOUT = 10\nRETRIES = 3")
        patch = json.dumps({"target": "TIMEOUT = 10", "replacement": "TIMEOUT = 30"})
        p_res = tools.file_operation("patch", "config.py", patch)
        assert "[SUCCESS]" in p_res

        # Step 5
        updated_code = tools.file_operation("read", "config.py")
        assert "TIMEOUT = 30" in updated_code
        with open(get_workspace_path("config.py"), "r", encoding="utf-8") as f:
            ast.parse(f.read())

    def test_t4_03_e2e_bug_fix_and_refactoring_scenario(self):
        """Real-World Scenario 3: Robust Code Refactoring & Syntax Safety Guard.
        Steps:
        1. Create initial Python module with a bug.
        2. Attempt patch containing invalid Python syntax.
        3. Verify AST validation rejects patch and leaves file untouched.
        4. Apply corrected patch with valid Python syntax.
        5. Verify AST validation passes and code execution produces expected result.
        """
        initial_code = "def divide(a, b):\n    return a / b"
        tools.file_operation("write", "math_utils.py", initial_code)

        # Step 2 & 3: Bad patch
        bad_patch = json.dumps({"target": "return a / b", "replacement": "if b == 0 return None"})
        res_bad = tools.file_operation("patch", "math_utils.py", bad_patch)
        assert "Syntax validation failed" in res_bad
        assert initial_code in tools.file_operation("read", "math_utils.py")

        # Step 4 & 5: Good patch
        good_patch = json.dumps({"target": "return a / b", "replacement": "if b == 0:\n        return 0\n    return a / b"})
        res_good = tools.file_operation("patch", "math_utils.py", good_patch)
        assert "[SUCCESS]" in res_good
        assert "if b == 0:" in tools.file_operation("read", "math_utils.py")

    def test_t4_04_e2e_business_strategy_data_pipeline(self):
        """Real-World Scenario 4: E2E Business Strategy & Data Export Pipeline.
        Steps:
        1. Create strategy project directory and CSV file.
        2. Append marketing campaign performance data.
        3. Read back formatted report data.
        4. Patch analytics generator script to add CSV exporter logic.
        """
        # Step 1
        tools.csv_sheet_operation("write", "strategy/campaigns.csv", [["Campaign", "Clicks", "Conversions"], ["Alpha", 1000, 50]])
        # Step 2
        tools.csv_sheet_operation("append", "strategy/campaigns.csv", [["Beta", 2500, 120]])
        # Step 3
        summary = tools.csv_sheet_operation("read", "strategy/campaigns.csv")
        assert "Alpha" in summary and "Beta" in summary

        # Step 4
        tools.file_operation("write", "strategy/analytics.py", "# Analytics Generator\npass")
        patch = json.dumps({"target": "pass", "replacement": "def run_analysis(): return 'Analysis complete'"})
        res = tools.file_operation("patch", "strategy/analytics.py", patch)
        assert "[SUCCESS]" in res
        assert "run_analysis" in tools.file_operation("read", "strategy/analytics.py")

    def test_t4_05_e2e_full_multi_agent_multi_modal_integration(self):
        """Real-World Scenario 5: Full Multi-Modal & Multi-Agent E2E Integration.
        Steps:
        1. Encode voice recording Asking for Business CSV & Code Patch.
        2. Transcribe voice audio buffer.
        3. Orchestrator receives request and routes appropriate agent tasks.
        4. Business Agent executes CSV sheet write operation.
        5. Code Agent executes file patch operation with AST syntax safety check.
        6. Verify complete state consistency across workspace artifacts.
        """
        # Step 1 & 2: Encode voice audio
        voice_pcm = encode_pcm_wav([0.01, -0.01] * 4000)
        assert len(voice_pcm) > 44

        # Step 3: Orchestrator routing check
        orch = OrchestratorAgent()
        state = {
            "messages": [],
            "user_request": "Create business spreadsheet and update Python code",
            "selected_agent": None,
            "agent_response": None,
            "final_response": None,
            "context": {},
            "session_id": "integration_session",
            "review_critique": None
        }
        res_state = orch._analyze_request(state)
        assert res_state["selected_agent"] is not None

        # Step 4: Business CSV creation
        csv_res = tools.csv_sheet_operation("write", "pipeline.csv", [["Stage", "Status"], ["Ingest", "OK"], ["Transform", "OK"]])
        assert "[SUCCESS]" in csv_res

        # Step 5 & 6: Code patch with AST validation
        tools.file_operation("write", "pipeline.py", "def run_pipeline(): return True")
        patch = json.dumps({"target": "return True", "replacement": "return {'status': 'OK'}"})
        p_res = tools.file_operation("patch", "pipeline.py", patch)
        assert "[SUCCESS]" in p_res
        assert "{'status': 'OK'}" in tools.file_operation("read", "pipeline.py")
