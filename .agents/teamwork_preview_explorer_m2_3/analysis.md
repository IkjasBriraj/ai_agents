# Frontend Agent Selector & Tool Routing Analysis Report

## Executive Summary
This analysis details the exact frontend implementation structure within `frontend/src/components/MultiAgentHub.tsx` for integrating the new **Business Agent** (`"business"`) into the agent selector UI and configuring default tool routing to `csv_sheet_operation`.

---

## 1. Direct Agent Selector Definition
- **File**: `frontend/src/components/MultiAgentHub.tsx`
- **Location**: Line 1136 (within the `mode === 'direct'` Interaction Settings section)
- **Current Code**:
  ```tsx
  // Lines 1135-1147
  <div className="grid grid-cols-3 gap-2">
    {['code', 'research', 'analysis'].map(a => (
      <Button
        key={a}
        variant={selectedDirectAgent === a ? 'carbon' : 'outline'}
        onClick={() => setSelectedDirectAgent(a)}
        className="text-[10px] uppercase h-8"
      >
        {a}
      </Button>
    ))}
  </div>
  ```
- **State Variable**: Line 81
  ```tsx
  const [selectedDirectAgent, setSelectedDirectAgent] = useState<string>('code');
  ```
- **Observation**:
  - The direct selector button array is currently hardcoded as `['code', 'research', 'analysis']`.
  - The parent `div` uses `grid-cols-3`, which accommodates 3 agent selector buttons. Expanding the array to 4 items requires updating the CSS grid column layout to `grid-cols-4` (or `grid-cols-2 md:grid-cols-4`) to ensure proper UI alignment.

---

## 2. Default Tool Routing Architecture & Execution Flow

Frontend tool routing operates across two primary interaction modes: **Direct Mode** and **Orchestrated Streaming Mode**, as well as during **Thinking Sub-step Animations** and **Tool Execution Parsing**.

### A. Direct Mode Tool Routing & Execution
- **Location**: Lines 465-535 (`handleSendMessage`)
- **Routing Logic**:
  1. User selects an agent (`selectedDirectAgent`).
  2. Line 467: `setActiveRoutingAgent(selectedDirectAgent)` sets active agent.
  3. Lines 471-477: Sets default tool hint (`setActiveTool`):
     ```tsx
     if (selectedDirectAgent === 'code') {
       setActiveTool(userText.toLowerCase().includes('file') || userText.toLowerCase().includes('create') ? 'file_operation' : 'generate_code');
     } else if (selectedDirectAgent === 'research') {
       setActiveTool('web_search');
     } else if (selectedDirectAgent === 'analysis') {
       setActiveTool('analyze_code');
     }
     ```
  4. Line 480: Executes backend direct chat API call via `OllamaService.chatDirectAgent(selectedDirectAgent, userText)`.
  5. Line 483 & 494: Parses tool executions or applies fallback tool execution metadata:
     ```tsx
     toolName: selectedDirectAgent === 'code' ? 'generate_code' : selectedDirectAgent === 'research' ? 'web_search' : 'analyze_code'
     ```

### B. Orchestrated Streaming Mode Tool Routing
- **Location**: Lines 635-788 (`OllamaService.chatMultiAgentStream`)
- **Routing Logic**:
  1. Lines 638-656: SSE `agent_selection` event receives `event.agent.toLowerCase()`.
  2. Lines 645-651: Default tool hint assigned upon agent selection event:
     ```tsx
     if (currentAgent === 'code') {
       setActiveTool('file_operation');
     } else if (currentAgent === 'research') {
       setActiveTool('web_search');
     } else if (currentAgent === 'analysis') {
       setActiveTool('analyze_code');
     }
     ```
  3. Lines 657-675: Real-time `tool_start` and `tool_end` SSE events update active tool and action log state.

### C. Agent Thinking Sub-Step Thoughts Rotation
- **Location**: Lines 178-231
- **Logic**: Arrays (`codeAgentThoughts`, `researchAgentThoughts`, `analysisAgentThoughts`) rotate every 3 seconds via `setInterval` to display contextual status messages while waiting for model inference.

### D. Tool Execution Parsing (`parseToolExecutions`)
- **Location**: Lines 320-415
- **Logic**: Scans response text for tool execution signatures (e.g. `[SUCCESS] Created:`, Python execution tags) or falls back to agent-specific default tool descriptors.

---

## 3. Exact Implementation Strategy for Business Agent Integration

To add `"business"` to the agent selector and map default tool routing to `csv_sheet_operation`, the following exact code changes should be implemented in `frontend/src/components/MultiAgentHub.tsx`:

### Step 1: Update Direct Agent Selector Array & Grid Layout
- **Target File**: `frontend/src/components/MultiAgentHub.tsx`
- **Line 1135-1136**: Change grid layout and array:
  ```tsx
  // Before:
  <div className="grid grid-cols-3 gap-2">
    {['code', 'research', 'analysis'].map(a => (
  
  // After:
  <div className="grid grid-cols-4 gap-2">
    {['code', 'research', 'analysis', 'business'].map(a => (
  ```

### Step 2: Add Direct Mode Tool Routing & Fallback
- **Target File**: `frontend/src/components/MultiAgentHub.tsx`
- **Lines 470-477**: Add `business` tool hint logic:
  ```tsx
  if (selectedDirectAgent === 'code') {
    setActiveTool(userText.toLowerCase().includes('file') || userText.toLowerCase().includes('create') ? 'file_operation' : 'generate_code');
  } else if (selectedDirectAgent === 'research') {
    setActiveTool('web_search');
  } else if (selectedDirectAgent === 'analysis') {
    setActiveTool('analyze_code');
  } else if (selectedDirectAgent === 'business') {
    setActiveTool('csv_sheet_operation');
  }
  ```
- **Line 494**: Update fallback tool execution name:
  ```tsx
  toolName: selectedDirectAgent === 'code' ? 'generate_code' 
    : selectedDirectAgent === 'research' ? 'web_search' 
    : selectedDirectAgent === 'analysis' ? 'analyze_code' 
    : selectedDirectAgent === 'business' ? 'csv_sheet_operation' 
    : 'default_tool'
  ```

### Step 3: Add Orchestrated Mode Tool Hint Routing
- **Target File**: `frontend/src/components/MultiAgentHub.tsx`
- **Lines 645-651**: Add `business` tool hint mapping:
  ```tsx
  if (currentAgent === 'code') {
    setActiveTool('file_operation');
  } else if (currentAgent === 'research') {
    setActiveTool('web_search');
  } else if (currentAgent === 'analysis') {
    setActiveTool('analyze_code');
  } else if (currentAgent === 'business') {
    setActiveTool('csv_sheet_operation');
  }
  ```

### Step 4: Define Business Agent Thinking Thoughts & Selector
- **Target File**: `frontend/src/components/MultiAgentHub.tsx`
- **Lines 198+**: Add `businessAgentThoughts` array:
  ```tsx
  const businessAgentThoughts = [
    "Analyzing business requirements and financial data schemas...",
    "Validating spreadsheet formulas and CSV data structures...",
    "Preparing csv_sheet_operation tool payload (read/write/append)...",
    "Calculating budget summaries, projections, and financial metrics...",
    "Structuring business report and spreadsheet outputs..."
  ];
  ```
- **Lines 210-216**: Update `thoughts` array selection in `useEffect`:
  ```tsx
  const thoughts = activeRoutingAgent === 'research' 
    ? researchAgentThoughts 
    : activeRoutingAgent === 'analysis' 
      ? analysisAgentThoughts 
      : activeRoutingAgent === 'business'
        ? businessAgentThoughts
        : codeAgentThoughts;
  ```

### Step 5: Update Tool Execution Parser Fallbacks (`parseToolExecutions`)
- **Target File**: `frontend/src/components/MultiAgentHub.tsx`
- **Lines 405+**: Add business agent smart heuristic fallback:
  ```tsx
  if (agentUsed === 'business' || textLower.includes('business') || textLower.includes('csv') || textLower.includes('financial')) {
    tools.push({
      toolName: 'csv_sheet_operation',
      status: 'success',
      details: 'Executed CSV spreadsheet operation for business model data.'
    });
  }
  ```

### Step 6 (Optional UI Enhancement): Network Visualizer Integration
- **Target File**: `frontend/src/components/MultiAgentHub.tsx`
- **Lines 1025-1095**: Add Business Agent visual card to the Multi-Agent Core Network visualizer display box with tag `"CSV SHEET"` and icon (`TrendingUp` or `FileText`), ensuring complete visual representation across the UI.

---

## 4. Verification Plan
1. **Frontend Compilation / Build**: Run `npm run build` or `npm run type-check` (or Vite build) to verify TypeScript types compile cleanly.
2. **UI Verification**:
   - Confirm selector button for `"business"` appears alongside `code`, `research`, and `analysis`.
   - Confirm selecting `"business"` in direct mode sets `selectedDirectAgent` to `'business'`.
   - Confirm executing queries in direct mode or orchestrated mode displays `csv_sheet_operation` as active tool.
