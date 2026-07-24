# Soft Handoff Report: Specialized Business Agent & CSV Tool Strategy

## 1. Observation
- **`backend/agents/specialized_agents.py`**:
  - Line 224: `BaseSpecializedAgent` defines common agent lifecycle (LLM initialization via `SafeChatOllama`, tool binding, ReAct prompt creation with `PromptTemplate`, parser initialization with `RobustReActParser`, execution via `AgentExecutor`).
  - Lines 408, 541, 594: `CodeAgent`, `ResearchAgent`, `AnalysisAgent` subclass `BaseSpecializedAgent`, passing specific `name`, `agent_type`, and `system_prompt`.
  - Line 703: `SPECIALIZED_AGENTS = {"code": CodeAgent, "research": ResearchAgent, "analysis": AnalysisAgent}` controls built-in agent registration.
  - Line 709: `create_specialized_agent(agent_type, ...)` checks `SPECIALIZED_AGENTS` dictionary.
- **`backend/agents/orchestrator.py`**:
  - Line 682: `get_available_agents(self)` iterates over `SPECIALIZED_AGENTS.items()` and calls `agent.get_capabilities()`.
- **`backend/agents/tools.py`**:
  - Line 21: `check_and_request_permission(path)` verifies if `abs_path` is safe via `is_safe_path` or requests interactive user permission via `current_agent_context`.
  - Lines 350, 383, 517: `read_file_content`, `write_file_content`, and `file_operation` normalize paths using `get_workspace_path`, check permissions via `check_and_request_permission(path)`, and validate extensions via `is_allowed_extension(path)`.
  - Line 909: `AGENT_TOOLS` maps agent keys (`"code"`, `"research"`, `"analysis"`) to tool getter functions.
  - Line 930: `get_tools_by_names` aggregates all system tools for dynamic lookup.

## 2. Logic Chain
1. **Agent Registration Pattern**: `BaseSpecializedAgent` provides all agent execution mechanics. Creating `BusinessAgent` requires defining `class BusinessAgent(BaseSpecializedAgent)` with a system prompt tailored for business planning, financial modeling, spreadsheet layouts, math calculations, and strategy reports, and adding `"business": BusinessAgent` to `SPECIALIZED_AGENTS`.
2. **Auto-Discovery by Orchestrator**: Because `orchestrator.get_available_agents()` dynamically queries `SPECIALIZED_AGENTS.items()`, registering `BusinessAgent` in `SPECIALIZED_AGENTS` automatically exposes its capabilities to the orchestrator API.
3. **Tool Security Standard**: All workspace I/O functions in `tools.py` enforce `check_and_request_permission(path)` and `is_allowed_extension(path)`. `csv_sheet_operation` can follow this exact pattern.
4. **CSV Tool Design**: `csv_sheet_operation(operation, path, data)` needs to support `"write"`, `"read"`, and `"append"` using Python's built-in `csv` module (`csv.writer`, `csv.reader`). Wrapping it in `StructuredTool.from_function` within `get_business_agent_tools()` and registering it in `AGENT_TOOLS["business"]` makes it fully available to `BusinessAgent` and sub-agent delegates.

## 3. Caveats
- Read-only investigation constraint: No code changes were executed during this turn.
- Frontend implementation (`frontend/src/components/MultiAgentHub.tsx`) and backend orchestrator routing (`backend/agents/orchestrator.py`) were analyzed at the strategy level; exact line modifications for those files will be completed by the Implementer agent.

## 4. Conclusion
The implementation strategy for `BusinessAgent` and `csv_sheet_operation` is fully specified and matches all structural standards of `backend/agents/specialized_agents.py` and `backend/agents/tools.py`. The full analysis is available at `d:\learning\code\ai_agents\.agents\teamwork_preview_explorer_m2_1\analysis.md`.

## 5. Verification Method
- Execute agent capability check: `python -c "from backend.agents.specialized_agents import SPECIALIZED_AGENTS, create_specialized_agent; print(list(SPECIALIZED_AGENTS.keys()))"`
- Run test script: `python backend/test_multi_agent.py`
- Inspect code files for presence of `BusinessAgent` and `csv_sheet_operation`.

## 6. Remaining Work (Soft Handoff for Implementer)
1. **`backend/agents/specialized_agents.py`**:
   - Add `BusinessAgent(BaseSpecializedAgent)` subclass with specialized business system prompt and helper methods (`generate_business_plan`, `create_financial_model`).
   - Add `"business": BusinessAgent` to `SPECIALIZED_AGENTS` dictionary.
2. **`backend/agents/tools.py`**:
   - Add `csv_sheet_operation(operation: str, path: str, data: Optional[List[List[Any]]] = None) -> str` supporting `write`, `read`, `append` and path permission check `check_and_request_permission(path)`.
   - Add `get_business_agent_tools()` function returning `csv_sheet_operation` and `file_operation`.
   - Add `"business": get_business_agent_tools` to `AGENT_TOOLS`.
   - Include `csv_sheet_operation` in `get_tools_by_names`.
3. **`backend/agents/orchestrator.py`**:
   - Update system prompt with business routing rules and `_analyze_request` keyword check loop.
4. **`frontend/src/components/MultiAgentHub.tsx`**:
   - Add `"business"` to agent selector list and configure default tool routing.
