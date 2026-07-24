# Analysis: Milestone 3 Backend Voice Recording & STT Transcription Endpoint

## Executive Summary
Milestone 3 requires adding Speech-to-Text (STT) capabilities to the backend via a new endpoint `/agents/voice/transcribe` in `backend/agents/api.py` and adding the `SpeechRecognition` library to `backend/requirements.txt`. This report provides a complete architectural analysis, dependency review, code analysis, proposed implementation strategy, and verification plan.

---

## 1. Scope & Component Breakdown

### Target Files
1. `backend/requirements.txt`:
   - Add `SpeechRecognition` python package.
2. `backend/agents/api.py`:
   - Import `File`, `UploadFile` from `fastapi`.
   - Import `io` and `speech_recognition as sr`.
   - Implement `POST /agents/voice/transcribe` inside `create_multi_agent_router`.
   - Accept WAV audio upload via `file: UploadFile = File(...)`.
   - Process audio bytes using `speech_recognition.Recognizer` and `recognize_google()`.
   - Return structured JSON response: `{"status": "success", "text": "..."}` or `{"status": "error", "message": "..."}`.

---

## 2. Codebase Investigation Findings

### A. Requirements (`backend/requirements.txt`)
- **Current State**: Contains 11 dependencies (`fastapi`, `uvicorn`, `httpx`, `sqlalchemy`, `pydantic`, `python-multipart`, `aiosqlite`, `langchain`, `langchain-community`, `langgraph`, `litellm`).
- **Observation**: `python-multipart` is already present in `requirements.txt` (line 6), which ensures FastAPI can parse `multipart/form-data` requests (`UploadFile`) without additional form parsing dependencies.
- **Action**: Append `SpeechRecognition` to `backend/requirements.txt`.

### B. API Router Architecture (`backend/agents/api.py` & `backend/main.py`)
- **Router Setup**: In `backend/agents/api.py`, routes are defined within `create_multi_agent_router(...)` which returns an `APIRouter(tags=["Multi-Agent System"])`.
- **Mounting Prefix**: In `backend/main.py` (lines 346–350), `multi_agent_router` is mounted with prefix `/api/multi-agent`:
  ```python
  multi_agent_router = create_multi_agent_router(
      model_name=DEFAULT_MAIN_MODEL,
      ollama_base_url=OLLAMA_URL
  )
  app.include_router(multi_agent_router, prefix="/api/multi-agent")
  ```
- **Endpoint Route**: Defining `@router.post("/agents/voice/transcribe")` inside `create_multi_agent_router()` will expose the endpoint at path `/api/multi-agent/agents/voice/transcribe`.

### C. Audio Processing & Non-Blocking Execution
- **Audio Loading**: `UploadFile.read()` returns raw audio `bytes`. `speech_recognition.AudioFile` natively supports file-like objects (e.g. `io.BytesIO(audio_bytes)`), which parses standard PCM WAV audio headers using Python's `wave` module.
- **Async Thread Offloading**: `sr.Recognizer().recognize_google(...)` makes a synchronous blocking network HTTP call to Google's Speech-to-Text API. Calling this directly in an `async def` FastAPI route would block the main asyncio event loop.
- **Pattern Alignment**: Existing endpoints in `backend/agents/api.py` (e.g., lines 170, 203, 237, 257, 277) use `await asyncio.to_thread(...)` for blocking tasks. Running transcription via `await asyncio.to_thread(_process_transcription, audio_bytes)` follows established project conventions and maintains event loop responsiveness.

---

## 3. Proposed Implementation Strategy

### Change 1: `backend/requirements.txt`
Add `SpeechRecognition` to requirements:

```diff
--- backend/requirements.txt
+++ backend/requirements.txt
@@ -10,3 +10,4 @@
 langgraph
 litellm
+SpeechRecognition
```

### Change 2: `backend/agents/api.py`

#### Imports Update:
```python
import asyncio
import io
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from pydantic import BaseModel, Field
import json
import speech_recognition as sr
```

#### Endpoint Implementation in `create_multi_agent_router`:
```python
    @router.post("/agents/voice/transcribe")
    async def transcribe_voice(file: UploadFile = File(...)):
        """
        Transcribe uploaded WAV audio file using SpeechRecognition Google STT engine.
        Accepts multipart/form-data with field 'file'.
        Returns JSON {"status": "success", "text": "..."} or {"status": "error", "message": "..."}.
        """
        if not file:
            return {"status": "error", "message": "No audio file provided"}

        try:
            audio_bytes = await file.read()
            if not audio_bytes:
                return {"status": "error", "message": "Audio file is empty"}

            def _process_transcription(data: bytes) -> str:
                recognizer = sr.Recognizer()
                audio_file = io.BytesIO(data)
                with sr.AudioFile(audio_file) as source:
                    audio_data = recognizer.record(source)
                return recognizer.recognize_google(audio_data)

            transcribed_text = await asyncio.to_thread(_process_transcription, audio_bytes)
            return {
                "status": "success",
                "text": transcribed_text
            }
        except sr.UnknownValueError:
            return {
                "status": "error",
                "message": "Speech recognition could not understand audio"
            }
        except sr.RequestError as e:
            return {
                "status": "error",
                "message": f"Speech recognition service error: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Transcription failed: {str(e)}"
            }
```

---

## 4. Error Handling Matrix

| Scenario | Cause | Response Payload | Status Code |
|---|---|---|---|
| Valid Audio WAV | Clear speech in WAV file | `{"status": "success", "text": "Hello world"}` | 200 OK |
| Unintelligible / Silence | `sr.UnknownValueError` | `{"status": "error", "message": "Speech recognition could not understand audio"}` | 200 OK |
| Network / Google API error | `sr.RequestError` | `{"status": "error", "message": "Speech recognition service error: ..."}` | 200 OK |
| Corrupted / Empty WAV | Invalid WAV header / 0 bytes | `{"status": "error", "message": "Audio file is empty"}` or `{"status": "error", "message": "Transcription failed: ..."}` | 200 OK |
| Missing file | Form field empty | `{"status": "error", "message": "No audio file provided"}` | 200 OK |

---

## 5. Verification Plan

1. **Dependency Installation Check**:
   - Verify `SpeechRecognition` package imports successfully in Python environment (`import speech_recognition as sr`).
2. **Unit / Integration Test Creation (`backend/test_voice_transcribe.py`)**:
   - Generate a valid PCM WAV audio byte buffer using Python's standard `wave` module.
   - Send `POST /api/multi-agent/agents/voice/transcribe` via `httpx.AsyncClient` or FastAPI `TestClient`.
   - Verify JSON payload structure (`status` and `text` or `message`).
3. **End-to-End Endpoint Verification**:
   - Verify route appears in FastAPI OpenAPI docs (`/docs`) and responds correctly to multipart file uploads.
