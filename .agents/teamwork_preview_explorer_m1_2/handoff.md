# Handoff Report — Milestone 1: AST Validation & CodeAgent Prompt Updates

## 1. Observation
- **File Paths Inspected**:
  - `backend/agents/tools.py`: Contains `file_operation(operation, path, content)` at lines 517–527 and `write_file_content` at lines 383–442. Currently supports `read`, `write`, and `list` operations. Line 402 performs `ast.parse(content)` for `.py` files during `write_file_content`. Line 830 registers `file_operation` in `get_code_agent_tools()`.
  - `backend/agents/specialized_agents.py`: `CodeAgent` class defined at lines 408–483. Rule 2 in `CRITICAL RULES` (line 422) mandates full rewrites via `write` operation. `WORKFLOW FOR FIXING EXISTING FILES` (lines 469–474) and `CodeAgent.fix_file` (lines 515–538) instruct using `write` with complete file content.
  - `backend/test_file_operations.py`: Verified workspace file testing framework.
  - `SCOPE.md` & `PROJECT.md`: Define requirements for surgical `file_operation(operation="patch", path=..., content=json_string)` with target matching, AST validation (`ast.parse`), and prompt updates for `CodeAgent`.

- **Existing Tool Registrations & Signatures**:
  - `file_operation` tool signature: `(operation: str, path: str, content: str = "") -> str`.
  - `write_file_content` performs `ast.parse` for `.py` files, but no patch-specific string replacement helper function currently exists in `backend/agents/tools.py`.

---

## 2. Logic Chain
1. **Adding Surgical `patch` Operation**:
   - Creating a helper function `patch_file_content(path: str, content: Any)` in `backend/agents/tools.py` allows parsing a JSON string or dict payload containing `target` and `replacement`.
   - Dispatching `operation == "patch"` inside `file_operation` routes calls directly to `patch_file_content(path, content)`.

2. **AST Pre-Write Safeguard**:
   - In `patch_file_content`, target matching replaces the first occurrence (`existing_content.replace(target, replacement, 1)`).
   - Before opening the file in write mode (`open(path, 'w')`), `ast.parse(updated_content)` is called for `.py` files.
   - If `SyntaxError` is raised, it is caught in a `try...except SyntaxError` block, returning the error message string without modifying the file on disk. This enforces strict atomicity and prevents saving broken code.

3. **Target Missing Error Handling**:
   - If `target not in existing_content`, `patch_file_content` returns a descriptive error string detailing the missing target string (`f"Error: Target string not found in file: {path}. Target: {repr(target)}"`).

4. **CodeAgent System Prompt Adaptation**:
   - Updating `CodeAgent` system prompt in `backend/agents/specialized_agents.py` (Rule 2, Tool usage guide, fixing workflow, and `fix_file` method) instructs `CodeAgent` to use `file_operation` with `operation: "patch"` for localized modifications instead of overwriting full files with `write`.

---

## 3. Caveats
- **Multi-line JSON String Escaping in Tool Input**: LLM tool calls may format JSON strings with newline escapes (`\n`). `safe_parse_input` in `tools.py` handles unicode escapes, but robust JSON parsing (`json.loads` + `extract_first_json`) in `patch_file_content` is necessary to ensure stability.
- **Identical Target Duplication**: `replace(target, replacement, 1)` targets only the first match. If multiple identical blocks exist, `CodeAgent` must provide sufficient context lines around the target snippet.
- **Uninvestigated Area**: Milestone 2 (`csv_sheet_operation`) and Milestone 3 (Voice STT API) are out of scope for this milestone investigation.

---

## 4. Conclusion
The implementation design for Milestone 1 is completely mapped, fully specified, and ready for Worker execution:
1. `backend/agents/tools.py`: Implement `patch_file_content(path, content)` with JSON payload parsing, exact string substitution (`replace(..., 1)`), pre-write AST syntax validation (`ast.parse`), and update `file_operation` to route `operation == "patch"`.
2. `backend/agents/specialized_agents.py`: Update `CodeAgent` system prompt and `fix_file` method to prioritize `operation: "patch"` for surgical fixes.
3. Analysis and diffs documented in `d:\learning\code\ai_agents\.agents\teamwork_preview_explorer_m1_2\analysis.md`.

---

## 5. Verification Method
1. **Inspect Analysis Artifact**:
   - Read `d:\learning\code\ai_agents\.agents\teamwork_preview_explorer_m1_2\analysis.md`.
2. **Post-Implementation Test Command**:
   - Run unit tests: `pytest backend/test_file_operations.py` (or Python test runner).
   - Test `file_operation(operation="patch", path="test.py", content='{"target": "...", "replacement": "..."}')`.
   - Verify that invalid Python syntax returns syntax error string without altering disk file.
3. **Invalidation Conditions**:
   - If a syntax error patch modifies the file on disk.
   - If `operation="patch"` fails to parse valid JSON payloads with double/triple quotes.
