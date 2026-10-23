// Natural Voice Engine for SeniorAgent Multi-Agent Hub
// Transforms robotic Web Speech API into crisp, human-like conversational audio.

export interface RankedVoice {
  voice: SpeechSynthesisVoice;
  name: string;
  lang: string;
  quality: 'neural' | 'natural' | 'enhanced' | 'standard';
  badge: string;
  score: number;
  gender: 'female' | 'male' | 'neutral';
  isDefaultRecommended?: boolean;
}

export interface VoiceSettings {
  voiceUri: string;
  rate: number;      // 0.8 to 1.3 (default 1.02 for natural conversational cadence)
  pitch: number;     // 0.8 to 1.2 (default 1.0)
  autoSpeak: boolean; // Auto-speak responses
}

const DEFAULT_SETTINGS: VoiceSettings = {
  voiceUri: '',
  rate: 1.02,
  pitch: 1.0,
  autoSpeak: true,
};

class NaturalVoiceEngine {
  private voices: SpeechSynthesisVoice[] = [];
  private rankedVoices: RankedVoice[] = [];
  private listeners: Array<() => void> = [];
  private activeUtterance: SpeechSynthesisUtterance | null = null;
  private heartbeatInterval: number | null = null;
  private settings: VoiceSettings = { ...DEFAULT_SETTINGS };

  constructor() {
    this.loadSettings();
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      this.initVoices();
    }
  }

  private loadSettings() {
    if (typeof window === 'undefined') return;
    try {
      const savedUri = localStorage.getItem('agent_voice_uri') || '';
      const savedRate = parseFloat(localStorage.getItem('agent_voice_rate') || '1.02');
      const savedPitch = parseFloat(localStorage.getItem('agent_voice_pitch') || '1.0');
      const savedAuto = localStorage.getItem('senior_agent_auto_speak');

      this.settings = {
        voiceUri: savedUri,
        rate: isNaN(savedRate) ? 1.02 : Math.min(1.3, Math.max(0.8, savedRate)),
        pitch: isNaN(savedPitch) ? 1.0 : Math.min(1.2, Math.max(0.8, savedPitch)),
        autoSpeak: savedAuto !== null ? savedAuto === 'true' : true,
      };
    } catch (e) {
      console.warn('Failed to load voice settings:', e);
    }
  }

  public saveSettings(newSettings: Partial<VoiceSettings>) {
    this.settings = { ...this.settings, ...newSettings };
    if (typeof window === 'undefined') return;
    try {
      if (newSettings.voiceUri !== undefined) {
        localStorage.setItem('agent_voice_uri', this.settings.voiceUri);
      }
      if (newSettings.rate !== undefined) {
        localStorage.setItem('agent_voice_rate', String(this.settings.rate));
      }
      if (newSettings.pitch !== undefined) {
        localStorage.setItem('agent_voice_pitch', String(this.settings.pitch));
      }
      if (newSettings.autoSpeak !== undefined) {
        localStorage.setItem('senior_agent_auto_speak', String(this.settings.autoSpeak));
      }
    } catch (e) {
      console.warn('Failed to save voice settings:', e);
    }
    this.notifyListeners();
  }

  public getSettings(): VoiceSettings {
    return { ...this.settings };
  }

  public subscribe(listener: () => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  private notifyListeners() {
    this.listeners.forEach(cb => {
      try {
        cb();
      } catch (e) {
        console.error('Voice listener error:', e);
      }
    });
  }

  private initVoices() {
    const update = () => {
      const rawVoices = window.speechSynthesis.getVoices();
      if (rawVoices.length > 0) {
        this.voices = rawVoices;
        this.rankedVoices = this.rankVoices(rawVoices);
        this.notifyListeners();
      }
    };

    update();
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = update;
    }
    // Periodic check for async engines (Chromium on Windows can take 200-500ms)
    setTimeout(update, 200);
    setTimeout(update, 1000);
  }

  /**
   * Score and categorize voices so natural neural voices are always prioritized
   * over legacy robotic desktop synthesizers.
   */
  private rankVoices(voices: SpeechSynthesisVoice[]): RankedVoice[] {
    const scored: RankedVoice[] = voices.map(v => {
      const name = v.name;
      const lowerName = name.toLowerCase();
      const lang = v.lang || '';
      let score = 10;
      let quality: RankedVoice['quality'] = 'standard';
      let badge = 'System';
      let gender: RankedVoice['gender'] = 'neutral';

      // Gender inference
      if (lowerName.includes('female') || lowerName.includes('jenny') || lowerName.includes('aria') || lowerName.includes('sonia') || lowerName.includes('ana') || lowerName.includes('samantha') || lowerName.includes('karen') || lowerName.includes('zira') || lowerName.includes('victoria') || lowerName.includes('ava') || lowerName.includes('zoe')) {
        gender = 'female';
      } else if (lowerName.includes('male') || lowerName.includes('guy') || lowerName.includes('christopher') || lowerName.includes('eric') || lowerName.includes('ryan') || lowerName.includes('david') || lowerName.includes('daniel') || lowerName.includes('george') || lowerName.includes('mark')) {
        gender = 'male';
      }

      // English language boost
      if (lang.toLowerCase().startsWith('en')) {
        score += 30;
      }

      // ── TIER 1: Edge Online Neural Voices (Studio Quality) ──
      // Microsoft's Azure Neural models available for free in Edge
      if (lowerName.includes('online (natural)') || (lowerName.includes('natural') && lowerName.includes('microsoft'))) {
        score += 80;
        quality = 'neural';
        badge = '✨ Studio Neural';
        // Jenny and Guy are universally acclaimed natural voices
        if (lowerName.includes('jenny') || lowerName.includes('guy') || lowerName.includes('aria')) {
          score += 20;
        }
      }
      // ── TIER 1.5: Google Chrome Natural Neural Voices ──
      else if (lowerName.includes('google') && lowerName.includes('english')) {
        score += 70;
        quality = 'neural';
        badge = '🌟 Google Natural';
        if (lowerName.includes('us') || lowerName.includes('uk')) {
          score += 10;
        }
      }
      // ── TIER 1.5: Apple Enhanced / Premium Neural Voices ──
      else if (lowerName.includes('enhanced') || lowerName.includes('premium') || lowerName.includes('siri')) {
        score += 65;
        quality = 'enhanced';
        badge = '🍎 Apple Enhanced';
      }
      // ── TIER 2: Natural Desktop / Windows OneCore ──
      else if (lowerName.includes('natural')) {
        score += 50;
        quality = 'natural';
        badge = 'Natural';
      }
      else if (lowerName.includes('samantha') || lowerName.includes('zira') || lowerName.includes('karen') || lowerName.includes('victoria')) {
        score += 25;
        quality = 'natural';
        badge = 'Clear Voice';
      }

      // ── DEPRIORITIZE: Robotic Legacy SAPI voices ──
      // "Microsoft David Desktop" is the infamous mechanical 1990s robotic voice
      if (lowerName.includes('david desktop') || lowerName.includes('hazel desktop') || lowerName.includes('espeak') || lowerName.includes('mbrola')) {
        score -= 60;
        badge = 'Robotic';
      }

      return {
        voice: v,
        name,
        lang,
        quality,
        badge,
        score,
        gender,
      };
    });

    // Sort descending by score, then alphabetically
    scored.sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return a.name.localeCompare(b.name);
    });

    // Mark top ranked voice as recommended default
    if (scored.length > 0) {
      scored[0].isDefaultRecommended = true;
    }

    return scored;
  }

  public getRankedVoices(): RankedVoice[] {
    if (this.rankedVoices.length === 0 && typeof window !== 'undefined' && 'speechSynthesis' in window) {
      const raw = window.speechSynthesis.getVoices();
      if (raw.length > 0) {
        this.rankedVoices = this.rankVoices(raw);
      }
    }
    return this.rankedVoices;
  }

  public getActiveVoice(): SpeechSynthesisVoice | null {
    const ranked = this.getRankedVoices();
    if (ranked.length === 0) return null;

    // 1. Check user preference if saved
    if (this.settings.voiceUri) {
      const found = ranked.find(rv => rv.voice.voiceURI === this.settings.voiceUri || rv.name === this.settings.voiceUri);
      if (found) return found.voice;
    }

    // 2. Fallback to highest ranked natural/neural voice
    return ranked[0].voice;
  }

  /**
   * Transforms raw agent markdown, code blocks, technical jargon, and emojis
   * into crisp, human-like conversational spoken English.
   */
  public prepareConversationalSpeech(text: string): string {
    if (!text || !text.trim()) return '';

    let clean = text;

    // 1. Strip code blocks with polite conversational summaries
    clean = clean.replace(/```[a-zA-Z0-9_\-]*\n[\s\S]*?```/g, ' I have generated the application code. ');
    clean = clean.replace(/```[\s\S]*?```/g, ' ');

    // 2. Strip inline code backticks cleanly
    clean = clean.replace(/`([^`]+)`/g, '$1');

    // 3. Remove images and keep markdown link titles
    clean = clean.replace(/!\[.*?\]\(.*?\)/g, '');
    clean = clean.replace(/\[(.*?)\]\(.*?\)/g, '$1');

    // 4. Remove all Unicode emojis (Emojis cause speech synthesizers to stutter or read 'rocket sparkles')
    clean = clean.replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{1F600}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{FE00}-\u{FE0F}\u{1F900}-\u{1F9FF}\u{1FA70}-\u{1FAFF}]/gu, '');

    // 5. Clean URLs to natural speech
    clean = clean.replace(/https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?(\/[^\s]*)?/gi, ' the local web preview ');
    clean = clean.replace(/https?:\/\/[^\s]+/gi, ' the web link ');

    // 6. Convert technical abbreviations and acronyms into natural phonetics
    const pronunciations: [RegExp, string][] = [
      [/\bUI\/UX\b/gi, 'U I and U X'],
      [/\bUI\b/g, 'U I'],
      [/\bUX\b/g, 'U X'],
      [/\bAPI\b/g, 'A P I'],
      [/\bCLI\b/g, 'C L I'],
      [/\bSDK\b/g, 'S D K'],
      [/\bHTML5?\b/gi, 'HTML 5'],
      [/\bCSS3?\b/gi, 'CSS'],
      [/\bSQL\b/g, 'sequel'],
      [/\bSQLite\b/gi, 'sequel lite'],
      [/\bPostgreSQL\b/gi, 'post gres'],
      [/\be\.?g\.?,?\s*/gi, 'for example, '],
      [/\bi\.?e\.?,?\s*/gi, 'that is, '],
      [/\bvs\.?\s*/gi, 'versus '],
      [/\betc\.?\s*/gi, 'etcetera. '],
      [/\bw\/\s*/gi, 'with '],
      [/\bw\/o\s*/gi, 'without '],
      [/\bdev\s+server\b/gi, 'development server'],
      [/\brepo\b/gi, 'repository'],
      [/\bconfig\b/gi, 'configuration'],
    ];

    for (const [pattern, replacement] of pronunciations) {
      clean = clean.replace(pattern, replacement);
    }

    // 7. Clean file paths into spoken friendly names (e.g. app/page.tsx -> "app page file")
    clean = clean.replace(/([a-zA-Z0-9_\-]+)\.(tsx|jsx|ts|js|html|css|py|json|md)\b/gi, '$1 file');

    // 8. Convert markdown headers and bullet points into natural conversational pauses
    clean = clean.replace(/^#{1,6}\s+(.*)$/gm, '$1. ');
    clean = clean.replace(/^\s*[\-\*\•]\s+(.*)$/gm, '$1, ');
    clean = clean.replace(/^\s*\d+[\.\)]\s+(.*)$/gm, '$1, ');

    // 9. Remove raw markdown formatting symbols
    clean = clean.replace(/[#*~_>|\\^]/g, ' ');
    clean = clean.replace(/[-=]{3,}/g, ' ');

    // 10. Normalize whitespace and sentence pacing
    clean = clean.replace(/\n+/g, '. ');
    clean = clean.replace(/\s+/g, ' ');
    clean = clean.replace(/\s*([.,?!])\s*/g, '$1 ');
    clean = clean.replace(/\.{2,}/g, '.');
    clean = clean.replace(/,\s*,/g, ',');
    clean = clean.trim();

    // 11. Truncate gracefully to ~350-420 chars ending on a complete sentence
    if (clean.length > 380) {
      const sentenceEnd = clean.indexOf('.', 300);
      if (sentenceEnd !== -1 && sentenceEnd < 450) {
        clean = clean.slice(0, sentenceEnd + 1);
      } else {
        const commaEnd = clean.indexOf(',', 320);
        clean = commaEnd !== -1 ? clean.slice(0, commaEnd) + '.' : clean.slice(0, 380) + '.';
      }
    }

    return clean;
  }

  /**
   * Speak text naturally using the top-rated or user-selected voice.
   */
  public speak(
    text: string,
    options?: {
      onStart?: () => void;
      onEnd?: () => void;
      onError?: (err: any) => void;
      voiceOverride?: SpeechSynthesisVoice;
      rateOverride?: number;
      pitchOverride?: number;
    }
  ) {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;

    this.stop();

    const cleanText = this.prepareConversationalSpeech(text);
    if (!cleanText) return;

    try {
      const utterance = new SpeechSynthesisUtterance(cleanText);
      this.activeUtterance = utterance;
      // Prevent Chromium garbage collection mid-speech
      (window as any)._naturalVoiceCurrentUtterance = utterance;

      const voice = options?.voiceOverride || this.getActiveVoice();
      if (voice) {
        utterance.voice = voice;
      }

      utterance.rate = options?.rateOverride ?? this.settings.rate;
      utterance.pitch = options?.pitchOverride ?? this.settings.pitch;

      utterance.onstart = () => {
        if (options?.onStart) options.onStart();
      };

      utterance.onend = () => {
        this.stopHeartbeat();
        this.activeUtterance = null;
        if (options?.onEnd) options.onEnd();
      };

      utterance.onerror = (e) => {
        this.stopHeartbeat();
        this.activeUtterance = null;
        if (options?.onError) options.onError(e);
      };

      // Chromium stall prevention: Chromium pauses long utterances after ~14 seconds
      this.startHeartbeat();

      window.speechSynthesis.resume();
      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.warn('Natural voice playback failed:', err);
      this.stopHeartbeat();
      if (options?.onError) options.onError(err);
    }
  }

  public stop() {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
      } catch (e) {}
    }
    this.stopHeartbeat();
    this.activeUtterance = null;
  }

  public isSpeaking(): boolean {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return false;
    return window.speechSynthesis.speaking;
  }

  public getRawVoices(): SpeechSynthesisVoice[] {
    return this.voices;
  }

  public getActiveUtterance(): SpeechSynthesisUtterance | null {
    return this.activeUtterance;
  }

  /**
   * Preview a specific voice with a short natural test phrase.
   */
  public previewVoice(voice: SpeechSynthesisVoice, onEnd?: () => void) {
    const sampleText = "Hello! I am your AI assistant, sounding more natural and ready to pair-program with you.";
    this.speak(sampleText, {
      voiceOverride: voice,
      onEnd,
    });
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    if (typeof window === 'undefined') return;
    this.heartbeatInterval = window.setInterval(() => {
      if (window.speechSynthesis && window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
      }
    }, 3000);
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }
}

export const naturalVoice = new NaturalVoiceEngine();
