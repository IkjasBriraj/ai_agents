## 2026-07-21T12:56:02Z
<USER_REQUEST>
MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work.

You are Worker M2-1. Your working directory is `d:\learning\code\ai_agents\.agents\teamwork_preview_worker_m2_1`.
Read the analysis reports and soft handoffs from the Explorers:
- `d:\learning\code\ai_agents\.agents\teamwork_preview_explorer_m2_1\analysis.md`
- `d:\learning\code\ai_agents\.agents\teamwork_preview_explorer_m2_1\handoff.md`
- `d:\learning\code\ai_agents\.agents\teamwork_preview_explorer_m2_2\analysis.md`
- `d:\learning\code\ai_agents\.agents\teamwork_preview_explorer_m2_2\handoff.md`
- `d:\learning\code\ai_agents\.agents\teamwork_preview_explorer_m2_3\analysis.md`
- `d:\learning\code\ai_agents\.agents\teamwork_preview_explorer_m2_3\handoff.md`

Your tasks:
1. `backend/agents/specialized_agents.py`:
   - Add `BusinessAgent(BaseSpecializedAgent)` subclass with system prompt specialized in business planning, financial modeling, spreadsheet layouts, math calculations, strategy reports.
   - Register `"business": BusinessAgent` in `SPECIALIZED_AGENTS`.
2. `backend/agents/tools.py`:
   - Implement `csv_sheet_operation(operation: str, path: str, data: Optional[List[List[Any]]] = None) -> str` supporting `write`, `read`, `append` operations.
   - Ensure `check_and_request_permission(path)` is called before file access.
   - Define `get_business_agent_tools()` function and register `"business": get_business_agent_tools` in `AGENT_TOOLS`.
   - Ensure `csv_sheet_operation` is included in `get_tools_by_names`.
3. `backend/agents/orchestrator.py`:
   - Add BusinessAgent description and routing rules to orchestrator system prompt.
   - Add `business_keywords` check and `elif is_business_request:` branch in `_analyze_request`.
   - Update fallback prompt and `valid_agent` list in `_analyze_request` to include `"business"`.
4. `frontend/src/components/MultiAgentHub.tsx`:
   - Add `"business"` to agent selector list `['code', 'research', 'analysis', 'business']`.
   - Update UI grid classes if needed (`grid-cols-4`).
   - Handle default tool routing for `"business"` to `csv_sheet_operation`.
5. Run build/test verification:
   - Execute pytest on `backend/test_multi_agent.py` or run Python verification scripts to ensure `BusinessAgent` and `csv_sheet_operation` work without errors.
   - Document build/test commands and results in your handoff report.

Write your report to `d:\learning\code\ai_agents\.agents\teamwork_preview_worker_m2_1\changes.md` and handoff to `d:\learning\code\ai_agents\.agents\teamwork_preview_worker_m2_1\handoff.md`.
Send a message back to parent conversation ID `3bbad57e-9a78-4c7f-9393-cb61462fe4ce` when complete.
</USER_REQUEST>
