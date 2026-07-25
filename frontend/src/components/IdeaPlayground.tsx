import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Bot, Sparkles, Send, Settings2, Code, Zap, StopCircle, Trash2, ChevronDown, ChevronUp, Brain, Flame, Globe } from 'lucide-react';
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { OllamaService } from '@/services/ollama';
import { SiriFluidOrb } from './SiriFluidOrb';
import { cn } from '@/lib/utils';
import { playSiriActivationSound } from '@/lib/siriAudio';

interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  thinking?: string;
  timestamp: Date;
  tools?: Array<{ name: string; result: string }>;
}

const AGENTS = {
  research: {
    id: 'research',
    name: 'Research Agent',
    description: 'Expert in gathering information, fetching web content, Firecrawl web scraping, and synthesizing complex topics.',
    systemPrompt: 'You are an advanced Research AI. Your goal is to provide accurate, well-researched, and detailed information. Use your tools (web_search, fetch_web_page, firecrawl) to search and gather facts.',
    tools: ['Web Search', 'Fetch Web Page', 'Firecrawl Web Scraper', 'Summarizer'],
    ideas: [
      "Research latest AI agent frameworks",
      "Compare LangChain vs CrewAI",
      "Scrape and analyze AI tech news",
      "Summarize quantum computing advances"
    ]
  },
  business: {
    id: 'business',
    name: 'Business Agent',
    description: 'Specializes in strategy, market analysis, financial models, and business planning.',
    systemPrompt: 'You are a Business Strategy AI. Provide actionable insights, professional reports, and strategic advice for business growth.',
    tools: ['Market Analyzer', 'Financial Modeler', 'Report Generator', 'Excel & PPT Tools'],
    ideas: [
      "Create a startup pitch deck outline",
      "Generate quarterly sales report",
      "Market analysis for AI SaaS",
      "Competitive landscape for fintech"
    ]
  }
};

export const IdeaPlayground: React.FC = () => {
  const [activeAgent, setActiveAgent] = useState<'research' | 'business'>('research');
  const [systemPrompt, setSystemPrompt] = useState(AGENTS.research.systemPrompt);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [temperature, setTemperature] = useState(0.7);
  const [expandedThinking, setExpandedThinking] = useState<Record<string, boolean>>({});
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const renderFrameRef = useRef<number | null>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isGenerating]);

  const toggleThinking = (id: string) => {
    setExpandedThinking(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleAgentChange = (agentId: 'research' | 'business') => {
    setActiveAgent(agentId);
    setSystemPrompt(AGENTS[agentId].systemPrompt);
    setMessages([]);
    handleStop();
  };

  const handleStop = useCallback(async () => {
    if (abortControllerRef.current) {
      try {
        abortControllerRef.current.abort();
      } catch (e) {}
      abortControllerRef.current = null;
    }
    
    // Explicit backend stop trigger
    try {
      await OllamaService.stopMultiAgent('default');
    } catch (e) {
      console.warn('Backend stop signal completed:', e);
    }
    
    setIsGenerating(false);
  }, []);

  const handleSend = async (overrideText?: string) => {
    const textToSend = overrideText || inputText;
    if (!textToSend.trim()) return;

    setInputText('');
    try {
      playSiriActivationSound();
    } catch (e) {}
    
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: textToSend,
      timestamp: new Date()
    };
    
    const agentMessageId = (Date.now() + 1).toString();
    const initialAgentMessage: Message = {
      id: agentMessageId,
      role: 'agent',
      content: '',
      thinking: '',
      timestamp: new Date(),
      tools: []
    };

    setMessages(prev => [...prev, userMessage, initialAgentMessage]);
    setIsGenerating(true);
    // Expand thinking by default while generating
    setExpandedThinking(prev => ({ ...prev, [agentMessageId]: true }));

    // High-performance streaming buffers
    let pendingContent = '';
    let pendingThinking = '';
    let isScheduled = false;

    const flushUpdates = () => {
      setMessages(prev => prev.map(msg => {
        if (msg.id === agentMessageId) {
          return {
            ...msg,
            content: msg.content + pendingContent,
            thinking: (msg.thinking || '') + pendingThinking,
          };
        }
        return msg;
      }));
      pendingContent = '';
      pendingThinking = '';
      isScheduled = false;
    };

    const scheduleFlush = () => {
      if (!isScheduled) {
        isScheduled = true;
        renderFrameRef.current = requestAnimationFrame(flushUpdates);
      }
    };

    try {
      const controller = await OllamaService.chatMultiAgentStream(
        textToSend,
        (event) => {
          if (event.type === 'token') {
            pendingContent += (event.content || '');
            scheduleFlush();
          } else if (event.type === 'thinking_stream' || event.type === 'thinking') {
            pendingThinking += (event.content || '');
            scheduleFlush();
          } else if (event.type === 'tool_start') {
            flushUpdates();
            setMessages(prev => prev.map(msg => 
              msg.id === agentMessageId 
                ? { 
                    ...msg, 
                    tools: [...(msg.tools || []), { name: event.content || 'Tool Execution', result: 'Running...' }]
                  }
                : msg
            ));
          } else if (event.type === 'tool_result') {
            flushUpdates();
            setMessages(prev => prev.map(msg => {
              if (msg.id === agentMessageId && msg.tools) {
                const tools = [...msg.tools];
                if (tools.length > 0) {
                  tools[tools.length - 1].result = event.content || 'Completed';
                }
                return { ...msg, tools };
              }
              return msg;
            }));
          } else if (event.type === 'done') {
            flushUpdates();
            setMessages(prev => prev.map(msg => {
              if (msg.id === agentMessageId && !msg.content.trim() && msg.thinking?.trim()) {
                return { ...msg, content: msg.thinking };
              }
              return msg;
            }));
            setIsGenerating(false);
          }
        },
        (err) => {
          console.error("Stream error:", err);
          flushUpdates();
          setIsGenerating(false);
        },
        { direct_agent: activeAgent, system_prompt: systemPrompt, temperature }
      );
      
      abortControllerRef.current = controller;
    } catch (error) {
      console.error("Error starting direct agent stream:", error);
      setIsGenerating(false);
    }
  };

  const handleClear = () => {
    handleStop();
    setMessages([]);
    setExpandedThinking({});
  };

  const currentAgent = AGENTS[activeAgent];

  return (
    <div className="flex flex-col min-h-[calc(100vh-200px)] h-full bg-background text-foreground overflow-hidden">
      {/* HEADER */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-6 py-4 border-b border-border bg-card/50 backdrop-blur-sm z-10">
        <div className="flex items-center gap-2.5">
          <Sparkles className="w-5 h-5 text-ibm-blue" />
          <h1 className="text-xl font-semibold tracking-tight">Play with Your Ideas</h1>
          <span className="text-[10px] bg-ibm-blue/20 text-ibm-blue border border-ibm-blue/40 px-2 py-0.5 font-mono uppercase rounded">
            AI Studio Engine
          </span>
        </div>
        
        <div className="flex bg-background/50 p-1 rounded-lg border border-border">
          <button 
            onClick={() => handleAgentChange('research')}
            className={cn(
              "px-4 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-2",
              activeAgent === 'research' ? "bg-ibm-blue text-white shadow-md font-semibold" : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Globe className="w-4 h-4" />
            Research Agent
          </button>
          <button 
            onClick={() => handleAgentChange('business')}
            className={cn(
              "px-4 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-2",
              activeAgent === 'business' ? "bg-purple-600 text-white shadow-md font-semibold" : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Zap className="w-4 h-4" />
            Business Agent
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* LEFT PANEL */}
        <aside className="w-[290px] hidden md:flex flex-col border-r border-border bg-card/30 p-4 gap-6 overflow-y-auto">
          <div className="flex flex-col gap-2">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Settings2 className="w-4 h-4 text-ibm-blue" /> System Prompt Instructions
            </h3>
            <textarea 
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              className="w-full h-36 bg-background border border-border rounded-lg p-3 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-ibm-blue resize-none leading-relaxed"
              placeholder="Custom agent persona and rules..."
            />
          </div>
          
          <div className="flex flex-col gap-3">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" /> Quick Idea Starters
            </h3>
            <div className="flex flex-col gap-2">
              {currentAgent.ideas.map((idea, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(idea)}
                  disabled={isGenerating}
                  className="text-left text-xs p-3 rounded-lg border border-border bg-background hover:border-ibm-blue/50 hover:bg-ibm-blue/5 transition-all text-foreground/90 disabled:opacity-50"
                >
                  {idea}
                </button>
              ))}
            </div>
          </div>
        </aside>

        {/* CENTER WORKSPACE */}
        <main className="flex-1 flex flex-col relative">
          <div className="flex-1 overflow-y-auto p-4 md:p-6 pb-28 space-y-6">
            {messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center text-muted-foreground gap-4 py-16">
                <SiriFluidOrb state="active" size="md" />
                <h3 className="text-lg font-medium text-foreground mt-2">
                  Ready to test {currentAgent.name}
                </h3>
                <p className="max-w-md text-sm text-muted-foreground">
                  Type any prompt below or click a Quick Idea on the left. The agent will execute tools (Web Search, Fetch, Firecrawl) and stream its response in real time.
                </p>
              </div>
            )}
            
            {messages.map((msg) => (
              <div 
                key={msg.id} 
                className={cn(
                  "flex max-w-[90%] animate-in fade-in slide-in-from-bottom-2",
                  msg.role === 'user' ? "ml-auto" : "mr-auto"
                )}
              >
                {msg.role === 'agent' && (
                  <div className="mr-3 mt-1 flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-card border border-border flex items-center justify-center shadow-sm">
                      <Bot className="w-4 h-4 text-ibm-blue" />
                    </div>
                  </div>
                )}
                
                <div className="flex flex-col gap-1.5 w-full">
                  <div className="flex items-center gap-2 mb-1 px-1">
                    <span className="text-xs font-medium text-muted-foreground">
                      {msg.role === 'user' ? 'You' : currentAgent.name}
                    </span>
                    <span className="text-[10px] text-muted-foreground/60">
                      {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>

                  {/* AGENT THINKING PROCESS DROPDOWN / ACCORDION */}
                  {msg.role === 'agent' && (msg.thinking || (isGenerating && msg.id === messages[messages.length - 1]?.id)) && (
                    <div className="mb-2 border border-purple-500/30 rounded-lg overflow-hidden bg-purple-950/20">
                      <button
                        onClick={() => toggleThinking(msg.id)}
                        className="w-full px-3 py-2 flex items-center justify-between text-xs font-mono text-purple-300 hover:bg-purple-900/30 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <Brain className="w-3.5 h-3.5 text-purple-400 animate-pulse" />
                          <span>Agent Reasoning Process</span>
                          {isGenerating && msg.id === messages[messages.length - 1]?.id && (
                            <span className="text-[10px] bg-purple-500/30 text-purple-200 px-1.5 py-0.5 rounded font-mono animate-pulse">Thinking...</span>
                          )}
                        </div>
                        {expandedThinking[msg.id] ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>

                      {expandedThinking[msg.id] && (
                        <div className="p-3 border-t border-purple-500/20 font-mono text-xs text-purple-200/90 bg-black/40 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                          {msg.thinking || "Analyzing user prompt, retrieving persona instructions, and selecting appropriate tool execution flow..."}
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* EXECUTED TOOLS BADGES */}
                  {msg.role === 'agent' && msg.tools && msg.tools.length > 0 && (
                    <div className="mb-2 flex flex-col gap-2">
                      {msg.tools.map((tool, idx) => (
                        <div key={idx} className="text-xs border border-blue-500/30 bg-blue-950/20 rounded-md p-2 flex flex-col gap-1">
                          <div className="flex items-center gap-1.5 text-ibm-blue font-medium">
                            <Code className="w-3.5 h-3.5" /> Executed Tool: <span className="font-mono text-foreground font-semibold">{tool.name}</span>
                          </div>
                          <div className="text-muted-foreground font-mono text-[11px] max-h-24 overflow-y-auto whitespace-pre-wrap">
                            {tool.result}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* MESSAGE CONTENT CARD */}
                  <div 
                    className={cn(
                      "p-4 rounded-2xl shadow-sm leading-relaxed",
                      msg.role === 'user' 
                        ? "bg-ibm-blue text-white rounded-tr-sm" 
                        : "carbon-card border-border rounded-tl-sm whitespace-pre-wrap text-sm text-foreground"
                    )}
                  >
                    {msg.content || (msg.role === 'agent' && isGenerating ? (
                      <div className="flex items-center gap-2 text-muted-foreground font-mono text-xs">
                        <SiriFluidOrb state="thinking" size="xs" />
                        <span>Generating response...</span>
                      </div>
                    ) : '')}
                  </div>
                </div>
              </div>
            ))}
            
            <div ref={messagesEndRef} />
          </div>

          {/* INPUT BAR */}
          <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-background via-background to-transparent border-t border-border/20 z-20">
            <div className="max-w-4xl mx-auto flex items-end gap-2 carbon-card border border-border rounded-xl p-2 shadow-xl bg-card/90 backdrop-blur-md">
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder={`Message ${currentAgent.name}... (Ctrl+Enter to send)`}
                className="flex-1 max-h-32 min-h-[44px] bg-transparent border-0 resize-none focus:ring-0 focus:outline-none p-2 text-sm text-foreground placeholder:text-muted-foreground"
                rows={1}
              />
              {isGenerating ? (
                <Button 
                  size="icon" 
                  variant="destructive" 
                  onClick={handleStop}
                  title="Stop Generation"
                  className="rounded-lg mb-1 h-10 w-10 shrink-0 shadow-md animate-pulse"
                >
                  <StopCircle className="w-5 h-5" />
                </Button>
              ) : (
                <Button 
                  size="icon" 
                  onClick={() => handleSend()}
                  disabled={!inputText.trim()}
                  className="rounded-lg mb-1 h-10 w-10 shrink-0 bg-ibm-blue hover:bg-ibm-blue/90 text-white shadow-md"
                >
                  <Send className="w-4 h-4" />
                </Button>
              )}
            </div>
          </div>
        </main>

        {/* RIGHT PANEL */}
        <aside className="w-[300px] hidden lg:flex flex-col border-l border-border bg-card/30 p-4 gap-6 overflow-y-auto">
          <Card className="carbon-card border-border bg-transparent shadow-none">
            <CardHeader className="pb-3 px-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <Bot className="w-5 h-5 text-ibm-blue" /> 
                {currentAgent.name}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground space-y-4 px-2">
              <p className="leading-relaxed">{currentAgent.description}</p>
              
              <div>
                <h4 className="font-medium text-foreground mb-2 flex items-center gap-2 text-xs uppercase tracking-wider">
                  <Code className="w-3.5 h-3.5 text-ibm-blue" /> Active Tools
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {currentAgent.tools.map(tool => (
                    <span key={tool} className="text-[10px] font-mono px-2 py-1 rounded bg-background border border-border text-foreground flex items-center gap-1">
                      {tool.includes('Firecrawl') && <Flame className="w-3 h-3 text-orange-400" />}
                      {tool}
                    </span>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="space-y-4 px-2">
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-muted-foreground">Temperature</span>
                <span className="text-ibm-blue font-semibold">{temperature}</span>
              </div>
              <input 
                type="range" 
                min="0" 
                max="2" 
                step="0.1" 
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full accent-ibm-blue bg-secondary h-1.5 rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <div className="bg-background border border-border rounded-lg p-3">
              <div className="flex justify-between items-center text-xs font-mono">
                <span className="text-muted-foreground">Total Messages</span>
                <span className="text-foreground">{messages.length}</span>
              </div>
              <div className="flex justify-between items-center text-xs font-mono mt-2 pt-2 border-t border-border/50">
                <span className="text-muted-foreground">Est. Context Tokens</span>
                <span className="text-ibm-blue font-semibold">~{Math.round(messages.reduce((acc, msg) => acc + ((msg.content.length + (msg.thinking?.length || 0)) / 4), 0))}</span>
              </div>
            </div>

            <Button 
              variant="outline" 
              className="w-full flex items-center justify-center gap-2 border-border/50 hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30 transition-colors text-xs font-mono uppercase"
              onClick={handleClear}
              disabled={messages.length === 0}
            >
              <Trash2 className="w-3.5 h-3.5" /> Clear Session
            </Button>
          </div>
        </aside>
      </div>
    </div>
  );
};

export default IdeaPlayground;
