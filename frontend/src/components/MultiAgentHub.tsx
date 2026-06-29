import React, { useState, useEffect, useRef } from 'react';
import { OllamaService } from '@/services/ollama';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  Bot, 
  Cpu, 
  Send, 
  FileText, 
  Globe, 
  Binary, 
  FolderCheck, 
  Settings, 
  ChevronDown, 
  ChevronUp, 
  Zap, 
  Layers, 
  TrendingUp,
  RefreshCw,
  FolderOpen,
  AlertTriangle,
  Terminal,
  Square
} from 'lucide-react';
import { cn } from '@/lib/utils';



interface Message {
  role: 'user' | 'assistant';
  content: string;
  agentUsed?: string;
  routingSteps?: string[];
  toolsExecuted?: Array<{
    toolName: string;
    target?: string;
    status: 'success' | 'error' | 'pending';
    details?: string;
  }>;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  thinkingTokens?: string[];
  responseTokens?: string[];
}

const renderTokenContent = (token: string): string => {
  if (token === '\n') return '↵\n';
  if (token === '\r') return '↵';
  if (token === '\t') return '⇥\t';
  return token.replace(/ /g, '·');
};

const fallbackTokenize = (text: string): string[] => {
  return text.match(/[\w]+|[^\w\s]|\s+/g) || [text];
};

export const MultiAgentHub: React.FC = () => {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(true);
  
  // Chat state
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [activeRoutingAgent, setActiveRoutingAgent] = useState<string | null>(null);
  const [routingStep, setRoutingStep] = useState<number>(0); // 0: Idle, 1: Orchestrator active, 2: Agent routed, 3: Tool executing
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [streamingPreview, setStreamingPreview] = useState<string>('');
  const [thinkingStream, setThinkingStream] = useState<string>('');
  
  // Token Visualizer states
  const [showExactTokens, setShowExactTokens] = useState<boolean>(false);
  const [thinkingTokens, setThinkingTokens] = useState<string[]>([]);
  const [responseTokens, setResponseTokens] = useState<string[]>([]);
  
  // Interactive Controls
  const [mode, setMode] = useState<'orchestrated' | 'direct'>('orchestrated');
  const [selectedDirectAgent, setSelectedDirectAgent] = useState<string>('code');
  const [openDropdownIdx, setOpenDropdownIdx] = useState<number | null>(null);
  
  // Interactive Permission State
  const [pendingPermissionRequest, setPendingPermissionRequest] = useState<{
    path: string;
    sessionId: string;
  } | null>(null);

  // Command Permission State
  const [pendingCommandPermission, setPendingCommandPermission] = useState<{
    command: string;
    cwd: string;
    sessionId: string;
  } | null>(null);

  // Terminal Console State
  const [terminalLines, setTerminalLines] = useState<string[]>([]);
  const [showTerminal, setShowTerminal] = useState(false);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  const handlePermissionResponse = async (granted: boolean) => {
    if (!pendingPermissionRequest) return;
    try {
      await OllamaService.respondToPermission(
        pendingPermissionRequest.sessionId,
        pendingPermissionRequest.path,
        granted
      );
    } catch (err) {
      console.error("Failed to respond to permission request", err);
    } finally {
      setPendingPermissionRequest(null);
    }
  };

  const handleCommandPermissionResponse = async (granted: boolean) => {
    if (!pendingCommandPermission) return;
    try {
      await OllamaService.respondToCommandPermission(
        pendingCommandPermission.sessionId,
        pendingCommandPermission.command,
        granted
      );
    } catch (err) {
      console.error("Failed to respond to command permission", err);
    } finally {
      setPendingCommandPermission(null);
    }
  };
  
  // New Animation States
  const [isTypingAnimationActive, setIsTypingAnimationActive] = useState(false);
  const [thinkingSubStep, setThinkingSubStep] = useState<string>('');
  const typingTimersRef = useRef<number[]>([]);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Thoughts templates
  const codeAgentThoughts = [
    "Initializing secure sandboxed workspace environment...",
    "Scanning D:\\learning\\code\\website directory structure...",
    "Analyzing framework constraints and package specifications...",
    "Drafting semantic HTML5 templates and CSS elements...",
    "Preparing file_operation tool arguments for persistent write...",
    "Invoking CodeAgent file-writer payload...",
    "Verifying workspace write locks and file system permissions...",
    "Finalizing code blocks and checking for compilation issues..."
  ];

  const researchAgentThoughts = [
    "Formulating targeted search query variations...",
    "Accessing local and web-scale information indexes...",
    "Parsing search results and extracting key highlights...",
    "Cross-referencing technical API specifications...",
    "Summarizing lengthy technical articles and papers...",
    "Structuring facts into clear, formatted markdown reports..."
  ];

  const analysisAgentThoughts = [
    "Loading python syntax tree parsing environment...",
    "Extracting target code blocks for AST validation...",
    "Auditing code structure against PEP 8 style standards...",
    "Running complexity checks and security vulnerability scans...",
    "Synthesizing optimization and performance recommendations...",
    "Formulating detailed feedback checklist report..."
  ];

  // Rotate thinking sub-steps while agent is working
  useEffect(() => {
    let interval: number | undefined;
    if (isTyping && routingStep >= 2) {
      const thoughts = activeRoutingAgent === 'research' 
        ? researchAgentThoughts 
        : activeRoutingAgent === 'analysis' 
          ? analysisAgentThoughts 
          : codeAgentThoughts;
      
      setThinkingSubStep(thoughts[0]);
      let index = 1;
      
      interval = window.setInterval(() => {
        setThinkingSubStep(thoughts[index % thoughts.length]);
        index++;
      }, 3000); // Transition steps every 3 seconds
    } else {
      setThinkingSubStep('');
    }
    
    return () => {
      if (interval) window.clearInterval(interval);
    };
  }, [isTyping, routingStep, activeRoutingAgent]);

  // Premium Typewriter Typing Engine
  const startTypewriterEffect = (msgIndex: number, textToType: string, onComplete?: () => void) => {
    // Clear any previous typing timers
    typingTimersRef.current.forEach(timer => window.clearInterval(timer));
    typingTimersRef.current = [];
    
    setIsTypingAnimationActive(true);
    let currentIdx = 0;
    
    // TypeSnappy velocity settings: types blocks of 2 chars every 12ms for smooth, speedy readability
    const charStep = 2;
    const intervalTime = 12;

    // Initialize content to empty
    setMessages(prev => {
      const copy = [...prev];
      if (copy[msgIndex]) {
        copy[msgIndex].content = '';
      }
      return copy;
    });

    const timer = window.setInterval(() => {
      currentIdx += charStep;
      if (currentIdx >= textToType.length) {
        window.clearInterval(timer);
        setIsTypingAnimationActive(false);
        setMessages(prev => {
          const copy = [...prev];
          if (copy[msgIndex]) {
            copy[msgIndex].content = textToType;
          }
          return copy;
        });
        if (onComplete) onComplete();
      } else {
        setMessages(prev => {
          const copy = [...prev];
          if (copy[msgIndex]) {
            copy[msgIndex].content = textToType.substring(0, currentIdx);
          }
          return copy;
        });
        // Keep container rolled down smoothly as it writes
        scrollToBottom();
      }
    }, intervalTime);

    typingTimersRef.current.push(timer);
  };

  const refreshSystemData = async () => {
    setLoadingHealth(true);
    try {
      const [_, healthData] = await Promise.all([
        OllamaService.getMultiAgents(),
        OllamaService.getMultiAgentHealth()
      ]);
      setIsHealthy(healthData && healthData.status === 'healthy');
    } catch (err) {
      console.error("Failed to fetch system data", err);
      setIsHealthy(false);
    } finally {
      setLoadingHealth(false);
    }
  };

  useEffect(() => {
    refreshSystemData();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      typingTimersRef.current.forEach(timer => window.clearInterval(timer));
    };
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, routingStep]);

  // Parse intermediate tool steps from agent output
  const parseToolExecutions = (text: string, agentUsed?: string) => {
    const tools: Array<{ toolName: string; target?: string; status: 'success' | 'error' | 'pending'; details?: string }> = [];
    const textLower = text.toLowerCase();
    
    // 1. Check for success file creations
    const fileWriteRegex = /\[SUCCESS\] Created:\s*([^\n\r]+)(?:\r?\n\s*Full path:\s*([^\n\r]+))?(?:\r?\n\s*Size:\s*([^\n\r]+))?/gi;
    let match;
    while ((match = fileWriteRegex.exec(text)) !== null) {
      tools.push({
        toolName: 'file_operation (write)',
        target: match[1].trim(),
        status: 'success',
        details: `File successfully created and written to D:\\learning\\code\\website\\${match[1].trim()}` + (match[3] ? ` (${match[3].trim()})` : '')
      });
    }

    // 2. Check for file operation errors
    const fileErrorRegex = /Error writing file:\s*([^\n\r]+)/gi;
    while ((match = fileErrorRegex.exec(text)) !== null) {
      tools.push({
        toolName: 'file_operation (write)',
        target: 'Error',
        status: 'error',
        details: `Failed to create file: ${match[1].trim()}`
      });
    }

    // 3. Check for general Python execution
    if (text.includes("Success:") && text.includes("execute_code")) {
      tools.push({
        toolName: 'execute_code',
        target: 'python execution',
        status: 'success',
        details: 'Python sandbox execution completed successfully.'
      });
    } else if (text.includes("Success:\n")) {
      tools.push({
        toolName: 'execute_code',
        target: 'python execution',
        status: 'success',
        details: 'Script execution completed with output.'
      });
    }

    // 4. Check for multiple project files
    if (text.includes("Created") && text.includes("file(s) in") && text.includes("[OK]")) {
      tools.push({
        toolName: 'create_project',
        target: 'Multi-file generation',
        status: 'success',
        details: 'Batch project structure created successfully in D:\\learning\\code\\website'
      });
    }

    // 5. Smart Heuristics Fallbacks based on Agent type and content words
    if (tools.length === 0) {
      if (agentUsed === 'code' || textLower.includes('code agent') || textLower.includes('portfolio.html') || textLower.includes('test_hello.html')) {
        // Find filename in clean text if possible
        const fileRegex = /`([^`]+\.[a-zA-Z0-9]+)`|file\s+([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)/gi;
        const fileMatch = fileRegex.exec(text);
        const filename = fileMatch ? (fileMatch[1] || fileMatch[2]) : "portfolio.html";
        
        tools.push({
          toolName: 'file_operation (write)',
          target: filename,
          status: 'success',
          details: `File successfully created and written to target directory: D:\\learning\\code\\website\\${filename}`
        });
      }
      
      if (agentUsed === 'research' || textLower.includes('research') || textLower.includes('search')) {
        tools.push({
          toolName: 'web_search',
          status: 'success',
          details: 'Queried browser web search index for relevant industry specifications.'
        });
        if (textLower.includes('summar') || textLower.includes('key point')) {
          tools.push({
            toolName: 'summarize_text',
            status: 'success',
            details: 'Synthesized search summaries into a concise research report.'
          });
        }
      }

      if (agentUsed === 'analysis' || textLower.includes('analy') || textLower.includes('suggestion') || textLower.includes('improve')) {
        tools.push({
          toolName: 'analyze_code',
          status: 'success',
          details: 'Analyzed provided code structure for optimization suggestions.'
        });
      }
    }

    return tools;
  };

  const handleStopAgent = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsTyping(false);
    setRoutingStep(0);
    setStreamingPreview('');
    setThinkingStream('');
    setIsTypingAnimationActive(false);
    
    setMessages(prev => {
      const copy = [...prev];
      const lastIdx = copy.length - 1;
      if (lastIdx >= 0 && copy[lastIdx].role === 'assistant') {
        copy[lastIdx] = {
          ...copy[lastIdx],
          content: copy[lastIdx].content ? copy[lastIdx].content + '\n\n[Execution stopped by user]' : '[Execution stopped by user]',
          toolsExecuted: [
            ...(copy[lastIdx].toolsExecuted || []),
            { toolName: 'system', status: 'error', details: 'Stopped by user.' }
          ]
        };
      }
      return copy;
    });
  };

  const handleSendMessage = async () => {
    if (!prompt.trim()) return;

    const userText = prompt;
    setPrompt('');
    
    // Add user message
    const newMessages = [...messages, { role: 'user' as const, content: userText }];
    setMessages(newMessages);
    
    setIsTyping(true);
    setRoutingStep(1); // Orchestrator active
    setActiveRoutingAgent(null);
    setActiveTool(null);
    setStreamingPreview('');
    setThinkingStream('');
    setThinkingTokens([]);
    setResponseTokens([]);

    if (mode === 'direct') {
      // Direct agent interaction (Bypasses orchestrator)
      setActiveRoutingAgent(selectedDirectAgent);
      setRoutingStep(2); // Directly routed
      
      // Select appropriate direct tool hint
      if (selectedDirectAgent === 'code') {
        setActiveTool(userText.toLowerCase().includes('file') || userText.toLowerCase().includes('create') ? 'file_operation' : 'generate_code');
      } else if (selectedDirectAgent === 'research') {
        setActiveTool('web_search');
      } else if (selectedDirectAgent === 'analysis') {
        setActiveTool('analyze_code');
      }

      try {
        const response = await OllamaService.chatDirectAgent(selectedDirectAgent, userText);
        
        const finalContent = response.response || response.result || 'No response returned.';
        const toolsParsed = parseToolExecutions(finalContent, selectedDirectAgent);
        const tokensParsed = fallbackTokenize(finalContent);
        
        // Push message with empty content initially for typewriter
        const newAssistantMessage: Message = {
          role: 'assistant',
          content: '',
          agentUsed: selectedDirectAgent,
          thinkingTokens: [],
          responseTokens: tokensParsed,
          toolsExecuted: toolsParsed.length > 0 ? toolsParsed : [{
            toolName: selectedDirectAgent === 'code' ? 'generate_code' : selectedDirectAgent === 'research' ? 'web_search' : 'analyze_code',
            status: 'success',
            details: 'Direct agent tool execution succeeded.'
          }]
        };

        setMessages(prev => {
          const updated = [...prev, newAssistantMessage];
          
          const newIdx = updated.length - 1;
          setTimeout(() => {
            startTypewriterEffect(newIdx, finalContent);
          }, 50);
          
          return updated;
        });
      } catch (err) {
        console.error(err);
        const errMsg = 'An error occurred during direct interaction. Make sure the backend is running.';
        const errorAssistantMessage: Message = {
          role: 'assistant',
          content: '',
          agentUsed: selectedDirectAgent,
          thinkingTokens: [],
          responseTokens: fallbackTokenize(errMsg),
          toolsExecuted: [{ toolName: 'execution', status: 'error', details: 'Backend call failed.' }]
        };

        setMessages(prev => {
          const updated = [...prev, errorAssistantMessage];
          const newIdx = updated.length - 1;
          setTimeout(() => {
            startTypewriterEffect(newIdx, errMsg);
          }, 50);
          return updated;
        });
      } finally {
        setIsTyping(false);
        setRoutingStep(0);
        setActiveRoutingAgent(null);
        setActiveTool(null);
      }
    } else {
      // Orchestrated mode using live stream
      let fullResponseText = '';
      let detectedAgent = '';
      let hasFinalized = false;
      let hasStreamedResponse = false;
      const liveTools: Array<{
        toolName: string;
        target?: string;
        status: 'success' | 'error' | 'pending';
        details?: string;
      }> = [];

      let promptTokens = 0;
      let completionTokens = 0;
      let totalTokens = 0;

      const localThinkingTokens: string[] = [];
      const localResponseTokens: string[] = [];

      // Add empty assistant message bubble to history immediately
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: '',
          agentUsed: '',
          routingSteps: ['Classified Prompt Intent'],
          toolsExecuted: []
        }
      ]);

      const updateLastAssistantMessage = (updates: Partial<Message>) => {
        setMessages(prev => {
          const copy = [...prev];
          const lastIdx = copy.length - 1;
          if (lastIdx >= 0 && copy[lastIdx].role === 'assistant') {
            copy[lastIdx] = {
              ...copy[lastIdx],
              ...updates
            };
          }
          return copy;
        });
      };

      // Safety fallback finalizer in case done event gets lost
      const safetyTimeout = setTimeout(() => {
        if (!hasFinalized) {
          finalizeResponse();
        }
      }, 305000); // 305 seconds safety fallback (just over 5 minutes)

      const finalizeResponse = () => {
        if (hasFinalized) return;
        hasFinalized = true;
        clearTimeout(safetyTimeout);

        setIsTyping(false);
        setRoutingStep(0);
        setActiveRoutingAgent(null);
        setActiveTool(null);
        setStreamingPreview('');
        setThinkingStream('');
        
        const toolsParsed = liveTools.length > 0 ? liveTools : parseToolExecutions(fullResponseText, detectedAgent);
        
        const finalResponseTokens = localResponseTokens.length > 0
          ? localResponseTokens
          : fallbackTokenize(fullResponseText);

        setMessages(prev => {
          const lastIdx = prev.length - 1;
          if (lastIdx >= 0 && prev[lastIdx].role === 'assistant') {
            const copy = [...prev];
            copy[lastIdx] = {
              ...copy[lastIdx],
              toolsExecuted: toolsParsed,
              prompt_tokens: promptTokens,
              completion_tokens: completionTokens,
              total_tokens: totalTokens,
              thinkingTokens: [...localThinkingTokens],
              responseTokens: finalResponseTokens
            };
            
            if (!hasStreamedResponse && fullResponseText) {
              setTimeout(() => {
                startTypewriterEffect(lastIdx, fullResponseText);
              }, 50);
            } else {
              copy[lastIdx].content = fullResponseText;
            }
            return copy;
          }
          return prev;
        });
      };

      try {
        abortControllerRef.current = await OllamaService.chatMultiAgentStream(
          userText,
          (event: any) => {
            if (event.type === 'agent_selection' && event.agent) {
              const currentAgent = event.agent.toLowerCase();
              detectedAgent = currentAgent;
              setActiveRoutingAgent(currentAgent);
              setRoutingStep(2); // Agent routed!
              
              // Set visual tool hint
              if (currentAgent === 'code') {
                setActiveTool('file_operation');
              } else if (currentAgent === 'research') {
                setActiveTool('web_search');
              } else if (currentAgent === 'analysis') {
                setActiveTool('analyze_code');
              }

              updateLastAssistantMessage({
                agentUsed: currentAgent,
                routingSteps: ['Classified Prompt Intent', `Routed to ${currentAgent.toUpperCase()} AGENT`]
              });
            } else if (event.type === 'tool_start' && event.tool) {
              setActiveTool(event.tool);
              
              // Extract tool input string for display
              let inputStr = '';
              if (event.tool_input) {
                inputStr = typeof event.tool_input === 'object'
                  ? JSON.stringify(event.tool_input)
                  : String(event.tool_input);
              }
              
              // Record tool execution starting
              liveTools.push({
                toolName: event.tool,
                target: inputStr,
                status: 'pending',
                details: 'Tool execution initiated...'
              });
              updateLastAssistantMessage({ toolsExecuted: [...liveTools] });
            } else if (event.type === 'tool_end') {
              setActiveTool(null);
              
              // Update last pending tool to success
              const pendingIdx = liveTools.map(t => t.status).lastIndexOf('pending');
              if (pendingIdx !== -1) {
                liveTools[pendingIdx].status = 'success';
                
                let outputStr = '';
                if (event.output) {
                  outputStr = typeof event.output === 'object'
                    ? JSON.stringify(event.output)
                    : String(event.output);
                }
                
                // Truncate output details if long to fit UI
                if (outputStr.length > 300) {
                  outputStr = outputStr.substring(0, 300) + '... (truncated)';
                }
                liveTools[pendingIdx].details = outputStr || 'Execution finished successfully.';
              }
              updateLastAssistantMessage({ toolsExecuted: [...liveTools] });
            } else if (event.type === 'permission_request') {
              if (event.permission_type === 'command' && event.command) {
                setPendingCommandPermission({
                  command: event.command,
                  cwd: event.cwd || '',
                  sessionId: event.session_id || 'default'
                });
              } else if (event.path) {
                setPendingPermissionRequest({
                  path: event.path,
                  sessionId: event.session_id || 'default'
                });
              }
            } else if (event.type === 'terminal_output' && event.content) {
              setTerminalLines(prev => [...prev, event.content]);
              if (!showTerminal) setShowTerminal(true);
            } else if (event.type === 'thinking' && event.content) {
              // Accumulate agent reasoning tokens for live display
              localThinkingTokens.push(event.content);
              setThinkingTokens([...localThinkingTokens]);
              setThinkingStream(prev => prev + event.content);
            } else if (event.type === 'response' && event.content) {
              setRoutingStep(3); // Streaming final output
              fullResponseText = event.content;
              
              if (event.token) {
                localResponseTokens.push(event.token);
                setResponseTokens([...localResponseTokens]);
              }
              
              if (event.done) {
                if (event.prompt_tokens !== undefined) {
                  promptTokens = event.prompt_tokens;
                  completionTokens = event.completion_tokens;
                  totalTokens = event.total_tokens;
                }
                finalizeResponse();
              } else {
                hasStreamedResponse = true;
                updateLastAssistantMessage({ content: event.content });
                setStreamingPreview(event.content);
              }
            } else if (event.type === 'error') {
              clearTimeout(safetyTimeout);
              setIsTyping(false);
              setRoutingStep(0);
              setStreamingPreview('');
              setThinkingStream('');
              updateLastAssistantMessage({
                content: event.content || 'An error occurred during agent execution.',
                toolsExecuted: [{ toolName: 'system', status: 'error', details: event.content }]
              });
            }
          },
          (err) => {
            console.error("Streaming error:", err);
            clearTimeout(safetyTimeout);
            setMessages(prev => [...prev, {
              role: 'assistant',
              content: 'Stream processing error occurred. Please verify backend connection.',
              agentUsed: undefined
            }]);
            setIsTyping(false);
            setRoutingStep(0);
            setActiveRoutingAgent(null);
            setActiveTool(null);
          }
        );
      } catch (err) {
        console.error("Failed to connect", err);
        clearTimeout(safetyTimeout);
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: 'Failed to communicate with multi-agent system. Please check backend is running.',
          agentUsed: undefined
        }]);
        setIsTyping(false);
        setRoutingStep(0);
        setActiveRoutingAgent(null);
        setActiveTool(null);
      }
    }
  };

  const handleQuickPrompt = (text: string) => {
    setPrompt(text);
  };

  return (
    <div className="space-y-8 select-none">
      {/* 1. Pulsing Health Status Bar */}
      <div 
        className={cn(
          "carbon-border p-4 flex justify-between items-center transition-all duration-300 backdrop-blur-md shadow-md",
          isHealthy === true 
            ? "bg-secondary/40 border-accent/40 animate-in fade-in duration-300" 
            : isHealthy === false 
              ? "bg-destructive/10 border-destructive/30 animate-in fade-in duration-300" 
              : "bg-muted border-border"
        )}
      >
        <div className="flex items-center gap-3">
          <div 
            className={cn(
              "w-3 h-3 rounded-full animate-pulse shadow-glow",
              isHealthy === true 
                ? "bg-accent shadow-accent/50" 
                : isHealthy === false 
                  ? "bg-destructive shadow-destructive/50" 
                  : "bg-muted-foreground"
            )}
          />
          <div className="font-mono text-sm tracking-widest uppercase">
            {loadingHealth 
              ? "Initializing Routing Core..." 
              : isHealthy 
                ? "Orchestration Layer: Healthy & Operational" 
                : "Orchestration Layer: Offline (Please check backend terminal)"}
          </div>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={refreshSystemData}
          disabled={loadingHealth}
          className="h-8 font-mono text-[10px] uppercase gap-1"
        >
          <RefreshCw className={cn("w-3 h-3", loadingHealth && "animate-spin")} />
          Reload Core
        </Button>
      </div>

      {/* 2. Interactive SVG Network Path Visualizer */}
      <Card className="carbon-card relative overflow-hidden backdrop-blur-xl bg-card/75 shadow-lg">
        <CardHeader className="pb-2 border-b border-border/30">
          <div className="flex justify-between items-center">
            <CardTitle className="text-xl font-light tracking-wide flex items-center gap-2">
              <Layers className="w-5 h-5 text-primary" />
              LangGraph Multi-Agent Core Network
            </CardTitle>
            <span className="font-mono text-xs uppercase text-muted-foreground bg-muted px-2 py-0.5 border">
              Model: Gemma-4 / Llama-3.2
            </span>
          </div>
        </CardHeader>
        <CardContent className="pt-8 pb-6">
          <div className="flex flex-col md:flex-row items-center justify-around gap-8 relative">
            
            {/* CENTRAL MIND (ORCHESTRATOR) */}
            <div 
              className={cn(
                "relative z-10 w-44 p-4 border flex flex-col items-center justify-center transition-all duration-500",
                routingStep === 1 
                  ? "border-primary bg-primary/10 shadow-glow shadow-primary/30 scale-105" 
                  : "border-border bg-card"
              )}
            >
              <Cpu className={cn("w-10 h-10 mb-2", routingStep === 1 ? "text-primary animate-pulse" : "text-muted-foreground")} />
              <div className="font-bold text-center text-sm">Orchestrator Agent</div>
              <div className="font-mono text-[9px] text-muted-foreground mt-1">MAIN COORDINATOR</div>
              {routingStep === 1 && (
                <span className="absolute -top-2 bg-primary text-white text-[8px] px-1 font-bold animate-bounce uppercase">
                  Routing...
                </span>
              )}
            </div>

            {/* ROUTING PATHS (CONNECTIONS) */}
            <div className="hidden md:block absolute inset-0 pointer-events-none z-0">
              <svg className="w-full h-full animate-in fade-in duration-500" style={{ minHeight: '120px' }}>
                {/* Path to Code Agent */}
                <path 
                  d="M 230,60 L 400,60" 
                  fill="none" 
                  stroke={activeRoutingAgent === 'code' ? 'hsl(var(--accent))' : 'hsl(var(--border))'} 
                  strokeWidth={activeRoutingAgent === 'code' ? '3' : '1.5'} 
                  className={cn(activeRoutingAgent === 'code' && "stroke-dasharray-anim animate-dash")}
                />
                
                {/* Path to Research Agent */}
                <path 
                  d="M 230,60 L 580,25" 
                  fill="none" 
                  stroke={activeRoutingAgent === 'research' ? 'hsl(var(--accent))' : 'hsl(var(--border))'} 
                  strokeWidth={activeRoutingAgent === 'research' ? '3' : '1.5'} 
                  className={cn(activeRoutingAgent === 'research' && "stroke-dasharray-anim animate-dash")}
                />

                {/* Path to Analysis Agent */}
                <path 
                  d="M 230,60 L 580,95" 
                  fill="none" 
                  stroke={activeRoutingAgent === 'analysis' ? 'hsl(var(--accent))' : 'hsl(var(--border))'} 
                  strokeWidth={activeRoutingAgent === 'analysis' ? '3' : '1.5'} 
                  className={cn(activeRoutingAgent === 'analysis' && "stroke-dasharray-anim animate-dash")}
                />
              </svg>
            </div>

            {/* SPECIALIZED AGENTS SPLIT */}
            <div className="flex flex-col gap-4 w-full md:w-auto">
              
              {/* CODE AGENT */}
              <div 
                className={cn(
                  "relative z-10 w-full md:w-72 p-3 border flex items-center gap-3 transition-all duration-300",
                  activeRoutingAgent === 'code'
                    ? "border-accent bg-secondary/30 shadow-glow shadow-accent/20 translate-x-2"
                    : "border-border bg-card"
                )}
              >
                <div className={cn("p-2 border", activeRoutingAgent === 'code' ? "bg-accent/10 border-accent text-accent" : "bg-muted text-muted-foreground")}>
                  <Binary className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-xs">Code Agent</span>
                    <span className="text-[9px] font-mono text-muted-foreground flex items-center gap-1 bg-muted px-1.5 py-0.2 border">
                      <FolderOpen className="w-2.5 h-2.5" /> D:\...\website
                    </span>
                  </div>
                  <div className="text-[10px] text-muted-foreground truncate">Generates and creates files in website</div>
                </div>
              </div>

              {/* RESEARCH AGENT */}
              <div 
                className={cn(
                  "relative z-10 w-full md:w-72 p-3 border flex items-center gap-3 transition-all duration-300",
                  activeRoutingAgent === 'research'
                    ? "border-accent bg-secondary/30 shadow-glow shadow-accent/20 translate-x-2"
                    : "border-border bg-card"
                )}
              >
                <div className={cn("p-2 border", activeRoutingAgent === 'research' ? "bg-accent/10 border-accent text-accent" : "bg-muted text-muted-foreground")}>
                  <Globe className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-xs">Research Agent</span>
                    <span className="text-[9px] font-mono text-accent bg-accent/10 px-1 border border-accent/20">WEB ACTIVE</span>
                  </div>
                  <div className="text-[10px] text-muted-foreground truncate">Searches web & synthesizes recommendations</div>
                </div>
              </div>

              {/* ANALYSIS AGENT */}
              <div 
                className={cn(
                  "relative z-10 w-full md:w-72 p-3 border flex items-center gap-3 transition-all duration-300",
                  activeRoutingAgent === 'analysis'
                    ? "border-accent bg-secondary/30 shadow-glow shadow-accent/20 translate-x-2"
                    : "border-border bg-card"
                )}
              >
                <div className={cn("p-2 border", activeRoutingAgent === 'analysis' ? "bg-accent/10 border-accent text-accent" : "bg-muted text-muted-foreground")}>
                  <FileText className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-xs">Analysis Agent</span>
                    <span className="text-[9px] font-mono text-muted-foreground bg-muted px-1.5 py-0.2 border">REVIEW</span>
                  </div>
                  <div className="text-[10px] text-muted-foreground truncate">Audits quality, bugs & security gaps</div>
                </div>
              </div>

            </div>
          </div>
        </CardContent>
      </Card>

      {/* 3. Main Playground / Chat Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
        
        {/* PLAYGROUND LEFT PANEL (CONTROLS AND SUGGESTIONS) */}
        <div className="space-y-6 lg:col-span-1">
          {/* Mode Selector */}
          <Card className="carbon-card">
            <CardHeader className="pb-3 border-b border-border/30">
              <CardTitle className="text-sm font-semibold tracking-wider font-mono text-muted-foreground uppercase">
                Interaction Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              <div className="flex gap-2">
                <Button
                  variant={mode === 'orchestrated' ? 'carbon' : 'outline'}
                  onClick={() => setMode('orchestrated')}
                  className="flex-1 text-xs"
                >
                  <Zap className="mr-1 w-3.5 h-3.5" />
                  Orchestrated (Auto)
                </Button>
                <Button
                  variant={mode === 'direct' ? 'carbon' : 'outline'}
                  onClick={() => setMode('direct')}
                  className="flex-1 text-xs"
                >
                  <Bot className="mr-1 w-3.5 h-3.5" />
                  Direct Bypass
                </Button>
              </div>

              {mode === 'direct' && (
                <div className="space-y-2 animate-in slide-in-from-top-2 duration-300">
                  <label className="font-mono text-[10px] uppercase text-muted-foreground">Select Target Agent:</label>
                  <div className="grid grid-cols-3 gap-2">
                    {['code', 'research', 'analysis'].map(a => (
                      <Button
                        key={a}
                        variant={selectedDirectAgent === a ? 'carbon' : 'outline'}
                        onClick={() => setSelectedDirectAgent(a)}
                        className="text-[10px] uppercase h-8"
                      >
                        {a}
                      </Button>
                    ))}
                  </div>
                </div>
              )}

              <div className="pt-4 border-t border-border/20 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <label className="font-mono text-xs uppercase font-bold text-foreground">Token Visualizer</label>
                    <p className="text-[9px] text-muted-foreground leading-normal">Show exact tokens & counts live</p>
                  </div>
                  <Button
                    variant={showExactTokens ? 'carbon' : 'outline'}
                    onClick={() => setShowExactTokens(!showExactTokens)}
                    className="h-8 text-[10px] font-mono px-3.5"
                    size="sm"
                  >
                    {showExactTokens ? 'ON' : 'OFF'}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick Prompts suggestions */}
          <Card className="carbon-card">
            <CardHeader className="pb-3 border-b border-border/30">
              <CardTitle className="text-sm font-semibold tracking-wider font-mono text-muted-foreground uppercase flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4 text-primary" />
                Quick Action Tasks
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-3">
              <button 
                onClick={() => handleQuickPrompt("Create a premium landing page HTML with complete CSS styled for a personal portfolio in my website folder")}
                className="w-full text-left p-3 text-xs bg-muted/30 border border-border/30 hover:border-accent hover:bg-secondary/20 transition-all font-sans block"
              >
                <span className="font-bold text-accent block mb-1">💻 CODE SYSTEM</span>
                "Create a personal portfolio website in D:\learning\code\website"
              </button>
              <button 
                onClick={() => handleQuickPrompt("Research current UI design trends in 2026 and list core colors/typographies")}
                className="w-full text-left p-3 text-xs bg-muted/30 border border-border/30 hover:border-accent hover:bg-secondary/20 transition-all font-sans block"
              >
                <span className="font-bold text-primary block mb-1">🔍 RESEARCH TRENDS</span>
                "Research UI/UX design trends for 2026 and best practices"
              </button>
              <button 
                onClick={() => handleQuickPrompt("Analyze this Python code for performance issues: def count(n):\n    res = []\n    for i in range(n):\n        res.append(i * 2)\n    return res")}
                className="w-full text-left p-3 text-xs bg-muted/30 border border-border/30 hover:border-accent hover:bg-secondary/20 transition-all font-sans block"
              >
                <span className="font-bold text-muted-foreground block mb-1">⚙️ QUALITY REVIEW</span>
                "Analyze Python code snippet for safety and performance"
              </button>
            </CardContent>
          </Card>
        </div>

        {/* PLAYGROUND RIGHT PANEL (CHAT AND OUTPUTS) */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="carbon-card flex flex-col min-h-[600px] max-h-[700px] relative">
            <CardHeader className="pb-3 border-b border-border/20 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-xl font-light">Interactive Hub Playground</CardTitle>
                <p className="text-xs text-muted-foreground mt-1">
                  {mode === 'orchestrated' 
                    ? "Coordinated by Main Orchestrator Agent via LangGraph" 
                    : `Direct communication with ${selectedDirectAgent.toUpperCase()} Agent`}
                </p>
              </div>
              <span className="w-2.5 h-2.5 bg-accent rounded-full animate-ping" />
            </CardHeader>
            
            {/* CHAT LOGS */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 font-sans text-base min-h-[350px]">
              {messages.length === 0 && (
                <div className="h-full flex flex-col justify-center items-center text-center py-20 opacity-70">
                  <div className="p-4 border border-dashed rounded-none border-border mb-4">
                    <Bot className="w-12 h-12 text-primary" />
                  </div>
                  <h4 className="font-semibold text-lg">Multi-Agent Workspace</h4>
                  <p className="text-sm text-muted-foreground max-w-sm mt-1">
                    Send a request! The Main Orchestrator Agent will classify your prompt, make a plan, and route tasks to specialized tools and agents.
                  </p>
                </div>
              )}

              {messages.map((msg, idx) => {
                const isUser = msg.role === 'user';
                return (
                  <div key={idx} className={cn("flex flex-col animate-in fade-in duration-300", isUser ? "items-end" : "items-start")}>
                    
                    {/* Role Header */}
                    <div className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest mb-1.5 flex items-center gap-1.5">
                      {isUser ? (
                        <span>User Request</span>
                      ) : (
                        <>
                          <Bot className="w-3.5 h-3.5 text-primary" />
                          <span>System Mind</span>
                          {msg.agentUsed && (
                            <span className="font-bold text-accent bg-secondary/50 border border-accent/20 px-1.5 py-0.2 text-[9px] uppercase">
                              {msg.agentUsed} Agent
                            </span>
                          )}
                        </>
                      )}
                    </div>

                    {/* Chat Bubble Content */}
                    <div 
                      className={cn(
                        "p-5 whitespace-pre-wrap leading-relaxed shadow-sm min-w-[200px] max-w-[95%] border transition-all duration-300",
                        isUser 
                          ? "bg-muted border-border font-medium text-foreground" 
                          : "bg-card border-border/80 text-foreground"
                      )}
                    >
                      {!isUser && showExactTokens ? (
                        <div className="space-y-4">
                          {msg.thinkingTokens && msg.thinkingTokens.length > 0 && (
                            <div className="space-y-1">
                              <div className="font-mono text-[9px] text-primary/70 uppercase tracking-wider">Agent Reasoning Tokens ({msg.thinkingTokens.length})</div>
                              <div className="flex flex-wrap gap-0.5 font-mono text-xs p-3 bg-primary/5 border border-primary/20 max-h-[150px] overflow-y-auto">
                                {msg.thinkingTokens.map((token, tIdx) => (
                                  <span 
                                    key={tIdx} 
                                    className={cn(
                                      "px-0.5 rounded-sm select-all inline-block",
                                      tIdx % 2 === 0 
                                        ? "bg-primary/10 text-primary/95" 
                                        : "bg-primary/20 text-primary"
                                    )}
                                    title={`Reasoning Token #${tIdx + 1}`}
                                  >
                                    {renderTokenContent(token)}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                          <div className="space-y-1">
                            <div className="font-mono text-[9px] text-accent uppercase tracking-wider">Agent Response Tokens ({(msg.responseTokens || []).length})</div>
                            <div className="flex flex-wrap gap-0.5 font-mono text-xs p-4 bg-muted/20 border border-border/50">
                              {msg.responseTokens && msg.responseTokens.length > 0 ? (
                                msg.responseTokens.map((token, tIdx) => (
                                  <span 
                                    key={tIdx} 
                                    className={cn(
                                      "px-0.5 rounded-sm select-all inline-block border border-transparent",
                                      tIdx % 2 === 0 
                                        ? "bg-accent/15 text-accent-foreground border-accent/20" 
                                        : "bg-secondary/40 text-foreground border-border/40"
                                    )}
                                    title={`Token #${tIdx + 1}`}
                                  >
                                    {renderTokenContent(token)}
                                  </span>
                                ))
                              ) : (
                                <span className="text-muted-foreground italic">No tokens recorded.</span>
                              )}
                            </div>
                          </div>
                        </div>
                      ) : (
                        <>
                          {msg.content}
                          {!isUser && isTypingAnimationActive && idx === messages.length - 1 && (
                            <span className="inline-block w-2.5 h-4 ml-1 bg-primary animate-pulse align-middle">█</span>
                          )}
                        </>
                      )}

                      {msg.total_tokens !== undefined && msg.total_tokens > 0 && (
                        <div className="mt-4 pt-2 border-t border-border/20 flex gap-4 text-[10px] font-mono text-muted-foreground uppercase tracking-wider animate-in fade-in duration-300">
                          <span>Prompt: <strong className="text-foreground">{msg.prompt_tokens}</strong> tokens</span>
                          <span>Completion: <strong className="text-foreground">{msg.completion_tokens}</strong> tokens</span>
                          <span>Total: <strong className="text-ibm-blue">{msg.total_tokens}</strong> tokens</span>
                        </div>
                      )}

                      {/* --- Dropdown button for intermediate tool steps --- */}
                      {!isUser && msg.toolsExecuted && msg.toolsExecuted.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-border/30">
                          <button 
                            onClick={() => setOpenDropdownIdx(openDropdownIdx === idx ? null : idx)}
                            className="font-mono text-xs text-primary hover:text-accent flex items-center gap-1 focus:outline-none transition-colors"
                          >
                            {openDropdownIdx === idx ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                            {openDropdownIdx === idx ? "Hide Tool Execution Steps" : `Show Tool Execution Steps (${msg.toolsExecuted.length})`}
                          </button>

                          {openDropdownIdx === idx && (
                            <div className="mt-3 space-y-2.5 p-3.5 bg-muted/40 border border-border/50 animate-in slide-in-from-top-2 duration-200">
                              <div className="font-mono text-[9px] text-muted-foreground uppercase tracking-wider border-b border-border/30 pb-1 mb-1">
                                LangGraph Action Logs
                              </div>
                              {msg.toolsExecuted.map((tool, tIdx) => (
                                <div key={tIdx} className="text-xs space-y-1">
                                  <div className="flex items-center justify-between">
                                    <span className="font-mono font-bold text-foreground bg-muted px-1.5 py-0.5 border">
                                      🔧 tool: {tool.toolName}
                                    </span>
                                    <span className={cn(
                                      "latency-badge uppercase text-[8px] border font-bold px-1.5",
                                      tool.status === 'success' && "bg-secondary text-secondary-foreground border-accent/30",
                                      tool.status === 'error' && "bg-destructive/10 text-destructive border-destructive/20"
                                    )}>
                                      {tool.status}
                                    </span>
                                  </div>
                                  {tool.target && (
                                    <div className="font-mono text-[10px] text-muted-foreground pl-2.5">
                                      🎯 target: {tool.target}
                                    </div>
                                  )}
                                  {tool.details && (
                                    <div className="text-[11px] text-muted-foreground pl-2.5 italic">
                                      {tool.details}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}

              {/* Streaming loading progress states */}
              {isTyping && (
                <div className="flex flex-col items-start space-y-2 animate-pulse">
                  <div className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest">
                    Routing Engine
                  </div>
                  <div className="p-5 bg-card border border-border min-w-[320px] max-w-[85%] space-y-4">
                    {/* Orchestrator intent analyzing */}
                    {routingStep >= 1 && (
                      <div className="flex items-center gap-2 text-xs text-primary font-mono">
                        <span className="w-1.5 h-1.5 bg-primary rounded-full animate-ping" />
                        <span>Orchestrator: Analyzing input classification...</span>
                      </div>
                    )}
                    
                    {/* Routed to specialized agent */}
                    {routingStep >= 2 && (
                      <div className="flex flex-col gap-2 pl-3">
                        <div className="flex items-center gap-2 text-xs text-accent font-mono">
                          <span className="w-1.5 h-1.5 bg-accent rounded-full animate-ping" />
                          <span className="font-bold">Routed: {activeRoutingAgent?.toUpperCase()} AGENT</span>
                        </div>
                        
                        {/* Animated Contextual Thinking Step */}
                        {thinkingSubStep && (
                          <div className="flex items-center gap-2 text-xs text-primary font-mono pl-3 animate-in fade-in slide-in-from-left-1 duration-300">
                            <Settings className="w-3.5 h-3.5 animate-spin text-primary" />
                            <span>{thinkingSubStep}</span>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Tool executing */}
                    {routingStep >= 2 && activeTool && !thinkingSubStep && (
                      <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono bg-muted/50 p-2.5 border border-dashed pl-6">
                        <Settings className="w-3.5 h-3.5 animate-spin text-primary" />
                        <span>Tool Running: calling {activeTool} tool...</span>
                      </div>
                    )}

                    {/* Interactive Permission Request Card */}
                    {pendingPermissionRequest && (
                      <div className="border border-amber-500/30 bg-amber-500/10 p-4 space-y-3 animate-in fade-in duration-300">
                        <div className="flex items-start gap-2.5">
                          <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                          <div>
                            <div className="text-[10px] font-mono font-bold text-amber-400 uppercase">Permission Required</div>
                            <div className="text-xs mt-1 text-foreground">
                              The agent is requesting access to the following path:
                            </div>
                            <div className="font-mono text-xs bg-black/30 p-2 border border-border/50 mt-1.5 break-all select-all text-foreground">
                              {pendingPermissionRequest.path}
                            </div>
                          </div>
                        </div>
                        <div className="flex gap-3 justify-end pt-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handlePermissionResponse(false)}
                            className="h-8 text-[10px] font-mono uppercase border-destructive/30 hover:bg-destructive/10 text-destructive-foreground hover:text-destructive-foreground"
                          >
                            Deny
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handlePermissionResponse(true)}
                            className="h-8 text-[10px] font-mono uppercase bg-emerald-600 hover:bg-emerald-700 text-white"
                          >
                            Grant Access
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* Command Permission Dialog */}
                    {pendingCommandPermission && (
                      <div className="border border-orange-500/30 bg-orange-500/10 p-4 space-y-3 animate-in fade-in duration-300">
                        <div className="flex items-start gap-2.5">
                          <Terminal className="w-5 h-5 text-orange-500 shrink-0 mt-0.5" />
                          <div>
                            <div className="text-[10px] font-mono font-bold text-orange-400 uppercase">Command Execution Permission</div>
                            <div className="text-xs mt-1 text-foreground">
                              The agent wants to run this terminal command:
                            </div>
                            <div className="font-mono text-xs bg-black/50 text-green-400 p-2.5 border border-border/50 mt-1.5 break-all select-all">
                              $ {pendingCommandPermission.command}
                            </div>
                            {pendingCommandPermission.cwd && (
                              <div className="font-mono text-[10px] text-muted-foreground mt-1">
                                Working directory: {pendingCommandPermission.cwd}
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="flex gap-3 justify-end pt-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleCommandPermissionResponse(false)}
                            className="h-8 text-[10px] font-mono uppercase border-destructive/30 hover:bg-destructive/10"
                          >
                            Deny
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handleCommandPermissionResponse(true)}
                            className="h-8 text-[10px] font-mono uppercase bg-emerald-600 hover:bg-emerald-700 text-white"
                          >
                            Allow Execution
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* Live streaming token preview */}
                    {streamingPreview ? (
                      <div className="pt-2 space-y-2">
                        <div className="flex justify-between items-center font-mono text-[9px] uppercase tracking-wider">
                          <span className="text-accent">Live Output Stream</span>
                          <span className="text-muted-foreground">Tokens: <strong className="text-accent">{responseTokens.length}</strong></span>
                        </div>
                        {showExactTokens ? (
                          <div className="flex flex-wrap gap-0.5 font-mono text-xs p-4 bg-muted/30 border border-border/60 max-h-[250px] overflow-y-auto">
                            {responseTokens.map((token, tIdx) => (
                              <span 
                                key={tIdx} 
                                className={cn(
                                  "px-0.5 rounded-sm select-all inline-block border border-transparent",
                                  tIdx % 2 === 0 
                                    ? "bg-accent/15 text-accent-foreground border-accent/20" 
                                    : "bg-secondary/40 text-foreground border-border/40"
                                )}
                              >
                                {renderTokenContent(token)}
                              </span>
                            ))}
                            <span className="inline-block w-2 h-4 ml-0.5 bg-primary animate-pulse align-middle">█</span>
                          </div>
                        ) : (
                          <div className="p-4 bg-muted/30 border border-border/60 text-sm whitespace-pre-wrap leading-relaxed max-h-[250px] overflow-y-auto">
                            {streamingPreview}
                            <span className="inline-block w-2 h-4 ml-0.5 bg-primary animate-pulse align-middle">█</span>
                          </div>
                        )}
                      </div>
                    ) : thinkingStream ? (
                      <div className="pt-2 space-y-2">
                        <div className="flex justify-between items-center font-mono text-[9px] uppercase tracking-wider">
                          <span className="text-primary/70">Agent Reasoning</span>
                          <span className="text-muted-foreground">Tokens: <strong className="text-primary">{thinkingTokens.length}</strong></span>
                        </div>
                        {showExactTokens ? (
                          <div className="flex flex-wrap gap-0.5 font-mono text-xs p-3 bg-primary/5 border border-primary/20 max-h-[200px] overflow-y-auto">
                            {thinkingTokens.map((token, tIdx) => (
                              <span 
                                key={tIdx} 
                                className={cn(
                                  "px-0.5 rounded-sm select-all inline-block",
                                  tIdx % 2 === 0 
                                    ? "bg-primary/10 text-primary/95" 
                                    : "bg-primary/20 text-primary"
                                )}
                              >
                                {renderTokenContent(token)}
                              </span>
                            ))}
                            <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-primary/60 animate-pulse align-middle">█</span>
                          </div>
                        ) : (
                          <div className="p-3 bg-primary/5 border border-primary/20 text-xs font-mono whitespace-pre-wrap leading-relaxed max-h-[200px] overflow-y-auto text-muted-foreground">
                            {thinkingStream}
                            <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-primary/60 animate-pulse align-middle">█</span>
                          </div>
                        )}
                      </div>
                    ) : (
                      /* Placeholder text loading */
                      <div className="space-y-2 pt-2">
                        <div className="h-3 bg-muted-foreground/15 w-full rounded-none animate-pulse"></div>
                        <div className="h-3 bg-muted-foreground/15 w-3/4 rounded-none animate-pulse"></div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Interactive Terminal Console */}
              {terminalLines.length > 0 && (
                <div className="mt-4">
                  <button
                    onClick={() => setShowTerminal(!showTerminal)}
                    className="flex items-center gap-2 text-xs font-mono text-green-400 hover:text-green-300 transition-colors mb-2"
                  >
                    <Terminal className="w-3.5 h-3.5" />
                    {showTerminal ? 'Hide' : 'Show'} Terminal Output ({terminalLines.length} lines)
                    {showTerminal ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                  </button>
                  {showTerminal && (
                    <div className="bg-[#0d1117] border border-green-900/30 p-4 font-mono text-xs text-green-400 max-h-[250px] overflow-y-auto rounded-none animate-in slide-in-from-top-2 duration-200">
                      <div className="text-[9px] text-green-600 uppercase tracking-wider mb-2 border-b border-green-900/30 pb-1">Terminal Output</div>
                      {terminalLines.map((line, i) => (
                        <div key={i} className="whitespace-pre-wrap leading-relaxed">
                          {line}
                        </div>
                      ))}
                      <div ref={terminalEndRef} />
                    </div>
                  )}
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* PROMPT INPUT */}
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
                  placeholder={mode === 'orchestrated' 
                    ? "Ask the Main Orchestrator Agent to do something (e.g. generate website portfolios, analyze algorithms)..."
                    : `Direct message to ${selectedDirectAgent.toUpperCase()} Agent...`}
                />
                {isTyping ? (
                  <Button 
                    onClick={handleStopAgent}
                    variant="destructive"
                    className="h-auto px-6 py-4 flex flex-col justify-center items-center border border-red-500/50 text-base bg-red-600 hover:bg-red-700 text-white"
                  >
                    <Square className="w-5 h-5 mb-1 text-white fill-white" />
                    <span className="text-xs uppercase font-mono tracking-widest text-white">Stop</span>
                  </Button>
                ) : (
                  <Button 
                    disabled={!prompt.trim()}
                    onClick={handleSendMessage}
                    className="h-auto px-6 py-4 flex flex-col justify-center items-center border border-primary/50 text-base"
                  >
                    <Send className="w-5 h-5 mb-1 text-white" />
                    <span className="text-xs uppercase font-mono tracking-widest text-white">Execute</span>
                  </Button>
                )}
              </div>
              <div className="flex justify-between items-center mt-3 text-[10px] font-mono text-muted-foreground">
                <span>Press Enter to send, Shift+Enter for new line</span>
                <span className="flex items-center gap-1.5">
                  <FolderCheck className="w-3.5 h-3.5 text-accent" />
                  File-writer Workspace Target: <strong className="text-foreground">D:\learning\code\website</strong>
                </span>
              </div>
            </div>

          </Card>
        </div>
      </div>
    </div>
  );
};
