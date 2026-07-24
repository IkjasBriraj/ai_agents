# Scope: Milestone 3 - Voice Recording and Local Speech-to-Text Transcription (R3)

## Mission
Implement microphone UI button, browser PCM WAV audio encoder, backend STT endpoint `/agents/voice/transcribe`, requirement dependency `SpeechRecognition`, and UI input field auto-population.

## Requirements Reference
- Path to User Request: `d:\learning\code\ai_agents\.agents\orchestrator\ORIGINAL_REQUEST.md`
- Path to Global Architecture: `d:\learning\code\ai_agents\.agents\orchestrator\PROJECT.md`

## Targeted Files
1. `backend/requirements.txt`:
   - Add `SpeechRecognition` library.
2. `backend/agents/api.py`:
   - Create POST endpoint `/agents/voice/transcribe` receiving WAV file as multipart upload (`UploadFile`).
   - Process audio using `speech_recognition.Recognizer` with `recognize_google()`. Return text JSON response `{"status": "success", "text": "..."}` or error handling.
3. `frontend/src/components/MultiAgentHub.tsx`:
   - Microphone button next to prompt textarea with recording state indicators (pulsing red dot, timer).
   - Client Audio Encoding: browser-native WAV encoder converting float32 mono channel buffer into standard 16-bit PCM WAV chunks (`Blob` of type `audio/wav`).
   - Submit audio blob to `/agents/voice/transcribe` endpoint.
   - Populate transcribed text directly into prompt textarea.

## Acceptance Criteria Verification
- Recording button records microphone input and successfully generates a `Blob` of type `audio/wav`.
- Uploading WAV file to `/api/multi-agent/agents/voice/transcribe` returns transcribed text.
- Voice transcription is automatically inserted into chat input box.
