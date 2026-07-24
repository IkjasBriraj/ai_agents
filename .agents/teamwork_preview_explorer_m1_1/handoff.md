# Handoff Report: `file_operation` Patch Operation Analysis (Milestone 1)

## 1. Observation

Direct observations from codebase inspection of `backend/agents/tools.py` and milestone scope documents:

1. **Existing `file_operation` Implementation (`backend/agents/tools.py` lines 517–527)**:
   ```python
   def file_operation(operation: str, path: str, content: str = "") -> str:
       """Perform file operations in workspace"""
       if operation == "read":
           return read_file_content(path)
       elif operation == "write":
           return write_file_content(path, content)
       elif operation == "list":
           return list_directory(path)
       else:
           return f"Error: Unknown operation: {operation}. Use 'read', 'write', or 'list'"
   ```
   *Observation*: Currently only handles `"read"`, `"write"`, and `"list"`. Does not support `"patch"`.

2. **Schema & Tool Descriptions (`backend/agents/tools.py`)**:
   - Lines 59–63 (`FileOperationInput`): `operation: str = Field(description="Operation: read, write, list")`.
   - Lines 829–837 (`get_code_agent_tools`): `description` lists `'read', 'write', 'list'`.
   - Lines 897–905 (`get_analysis_agent_tools`): `description` lists `'read', 'write'`.

3. **Existing Safety & Validation Patterns (`backend/agents/tools.py` lines 383–442)**:
   - `write_file_content` checks `get_workspace_path(path)`, `check_and_request_permission(path)`, `is_allowed_extension(path)`, `MAX_FILE_SIZE`, and for `.py` files calls `ast.parse(content)`.

4. **Scope Requirements (`.agents/sub_orch_m1/SCOPE.md` lines 11–15 & `.agents/orchestrator/PROJECT.md` lines 34–39)**:
   - Parse `content` as JSON string containing `target` and `replacement`.
   - Perform exact string substitution of first occurrence of `target`.
   - If `target` is missing, return a descriptive error detailing target string and line matching attempt.
   - For `.py` files, validate updated code with `ast.parse` before writing to disk; return syntax error message without modifying file if syntax is invalid.

---

## 2. Logic Chain

1. **From Obs 1 & Obs 4**: Since `file_operation` (lines 517–527) only dispatches `read`, `write`, and `list`, adding `operation: "patch"` requires defining a new `patch_file_content(path: str, content: str) -> str` function and adding an `elif operation == "patch":` branch to `file_operation`.
2. **From Obs 3 & Obs 4**: `patch_file_content` must adopt the workspace resolution (`get_workspace_path`), security checks (`check_and_request_permission`), extension checks (`is_allowed_extension`), and size limits (`MAX_FILE_SIZE`) used in `write_file_content` to maintain consistency across file tool operations.
3. **From Obs 4**: To replace exact code blocks without whole-file rewrites:
   - Parse `content` via `json.loads` (with fallback to `extract_first_json`).
   - Read the existing file content.
   - Verify `target in original_content`. If false, construct diagnostic error with line search details (line counts, target first line, exact/partial matching file line numbers).
   - If true, call `original_content.replace(target, replacement, 1)` to substitute ONLY the first occurrence.
   - Run `ast.parse(new_content)` for Python files (`.py`). If `SyntaxError` is raised, return the syntax error message immediately *before* calling `open(path, 'w')`.
4. **From Obs 2**: Updating `FileOperationInput` schema and `StructuredTool` descriptions ensures LLM tool calls and agent prompt validations recognize `"patch"` as a valid operation.

---

## 3. Caveats

1. **Read-Only Investigation Scope**: Explorer 1 was dispatched with read-only instructions. No files in `backend/` were altered during this step.
2. **`CodeAgent` System Prompt Update**: Prompt updates in `backend/agents/specialized_agents.py` are scoped as part of Milestone 1 Item 2 (separate task / implementation sub-step).

---

## 4. Conclusion

The technical strategy for expanding `file_operation` to support `operation: "patch"` is fully defined, documented, and ready for implementation. Implementation will require:
1. Adding `patch_file_content(path, content)` in `backend/agents/tools.py`.
2. Updating `file_operation` in `backend/agents/tools.py` to route `"patch"`.
3. Updating `FileOperationInput` and tool descriptions in `backend/agents/tools.py`.

The complete blueprint and proposed code are available in `d:\learning\code\ai_agents\.agents\teamwork_preview_explorer_m1_1\analysis.md`.

---

## 5. Verification Method

To independently verify the implementation once completed:

1. **Unit Test Execution**:
   - Run python test script verifying `file_operation(operation="patch", ...)`:
     ```bash
     python -m unittest backend/test_file_operations.py
     ```
2. **Acceptance Criteria Verification**:
   - **Patch Replacement**: Create a test file `test_patch.py` with content `def old(): pass`. Call `file_operation(operation="patch", path="test_patch.py", content='{"target": "def old(): pass", "replacement": "def old(): print(\\\"new\\\")"}')`. Verify file content changes to `def old(): print("new")`.
   - **Syntax Validation**: Call patch operation with invalid Python code (`replacement: "def invalid_syntax("`). Verify return message contains `Syntax validation failed` and `test_patch.py` remains unchanged.
   - **Missing Target Handling**: Call patch operation with non-existent target string. Verify return message contains `Error: Target string not found in file` along with line details.
3. **Invalidation Conditions**:
   - If `patch` writes syntactically invalid Python code to disk.
   - If `patch` replaces more than 1 occurrence of target string.
   - If `patch` fails when `content` is formatted with JSON escapes.
