## 2026-07-21T07:25:39Z
You are Worker 1 for Milestone 1 (Incremental Code Modifiers - R1).
Working directory: d:\learning\code\ai_agents\.agents\teamwork_preview_worker_m1_1

SCOPE DOCUMENT: d:\learning\code\ai_agents\.agents\sub_orch_m1\SCOPE.md
PROJECT DOCUMENT: d:\learning\code\ai_agents\.agents\orchestrator\PROJECT.md
EXPLORER 1 REPORT: d:\learning\code\ai_agents\.agents\teamwork_preview_explorer_m1_1\handoff.md
EXPLORER 2 REPORT: d:\learning\code\ai_agents\.agents\teamwork_preview_explorer_m1_2\handoff.md
EXPLORER 3 REPORT: d:\learning\code\ai_agents\.agents\teamwork_preview_explorer_m1_3\handoff.md

Your tasks:
1. In `backend/agents/tools.py`:
   - Create `patch_file_content(path: str, content: Any) -> str` supporting `operation: "patch"`.
   - Parse `content` as JSON `{"target": "...", "replacement": "..."}` (supporting both raw JSON string and parsed dict).
   - Read existing file content and check if `target` is present. If missing, return clear error detailing line numbers and line search context.
   - Replace ONLY the first occurrence of `target` in the file (`existing_content.replace(target, replacement, 1)`).
   - Perform AST validation (`ast.parse`) for `.py` files before writing to disk. Return syntax error message without saving file if syntax is invalid.
   - Route `elif operation == "patch": return patch_file_content(path, content)` in `file_operation`.
   - Update `FileOperationInput` schema and tool descriptions in `get_code_agent_tools` / `get_analysis_agent_tools`.
2. In `backend/agents/specialized_agents.py`:
   - Update `CodeAgent` system prompt, workflow instructions, and `fix_file` method to mandate using `file_operation` with `operation: "patch"` for localized fixes instead of full file rewrites.
3. In `backend/test_file_operations.py`:
   - Add comprehensive test functions for:
     - `test_patch_file_success`
     - `test_patch_file_missing_target`
     - `test_patch_file_invalid_ast`
     - `test_code_agent_prompt_patch_instruction`
4. Run build and test verification using `run_command` (e.g. `pytest backend/test_file_operations.py` or `python backend/test_file_operations.py`) and record full test results in your handoff report.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work.

Write your changes report to `d:\learning\code\ai_agents\.agents\teamwork_preview_worker_m1_1\changes.md` and handoff report to `d:\learning\code\ai_agents\.agents\teamwork_preview_worker_m1_1\handoff.md`.
Send a completion message back to parent orchestrator when complete.
