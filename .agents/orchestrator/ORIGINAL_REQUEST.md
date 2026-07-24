# Original User Request

## 2026-07-21T12:52:45Z

Implement advanced capabilities in the local AI agents application, including incremental code modifications (`patch` operations), a specialized Business Agent with CSV spreadsheet tools, and a browser-native voice recording and local Speech-to-Text transcription feature.

Working directory: `d:\learning\code\ai_agents`
Integrity mode: development

## Requirements

### R1. Incremental Code Modifiers (Surgical File Edits)
- **Tool expansion:** Add support for a `"patch"` operation in the backend `file_operation` tool inside `backend/agents/tools.py`.
- **Patch Format:** The `patch` operation must parse its `content` argument as a JSON string containing `target` (the block of code to search for) and `replacement` (the new code to put in its place).
- **Substitution Logic:** It must perform an exact string substitution of the first occurrence of `target` in the file. If `target` is not found, the tool must return a clear error list detailing the exact lines it failed to match.
- **Validation:** When editing `.py` files, validate the parsed AST of the modified file (`ast.parse`) before saving to disk to prevent corrupting Python syntax.
- **Agent Prompts:** Update the `CodeAgent` system prompt in `backend/agents/specialized_agents.py` to instruct the agent to utilize `file_operation` with `operation: "patch"` instead of completely rewriting files for small fixes or updates.

### R2. Specialized Business Agent
- **Business Agent Definition:** Add a new `BusinessAgent(BaseSpecializedAgent)` class to `backend/agents/specialized_agents.py` with a system prompt specialized in business planning, financial modeling, spreadsheet layouts, math calculations, and strategy reports.
- **Spreadsheet Tool:** Create `csv_sheet_operation(operation: str, path: str, data: Optional[List[List[Any]]] = None) -> str` in `backend/agents/tools.py`:
  - `operation == 'write'`: Write a 2D array of rows to a CSV file.
  - `operation == 'read'`: Read and return formatted CSV spreadsheet contents.
  - `operation == 'append'`: Append new rows to an existing CSV file.
  - Verify path safety permissions via `check_and_request_permission(path)`.
- **System Integration:** Add the Business Agent to the orchestrator routing rules system prompt in `backend/agents/orchestrator.py` and the `_analyze_request` keyword check loop.
- **UI Selector:** Add `"business"` to the direct agent selector list in `MultiAgentHub.tsx` (`['code', 'research', 'analysis', 'business']`) and handle its default tool routing to `csv_sheet_operation`.

### R3. Voice Recording and Local Speech-to-Text Transcription
- **Microphone UI:** Add a microphone button next to the prompt textarea in `MultiAgentHub.tsx` with recording state indicators (pulsing red dot, timer).
- **Client Audio Encoding:** Implement a browser-native WAV encoder in `MultiAgentHub.tsx` that records voice audio and converts the float32 mono channel buffer into standard 16-bit PCM WAV chunks.
- **Transcription Endpoint:** Add the `SpeechRecognition` library to `backend/requirements.txt` and create a `/agents/voice/transcribe` POST endpoint in `backend/agents/api.py` that receives the WAV file as a multipart upload, processes it using `speech_recognition.Recognizer` with `recognize_google()`, and returns the text.
- **UI Integration:** Populate the transcribed text directly into the prompt text area when the recording completes.

## Acceptance Criteria

### R1. Surgical Patch Edits
- [ ] Calling `file_operation(operation="patch", path="test.py", content='{"target": "def old(): pass", "replacement": "def old(): print(\\\"new\\\")"}')` replaces the target code block successfully.
- [ ] Attempting to patch a Python file with invalid syntax returns a syntax error message and does not modify the file.
- [ ] Attempting to patch with a target string that is missing from the file returns a descriptive error indicating the target was not found.

### R2. Business Agent
- [ ] The Business Agent is loaded by `get_available_agents()` and displayed in the frontend selector.
- [ ] Business queries (e.g. "make a business plan spreadsheet") are routed to the Business Agent by the orchestrator.
- [ ] The `csv_sheet_operation` creates and reads valid CSV files in the workspace.

### R3. Voice Transcription
- [ ] The recording button records microphone input and successfully generates a `Blob` of type `audio/wav`.
- [ ] Uploading a WAV file to `/api/multi-agent/agents/voice/transcribe` returns the transcribed text.
- [ ] The voice transcription is automatically inserted into the chat input box.
