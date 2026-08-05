import React, { useState } from 'react';
import { X, Sparkles, Key, Cpu, Brain, Check, Play, Eye, EyeOff, ShieldCheck, ArrowRight, Zap, RefreshCw } from 'lucide-react';
import './LiquidGlass.css';
import { OllamaService } from '@/services/ollama';

export interface TestAgentProps {
  agent: {
    id: string;
    name: string;
    persona?: string;
    system_prompt?: string;
    tools?: string[];
  };
  onClose: () => void;
}

export const PROVIDERS = [
  { id: 'ollama', name: 'OLLAMA (Local First)', requiresKey: false, defaultModel: 'granite4.1:8b', models: ['granite4.1:8b', 'gemma4:26b', 'llama3.2:latest', 'qwen3.5:9b'] },
  { id: 'openai', name: 'OPENAI', requiresKey: true, defaultModel: 'gpt-4o', models: ['gpt-4o', 'gpt-4o-mini', 'o3-mini', 'gpt-4-turbo'] },
  { id: 'anthropic', name: 'ANTHROPIC', requiresKey: true, defaultModel: 'claude-3-5-sonnet-20241022', models: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229'] },
  { id: 'ibm', name: 'IBM WATSONX', requiresKey: true, defaultModel: 'granite-3-8b-instruct', models: ['granite-3-8b-instruct', 'granite-3-20b-multilingual', 'llama-3-3-70b-instruct'] },
  { id: 'gemini', name: 'GOOGLE GEMINI', requiresKey: true, defaultModel: 'gemini-1.5-pro', models: ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-2.0-flash-exp'] },
  { id: 'deepseek', name: 'DEEPSEEK', requiresKey: true, defaultModel: 'deepseek-chat', models: ['deepseek-chat', 'deepseek-reasoner'] },
];

export const LiquidGlassTestPanel: React.FC<TestAgentProps> = ({ agent, onClose }) => {
  const [provider, setProvider] = useState<string>('ollama');
  const [selectedModel, setSelectedModel] = useState<string>('granite4.1:8b');
  const [apiKey, setApiKey] = useState<string>('');
  const [showApiKey, setShowApiKey] = useState<boolean>(false);
  const [step, setStep] = useState<'config' | 'expanded'>('config');
  const [thinkingLevel, setThinkingLevel] = useState<'disabled' | 'low' | 'medium' | 'high'>('medium');
  const [prompt, setPrompt] = useState<string>(`Analyze and run a test for ${agent.name}.`);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [executionTime, setExecutionTime] = useState<number | null>(null);

  const activeProviderObj = PROVIDERS.find((p) => p.id === provider) || PROVIDERS[0];

  const handleProviderChange = (newProviderId: string) => {
    setProvider(newProviderId);
    const pObj = PROVIDERS.find((p) => p.id === newProviderId);
    if (pObj) {
      setSelectedModel(pObj.defaultModel);
    }
  };

  const handleProceedToTest = () => {
    setStep('expanded');
  };

  const handleRunTest = async () => {
    if (!prompt.trim()) return;
    setIsLoading(true);
    setTestResult(null);
    setExecutionTime(null);
    const startTime = Date.now();

    try {
      const response = await OllamaService.testSingleAgent({
        agent_id: agent.id,
        provider,
        model: selectedModel,
        api_key: apiKey,
        thinking_level: thinkingLevel,
        prompt,
      });
      setTestResult(response);
      setExecutionTime(round((Date.now() - startTime) / 1000, 2));
    } catch (err: any) {
      setTestResult({
        status: 'error',
        error: err?.message || 'Failed to execute test with agent.',
      });
      setExecutionTime(round((Date.now() - startTime) / 1000, 2));
    } finally {
      setIsLoading(false);
    }
  };

  function round(val: number, decimals: number) {
    return Number(Math.round(Number(val + 'e' + decimals)) + 'e-' + decimals);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 liquid-glass-backdrop animate-in fade-in duration-300">
      <div
        className={`liquid-glass-container text-slate-100 transition-all duration-500 ease-out ${
          step === 'config'
            ? 'w-full max-w-lg p-6 min-h-[420px]'
            : 'w-full max-w-4xl p-8 min-h-[640px]'
        }`}
      >
        {/* Glowing Orbs */}
        <div className="liquid-glow-orb bg-indigo-600/30 top-[-40px] left-[-30px]" />
        <div className="liquid-glow-orb bg-purple-600/30 bottom-[-40px] right-[-30px]" />

        <div className="liquid-glass-content flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-6">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 shadow-inner">
                <Brain className="w-6 h-6 animate-pulse" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xl font-bold tracking-tight text-white">{agent.name}</h3>
                  <span className="px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    {agent.id}
                  </span>
                </div>
                <p className="text-xs text-slate-400 font-mono mt-0.5">
                  {step === 'config' ? 'Step 1: Select Model Provider & Key' : 'Step 2: Interactive Prompt & Reasoning Studio'}
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-full hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* STEP 1: CONFIGURATION */}
          {step === 'config' && (
            <div className="flex-1 flex flex-col justify-between gap-6 animate-in fade-in zoom-in-95 duration-300">
              <div className="space-y-5">
                {/* Provider Dropdown */}
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2 flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-indigo-400" />
                    Model Provider
                  </label>
                  <select
                    value={provider}
                    onChange={(e) => handleProviderChange(e.target.value)}
                    className="w-full py-3 px-4 rounded-xl liquid-input-glass text-sm font-medium focus:ring-2 focus:ring-indigo-500 cursor-pointer"
                  >
                    {PROVIDERS.map((p) => (
                      <option key={p.id} value={p.id} className="bg-slate-900 text-slate-100">
                        {p.name} {p.requiresKey ? '(Cloud Key Required)' : '(Local)'}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Model Selection */}
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2 flex items-center gap-2">
                    <Zap className="w-4 h-4 text-amber-400" />
                    Select Model
                  </label>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="w-full py-3 px-4 rounded-xl liquid-input-glass text-sm font-medium cursor-pointer"
                  >
                    {activeProviderObj.models.map((m) => (
                      <option key={m} value={m} className="bg-slate-900 text-slate-100">
                        {m}
                      </option>
                    ))}
                  </select>
                </div>

                {/* API Key Input (if cloud provider) */}
                {activeProviderObj.requiresKey && (
                  <div className="animate-in fade-in duration-300">
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2 flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <Key className="w-4 h-4 text-emerald-400" />
                        {activeProviderObj.name} API Key
                      </span>
                      <span className="text-[10px] text-emerald-400/80 font-mono flex items-center gap-1">
                        <ShieldCheck className="w-3 h-3" /> Encrypted Local State
                      </span>
                    </label>
                    <div className="relative">
                      <input
                        type={showApiKey ? 'text' : 'password'}
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder={`Enter your ${activeProviderObj.name} API key...`}
                        className="w-full py-3 pl-4 pr-12 rounded-xl liquid-input-glass text-sm font-mono tracking-wider"
                      />
                      <button
                        type="button"
                        onClick={() => setShowApiKey(!showApiKey)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white p-1"
                      >
                        {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Action Button */}
              <button
                onClick={handleProceedToTest}
                disabled={activeProviderObj.requiresKey && !apiKey.trim()}
                className="w-full py-3.5 px-6 rounded-2xl liquid-btn-primary font-semibold text-sm flex items-center justify-center gap-2 group disabled:opacity-50 disabled:pointer-events-none mt-4"
              >
                <span>Continue to Prompt Studio</span>
                <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </button>
            </div>
          )}

          {/* STEP 2: EXPANDED PROMPT & REASONING STUDIO */}
          {step === 'expanded' && (
            <div className="flex-1 flex flex-col gap-6 animate-in fade-in zoom-in-95 duration-500">
              {/* Configuration Bar */}
              <div className="flex items-center justify-between bg-white/5 border border-white/10 rounded-2xl p-3.5">
                <div className="flex items-center gap-3 text-xs font-mono">
                  <span className="px-2.5 py-1 rounded-lg bg-indigo-500/20 text-indigo-300 font-semibold border border-indigo-500/30 uppercase">
                    {provider}
                  </span>
                  <span className="text-slate-300 font-medium">{selectedModel}</span>
                  {activeProviderObj.requiresKey && (
                    <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[10px] flex items-center gap-1">
                      <ShieldCheck className="w-3 h-3" /> Key Loaded
                    </span>
                  )}
                </div>

                <button
                  onClick={() => setStep('config')}
                  className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1 px-2.5 py-1 rounded-lg hover:bg-white/5 transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Change Settings
                </button>
              </div>

              {/* Main Testing Workspace Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1">
                {/* Left Column: Controls & Prompt */}
                <div className="lg:col-span-5 flex flex-col gap-5">
                  {/* Thinking Level Selector */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2 flex items-center gap-2">
                      <Brain className="w-4 h-4 text-purple-400" />
                      Thinking Level
                    </label>
                    <div className="grid grid-cols-4 gap-1.5 p-1 rounded-xl bg-slate-900/60 border border-white/10">
                      {(['disabled', 'low', 'medium', 'high'] as const).map((lvl) => (
                        <button
                          key={lvl}
                          type="button"
                          onClick={() => setThinkingLevel(lvl)}
                          className={`py-2 px-2 text-xs font-semibold capitalize rounded-lg transition-all ${
                            thinkingLevel === lvl
                              ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-md'
                              : 'text-slate-400 hover:text-white hover:bg-white/5'
                          }`}
                        >
                          {lvl}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Prompt Text Area */}
                  <div className="flex-1 flex flex-col">
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2 flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-amber-400" />
                      Agent Prompt
                    </label>
                    <textarea
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      placeholder="Type a task or instruction for this agent..."
                      rows={6}
                      className="w-full flex-1 p-4 rounded-2xl liquid-input-glass text-sm font-sans resize-none leading-relaxed"
                    />
                  </div>

                  {/* Submit Button */}
                  <button
                    onClick={handleRunTest}
                    disabled={isLoading || !prompt.trim()}
                    className="w-full py-3.5 px-6 rounded-2xl liquid-btn-primary font-semibold text-sm flex items-center justify-center gap-2 disabled:opacity-50 disabled:pointer-events-none"
                  >
                    {isLoading ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span>Agent Reasoning...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 fill-current" />
                        <span>Run Agent Test</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Right Column: Output / Response Terminal */}
                <div className="lg:col-span-7 flex flex-col rounded-2xl bg-slate-950/80 border border-white/10 overflow-hidden shadow-2xl">
                  {/* Output Header */}
                  <div className="px-4 py-3 bg-slate-900/80 border-b border-white/10 flex items-center justify-between font-mono text-xs text-slate-400">
                    <span className="flex items-center gap-2 text-indigo-400 font-semibold">
                      <Sparkles className="w-3.5 h-3.5" /> Output Console
                    </span>
                    {executionTime !== null && (
                      <span className="text-emerald-400 font-medium">⚡ Response Time: {executionTime}s</span>
                    )}
                  </div>

                  {/* Output Body */}
                  <div className="p-5 flex-1 overflow-y-auto max-h-[380px] font-mono text-sm leading-relaxed text-slate-200 no-scrollbar">
                    {isLoading ? (
                      <div className="h-full flex flex-col items-center justify-center gap-3 text-slate-400 py-12">
                        <div className="w-10 h-10 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
                        <p className="text-xs tracking-wider uppercase animate-pulse">Running {agent.name}...</p>
                      </div>
                    ) : testResult ? (
                      <div>
                        {testResult.status === 'error' ? (
                          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-xs">
                            <strong>Execution Error:</strong> {testResult.error}
                          </div>
                        ) : (
                          <div className="space-y-4">
                            <div className="flex items-center gap-2 pb-3 border-b border-white/10 text-xs text-emerald-400">
                              <Check className="w-4 h-4" />
                              <span>Execution completed successfully</span>
                            </div>
                            <div className="whitespace-pre-wrap font-sans text-slate-100 leading-relaxed text-sm">
                              {typeof testResult.result === 'string'
                                ? testResult.result
                                : JSON.stringify(testResult.result, null, 2)}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 py-16">
                        <Cpu className="w-12 h-12 mb-3 text-slate-700 stroke-1" />
                        <p className="text-xs uppercase tracking-wider">Ready for agent execution</p>
                        <p className="text-[11px] text-slate-600 mt-1 max-w-xs">
                          Configure your thinking level and prompt, then click 'Run Agent Test'.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
