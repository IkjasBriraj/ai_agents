# Scope: Milestone 1 - Incremental Code Modifiers (R1)

## Mission
Implement surgical file patch operations, Python AST validation, and CodeAgent prompt updates.

## Requirements Reference
- Path to User Request: `d:\learning\code\ai_agents\.agents\orchestrator\ORIGINAL_REQUEST.md`
- Path to Global Architecture: `d:\learning\code\ai_agents\.agents\orchestrator\PROJECT.md`

## Targeted Files
1. `backend/agents/tools.py`:
   - Expand `file_operation` to support `operation: "patch"`.
   - Parse `content` argument as JSON string with `target` and `replacement`.
   - Perform exact string substitution of first occurrence of `target`. If `target` is not found, return clear error list with line details.
   - For `.py` files, validate updated content via `ast.parse` before writing to disk. Return syntax error message without saving file if syntax is invalid.
2. `backend/agents/specialized_agents.py`:
   - Update `CodeAgent` system prompt to instruct utilizing `file_operation` with `operation: "patch"` instead of full file rewrites for small fixes/updates.

## Acceptance Criteria Verification
- `file_operation(operation="patch", path="test.py", content='{"target": "def old(): pass", "replacement": "def old(): print(\\\"new\\\")"}')` replaces target code block.
- Invalid Python syntax patch returns syntax error message and does NOT modify file.
- Missing target string returns descriptive error indicating target not found.
