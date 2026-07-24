# Milestone 3 Verification, Build, and Testing Infrastructure Analysis

## Executive Summary
This report presents the complete verification, build, and testing infrastructure analysis for **Milestone 3: Voice Recording & Local Speech-to-Text (STT) Transcription**. 

The scope of Milestone 3 requires:
1. Adding `SpeechRecognition` dependency to `backend/requirements.txt`.
2. Implementing the POST endpoint `/agents/voice/transcribe` in `backend/agents/api.py` accepting multipart WAV uploads and performing STT.
3. Adding a voice recording UI, browser-native 16-bit PCM WAV audio encoder, API submission, and automatic prompt text population in `frontend/src/components/MultiAgentHub.tsx`.
4. Establishing rigorous backend test scripts and frontend type/build verification pipelines.

---

## 1. Backend Verification & Test Infrastructure for `/agents/voice/transcribe`

### 1.1 Endpoint Interface Contract
- **Endpoint**: `POST /agents/voice/transcribe` (or proxy path `/api/multi-agent/agents/voice/transcribe`)
- **Content-Type**: `multipart/form-data`
- **Form Field**: `file` (WAV audio binary)
- **Success Response**: `{"status": "success", "text": "<transcribed text>"}`
- **Error Response**: `{"status": "error", "message": "<error details>"}` (HTTP Status 400 or 500 depending on error type)

### 1.2 Synthetic & Sample WAV Data Generation
For reproducible local testing without depending on pre-recorded external audio files, synthetic WAV data can be programmatically generated in Python using the built-in `wave`, `struct`, and `io` modules.

```python
import io
import wave
import struct
import math

def generate_synthetic_pcm_wav(duration_sec: float = 1.0, sample_rate: int = 16000, frequency: float = 440.0) -> bytes:
    """
    Generates a 16-bit PCM mono WAV byte stream in memory.
    - Mono (1 channel)
    - 16,000 Hz sample rate
    - 16-bit signed integer PCM (2 bytes/sample)
    """
    byte_io = io.BytesIO()
    with wave.open(byte_io, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2) # 16-bit PCM
        wav.setframerate(sample_rate)
        
        num_samples = int(duration_sec * sample_rate)
        for i in range(num_samples):
            # Generate 440 Hz sine wave sample
            sample_val = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
            packed_sample = struct.pack('<h', sample_val)
            wav.writeframesraw(packed_sample)
            
    byte_io.seek(0)
    return byte_io.getvalue()
```

### 1.3 Backend Test Script Architecture (`backend/test_voice_transcribe.py`)
Because the backend operates under offline / isolated network constraints (e.g. `CODE_ONLY` mode) or environments where external STT endpoints may be unreachable, unit tests must mock `speech_recognition.Recognizer.recognize_google` while integration tests verify actual audio parsing.

```python
"""
Test Suite for /agents/voice/transcribe endpoint
File: backend/test_voice_transcribe.py
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app # FastAPI application entrypoint

client = TestClient(app)

class TestVoiceTranscribeEndpoint(unittest.TestCase):

    def test_transcribe_success_mocked(self):
        """Test successful STT transcription with mocked Recognizer"""
        wav_bytes = generate_synthetic_pcm_wav(duration_sec=1.0)
        
        with patch("speech_recognition.Recognizer.recognize_google", return_value="hello world"):
            with patch("speech_recognition.Recognizer.record", return_value=MagicMock()):
                response = client.post(
                    "/agents/voice/transcribe",
                    files={"file": ("sample.wav", wav_bytes, "audio/wav")}
                )
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data["status"], "success")
                self.assertEqual(data["text"], "hello world")

    def test_transcribe_invalid_audio_format(self):
        """Test handling of invalid/corrupted audio payload"""
        invalid_bytes = b"NOT_A_WAV_FILE_CONTENT"
        response = client.post(
            "/agents/voice/transcribe",
            files={"file": ("corrupt.wav", invalid_bytes, "audio/wav")}
        )
        self.assertTrue(response.status_code in [400, 500] or response.json().get("status") == "error")

    def test_transcribe_unintelligible_audio(self):
        """Test speech_recognition.UnknownValueError handling"""
        import speech_recognition as sr
        wav_bytes = generate_synthetic_pcm_wav(duration_sec=0.5)
        
        with patch("speech_recognition.Recognizer.recognize_google", side_effect=sr.UnknownValueError()):
            with patch("speech_recognition.Recognizer.record", return_value=MagicMock()):
                response = client.post(
                    "/agents/voice/transcribe",
                    files={"file": ("silent.wav", wav_bytes, "audio/wav")}
                )
                data = response.json()
                self.assertEqual(data["status"], "error")
                self.assertIn("Could not understand audio", data["message"])
```

### 1.4 Backend Execution Command
```powershell
$env:PYTHONIOENCODING="utf-8"; d:\learning\code\ai_agents\backend\venv\Scripts\python.exe test_voice_transcribe.py
```

---

## 2. Frontend Build & TypeScript Type Checking for `MultiAgentHub.tsx`

### 2.1 Target File & Key Components
- **File**: `frontend/src/components/MultiAgentHub.tsx`
- **Key Enhancements Required**:
  1. **Recording State**: `isRecording` (boolean), `recordingTime` (seconds), `isTranscribing` (boolean).
  2. **Mic Button UI**: Microphone icon with active recording pulsing indicator (`bg-red-500 animate-pulse`), timer display (`00:05`), and stop recording trigger.
  3. **PCM WAV Encoder**: AudioContext + ScriptProcessor / AudioWorklet node converting float32 audio channel data to 16-bit mono 16kHz PCM WAV binary `Blob`.
  4. **API Integration**: Submit WAV Blob to `/api/multi-agent/agents/voice/transcribe` via `axios` or `fetch`.
  5. **Auto-Population**: Update prompt textarea (`setPrompt((prev) => prev ? `${prev} ${transcribedText}` : transcribedText)`).

### 2.2 PCM WAV Encoder Implementation Specification
```typescript
function encodeWAV(samples: Float32Array, sampleRate: int = 16000): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  /* RIFF identifier */
  writeString(view, 0, 'RIFF');
  /* RIFF chunk length */
  view.setUint32(4, 36 + samples.length * 2, true);
  /* RIFF type */
  writeString(view, 8, 'WAVE');
  /* format chunk identifier */
  writeString(view, 12, 'fmt ');
  /* format chunk length */
  view.setUint32(16, 16, true);
  /* sample format (raw PCM) */
  view.setUint16(20, 1, true);
  /* channel count (mono) */
  view.setUint16(22, 1, true);
  /* sample rate */
  view.setUint32(24, sampleRate, true);
  /* byte rate (sampleRate * 2) */
  view.setUint32(28, sampleRate * 2, true);
  /* block align (channel count * bytes per sample) */
  view.setUint16(32, 2, true);
  /* bits per sample */
  view.setUint16(34, 16, true);
  /* data chunk identifier */
  writeString(view, 36, 'data');
  /* data chunk length */
  view.setUint32(40, samples.length * 2, true);

  // Float to 16-bit PCM conversion
  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }

  return new Blob([buffer], { type: 'audio/wav' });
}

function writeString(view: DataView, offset: number, string: string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}
```

### 2.3 Frontend Build & Type Validation Pipeline
- Run TypeScript compiler build check:
  ```cmd
  cd frontend
  npx tsc -b
  ```
- Run Vite production build:
  ```cmd
  npm run build
  ```
- Note: Build verification ensures zero TypeScript type errors (`TS6133`, `TS2304`, etc.) and zero broken component props.

---

## 3. Multi-Role Strategy & Verification Matrix

| Role | Primary Responsibility | Verification Actions & Commands |
|------|------------------------|----------------------------------|
| **Worker (Implementer)** | Add `SpeechRecognition` to `requirements.txt`, implement `/agents/voice/transcribe` in `api.py`, update `MultiAgentHub.tsx` with recording UI & WAV encoder, and write `test_voice_transcribe.py`. | 1. `$env:PYTHONIOENCODING="utf-8"; d:\learning\code\ai_agents\backend\venv\Scripts\python.exe test_voice_transcribe.py`<br>2. `npm run build` in `frontend/` |
| **Reviewer 1 & 2** | Code quality, architecture, resource safety, and interface contract compliance. | 1. Code review `api.py` for temporary stream cleanup and proper error handling (`UnknownValueError`, `RequestError`).<br>2. Review `MultiAgentHub.tsx` for proper AudioContext closing & track stopping to prevent memory/microphone lock. |
| **Challenger 1 & 2** | Adversarial edge-case testing & failure mode validation. | 1. Test 0-byte audio upload.<br>2. Test corrupt/non-WAV file uploads.<br>3. Test browser microphone permission denial (`NotAllowedError`).<br>4. Test rapid start/stop mic button toggling.<br>5. Test long recording audio buffer limits. |
| **Forensic Auditor** | Final compliance audit & verification gate against `SCOPE.md` acceptance criteria. | 1. Confirm no project files placed in `.agents/`.<br>2. Confirm exact file edits: `backend/requirements.txt`, `backend/agents/api.py`, `frontend/src/components/MultiAgentHub.tsx`, `backend/test_voice_transcribe.py`.<br>3. Confirm 100% test pass rate & clean build output. |

---

## 4. Verification Checklist & Invalidation Conditions

### 4.1 Verification Steps
1. **Dependency Verification**: Run `pip list` or check `requirements.txt` for `SpeechRecognition`.
2. **Backend Test Suite Pass**: Run `python test_voice_transcribe.py` in `backend/venv` and confirm all test cases pass (`OK`).
3. **Frontend Build Pass**: Run `npm run build` inside `frontend/` and confirm exit code 0.
4. **UI Behavior Pass**: Mic button toggles recording state, timer advances, stops on click, sends WAV payload, and populates prompt textarea.

### 4.2 Invalidation Conditions
- Backend endpoint returns 500 Unhandled Server Error when invalid/empty audio is posted.
- AudioContext or MediaStream tracks are left active after recording stops, locking microphone.
- Frontend TypeScript type check fails (`tsc -b` throws errors).
- Source or test files placed in `.agents/` folder.
