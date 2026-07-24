# Soft Handoff Report: BusinessAgent Orchestrator Routing Strategy

## 1. Observation
- **System Prompt Structure (`backend/agents/orchestrator.py:58-101`)**:
  - `self.system_prompt` lists four specialized agents (`CODE AGENT`, `RESEARCH AGENT`, `ANALYSIS AGENT`, `ANALYZE AND FIX`).
  - Contains `IMPORTANT ROUTING RULES:` mapping user intents to agent identifier strings.
  - Specifies output constraint: `Respond with ONLY the agent name: "code", "research", "analysis", "analyze_and_fix"`.
- **Request Analysis Logic (`backend/agents/orchestrator.py:142-233`)**:
  - `_analyze_request` checks `fix_keywords` (line 149), `terminal_keywords` (line 160), and `schedule_keywords` (line 166).
  - Decision tree at lines 175-179:
    ```python
    if is_fix_request:
        selected_agent = "analyze_and_fix"
    elif is_terminal_request or is_schedule_request:
        selected_agent = "code"
    ```
  - Fallback LLM prompt at line 195:
    `HumanMessage(content=f"User request: {user_request}\n\nWhich agent should handle this? Respond with ONLY ONE of: code, research, analysis, analyze_and_fix, general")`
  - Response sanitization loop at lines 203-207:
    `for valid_agent in ["analyze_and_fix", "code", "research", "analysis", "general"]:`
- **Agent Registry (`backend/agents/specialized_agents.py:703-707`)**:
  - `SPECIALIZED_AGENTS` dictionary maps agent names to classes (`"code"`, `"research"`, `"analysis"`).

## 2. Logic Chain
1. *From Observation 1*: `self.system_prompt` defines available specialized agents and explicit routing rules for the LLM. Adding `BusinessAgent` requires introducing item `5. BUSINESS AGENT`, adding a routing rule for business/financial/spreadsheet tasks, and updating the allowed agent names in the output constraint.
2. *From Observation 2*: `_analyze_request` uses deterministic keyword pre-checks before reaching the LLM fallback. Introducing `business_keywords` and an `elif is_business_request:` branch allows fast-path routing of business/financial/CSV queries to `"business"`.
3. *From Observation 2*: In the LLM fallback route within `_analyze_request`, the `HumanMessage` prompt and the `valid_agent` sanitization list enforce valid agent choices. Both must be updated to include `"business"`.
4. *From Observation 3*: Once `selected_agent` is set to `"business"`, `_execute_agent` calls `create_specialized_agent("business", ...)` which resolves `"business"` from `SPECIALIZED_AGENTS` when implemented.

## 3. Caveats
- Read-only investigation mode: No direct changes were made to `backend/agents/orchestrator.py` or `backend/agents/specialized_agents.py`. Implementation must be carried out by an implementer agent.
- Assumes `BusinessAgent` will be registered under key `"business"` in `SPECIALIZED_AGENTS` within `backend/agents/specialized_agents.py`.

## 4. Conclusion
Integrating `BusinessAgent` into `backend/agents/orchestrator.py` requires three localized modifications:
1. Updating `self.system_prompt` in `OrchestratorAgent.__init__` with Business Agent capabilities and routing rules.
2. Adding `business_keywords` pre-check and `elif is_business_request:` branch in `_analyze_request`.
3. Updating the LLM fallback `HumanMessage` prompt and `valid_agent` list in `_analyze_request` to include `"business"`.

## 5. Verification Method
- **Files to Inspect**: `backend/agents/orchestrator.py`
- **Validation**:
  - Test keyword matching by passing a request containing `"csv"` or `"financial"` to `_analyze_request` and verifying `selected_agent == "business"`.
  - Test LLM routing fallback for ambiguous business queries.

## 6. Remaining Work (Next Steps for Implementer)
1. Implement proposed system prompt updates, `business_keywords` pre-check, and `valid_agent` sanitization loop in `backend/agents/orchestrator.py`.
2. Ensure `BusinessAgent` is registered in `SPECIALIZED_AGENTS` in `backend/agents/specialized_agents.py`.
3. Run backend tests to verify request routing to `BusinessAgent`.
