import React, { useState, useEffect } from 'react';
import { naturalVoice, type RankedVoice, type VoiceSettings } from '../services/naturalVoice';
import { Volume2, VolumeX, Play, Square, Sparkles, Check, RefreshCw, X, Sliders, Info } from 'lucide-react';

interface VoiceSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const VoiceSettingsModal: React.FC<VoiceSettingsModalProps> = ({ isOpen, onClose }) => {
  const [voices, setVoices] = useState<RankedVoice[]>([]);
  const [settings, setSettings] = useState<VoiceSettings>(naturalVoice.getSettings());
  const [previewingVoiceUri, setPreviewingVoiceUri] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState<string>('');

  useEffect(() => {
    if (isOpen) {
      setVoices(naturalVoice.getRankedVoices());
      setSettings(naturalVoice.getSettings());
    }

    const unsubscribe = naturalVoice.subscribe(() => {
      setVoices(naturalVoice.getRankedVoices());
      setSettings(naturalVoice.getSettings());
    });

    return () => {
      unsubscribe();
      naturalVoice.stop();
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const activeVoice = naturalVoice.getActiveVoice();
  const currentVoiceUri = settings.voiceUri || activeVoice?.voiceURI || '';

  const handleSelectVoice = (voiceUri: string) => {
    naturalVoice.saveSettings({ voiceUri });
    setSettings(prev => ({ ...prev, voiceUri }));
  };

  const handleRateChange = (newRate: number) => {
    naturalVoice.saveSettings({ rate: newRate });
    setSettings(prev => ({ ...prev, rate: newRate }));
  };

  const handlePitchChange = (newPitch: number) => {
    naturalVoice.saveSettings({ pitch: newPitch });
    setSettings(prev => ({ ...prev, pitch: newPitch }));
  };

  const handleToggleAutoSpeak = () => {
    const nextVal = !settings.autoSpeak;
    naturalVoice.saveSettings({ autoSpeak: nextVal });
    setSettings(prev => ({ ...prev, autoSpeak: nextVal }));
  };

  const handlePreviewVoice = (rv: RankedVoice) => {
    if (previewingVoiceUri === rv.voice.voiceURI) {
      naturalVoice.stop();
      setPreviewingVoiceUri(null);
    } else {
      setPreviewingVoiceUri(rv.voice.voiceURI);
      naturalVoice.previewVoice(rv.voice, () => {
        setPreviewingVoiceUri(null);
      });
    }
  };

  const handleResetDefaults = () => {
    const defaults: Partial<VoiceSettings> = {
      voiceUri: '',
      rate: 1.02,
      pitch: 1.0,
      autoSpeak: true,
    };
    naturalVoice.saveSettings(defaults);
    setSettings(naturalVoice.getSettings());
    naturalVoice.stop();
    setPreviewingVoiceUri(null);
  };

  const filteredVoices = voices.filter(v => {
    if (!searchFilter.trim()) return true;
    const q = searchFilter.toLowerCase();
    return v.name.toLowerCase().includes(q) || v.lang.toLowerCase().includes(q) || v.badge.toLowerCase().includes(q);
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-200">
      <div 
        className="w-full max-w-xl max-h-[90vh] bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl flex flex-col overflow-hidden text-slate-100"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-amber-500 to-orange-400 flex items-center justify-center text-slate-950 font-bold shadow-lg shadow-amber-500/20">
              <Volume2 className="w-5 h-5 text-slate-950" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                Natural Voice Intelligence
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  Neural TTS
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Select human-sounding neural voices and adjust conversational prosody
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              naturalVoice.stop();
              onClose();
            }}
            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Active Voice Summary Card */}
          <div className="p-4 rounded-xl bg-gradient-to-r from-slate-800/80 via-slate-800/50 to-amber-950/30 border border-slate-700/80 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Active Voice
              </span>
              <button
                onClick={handleToggleAutoSpeak}
                className={`text-xs px-2.5 py-1 rounded-full border transition-all flex items-center gap-1.5 ${
                  settings.autoSpeak
                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-sm'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}
                title="Toggle automatic speech on response"
              >
                {settings.autoSpeak ? <Volume2 className="w-3 h-3 text-amber-400" /> : <VolumeX className="w-3 h-3" />}
                {settings.autoSpeak ? 'Auto-Speak ON' : 'Muted'}
              </button>
            </div>

            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="font-semibold text-sm text-slate-100 truncate">
                    {activeVoice ? activeVoice.name : 'Detecting system voices...'}
                  </h3>
                  {activeVoice && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      {activeVoice.lang}
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  Natural breathing pacing · Markdown & emoji sanitizer enabled
                </p>
              </div>

              {activeVoice && (
                <button
                  onClick={() => {
                    const found = voices.find(v => v.voice.voiceURI === activeVoice.voiceURI);
                    if (found) handlePreviewVoice(found);
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow transition-all ${
                    previewingVoiceUri === activeVoice.voiceURI
                      ? 'bg-amber-500 text-slate-950 animate-pulse'
                      : 'bg-slate-700 hover:bg-slate-600 text-slate-100'
                  }`}
                >
                  {previewingVoiceUri === activeVoice.voiceURI ? (
                    <>
                      <Square className="w-3 h-3 fill-current" /> Stop
                    </>
                  ) : (
                    <>
                      <Play className="w-3 h-3 fill-current text-amber-400" /> Test Voice
                    </>
                  )}
                </button>
              )}
            </div>
          </div>

          {/* Prosody & Cadence Tuning */}
          <div className="space-y-4 p-4 rounded-xl bg-slate-800/40 border border-slate-800">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-mono uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-slate-400" /> Speech Cadence & Tone
              </h4>
              <button
                onClick={handleResetDefaults}
                className="text-[11px] text-slate-400 hover:text-amber-300 flex items-center gap-1 transition-colors"
                title="Reset to recommended natural speech settings"
              >
                <RefreshCw className="w-3 h-3" /> Reset Defaults
              </button>
            </div>

            {/* Speed / Rate */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-300">Speech Speed: <strong className="text-amber-300 font-mono">{settings.rate.toFixed(2)}x</strong></span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleRateChange(0.92)}
                    className={`px-2 py-0.5 rounded text-[10px] font-mono border transition-all ${
                      Math.abs(settings.rate - 0.92) < 0.03 ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                  >
                    Relaxed (0.9x)
                  </button>
                  <button
                    onClick={() => handleRateChange(1.02)}
                    className={`px-2 py-0.5 rounded text-[10px] font-mono border transition-all ${
                      Math.abs(settings.rate - 1.02) < 0.03 ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                  >
                    Natural (1.02x)
                  </button>
                  <button
                    onClick={() => handleRateChange(1.15)}
                    className={`px-2 py-0.5 rounded text-[10px] font-mono border transition-all ${
                      Math.abs(settings.rate - 1.15) < 0.03 ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                  >
                    Brisk (1.15x)
                  </button>
                </div>
              </div>
              <input
                type="range"
                min="0.8"
                max="1.3"
                step="0.02"
                value={settings.rate}
                onChange={e => handleRateChange(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-amber-400"
              />
            </div>

            {/* Pitch */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-300">Vocal Pitch: <strong className="text-amber-300 font-mono">{settings.pitch.toFixed(2)}</strong></span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handlePitchChange(0.95)}
                    className={`px-2 py-0.5 rounded text-[10px] font-mono border transition-all ${
                      Math.abs(settings.pitch - 0.95) < 0.03 ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                  >
                    Warm (0.95)
                  </button>
                  <button
                    onClick={() => handlePitchChange(1.0)}
                    className={`px-2 py-0.5 rounded text-[10px] font-mono border transition-all ${
                      Math.abs(settings.pitch - 1.0) < 0.03 ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                  >
                    Neutral (1.0)
                  </button>
                  <button
                    onClick={() => handlePitchChange(1.05)}
                    className={`px-2 py-0.5 rounded text-[10px] font-mono border transition-all ${
                      Math.abs(settings.pitch - 1.05) < 0.03 ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                  >
                    Crisp (1.05)
                  </button>
                </div>
              </div>
              <input
                type="range"
                min="0.8"
                max="1.2"
                step="0.02"
                value={settings.pitch}
                onChange={e => handlePitchChange(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-amber-400"
              />
            </div>
          </div>

          {/* Voice Selector List */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-mono uppercase tracking-wider text-slate-300">
                Available Voices ({voices.length})
              </h4>
              <input
                type="text"
                value={searchFilter}
                onChange={e => setSearchFilter(e.target.value)}
                placeholder="Search voices (e.g. Natural, Jenny)..."
                className="px-2.5 py-1 bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-400/50 w-48"
              />
            </div>

            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {filteredVoices.length === 0 ? (
                <div className="text-center py-6 text-xs text-slate-400">
                  No matching voices found. Try clearing your search filter.
                </div>
              ) : (
                filteredVoices.map(rv => {
                  const isSelected = rv.voice.voiceURI === currentVoiceUri || rv.name === currentVoiceUri;
                  const isPlaying = previewingVoiceUri === rv.voice.voiceURI;

                  return (
                    <div
                      key={rv.voice.voiceURI || rv.name}
                      onClick={() => handleSelectVoice(rv.voice.voiceURI)}
                      className={`p-3 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-3 ${
                        isSelected
                          ? 'bg-amber-500/10 border-amber-500/60 shadow-[0_0_12px_rgba(245,158,11,0.15)]'
                          : 'bg-slate-800/50 hover:bg-slate-800 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-xs text-slate-100 truncate">
                            {rv.name}
                          </span>
                          <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                            rv.quality === 'neural'
                              ? 'bg-purple-500/20 text-purple-300 border-purple-500/40 font-bold'
                              : rv.quality === 'enhanced'
                              ? 'bg-blue-500/20 text-blue-300 border-blue-500/40'
                              : rv.quality === 'natural'
                              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                              : 'bg-slate-700/60 text-slate-400 border-slate-700'
                          }`}>
                            {rv.badge}
                          </span>
                          {rv.isDefaultRecommended && (
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                              ★ Top Pick
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-400">
                          <span>{rv.lang}</span>
                          <span>·</span>
                          <span className="capitalize">{rv.gender} voice</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handlePreviewVoice(rv);
                          }}
                          className={`p-1.5 rounded-lg border text-xs transition-all ${
                            isPlaying
                              ? 'bg-amber-500 text-slate-950 border-amber-400 animate-pulse'
                              : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
                          }`}
                          title={isPlaying ? "Stop preview" : "Preview sample voice audio"}
                        >
                          {isPlaying ? <Square className="w-3.5 h-3.5 fill-current" /> : <Play className="w-3.5 h-3.5 text-amber-400 fill-current" />}
                        </button>
                        {isSelected && (
                          <div className="w-6 h-6 rounded-full bg-amber-500 text-slate-950 flex items-center justify-center font-bold">
                            <Check className="w-3.5 h-3.5" />
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Browser Pro Tip Note */}
          <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl flex items-start gap-2.5 text-xs text-slate-400">
            <Info className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <span>
              <strong className="text-slate-200 font-semibold">Pro Tip for Studio-Grade Voices:</strong> Microsoft Edge and Google Chrome provide built-in Online Neural studio voices (e.g. <span className="text-amber-300">Microsoft Jenny (Natural)</span> and <span className="text-amber-300">Google US English</span>) that sound indistinguishable from real humans.
            </span>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between text-xs text-slate-400">
          <span>Settings auto-saved to browser local storage</span>
          <button
            onClick={() => {
              naturalVoice.stop();
              onClose();
            }}
            className="px-4 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-lg shadow transition-all"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
