# Original User Request

## 2026-07-21T12:53:52Z

You are Sub-Orchestrator M1 for Milestone 1 (Incremental Code Modifiers - R1).
Your working directory is `d:\learning\code\ai_agents\.agents\sub_orch_m1`.
Read `d:\learning\code\ai_agents\.agents\sub_orch_m1\SCOPE.md`, `d:\learning\code\ai_agents\.agents\orchestrator\ORIGINAL_REQUEST.md`, and `d:\learning\code\ai_agents\.agents\orchestrator\PROJECT.md`.
Maintain `BRIEFING.md`, `progress.md`, and `SCOPE.md` in your working directory `d:\learning\code\ai_agents\.agents\sub_orch_m1`.
Your scope is:
1. Expand `file_operation` in `backend/agents/tools.py` to support `operation: "patch"`. Parse `content` as JSON `{"target": "...", "replacement": "..."}`. Exact string substitution of first occurrence of `target`. Return error detailing line numbers if target is missing.
2. Validate AST (`ast.parse`) for `.py` files before saving to disk. Return syntax error message without modifying file if syntax is invalid.
3. Update `CodeAgent` system prompt in `backend/agents/specialized_agents.py` to use `file_operation` with `operation: "patch"`.
Follow the Explorer -> Worker -> Reviewer -> Challenger -> Auditor cycle.
Mandatory warning for Worker: "DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work."
Run build & test checks (e.g. `pytest backend/test_file_operations.py` or worker verification).
Send a message with your handoff report to parent conversation ID `b73d6c76-cd71-4753-b907-931f5da9ad05` when complete.
