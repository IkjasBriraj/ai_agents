# Project: Local AI Agents Application Enhancements

## Architecture
The local AI agents application is a full-stack system comprising a Python FastAPI backend (`backend/`) and a React/TypeScript Vite frontend (`frontend/`).

### System Component Interactions
1. **Backend Tools (`backend/agents/tools.py`)**:
   - `file_operation(operation, path, content, ...)`: Expanded to support `"patch"` operation with exact string substitution and AST validation (`ast.parse`) for Python files (`.py`).
   - `csv_sheet_operation(operation, path, data)`: New tool supporting `"write"`, `"read"`, `"append"` with workspace path safety verification via `check_and_request_permission(path)`.
2. **Specialized Agents (`backend/agents/specialized_agents.py`)**:
   - `CodeAgent`: System prompt updated to mandate using `file_operation` with `operation: "patch"` for incremental fixes instead of full rewrites.
   - `BusinessAgent`: New `BaseSpecializedAgent` subclass for business planning, financial modeling, spreadsheet layouts, math calculations, strategy reports.
3. **Orchestrator Routing (`backend/agents/orchestrator.py`)**:
   - System prompt updated with Business Agent routing rules.
   - `_analyze_request` keyword check updated to route business-related queries to Business Agent.
4. **API Endpoints (`backend/agents/api.py`)**:
   - `/agents/voice/transcribe`: POST endpoint accepting multipart upload `file: UploadFile` (WAV format), using `speech_recognition.Recognizer().recognize_google()` to return transcribed string JSON `{"text": "..."}` or error response.
5. **Frontend UI (`frontend/src/components/MultiAgentHub.tsx`)**:
   - Agent Selector: Included `"business"` in selector list (`['code', 'research', 'analysis', 'business']`) and default tool routing to `csv_sheet_operation`.
   - Voice Recording UI: Microphone icon button next to prompt textarea with recording state indicators (pulsing red dot, timer counter).
   - Audio Encoder: Browser-native AudioContext + ScriptProcessor/AudioWorklet PCM WAV encoder generating 16-bit mono 16kHz PCM WAV `Blob`.
   - Voice Integration: Submits WAV blob to `/agents/voice/transcribe` (or `/api/multi-agent/agents/voice/transcribe` via proxy) and populates prompt textarea.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Incremental Code Modifiers (R1) | `file_operation` patch in `tools.py`, AST check, `CodeAgent` prompt in `specialized_agents.py` | none | PLANNED |
| M2 | Business Agent & CSV Tool (R2) | `BusinessAgent` in `specialized_agents.py`, `csv_sheet_operation` in `tools.py`, routing in `orchestrator.py`, selector in `MultiAgentHub.tsx` | none | PLANNED |
| M3 | Voice STT & UI (R3) | `SpeechRecognition` in `requirements.txt`, `/agents/voice/transcribe` in `api.py`, mic UI & WAV encoder in `MultiAgentHub.tsx` | none | PLANNED |
| M4 | Integration & Acceptance (E2E Gate) | Verification of all R1-R3 acceptance criteria, E2E Test Suite Pass (Tiers 1-4), Tier 5 Adversarial Coverage Hardening | M1, M2, M3, E2E Track | PLANNED |

## Interface Contracts

### 1. `file_operation` Patch Operation
- **Call**: `file_operation(operation="patch", path=rel_or_abs_path, content=json_string)`
- **Content JSON**: `{"target": "<exact string to replace>", "replacement": "<new string>"}`
- **Behavior**: Finds first exact match of `target` in target file. Replaces with `replacement`.
- **Validation**: If target file is `.py`, parses updated code with `ast.parse`. If syntax error occurs, fails without altering file, returning syntax error string.
- **Error Handling**: If `target` is not found, returns error detailing target string and line matching attempt.

### 2. `csv_sheet_operation`
- **Signature**: `csv_sheet_operation(operation: str, path: str, data: Optional[List[List[Any]]] = None) -> str`
- **Operations**:
  - `"write"`: Writes 2D array `data` to CSV path.
  - `"read"`: Reads CSV file at `path` and returns formatted string representation.
  - `"append"`: Appends 2D array `data` rows to CSV file.
- **Safety**: Calls `check_and_request_permission(path)` before file access.

### 3. Voice Transcription API
- **Endpoint**: `POST /agents/voice/transcribe` (or frontend request path `/api/multi-agent/agents/voice/transcribe`)
- **Payload**: `multipart/form-data` with form field `file` containing WAV audio bytes.
- **Response**: `{"status": "success", "text": "transcribed string"}` or `{"status": "error", "message": "error details"}`

## Code Layout
- `backend/agents/tools.py`
- `backend/agents/specialized_agents.py`
- `backend/agents/orchestrator.py`
- `backend/agents/api.py`
- `backend/requirements.txt`
- `frontend/src/components/MultiAgentHub.tsx`
