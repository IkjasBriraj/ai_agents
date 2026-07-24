# Analysis Report: Orchestrator Routing & BusinessAgent Integration

## Executive Summary
This analysis investigates the routing rules, system prompt structure, and request analysis pipeline (`_analyze_request`) within `backend/agents/orchestrator.py`. It details how the Orchestrator agent routes user queries to specialized agents, and provides an exact implementation strategy for integrating the new `BusinessAgent` ("business") into `backend/agents/orchestrator.py` as required for Milestone 2.

---

## Section 1: Orchestrator Routing Rules & System Prompt Structure

### 1. System Prompt Architecture
The system prompt for the `OrchestratorAgent` is defined in its constructor `__init__` (`backend/agents/orchestrator.py:58-101`) as `self.system_prompt`. It serves as the primary instructions for the LLM when fallback routing is required.

The system prompt is structured into four main components:
1. **Role Definition & Agent Catalog**:
   - Defines the Orchestrator's role.
   - Lists available specialized agents with bullet points outlining their capabilities:
     - `1. CODE AGENT` (Software dev, code generation, terminal execution, file ops, scheduling)
     - `2. RESEARCH AGENT` (Information gathering, technology research, summaries)
     - `3. ANALYSIS AGENT` (Code quality analysis, bug identification, architecture review - read-only)
     - `4. ANALYZE AND FIX` (Chained execution: Analysis Agent first, then Code Agent fixes)
2. **Orchestrator Responsibilities**:
   - 1. Analyze request, 2. Determine agent, 3. Route request, 4. Return response.
3. **IMPORTANT ROUTING RULES**:
   - Intent-to-agent mapping rules:
     - `"analyze AND fix"`, `"find and fix errors"`, `"debug and fix"`, `"fix the errors in"` -> `"analyze_and_fix"`
     - Analyze/review code only (no fixing) -> `"analysis"`
     - Create, generate, or write new code -> `"code"`
     - Fix or update an existing file -> `"code"`
     - Run terminal/shell commands (npm, pip, python) -> `"code"`
     - Schedule task, set timer, periodic check -> `"code"`
4. **Strict Output Constraint**:
   - `Respond with ONLY the agent name: "code", "research", "analysis", "analyze_and_fix"`
   - `If the request is general or conversational, respond with "general".`

### 2. Dynamic Prompt Construction in `_analyze_request`
When the LLM fallback path is taken, `_analyze_request` (lines 180-196) dynamically constructs the context prompt:
```python
messages = [
    SystemMessage(content=self.system_prompt + history_prompt + semantic_prompt),
    HumanMessage(content=f"User request: {user_request}\n\nWhich agent should handle this? Respond with ONLY ONE of: code, research, analysis, analyze_and_fix, general")
]
```
- `history_prompt`: Injects formatted multi-turn conversation history retrieved via `multi_agent_memory.format_history(session_id)`.
- `semantic_prompt`: Injects relevant workspace file context from RAG vector memory via `multi_agent_memory.get_semantic_context(user_request)`.

---

## Section 2: Request Analysis Pipeline (`_analyze_request`)

The `_analyze_request` method (`backend/agents/orchestrator.py:142-233`) implements a hybrid deterministic keyword-filtering and LLM-fallback classification strategy.

```
                  ┌─────────────────────────────────┐
                  │          user_request           │
                  └────────────────┬────────────────┘
                                   │
                           [lower_case()]
                                   │
                ┌──────────────────┴──────────────────┐
                ▼                                     ▼
      [Keyword Pre-checks]                   [Keyword Pre-checks]
      - fix_keywords                         - terminal_keywords
      - schedule_keywords
                │                                     │
         Is fix request?                     Is terminal/schedule?
          ┌─────┴─────┐                         ┌─────┴─────┐
        YES           NO                      YES           NO
         │             │                       │             │
         ▼             └───────────┬───────────┘             │
  selected_agent =                 │                         │
 "analyze_and_fix"                 ▼                         │
                         selected_agent = "code"             │
                                                             ▼
                                                    [LLM Fallback Route]
                                                    - SystemMessage + Memory
                                                    - HumanMessage prompt
                                                    - SafeChatOllama invocation
                                                    - Substring Match Sanitization
```

### Step-by-Step Breakdown

1. **Input Extraction & Normalization (Lines 144-148)**:
   - Extracts `user_request` and `session_id`.
   - Normalizes input string to lowercase (`request_lower = user_request.lower()`).

2. **Deterministic Fast-Path Keyword Pre-checks (Lines 149-174)**:
   - **`fix_keywords`**: List of phrases (`"fix error"`, `"fix bug"`, `"debug and fix"`, `"find and fix"`, `"getting an error"`, etc.).
   - **`terminal_keywords`**: List of command execution phrases (`"run the app"`, `"start the server"`, `"npm run"`, `"pip install"`, etc.).
   - **`schedule_keywords`**: List of scheduling phrases (`"schedule"`, `"every day"`, `"periodically"`, `"loop"`, `"timer"`, etc.).

3. **Fast-Path Decision Tree (Lines 175-179)**:
   - `if is_fix_request:` -> `selected_agent = "analyze_and_fix"` (skips LLM call).
   - `elif is_terminal_request or is_schedule_request:` -> `selected_agent = "code"` (skips LLM call).
   - `else:` -> Proceed to LLM Fallback Routing.

4. **LLM Fallback Classification & Sanitization (Lines 180-209)**:
   - Invokes `self.llm.invoke(messages)`.
   - Strips and lowercases raw response (`selected_agent = response.content.strip().lower()`).
   - Runs sanitization loop over valid agent list `["analyze_and_fix", "code", "research", "analysis", "general"]`:
     ```python
     for valid_agent in ["analyze_and_fix", "code", "research", "analysis", "general"]:
         if valid_agent in selected_agent:
             selected_agent = valid_agent
             break
     else:
         selected_agent = "general"
     ```

5. **Post-routing Enhancements & State Mutators (Lines 211-233)**:
   - Appends software design guidelines if `selected_agent in ["code", "analyze_and_fix"]`.
   - Mutates state: `state["selected_agent"] = selected_agent`.
   - Records selection into graph state messages.
   - Pushes `agent_selection` event to async event queue if streaming context is provided.

---

## Section 3: Implementation Strategy for BusinessAgent Integration

To add `BusinessAgent` ("business") to the orchestrator routing rules and `_analyze_request` pipeline, the following precise changes must be applied to `backend/agents/orchestrator.py`.

### 1. System Prompt Modification (`self.system_prompt`)
In `OrchestratorAgent.__init__` (`backend/agents/orchestrator.py`), update `self.system_prompt`:
- Add `5. BUSINESS AGENT` capability description under `Available specialized agents:`.
- Add business routing rule under `IMPORTANT ROUTING RULES:`.
- Update final response constraint line to include `"business"`.

**Proposed System Prompt Patch**:
```text
Available specialized agents:
...
4. ANALYZE AND FIX - For requests that need BOTH analysis AND fixing:
   ...

5. BUSINESS AGENT - For business planning, financial modeling, and spreadsheet tasks:
   - Business strategy, business plans, and market analysis
   - Financial modeling, budgeting, revenue/profit calculations, and cash flow analysis
   - CSV data operations (reading, writing, appending spreadsheet data)
   - Math and financial summaries

IMPORTANT ROUTING RULES:
- If the user asks to "analyze AND fix", "find and fix errors", "debug and fix", "fix the errors in", "fix bugs in" -> respond with "analyze_and_fix"
- If the user asks for business planning, financial modeling, budgeting, strategy reports, or spreadsheet/CSV file operations (read, write, append CSV) -> respond with "business"
- If the user asks to only analyze or review code (no fixing) -> respond with "analysis"
...

Respond with ONLY the agent name: "code", "research", "analysis", "business", "analyze_and_fix"
If the request is general or conversational, respond with "general".
```

### 2. `_analyze_request` Keyword Pre-check Enhancement
In `_analyze_request` (`backend/agents/orchestrator.py:142-233`):
- Add `business_keywords` list containing business, financial, spreadsheet, and CSV keywords.
- Add `is_business_request` check.
- Update `if/elif/else` decision tree.

**Proposed Python Code Snippet**:
```python
        # Quick keyword-based pre-check for business patterns
        business_keywords = [
            "csv", "spreadsheet", "excel", "financial", "business plan",
            "business strategy", "revenue", "profit", "budget", "market analysis",
            "forecast", "financial model", "cash flow", "balance sheet",
            "csv_sheet_operation", "financial report", "sales analysis"
        ]
        is_business_request = any(kw in request_lower for kw in business_keywords)

        if is_fix_request:
            selected_agent = "analyze_and_fix"
        elif is_business_request:
            selected_agent = "business"
        elif is_terminal_request or is_schedule_request:
            selected_agent = "code"
        else:
            ...
```

### 3. LLM Fallback Prompt & Sanitization Loop Updates
- Update the prompt message in `HumanMessage`:
  `Which agent should handle this? Respond with ONLY ONE of: code, research, analysis, business, analyze_and_fix, general`
- Update the valid agents loop list to include `"business"`:
  ```python
  for valid_agent in ["analyze_and_fix", "business", "code", "research", "analysis", "general"]:
      if valid_agent in selected_agent:
          selected_agent = valid_agent
          break
  else:
      selected_agent = "general"
  ```

### 4. Downstream Execution Verification (`_execute_agent`)
When `selected_agent == "business"`, `_execute_agent` executes:
```python
agent = create_specialized_agent("business", agent_model, self.ollama_base_url)
```
Because `create_specialized_agent` checks `SPECIALIZED_AGENTS` dictionary (where `BusinessAgent` will be registered as `"business"`), `BusinessAgent` will be dynamically instantiated and invoked with `agent.process(user_request, context, ...)`.

---

## Verification Method
To verify the implementation once applied:
1. **Unit Test / Keyword Pre-check Verification**:
   - Query: `"Generate a revenue forecast and save to forecast.csv"`
   - Assert `_analyze_request` sets `selected_agent = "business"`.
2. **LLM Fallback Verification**:
   - Query: `"How should we price our new SaaS tier based on competitor margins?"`
   - Assert `_analyze_request` routes to `"business"`.
3. **Execution Integration Verification**:
   - Ensure `get_available_agents()` includes capability listing for `BusinessAgent`.
