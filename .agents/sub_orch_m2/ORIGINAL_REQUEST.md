# Original Request - Sub-Orchestrator M2

## 2026-07-21T12:53:52Z

You are Sub-Orchestrator M2 for Milestone 2 (Specialized Business Agent & CSV Tool - R2).
Your working directory is `d:\learning\code\ai_agents\.agents\sub_orch_m2`.
Read `d:\learning\code\ai_agents\.agents\sub_orch_m2\SCOPE.md`, `d:\learning\code\ai_agents\.agents\orchestrator\ORIGINAL_REQUEST.md`, and `d:\learning\code\ai_agents\.agents\orchestrator\PROJECT.md`.
Maintain `BRIEFING.md`, `progress.md`, and `SCOPE.md` in `d:\learning\code\ai_agents\.agents\sub_orch_m2`.
Your scope is:
1. Add `BusinessAgent(BaseSpecializedAgent)` class to `backend/agents/specialized_agents.py` with system prompt specialized in business planning, financial modeling, spreadsheet layouts, math calculations, strategy reports.
2. Create `csv_sheet_operation(operation: str, path: str, data: Optional[List[List[Any]]] = None) -> str` in `backend/agents/tools.py` (`write`, `read`, `append`), with `check_and_request_permission(path)`.
3. Add `BusinessAgent` to orchestrator routing rules system prompt and `_analyze_request` keyword check loop in `backend/agents/orchestrator.py`.
4. Add `"business"` to direct agent selector list in `frontend/src/components/MultiAgentHub.tsx` (`['code', 'research', 'analysis', 'business']`) and handle default tool routing to `csv_sheet_operation`.
Follow the Explorer -> Worker -> Reviewer -> Challenger -> Auditor cycle.
Mandatory warning for Worker: "DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work."
Run build & test checks (e.g. `pytest backend/test_multi_agent.py` or worker verification).
Send a message with your handoff report to parent conversation ID `b73d6c76-cd71-4753-b907-931f5da9ad05` when complete.
