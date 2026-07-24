# Milestone 1: Test Infrastructure Inspection & Verification Strategy Analysis

## 1. Test Infrastructure Overview

### 1.1 Existing Test Files in `backend/`
Inspection of `backend/` revealed the following key test files:
- `backend/test_file_operations.py`: Primary test suite for file tools (`write_file_content`, `read_file_content`, `list_directory`, `create_project_structure`). It includes a custom test runner `main()` returning exit code 0 or 1, and standard `test_*` functions compatible with Pytest.
- `backend/test_agent.py`: Integration test script for agent HTTP endpoints (`/api/multi-agent/agents/chat`).
- `backend/test_agent_security.py`: Tests for workspace path safety and permissions (`is_safe_path`, path traversal checks).
- `backend/test_guide_api.py`, `backend/test_interactive_permissions.py`, `backend/test_memory.py`, `backend/test_multi_agent.py`, `backend/test_scheduler_and_commands.py`: Specialized module test suites.

### 1.2 Current Runner & Framework Patterns
1. **Execution Patterns**:
   - Standard Pytest runner: `pytest backend/test_file_operations.py` or `python -m pytest backend/`.
   - Standalone CLI execution: `python backend/test_file_operations.py` (which runs `main()` with explicit pass/fail formatting and sys.exit status).
2. **Workspace Management**:
   - Workspace root is defined in `backend/agents/config.py` as `AGENT_WORKSPACE_DIR`. Tests construct temporary files inside this workspace directory via `get_workspace_path(...)`.

---

## 2. Milestone 1 Targeted Components

### 2.1 Component 1: `file_operation(operation="patch", path=..., content=...)`
- **Location**: `backend/agents/tools.py` (line ~517)
- **Current Behavior**: Handles `"read"`, `"write"`, and `"list"`. Returns error for unknown operations.
- **Required Milestone 1 Behavior**:
  - Support `operation: "patch"`.
  - Parse `content` parameter as JSON: `{"target": "<string to replace>", "replacement": "<new string>"}`.
  - Perform exact string substitution of the first occurrence of `target`.
  - If `target` is not found, return an error detailing line numbers (e.g. line count scanned or missing string context).
  - If `path` ends with `.py`, run `ast.parse(updated_content)`. If syntax error occurs, return error message and do NOT alter the file.

### 2.2 Component 2: `CodeAgent` System Prompt
- **Location**: `backend/agents/specialized_agents.py` (line ~408)
- **Current Prompt**: Instructs agent to read with `"read"` and overwrite with `"write"`.
- **Required Milestone 1 Prompt**:
  - Mandate using `file_operation` with `operation: "patch"` for incremental modifications/fixes instead of doing full file rewrites.

---

## 3. Test Suite Design for Milestone 1

We design 4 concrete test cases to be added to `backend/test_file_operations.py` (or a dedicated test module `backend/test_patch_operations.py`).

### Test Case 1: `file_operation` Patch Success (Replacing Target Block)
- **Function Name**: `test_patch_file_success()`
- **Setup**: Create a Python file `test_patch_success.py` in workspace:
  ```python
  def greet():
      msg = "Hello World"
      print(msg)
  ```
- **Execution**:
  ```python
  patch_payload = json.dumps({
      "target": 'msg = "Hello World"',
      "replacement": 'msg = "Hello Milestone 1"'
  })
  result = file_operation(operation="patch", path="test_patch_success.py", content=patch_payload)
  ```
- **Assertions**:
  - `result` contains success confirmation (e.g. `"successfully patched"` or does not start with `"Error"`).
  - Reading `test_patch_success.py` reveals updated content: `msg = "Hello Milestone 1"`.
  - `ast.parse()` on updated file content succeeds without syntax errors.

### Test Case 2: Missing Target Error Detailing Line Numbers
- **Function Name**: `test_patch_file_missing_target()`
- **Setup**: Create a file `test_patch_missing.py` with 5 lines of code:
  ```python
  line 1
  line 2
  line 3
  line 4
  line 5
  ```
- **Execution**:
  ```python
  patch_payload = json.dumps({
      "target": "non_existent_target_string",
      "replacement": "replacement_string"
  })
  result = file_operation(operation="patch", path="test_patch_missing.py", content=patch_payload)
  ```
- **Assertions**:
  - `result` starts with `"Error"` or contains explicit error notification.
  - `result` contains `"non_existent_target_string"` and line information (e.g., `"not found in file test_patch_missing.py (scanned 5 lines)"` or line details).
  - File content of `test_patch_missing.py` remains unchanged.

### Test Case 3: Python AST Validation Failure on Invalid Syntax
- **Function Name**: `test_patch_file_invalid_ast()`
- **Setup**: Create a valid Python file `test_patch_ast.py`:
  ```python
  def valid_function():
      return 42
  ```
- **Execution**:
  ```python
  patch_payload = json.dumps({
      "target": "return 42",
      "replacement": "def broken_syntax(:"
  })
  result = file_operation(operation="patch", path="test_patch_ast.py", content=patch_payload)
  ```
- **Assertions**:
  - `result` contains `"Syntax error"` or `"SyntaxError"` detailing syntax invalidity.
  - File content of `test_patch_ast.py` remains completely UNCHANGED (`return 42`).

### Test Case 4: CodeAgent System Prompt Verification
- **Function Name**: `test_code_agent_prompt_patch_instruction()`
- **Setup**: Import `CodeAgent` from `agents.specialized_agents`.
- **Execution**:
  ```python
  agent = CodeAgent()
  prompt = agent.system_prompt
  ```
- **Assertions**:
  - `"patch"` is in `prompt.lower()`.
  - Prompt contains instruction regarding `file_operation` with `operation: "patch"`.

---

## 4. Proposed Code Code snippet for `backend/test_file_operations.py`

Below is the concrete test implementation snippet ready for inclusion into `backend/test_file_operations.py`:

```python
import json
import ast
from agents.tools import file_operation, write_file_content, read_file_content
from agents.specialized_agents import CodeAgent

def test_patch_file_success():
    """Test 1: Successful patch operation replacing target block"""
    print_section("Testing Patch File Success")
    initial_code = "def calc():\n    val = 10\n    return val\n"
    write_file_content("test_patch_success.py", initial_code)
    
    payload = json.dumps({
        "target": "val = 10",
        "replacement": "val = 20"
    })
    res = file_operation(operation="patch", path="test_patch_success.py", content=payload)
    print(f"Result: {res}")
    
    content = read_file_content("test_patch_success.py")
    assert "val = 20" in content, "Target block was not replaced"
    assert "Error" not in res, "Patch operation returned error"
    print("✓ Patch file success verified!")
    return True

def test_patch_file_missing_target():
    """Test 2: Missing target error detailing line numbers"""
    print_section("Testing Patch Missing Target Error")
    initial_code = "line 1\nline 2\nline 3\n"
    write_file_content("test_patch_missing.py", initial_code)
    
    payload = json.dumps({
        "target": "non_existent_line",
        "replacement": "replaced_line"
    })
    res = file_operation(operation="patch", path="test_patch_missing.py", content=payload)
    print(f"Result: {res}")
    
    content = read_file_content("test_patch_missing.py")
    assert content == initial_code, "File content modified when target missing"
    assert "Error" in res or "not found" in res.lower(), "Expected error message not returned"
    assert "line" in res.lower(), "Error message missing line number details"
    print("✓ Missing target error verified!")
    return True

def test_patch_file_invalid_ast():
    """Test 3: Python AST validation failure on invalid syntax"""
    print_section("Testing AST Validation Failure")
    initial_code = "def valid():\n    return True\n"
    write_file_content("test_patch_ast.py", initial_code)
    
    payload = json.dumps({
        "target": "return True",
        "replacement": "def broken(:"
    })
    res = file_operation(operation="patch", path="test_patch_ast.py", content=payload)
    print(f"Result: {res}")
    
    content = read_file_content("test_patch_ast.py")
    assert content == initial_code, "File modified despite invalid AST syntax!"
    assert "syntax" in res.lower(), "Expected syntax error response"
    print("✓ AST validation failure verified!")
    return True

def test_code_agent_prompt_patch_instruction():
    """Test 4: CodeAgent prompt content verification"""
    print_section("Testing CodeAgent System Prompt Patch Instruction")
    agent = CodeAgent()
    prompt = agent.system_prompt
    assert "patch" in prompt.lower(), "CodeAgent prompt does not contain 'patch' operation instructions"
    print("✓ CodeAgent prompt patch instruction verified!")
    return True
```

---

## 5. Test Runner Execution Commands

Tests can be executed in two ways:

1. **Via Pytest**:
   ```powershell
   pytest backend/test_file_operations.py
   ```
   Or explicitly running module:
   ```powershell
   python -m pytest backend/test_file_operations.py -v
   ```

2. **Via Standalone Script**:
   ```powershell
   python backend/test_file_operations.py
   ```
