# Analysis Report: Specialized Business Agent & CSV Tool Architecture (Milestone M2)

## Executive Summary
This analysis details the architecture of specialized agents and tool definitions in the AI agent framework (`backend/agents/specialized_agents.py` and `backend/agents/tools.py`). It formulates the exact implementation strategy for introducing the `BusinessAgent` class and the `csv_sheet_operation` tool for Milestone M2.

---

## 1. Analysis of Specialized Agents Architecture (`backend/agents/specialized_agents.py`)

### 1.1 Base Agent Class (`BaseSpecializedAgent`)
All specialized agents inherit from `BaseSpecializedAgent` (lines 224-406).
- **Initialization**:
  - Sets `name`, `agent_type`, `system_prompt`, `model_name`, and `ollama_base_url`.
  - Instantiates `SafeChatOllama` with temperature `0.2` and timeout `300`.
  - Tool Loading: Calls `get_tools_by_names(custom_tools)` if explicit tool names are passed, or `get_tools_for_agent(agent_type)` from `tools.py`.
- **ReAct Prompt Construction**:
  - Escapes curly braces in `system_prompt` (`system_prompt.replace("{", "{{").replace("}", "}}")`).
  - Constructs standard LangChain ReAct prompt template featuring structured thought blocks:
    - `[Analyze Constraint]` -> `[Identify Tool]` -> `[Predict Outcome]`.
  - Injects available tools (`{tools}`), tool names (`{tool_names}`), anti-loop guidelines, and chat history (`{chat_history}`).
- **Execution Engine**:
  - Wraps `SafeChatOllama` LLM and tools in `create_react_agent` using `RobustReActParser`.
  - Instantiates `AgentExecutor` with `max_iterations=50` and `max_execution_time=300`.
- **Capability Metadata**:
  - Method `get_capabilities()` returns a dictionary:
    ```python
    {
        "name": self.name,
        "type": self.agent_type,
        "tools": [tool.name for tool in self.tools],
        "description": self.system_prompt[:200]
    }
    ```

### 1.2 Agent Registration & Instantiation
- **`SPECIALIZED_AGENTS` Registry** (lines 703-707):
  ```python
  SPECIALIZED_AGENTS = {
      "code": CodeAgent,
      "research": ResearchAgent,
      "analysis": AnalysisAgent,
  }
  ```
- **Factory Function `create_specialized_agent`** (lines 709-733):
  - Checks if `agent_type` is present in `SPECIALIZED_AGENTS`. If found, instantiates and returns `SPECIALIZED_AGENTS[agent_type](model_name, ollama_base_url)`.
  - Fallback: Queries SQLite database (`AgentModel`) for custom agent definitions and instantiates `CustomSpecializedAgent`.
- **Integration with `orchestrator.get_available_agents()`**:
  - In `backend/agents/orchestrator.py` (lines 682-688):
    ```python
    def get_available_agents(self) -> List[Dict[str, Any]]:
        agents = []
        for agent_type, agent_class in SPECIALIZED_AGENTS.items():
            agent = agent_class(self.model_name, self.ollama_base_url)
            agents.append(agent.get_capabilities())
        return agents
    ```
  - Simply adding `"business": BusinessAgent` to `SPECIALIZED_AGENTS` automatically exposes `BusinessAgent` capabilities via the orchestrator API.

### 1.3 Existing Specialized Subclasses
1. **`CodeAgent`** (lines 408-540):
   - Agent type: `"code"`.
   - System prompt focuses on code creation/fixing, file safety, modular project architecture, complete non-truncated code, and deep quality auditing.
   - Core tools: `file_operation`, `recursive_list`, `grep_search`, `create_project`, `execute_terminal`, `schedule_task`.
   - Additional methods: `generate_app`, `fix_file`.
2. **`ResearchAgent`** (lines 541-593):
   - Agent type: `"research"`.
   - System prompt focuses on information gathering, web searching, summarizing documents, citing sources.
   - Core tools: `web_search`, `summarize_text`.
   - Additional method: `research_topic`.
3. **`AnalysisAgent`** (lines 594-686):
   - Agent type: `"analysis"`.
   - System prompt focuses on code analysis, bug identification, security review, performance optimization, file analysis with structured reporting (`ERRORS FOUND`, `FIXES REQUIRED`, `SEVERITY`).
   - Core tools: `analyze_code`, `file_operation`.
   - Additional methods: `analyze_code`, `analyze_file`.

---

## 2. Analysis of Tool Definitions & Security Architecture (`backend/agents/tools.py`)

### 2.1 Tool Structure & Parsing Pipeline
- Tools are declared either using the `@tool` decorator or `StructuredTool.from_function(...)`.
- `safe_parse_input(x: Any) -> Dict[str, Any]` (lines 225-260):
  - Handles string vs dict action inputs from LLMs.
  - Strips markdown formatting (` ```json ... ``` `).
  - Uses `extract_first_json` and `robust_parse_json_fields` as fallback parsing when LLMs output trailing/malformed text.

### 2.2 Path Safety & Interactive Permissions (`check_and_request_permission`)
- `check_and_request_permission(path: str) -> bool` (lines 21-50):
  1. Resolves path to absolute path `abs_path = os.path.abspath(path)`.
  2. Calls `is_safe_path(abs_path)`. If `True` (inside workspace `AGENT_WORKSPACE_DIR` or whitelisted path), access is granted immediately.
  3. If not in a safe path, retrieves context `current_agent_context.get()`.
  4. If `queue` and `loop` exist (interactive session), calls `register_and_wait_for_permission(session_id, abs_path, queue, loop)` to request runtime permission from user.
  5. Returns boolean `granted`.
- Standard File Access Pattern in `tools.py`:
  - Path normalization:
    ```python
    if not os.path.isabs(path) or path.startswith('/') or path.startswith('\\'):
        rel_path = path.lstrip('/\\')
        path = get_workspace_path(rel_path)
    ```
  - Safety verification:
    ```python
    if not check_and_request_permission(path):
        return f"Error: Access denied. Path must be whitelisted: {path}"
    ```
  - Extension check:
    ```python
    if not is_allowed_extension(path):
        return f"Error: File extension not allowed. File: {path}"
    ```

### 2.3 Tool Registries
- `AGENT_TOOLS`: Maps agent types (`"code"`, `"research"`, `"analysis"`) to factory functions returning lists of `StructuredTool` instances.
- `get_tools_for_agent(agent_type: str)`: Filters `AGENT_TOOLS[agent_type]()` against configured enabled tools.
- `get_tools_by_names(tool_names: List[str])`: Looks up tools by name across all system tools.

---

## 3. Implementation Strategy for `BusinessAgent`

### 3.1 Class Specification
- Inherits from `BaseSpecializedAgent` in `backend/agents/specialized_agents.py`.
- Signature:
  ```python
  class BusinessAgent(BaseSpecializedAgent):
      """Agent specialized in business planning, financial modeling, spreadsheet layouts, math calculations, and strategy reports"""
      def __init__(self, model_name: str = DEFAULT_MAIN_MODEL, ollama_base_url: str = "http://localhost:11434"):
          ...
  ```

### 3.2 System Prompt Design
```python
system_prompt = f"""You are a Business Agent specialized in business strategy, financial modeling, spreadsheet creation, math calculations, and market analysis.

{get_workspace_instructions()}

Your capabilities:
- Create business plans, market research analysis, and strategic growth reports
- Build financial models, revenue projections, profit margin calculations, and unit economics
- Generate and manipulate CSV spreadsheets for budget tracking, balance sheets, and financial statements
- Perform accurate mathematical and business metrics calculations
- Format structured reports and spreadsheet layouts cleanly

CRITICAL RULES FOR TOOL USAGE:
1. For creating, updating, or reading spreadsheet data, ALWAYS call the `csv_sheet_operation` tool.
2. For writing detailed strategic reports or markdown documents, call the `file_operation` tool.
3. When providing financial models or calculations, clearly show assumptions, formulas, and tabular summaries in your Final Answer.

Tools YOU MUST USE:
1. csv_sheet_operation - Read, write, or append CSV spreadsheet data
   To WRITE a sheet: {{"operation": "write", "path": "financials.csv", "data": [["Header1", "Header2"], ["Val1", "Val2"]]}}
   To READ a sheet:  {{"operation": "read", "path": "financials.csv"}}
   To APPEND rows:   {{"operation": "append", "path": "financials.csv", "data": [["Row1Val1", "Row1Val2"]]}}
2. file_operation - READ, WRITE, or LIST text/markdown business reports in workspace
"""
```

### 3.3 Helper Methods
- `generate_business_plan(self, requirements: str, ...)`: Returns structured response dict with type `"business_plan"`.
- `create_financial_model(self, model_specs: str, ...)`: Returns structured response dict with type `"financial_model"`.

### 3.4 Registry Updates
Add `"business": BusinessAgent` to `SPECIALIZED_AGENTS` in `backend/agents/specialized_agents.py`.

---

## 4. Implementation Strategy for `csv_sheet_operation` Tool

### 4.1 Function Specification
```python
def csv_sheet_operation(operation: str, path: str, data: Optional[List[List[Any]]] = None) -> str:
    """Perform CSV spreadsheet operations (write, read, append) in workspace safely"""
```

### 4.2 Detailed Logic Breakdown

1. **Path Resolution & Security Check**:
   ```python
   if not os.path.isabs(path) or path.startswith('/') or path.startswith('\\'):
       rel_path = path.lstrip('/\\')
       path = get_workspace_path(rel_path)

   if not check_and_request_permission(path):
       return f"Error: Access denied. Path must be whitelisted: {path}"

   if not is_allowed_extension(path):
       return f"Error: File extension not allowed. File: {path}"
   ```

2. **Data Parsing & Resiliency**:
   If `data` is provided as a string (due to LLM formatting):
   ```python
   if isinstance(data, str):
       try:
           import json
           data = json.loads(data)
       except Exception:
           try:
               import ast
               data = ast.literal_eval(data)
           except Exception:
               return "Error: Invalid data format for CSV operation. Must be a 2D list of rows."
   ```

3. **Operation Handlers**:
   - **`operation == "read"`**:
     - Check file existence `os.path.exists(path)`.
     - Check file size vs `MAX_FILE_SIZE`.
     - Open file with `csv.reader` (encoding utf-8).
     - Format output as markdown table or tabular preview detailing total row count and column headers.
   - **`operation == "write"`**:
     - Ensure `data` is present and valid list of lists.
     - Create parent directories with `os.makedirs(os.path.dirname(path), exist_ok=True)` if applicable.
     - Open file in `'w'` mode (`newline=''`, `encoding='utf-8'`).
     - Write rows using `csv.writer(f).writerows(data)`.
     - Return success status string with relative path, full path, row count, and column count.
   - **`operation == "append"`**:
     - Ensure `data` is present and valid list of lists.
     - Open file in `'a'` mode (`newline=''`, `encoding='utf-8'`).
     - Write rows using `csv.writer(f).writerows(data)`.
     - Return success status string with count of appended rows.
   - **Invalid operation**:
     - Return error message `Error: Unknown operation '{operation}'. Supported operations: 'write', 'read', 'append'`.

### 4.3 Tool Definition & Registration in `tools.py`
1. Define `get_business_agent_tools() -> List[StructuredTool]`:
   ```python
   def get_business_agent_tools() -> List[StructuredTool]:
       """Get tools for Business Agent"""
       return [
           StructuredTool.from_function(
               name="csv_sheet_operation",
               func=lambda x: csv_sheet_operation(
                   safe_parse_input(x).get("operation", "read"),
                   safe_parse_input(x).get("path", ""),
                   safe_parse_input(x).get("data", None)
               ),
               description="Perform CSV spreadsheet operations in workspace. Operations: 'write', 'read', 'append'. Input should be a dict with 'operation' ('write'/'read'/'append'), 'path' (CSV file path), and optional 'data' (2D array of rows for write/append)."
           ),
           StructuredTool.from_function(
               name="file_operation",
               func=lambda x: file_operation(
                   safe_parse_input(x).get("operation", "read"),
                   safe_parse_input(x).get("path", ""),
                   safe_parse_input(x).get("content", "")
               ),
               description="Perform file operations in workspace (read, write business strategy reports). Input should be a dict with 'operation', 'path', and optional 'content'."
           ),
       ]
   ```
2. Update `AGENT_TOOLS`:
   ```python
   AGENT_TOOLS = {
       "code": get_code_agent_tools,
       "research": get_research_agent_tools,
       "analysis": get_analysis_agent_tools,
       "business": get_business_agent_tools,
   }
   ```
3. Add `csv_sheet_operation` to `get_tools_by_names` list of all system tools.

---

## 5. Downstream Integration Notes
- **Orchestrator (`backend/agents/orchestrator.py`)**:
  - Update system prompt to list Business Agent for business strategy, financial modeling, spreadsheets, unit economics.
  - Update `_analyze_request` keyword loop to include business-related keywords (`"business"`, `"plan"`, `"financial"`, `"model"`, `"revenue"`, `"budget"`, `"excel"`, `"csv"`, `"sheet"`).
- **Frontend (`frontend/src/components/MultiAgentHub.tsx`)**:
  - Add `"business"` to agent selector option list (`['code', 'research', 'analysis', 'business']`).
  - Configure direct selector tool execution mapping for `csv_sheet_operation`.
