# Scope: Milestone 2 - Specialized Business Agent & CSV Tool (R2)

## Mission
Implement the BusinessAgent class, csv_sheet_operation tool, path permission checks, orchestrator routing rules, and frontend agent selector integration.

## Requirements Reference
- Path to User Request: `d:\learning\code\ai_agents\.agents\orchestrator\ORIGINAL_REQUEST.md`
- Path to Global Architecture: `d:\learning\code\ai_agents\.agents\orchestrator\PROJECT.md`

## Targeted Files
1. `backend/agents/specialized_agents.py`:
   - Add `BusinessAgent(BaseSpecializedAgent)` class with system prompt specialized in business planning, financial modeling, spreadsheet layouts, math calculations, strategy reports.
2. `backend/agents/tools.py`:
   - Create `csv_sheet_operation(operation: str, path: str, data: Optional[List[List[Any]]] = None) -> str`.
   - Support `operation == 'write'`, `'read'`, `'append'`.
   - Verify path safety via `check_and_request_permission(path)`.
3. `backend/agents/orchestrator.py`:
   - Add Business Agent to orchestrator system prompt routing rules and `_analyze_request` keyword check loop.
4. `frontend/src/components/MultiAgentHub.tsx`:
   - Add `"business"` to direct agent selector list (`['code', 'research', 'analysis', 'business']`).
   - Handle default tool routing to `csv_sheet_operation`.

## Acceptance Criteria Verification
- `BusinessAgent` loaded by `get_available_agents()` and displayed in frontend selector.
- Business queries routed to Business Agent by orchestrator.
- `csv_sheet_operation` creates and reads valid CSV files in workspace.
