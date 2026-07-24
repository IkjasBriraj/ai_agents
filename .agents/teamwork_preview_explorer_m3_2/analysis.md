# Technical Analysis: Frontend Voice Recording & Local STT Integration (Milestone 3)

## 1. Executive Summary
This analysis outlines the frontend design and implementation strategy for Milestone 3 (Voice Recording & Local STT). The goal is to add a microphone UI button alongside the chat prompt textarea in `frontend/src/components/MultiAgentHub.tsx`, capture microphone audio using browser-native Web Audio API, encode the float32 mono channel buffer into a standard 16-bit PCM WAV `Blob` (`audio/wav`), send the audio blob to the FastAPI backend transcription endpoint (`/agents/voice/transcribe` or proxy path `/api/multi-agent/agents/voice/transcribe`), and automatically populate the transcribed speech into the prompt textarea.

---

## 2. Current Codebase Structure & Component Analysis

### 2.1 File Locations
- Main UI Component: `frontend/src/components/MultiAgentHub.tsx` (1,783 lines)
- API Service Layer: `frontend/src/services/ollama.ts` (529 lines)
- Package Dependencies: `lucide-react` (v1.14.0), `react` (v19.2.5), `axios` (v1.15.2)

### 2.2 Existing Prompt Input Layout in `MultiAgentHub.tsx`
In `MultiAgentHub.tsx` (lines 1640–1675), the prompt input bar is rendered at the bottom of the hub workspace card:
```tsx
<div className="p-4 border-t border-border bg-muted/20">
  <div className="flex gap-4">
    <textarea
      value={prompt}
      onChange={(e) => setPrompt(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          handleSendMessage();
        }
      }}
      className="flex-1 p-4 bg-muted border border-border min-h-[75px] max-h-[120px] text-base focus:outline-none focus:ring-2 focus:ring-primary transition-all font-sans leading-relaxed"
      placeholder={...}
    />
    {isTyping ? (
      <Button onClick={handleStopAgent} ...>Stop</Button>
    ) : (
      <Button disabled={!prompt.trim()} onClick={handleSendMessage} ...>Execute</Button>
    )}
  </div>
</div>
```

---

## 3. Detailed Component & Audio Engine Design

### 3.1 Audio Capture & WAV Encoding Pipeline
To meet the acceptance criteria without adding third-party heavy audio dependencies, we utilize browser-native Web Audio API (`AudioContext` and `ScriptProcessorNode` / `MediaStreamAudioSourceNode`):

1. **Microphone Access**:
   `navigator.mediaDevices.getUserMedia({ audio: true })` requests microphone permission and retrieves the `MediaStream`.

2. **Audio Processing Node**:
   An `AudioContext` instance creates a source node from the microphone stream (`audioContext.createMediaStreamSource(stream)`) and attaches a `ScriptProcessorNode` (buffer size 4096, 1 input channel, 1 output channel).
   On each `onaudioprocess` event, raw 32-bit floating point PCM audio samples (`Float32Array`) from channel 0 are collected into a ref array (`audioChunksRef.current.push(new Float32Array(channelData))`).

3. **16-bit Mono PCM WAV Binary Encoder**:
   Upon stopping the recording, all captured `Float32Array` chunks are concatenated into a single flat `Float32Array`. A standard 44-byte RIFF/WAVE header and 16-bit signed PCM integer sample array are written into an `ArrayBuffer` using `DataView` (little-endian byte ordering):
   - **Header Structure (44 Bytes)**:
     - `0..3`: `"RIFF"`
     - `4..7`: `36 + numSamples * 2` (32-bit unsigned uint)
     - `8..11`: `"WAVE"`
     - `12..15`: `"fmt "`
     - `16..19`: `16` (PCM subchunk size)
     - `20..21`: `1` (Linear PCM format)
     - `22..23`: `1` (Mono channel count)
     - `24..27`: `sampleRate` (e.g. 44100 / 48000 Hz)
     - `28..31`: `sampleRate * 2` (Byte rate)
     - `32..33`: `2` (Block align: 1 channel * 2 bytes)
     - `34..35`: `16` (Bits per sample)
     - `36..39`: `"data"`
     - `40..43`: `numSamples * 2` (Data length)
   - **Data Conversion**:
     Float32 values in `[-1.0, 1.0]` are clamped and mapped to 16-bit signed integers `[-32768, 32767]`:
     ```ts
     const s = Math.max(-1, Math.min(1, merged[i]));
     const int16 = s < 0 ? s * 0x8000 : s * 0x7FFF;
     view.setInt16(dataOffset, int16, true);
     ```
   - **Output Blob**:
     `new Blob([buffer], { type: 'audio/wav' })` produces the WAV file blob.

---

## 4. Proposed UI & State Management

### 4.1 New Imports in `MultiAgentHub.tsx`
Add `Mic`, `MicOff`, `Loader2` from `lucide-react`:
```ts
import { 
  Bot, Cpu, Send, FileText, Globe, Binary, FolderCheck, Settings, 
  ChevronDown, ChevronUp, Zap, Layers, TrendingUp, RefreshCw, 
  FolderOpen, AlertTriangle, Terminal, Square, Copy, Check,
  Mic, MicOff, Loader2
} from 'lucide-react';
```

### 4.2 State & Reference Additions
Add recording state and audio stream refs inside `MultiAgentHub`:
```ts
// Voice Recording state
const [isRecording, setIsRecording] = useState(false);
const [isTranscribing, setIsTranscribing] = useState(false);
const [recordingTime, setRecordingTime] = useState(0);

const mediaStreamRef = useRef<MediaStream | null>(null);
const audioContextRef = useRef<AudioContext | null>(null);
const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null);
const audioChunksRef = useRef<Float32Array[]>([]);
const recordingTimerRef = useRef<number | null>(null);
```

### 4.3 Helper Functions & Handlers
1. `encodeWAV(chunks: Float32Array[], sampleRate: number): Blob`
2. `startRecording()`: Requests microphone stream, starts audio context & processor, starts 1-second interval counter.
3. `stopRecording()`: Stops timer, disconnects nodes, closes audio context, encodes `Blob`, invokes `OllamaService.transcribeVoice`, appends transcribed text to `prompt`.

### 4.4 Formatted Duration Counter Helper
```ts
const formatRecordingTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};
```

---

## 5. Recommended Code Implementation Details

### 5.1 Service Addition (`frontend/src/services/ollama.ts`)
Add `transcribeVoice` method to `OllamaService`:
```ts
  async transcribeVoice(audioBlob: Blob): Promise<{ status: string; text?: string; message?: string }> {
    const formData = new FormData();
    formData.append('file', audioBlob, 'recording.wav');
    try {
      const response = await axios.post(`${API_BASE}/api/multi-agent/agents/voice/transcribe`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    } catch (err) {
      // Proxy route fallback
      const response = await axios.post(`${API_BASE}/agents/voice/transcribe`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    }
  }
```

### 5.2 Microphone Button UI JSX
Replace the prompt input container in `MultiAgentHub.tsx` with:
```tsx
{/* PROMPT INPUT WITH MIC BUTTON */}
<div className="p-4 border-t border-border bg-muted/20">
  <div className="flex gap-3 items-center">
    <textarea
      value={prompt}
      onChange={(e) => setPrompt(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          handleSendMessage();
        }
      }}
      className="flex-1 p-4 bg-muted border border-border min-h-[75px] max-h-[120px] text-base focus:outline-none focus:ring-2 focus:ring-primary transition-all font-sans leading-relaxed"
      placeholder={
        mode === 'orchestrated'
          ? "Ask the Main Orchestrator Agent to do something (e.g. generate website portfolios, analyze algorithms)..."
          : `Direct message to ${selectedDirectAgent.toUpperCase()} Agent...`
      }
    />
    
    {/* Voice Microphone Button */}
    <div className="flex flex-col items-center gap-1">
      <Button
        type="button"
        variant={isRecording ? "destructive" : "outline"}
        disabled={isTranscribing || isTyping}
        onClick={isRecording ? stopRecording : startRecording}
        className={cn(
          "h-[75px] px-4 flex flex-col justify-center items-center border transition-all duration-300",
          isRecording 
            ? "border-red-500 bg-red-600/90 hover:bg-red-700 text-white shadow-lg shadow-red-500/20" 
            : "border-border hover:border-primary hover:bg-primary/10 text-foreground"
        )}
        title={isRecording ? "Stop voice recording" : "Start voice recording"}
      >
        {isTranscribing ? (
          <Loader2 className="w-5 h-5 animate-spin text-primary" />
        ) : isRecording ? (
          <div className="relative flex items-center justify-center">
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-white rounded-full animate-ping" />
            <MicOff className="w-5 h-5 text-white" />
          </div>
        ) : (
          <Mic className="w-5 h-5 text-primary" />
        )}
        <span className="text-[10px] uppercase font-mono tracking-wider mt-1">
          {isTranscribing ? "Transcribing" : isRecording ? formatRecordingTime(recordingTime) : "Record"}
        </span>
      </Button>
    </div>

    {/* Send / Stop Execution Button */}
    {isTyping ? (
      <Button
        onClick={handleStopAgent}
        variant="destructive"
        className="h-[75px] px-6 flex flex-col justify-center items-center border border-red-500/50 text-base bg-red-600 hover:bg-red-700 text-white"
      >
        <Square className="w-5 h-5 mb-1 text-white fill-white" />
        <span className="text-xs uppercase font-mono tracking-widest text-white">Stop</span>
      </Button>
    ) : (
      <Button
        disabled={!prompt.trim()}
        onClick={handleSendMessage}
        className="h-[75px] px-6 flex flex-col justify-center items-center border border-primary/50 text-base"
      >
        <Send className="w-5 h-5 mb-1 text-white" />
        <span className="text-xs uppercase font-mono tracking-widest text-white">Execute</span>
      </Button>
    )}
  </div>
  
  <div className="flex justify-between items-center mt-3 text-[10px] font-mono text-muted-foreground">
    <span className="flex items-center gap-2">
      {isRecording && (
        <span className="flex items-center gap-1 text-red-400 font-bold animate-pulse">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-ping inline-block" />
          RECORDING VOICE... ({formatRecordingTime(recordingTime)})
        </span>
      )}
      {!isRecording && "Press Enter to send, Shift+Enter for new line"}
    </span>
    <span className="flex items-center gap-1.5">
      <FolderCheck className="w-3.5 h-3.5 text-accent" />
      File-writer Workspace Target: <strong className="text-foreground">D:\learning\code\website</strong>
    </span>
  </div>
</div>
```

---

## 6. Verification Plan & Test Conditions
1. Build verification: `npm run build` in `frontend/` directory to verify TypeScript compilation.
2. Interface verification: Verify microphone permission request, timer counter start, pulsing red dot indicator display, WAV Blob binary format validation (`audio/wav` type), backend form submission, and textarea text auto-population.
