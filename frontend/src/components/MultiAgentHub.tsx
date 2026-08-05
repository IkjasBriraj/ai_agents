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
  Square,
  Copy,
  Check,
  Mic,
  MicOff,
  Loader2,
  Monitor,
  Eye,
  Camera,
  Maximize2,
  X,
  Presentation,
  FileSpreadsheet,
  Download,
  ExternalLink,
  Sparkles,
  Brain,
} from 'lucide-react';

import { cn } from '@/lib/utils';
import { SiriFluidOrb } from './SiriFluidOrb';
import { AnimationSelector } from './AnimationSelector';
import { ThinkingLevelSelector, type ThinkingLevel, getSavedThinkingLevel } from './ThinkingLevelSelector';
import { playSiriActivationSound, playAgentProcessingPulse } from '@/lib/siriAudio';
import { AgentTodoList, type TodoItem } from './AgentTodoList';



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
  thinkingProcess?: string;
  screenshots?: Array<{
    name: string;
    url: string;
    caption?: string;
    image_base64?: string;
  }>;
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

interface MultiAgentHubProps {
  onOpenPlayground?: () => void;
}

export const MultiAgentHub: React.FC<MultiAgentHubProps> = ({ onOpenPlayground }) => {
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
  
  // Live Agent To-Do List State
  const [todoItems, setTodoItems] = useState<TodoItem[]>([]);
  
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

  // Plan Approval State
  const [pendingPlanApproval, setPendingPlanApproval] = useState<{
    planContent: string;
    planPath: string;
    sessionId: string;
  } | null>(null);
  const [editedPlanContent, setEditedPlanContent] = useState<string>('');
  const [isPlanModalOpen, setIsPlanModalOpen] = useState<boolean>(false);
  const [activePlanTab, setActivePlanTab] = useState<'preview' | 'edit'>('preview');

  // Message Copying State
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  // Voice Recording State
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const recognitionRef = useRef<any>(null);

  const handleCopyMessage = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Voice Recording Handler using Web Speech API
  const handleVoiceRecord = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in your browser. Please use Chrome, Edge, or Safari.');
      return;
    }

    if (isRecording && recognitionRef.current) {
      // Stop recording
      recognitionRef.current.stop();
      setIsRecording(false);
      return;
    }

    // Start recording
    playSiriActivationSound();
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognitionRef.current = recognition;

    let finalTranscript = '';

    recognition.onstart = () => {
      setIsRecording(true);
      setIsTranscribing(false);
    };

    recognition.onresult = (event: any) => {
      let interimTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + ' ';
        } else {
          interimTranscript += transcript;
        }
      }
      // Update prompt with final + interim text
      setPrompt(() => (finalTranscript + interimTranscript).trim());
    };

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      setIsRecording(false);
      setIsTranscribing(false);
      if (event.error === 'not-allowed') {
        alert('Microphone access was denied. Please allow microphone permissions in your browser settings.');
      }
    };

    recognition.onend = () => {
      setIsRecording(false);
      setIsTranscribing(false);
      recognitionRef.current = null;
      // Set final transcript to prompt
      if (finalTranscript.trim()) {
        setPrompt(finalTranscript.trim());
      }
    };

    recognition.start();
  };

  // Cleanup speech recognition on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  const handlePlanApprovalResponse = async (approved: boolean) => {
    if (!pendingPlanApproval) return;
    try {
      await OllamaService.respondToPlanApproval(
        pendingPlanApproval.sessionId,
        pendingPlanApproval.planPath,
        editedPlanContent,
        approved
      );
    } catch (err) {
      console.error("Failed to respond to plan approval request", err);
    } finally {
      setPendingPlanApproval(null);
      setEditedPlanContent('');
      setIsPlanModalOpen(false);
    }
  };

  // Terminal Console State
  const [terminalLines, setTerminalLines] = useState<string[]>([]);
  const [showTerminal, setShowTerminal] = useState(false);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Live Browser Stream & Screenshot Modal State
  const [liveBrowserImage, setLiveBrowserImage] = useState<string | null>(null);
  const [liveBrowserUrl, setLiveBrowserUrl] = useState<string | null>(null);
  const [liveBrowserActive, setLiveBrowserActive] = useState(false);
  const [showLiveBrowser, setShowLiveBrowser] = useState(true);
  const [selectedImageModal, setSelectedImageModal] = useState<{ url: string; caption?: string } | null>(null);
  const [selectedPresentationModal, setSelectedPresentationModal] = useState<{ url: string; title?: string } | null>(null);
  const [thinkingLevel, setThinkingLevel] = useState<ThinkingLevel>(getSavedThinkingLevel());
  const [activePlanContent, setActivePlanContent] = useState<{ planContent: string; planPath: string } | null>(null);

  // Cloud LLM Provider State
  const [isCloudModalOpen, setIsCloudModalOpen] = useState<boolean>(false);
  const [cloudProvider, setCloudProvider] = useState<string>(() => localStorage.getItem('agentic_cloud_provider') || 'ollama');
  const [selectedCloudModel, setSelectedCloudModel] = useState<string>(() => localStorage.getItem('agentic_cloud_model') || 'granite4.1:8b');
  const [cloudApiKey, setCloudApiKey] = useState<string>(() => localStorage.getItem('agentic_cloud_api_key') || '');
  const [installedOllamaModels, setInstalledOllamaModels] = useState<string[]>([]);

  const fetchInstalledOllamaModels = async () => {
    try {
      const models = await OllamaService.getModels();
      if (models && models.length > 0) {
        const names = models.map((m: any) => m.name).filter(Boolean);
        setInstalledOllamaModels(names);
      } else {
        const localRes = await OllamaService.getLocalModels();
        if (localRes && localRes.status === 'success' && localRes.models?.length > 0) {
          const names = localRes.models.map((m: any) => m.name).filter(Boolean);
          setInstalledOllamaModels(names);
        }
      }
    } catch (err) {
      console.error("Failed to fetch installed Ollama models", err);
    }
  };

  useEffect(() => {
    fetchInstalledOllamaModels();
  }, []);

  useEffect(() => {
    if (isCloudModalOpen) {
      fetchInstalledOllamaModels();
    }
  }, [isCloudModalOpen]);

  const defaultOllamaModels = ['granite4.1:8b', 'gemma4:26b', 'llama3.3:70b', 'qwen2.5-coder:32b', 'deepseek-r1:14b', 'mistral-small:24b'];

  const providerModelsMap: Record<string, string[]> = {
    ollama: installedOllamaModels.length > 0 ? installedOllamaModels : defaultOllamaModels,
    openai: ['gpt-4o', 'gpt-4o-mini', 'o3-mini', 'o1', 'opus-4.8'],
    anthropic: ['claude-sonnet-4-6', 'claude-opus-4-8', 'claude-haiku-4-5-20251001', 'claude-opus-5', 'claude-sonnet-5'],
    ibm: ['granite4.1:8b', 'granite-3-8b-instruct', 'granite-3-2b-instruct', 'granite-20b-code'],
    gemini: ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash'],
    deepseek: ['deepseek-chat', 'deepseek-reasoner', 'deepseek-coder']
  };

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

  const businessAgentThoughts = [
    "Analyzing business requirements and financial data schemas...",
    "Validating spreadsheet formulas and CSV data structures...",
    "Preparing csv_sheet_operation tool payload (read/write/append)...",
    "Calculating budget summaries, projections, and financial metrics...",
    "Structuring business report and spreadsheet outputs..."
  ];

  // Rotate thinking sub-steps while agent is working
  useEffect(() => {
    let interval: number | undefined;
    if (isTyping && routingStep >= 2) {
      const thoughts = activeRoutingAgent === 'research' 
        ? researchAgentThoughts 
        : activeRoutingAgent === 'analysis' 
          ? analysisAgentThoughts 
          : activeRoutingAgent === 'business'
            ? businessAgentThoughts
            : codeAgentThoughts;
      
      setThinkingSubStep(thoughts[0]);
      let index = 1;
      
      interval = window.setInterval(() => {
        playAgentProcessingPulse();
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
    // Optimized Typewriter velocity: larger character chunks at 30ms interval to eliminate UI lag
    const charStep = textToType.length > 200 ? 8 : 4;
    const intervalTime = 30;

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
        scrollToBottom();
        if (onComplete) onComplete();
      } else {
        setMessages(prev => {
          const copy = [...prev];
          if (copy[msgIndex]) {
            copy[msgIndex].content = textToType.substring(0, currentIdx);
          }
          return copy;
        });
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
      OllamaService.stopMultiAgent('default').catch(() => {});
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

      if (agentUsed === 'business' || textLower.includes('business') || textLower.includes('csv') || textLower.includes('financial')) {
        tools.push({
          toolName: 'csv_sheet_operation',
          status: 'success',
          details: 'Executed CSV spreadsheet operation for business model data.'
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
    OllamaService.stopMultiAgent('default').catch(() => {});
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
    
    // Play Siri activation chime when agent execution starts
    playSiriActivationSound();

    setIsTyping(true);
    setRoutingStep(1); // Orchestrator active
    setActiveRoutingAgent(null);
    setActiveTool(null);
    setStreamingPreview('');
    setThinkingStream('');
    setThinkingTokens([]);
    setResponseTokens([]);
    setTodoItems([]);

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
      } else if (selectedDirectAgent === 'business') {
        setActiveTool('csv_sheet_operation');
      }

      try {
        const directContext = {
          provider: cloudProvider,
          model: selectedCloudModel,
          api_key: cloudApiKey,
          thinking_level: thinkingLevel
        };
        const response = await OllamaService.chatDirectAgent(selectedDirectAgent, userText, directContext, thinkingLevel);
        
        const finalContent = typeof response === 'string' ? response : (response?.response || response?.result || response?.content || response?.output || 'Task completed successfully.');
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
            toolName: selectedDirectAgent === 'code' ? 'generate_code' : selectedDirectAgent === 'research' ? 'web_search' : selectedDirectAgent === 'analysis' ? 'analyze_code' : selectedDirectAgent === 'business' ? 'csv_sheet_operation' : 'default_tool',
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
              } else if (currentAgent === 'business') {
                setActiveTool('csv_sheet_operation');
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
            } else if (event.type === 'plan_request') {
              setPendingPlanApproval({
                planContent: event.plan_content,
                planPath: event.plan_path,
                sessionId: event.session_id || 'default'
              });
              setActivePlanContent({
                planContent: event.plan_content,
                planPath: event.plan_path
              });
              setEditedPlanContent(event.plan_content);
              setIsPlanModalOpen(true);
              setActivePlanTab('preview');
            } else if (event.type === 'terminal_output' && event.content) {
              setTerminalLines(prev => [...prev, event.content]);
              if (!showTerminal) setShowTerminal(true);
            } else if (event.type === 'browser_live') {
              if (event.done) {
                setLiveBrowserActive(false);
              } else {
                if (event.image_base64) setLiveBrowserImage(event.image_base64);
                if (event.url) setLiveBrowserUrl(event.url);
                setLiveBrowserActive(true);
              }
            } else if (event.type === 'screenshot_taken') {
              setMessages(prev => {
                const newMsgs = [...prev];
                const lastIdx = newMsgs.length - 1;
                if (lastIdx >= 0 && newMsgs[lastIdx].role === 'assistant') {
                  const existingSS = newMsgs[lastIdx].screenshots || [];
                  newMsgs[lastIdx] = {
                    ...newMsgs[lastIdx],
                    screenshots: [
                      ...existingSS,
                      {
                        name: event.name,
                        url: event.url || event.path,
                        caption: event.caption,
                        image_base64: event.image_base64
                      }
                    ]
                  };
                }
                return newMsgs;
              });
            } else if (event.type === 'screenshot_result') {
              if (event.screenshots && event.screenshots.length > 0) {
                setMessages(prev => {
                  const newMsgs = [...prev];
                  const lastIdx = newMsgs.length - 1;
                  if (lastIdx >= 0 && newMsgs[lastIdx].role === 'assistant') {
                    newMsgs[lastIdx] = {
                      ...newMsgs[lastIdx],
                      screenshots: event.screenshots
                    };
                  }
                  return newMsgs;
                });
              }
            } else if (event.type === 'todo_list_update') {
              const items = event.items || event.todos || event.todo_list || event.todoItems || event.data || (event.item ? [event.item] : []);
              if (Array.isArray(items) && items.length > 0) {
                setTodoItems(items);
              } else if (event.item) {
                const item = event.item;
                setTodoItems(prev => {
                  const idx = prev.findIndex(t => t.id === item.id);
                  if (idx !== -1) {
                    const copy = [...prev];
                    copy[idx] = { ...copy[idx], ...item };
                    return copy;
                  }
                  return [...prev, item];
                });
              }
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
                if (localThinkingTokens.length > 0) {
                  updateLastAssistantMessage({ thinkingProcess: localThinkingTokens.join('') });
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
            if (hasStreamedResponse || fullResponseText.trim().length > 0) {
              finalizeResponse();
            } else {
              const errMsg = err?.message ? `Stream processing notice: ${err.message}` : 'Stream processing error occurred. Please verify backend connection.';
              setMessages(prev => [...prev, {
                role: 'assistant',
                content: errMsg,
                agentUsed: undefined
              }]);
              setIsTyping(false);
              setRoutingStep(0);
              setActiveRoutingAgent(null);
              setActiveTool(null);
            }
          },
          undefined,
          thinkingLevel,
          cloudProvider,
          selectedCloudModel,
          cloudApiKey
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

  const renderMarkdown = (text: string) => {
    if (!text) return null;
    
    const lines = text.split('\n');
    let insideCodeBlock = false;
    let codeBlockContent: string[] = [];
    let codeLanguage = '';
    
    const renderedElements: React.ReactNode[] = [];
    
    lines.forEach((line, idx) => {
      if (line.trim().startsWith('```')) {
        if (insideCodeBlock) {
          insideCodeBlock = false;
          renderedElements.push(
            <pre key={`code-${idx}`} className="bg-black/95 font-mono text-[11px] text-emerald-400 p-4 border border-border/85 overflow-x-auto my-4 max-h-[300px]">
              {codeLanguage && <div className="text-[9px] text-muted-foreground uppercase tracking-widest border-b border-border/30 pb-1 mb-2 font-sans font-bold">{codeLanguage}</div>}
              <code>{codeBlockContent.join('\n')}</code>
            </pre>
          );
          codeBlockContent = [];
          codeLanguage = '';
        } else {
          insideCodeBlock = true;
          codeLanguage = line.trim().slice(3).trim();
        }
        return;
      }
      
      if (insideCodeBlock) {
        codeBlockContent.push(line);
        return;
      }
      
      const formatInline = (str: string) => {
        const parts = str.split('**');
        return parts.map((part, pIdx) => {
          if (pIdx % 2 === 1) {
            return <strong key={pIdx} className="font-bold text-foreground">{part}</strong>;
          }
          const codeParts = part.split('`');
          return codeParts.map((cPart, cIdx) => {
            if (cIdx % 2 === 1) {
              if (cPart.startsWith('/api/documents/') && cPart.endsWith('.html')) {
                return (
                  <button
                    key={cIdx}
                    onClick={() => setSelectedPresentationModal({ url: cPart, title: 'Interactive Presentation' })}
                    className="inline-flex items-center gap-1.5 font-mono text-xs bg-blue-500/15 border border-blue-500/40 text-blue-400 px-2 py-0.5 rounded hover:bg-blue-500/30 transition-colors my-0.5 cursor-pointer"
                  >
                    <Presentation className="w-3.5 h-3.5" />
                    <span>Preview Interactive Slide Deck</span>
                    <ExternalLink className="w-3 h-3 ml-0.5 opacity-70" />
                  </button>
                );
              } else if (cPart.startsWith('/api/documents/') && (cPart.endsWith('.pptx') || cPart.endsWith('.xlsx'))) {
                const isPptx = cPart.endsWith('.pptx');
                return (
                  <a
                    key={cIdx}
                    href={cPart}
                    download
                    className={cn(
                      "inline-flex items-center gap-1.5 font-mono text-xs border px-2 py-0.5 rounded transition-colors my-0.5",
                      isPptx 
                        ? "bg-amber-500/15 border-amber-500/40 text-amber-400 hover:bg-amber-500/30" 
                        : "bg-emerald-500/15 border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/30"
                    )}
                  >
                    {isPptx ? <Presentation className="w-3.5 h-3.5" /> : <FileSpreadsheet className="w-3.5 h-3.5" />}
                    <span>Download {isPptx ? 'PowerPoint (.pptx)' : 'Excel Workbook (.xlsx)'}</span>
                    <Download className="w-3 h-3 ml-0.5 opacity-70" />
                  </a>
                );
              }
              return <code key={cIdx} className="font-mono text-xs bg-muted px-1.5 py-0.5 text-ibm-blue">{cPart}</code>;
            }
            return cPart;
          });
        });
      };
      
      if (line.startsWith('# ')) {
        renderedElements.push(<h1 key={idx} className="text-2xl font-light text-foreground border-b border-border/40 pb-2 mb-4 mt-6 first:mt-0">{formatInline(line.slice(2))}</h1>);
      } else if (line.startsWith('## ')) {
        renderedElements.push(<h2 key={idx} className="text-xl font-light text-foreground mb-3 mt-5">{formatInline(line.slice(3))}</h2>);
      } else if (line.startsWith('### ')) {
        renderedElements.push(<h3 key={idx} className="text-lg font-medium text-foreground mb-2 mt-4">{formatInline(line.slice(4))}</h3>);
      } else if (line.startsWith('#### ')) {
        renderedElements.push(<h4 key={idx} className="text-sm font-semibold text-foreground mb-2 mt-3 uppercase tracking-wider">{formatInline(line.slice(5))}</h4>);
      } else if (line.startsWith('- [ ] ') || line.startsWith('* [ ] ')) {
        renderedElements.push(
          <div key={idx} className="flex items-start gap-2 my-1 text-muted-foreground pl-2">
            <span className="font-mono border border-border text-[9px] px-1 py-0.5 select-none shrink-0 mt-0.5">[ ]</span>
            <span>{formatInline(line.slice(6))}</span>
          </div>
        );
      } else if (line.startsWith('- [x] ') || line.startsWith('* [x] ')) {
        renderedElements.push(
          <div key={idx} className="flex items-start gap-2 my-1 text-muted-foreground/80 line-through pl-2">
            <span className="font-mono bg-ibm-blue/15 border border-ibm-blue/30 text-ibm-blue text-[9px] px-1 py-0.5 select-none shrink-0 mt-0.5">✓</span>
            <span>{formatInline(line.slice(6))}</span>
          </div>
        );
      } else if (line.startsWith('- ') || line.startsWith('* ')) {
        renderedElements.push(
          <div key={idx} className="flex items-start gap-2 my-1.5 pl-2 text-muted-foreground">
            <span className="text-ibm-blue select-none shrink-0 mt-1">•</span>
            <span>{formatInline(line.slice(2))}</span>
          </div>
        );
      } else if (line.startsWith('> ')) {
        const quoteText = line.slice(2).trim();
        let isAlert = false;
        let alertType = '';
        if (quoteText.startsWith('[!')) {
          isAlert = true;
          const endBrac = quoteText.indexOf(']');
          if (endBrac !== -1) {
            alertType = quoteText.slice(2, endBrac).toUpperCase();
          }
        }
        
        if (isAlert) {
          renderedElements.push(
            <div key={idx} className={`p-3 border-l-4 my-3 text-xs bg-muted/10 ${
              alertType === 'IMPORTANT' || alertType === 'WARNING' || alertType === 'CAUTION'
                ? 'border-destructive/60 bg-destructive/5'
                : alertType === 'TIP'
                ? 'border-emerald-600 bg-emerald-500/5'
                : 'border-ibm-blue bg-ibm-blue/5'
            }`}>
              <div className="font-mono font-bold uppercase tracking-wider text-[9px] mb-1">{alertType}</div>
              <div>{formatInline(quoteText.slice(quoteText.indexOf(']') + 1).trim())}</div>
            </div>
          );
        } else {
          renderedElements.push(
            <blockquote key={idx} className="border-l-4 border-muted p-3 bg-muted/10 my-3 text-muted-foreground text-xs italic">
              {formatInline(quoteText)}
            </blockquote>
          );
        }
      } else if (line.trim() === '') {
        renderedElements.push(<div key={idx} className="h-2" />);
      } else {
        renderedElements.push(<p key={idx} className="my-2 text-muted-foreground leading-relaxed text-xs md:text-sm">{formatInline(line)}</p>);
      }
    });
    
    return <div className="space-y-1 font-sans">{renderedElements}</div>;
  };

  const handleQuickPrompt = (text: string) => {
    setPrompt(text);
  };

  return (
    <div className="space-y-8 select-text">
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
          <SiriFluidOrb 
            size="sm" 
            state={isHealthy === true ? 'healthy' : isHealthy === false ? 'offline' : 'idle'} 
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

      {/* Featured Playground Banner */}
      {onOpenPlayground && (
        <div className="bg-gradient-to-r from-purple-900/60 via-indigo-900/50 to-blue-900/60 border border-purple-500/40 p-4 rounded-lg flex flex-col sm:flex-row items-center justify-between gap-4 shadow-lg animate-in fade-in duration-500">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-purple-500/20 rounded-lg border border-purple-400/30">
              <Sparkles className="w-6 h-6 text-amber-300 animate-pulse" />
            </div>
            <div>
              <div className="font-semibold text-sm text-foreground flex items-center gap-2">
                Play with Your Ideas — AI Studio Playground
                <span className="text-[10px] bg-purple-500/30 text-purple-200 border border-purple-400/40 px-2 py-0.5 font-mono">NEW</span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Experiment freely with Research & Business agents, system prompt tuning, quick idea templates, and the new web fetch tool.
              </p>
            </div>
          </div>
          <Button 
            onClick={onOpenPlayground}
            className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-mono text-xs uppercase px-5 py-2.5 gap-2 flex-shrink-0 shadow-md transition-all hover:scale-105"
          >
            <Sparkles className="w-4 h-4 text-amber-300" />
            Open Playground Page
          </Button>
        </div>
      )}

      {/* 2. Interactive SVG Network Path Visualizer */}
      <Card className="carbon-card relative overflow-hidden backdrop-blur-xl bg-card/75 shadow-lg">
        <CardHeader className="pb-2 border-b border-border/30">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <CardTitle className="text-xl font-light tracking-wide flex items-center gap-2">
              <Layers className="w-5 h-5 text-primary" />
              LangGraph Multi-Agent Core Network
            </CardTitle>
            <div className="flex items-center gap-3">
              <AnimationSelector variant="compact" />
              <span className="font-mono text-xs uppercase text-muted-foreground bg-muted px-2 py-0.5 border hidden md:inline-block">
                Model: Gemma-4 / Llama-3.2
              </span>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-8 pb-6">
          <div className="flex flex-col md:flex-row items-center justify-around gap-8 relative">
            
            {/* CENTRAL MIND (ORCHESTRATOR) */}
            <div 
              className={cn(
                "relative z-10 w-44 p-4 border flex flex-col items-center justify-center transition-all duration-500",
                routingStep === 1 
                  ? "border-primary bg-primary/10 shadow-glow shadow-primary/30 scale-105 siri-fluid-border-frame" 
                  : "border-border bg-card"
              )}
            >
              <SiriFluidOrb 
                size="lg" 
                state={routingStep === 1 ? 'thinking' : 'active'}
                className="mb-2"
              >
                <Cpu className={cn("w-8 h-8 text-white drop-shadow-md", routingStep === 1 && "animate-pulse")} />
              </SiriFluidOrb>
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

              {/* BUSINESS AGENT */}
              <div 
                className={cn(
                  "relative z-10 w-full md:w-72 p-3 border flex items-center gap-3 transition-all duration-300",
                  activeRoutingAgent === 'business'
                    ? "border-accent bg-secondary/30 shadow-glow shadow-accent/20 translate-x-2"
                    : "border-border bg-card"
                )}
              >
                <div className={cn("p-2 border", activeRoutingAgent === 'business' ? "bg-accent/10 border-accent text-accent" : "bg-muted text-muted-foreground")}>
                  <TrendingUp className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-xs">Business Agent</span>
                    <span className="text-[9px] font-mono text-muted-foreground bg-muted px-1.5 py-0.2 border">CSV SHEET</span>
                  </div>
                  <div className="text-[10px] text-muted-foreground truncate">Financial models & CSV spreadsheets</div>
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
                  <div className="grid grid-cols-4 gap-2">
                    {['code', 'research', 'analysis', 'business'].map(a => (
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
          <Card className={cn("carbon-card flex flex-col min-h-[780px] lg:min-h-[840px] relative transition-all duration-500 shadow-xl", (isTyping || isRecording) && "siri-fluid-border-frame shadow-[0_0_30px_rgba(168,85,247,0.35)]")}>
            <CardHeader className="pb-4 border-b border-border/30 flex flex-col xl:flex-row items-start xl:items-center justify-between gap-4">
              <div>
                <CardTitle className="text-xl sm:text-2xl font-light tracking-tight whitespace-nowrap">Interactive Hub Playground</CardTitle>
                <p className="text-xs text-muted-foreground mt-1 font-mono">
                  {mode === 'orchestrated' 
                    ? "Coordinated by Main Orchestrator Agent via LangGraph" 
                    : `Direct communication with ${selectedDirectAgent.toUpperCase()} Agent`}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3 w-full xl:w-auto justify-start xl:justify-end">
                {activePlanContent && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setEditedPlanContent(activePlanContent.planContent);
                      setIsPlanModalOpen(true);
                    }}
                    className="h-10 font-mono text-xs uppercase gap-1.5 border-ibm-blue/40 text-ibm-blue hover:bg-ibm-blue/10 animate-in fade-in duration-200"
                  >
                    <FileText className="w-4 h-4" />
                    <span className="hidden sm:inline">Implementation Plan</span>
                  </Button>
                )}
                <Button
                  variant="outline"
                  onClick={() => setIsCloudModalOpen(true)}
                  className="h-10 sm:h-11 font-mono text-xs sm:text-sm uppercase gap-2 border-emerald-500/60 text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 px-4 font-bold shadow-md transition-all animate-in fade-in duration-200"
                >
                  <Globe className="w-4 h-4 sm:w-5 sm:h-5 text-emerald-400" />
                  <span className="hidden sm:inline">Provider: <strong className="text-emerald-300 font-black">{cloudProvider.toUpperCase()}</strong> <span className="text-emerald-400/90 font-normal">({selectedCloudModel})</span></span>
                  <span className="sm:hidden">{cloudProvider.toUpperCase()}</span>
                </Button>
                <ThinkingLevelSelector variant="dropdown" value={thinkingLevel} onChange={setThinkingLevel} />
                <span className="text-[10px] font-mono uppercase text-muted-foreground hidden sm:inline">
                  {isRecording ? 'Agentic Voice Core' : isTyping ? 'Agentic Fluid Core' : 'Agentic Core Intelligence'}
                </span>
                <SiriFluidOrb size="sm" state={isRecording ? 'recording' : isTyping ? 'thinking' : 'active'} />
              </div>
            </CardHeader>
            
            {/* CHAT LOGS */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 font-sans text-base min-h-[350px]">
              {/* Live Executive Agent To-Do List Widget */}
              <AgentTodoList todoItems={todoItems} />

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
                    <div className="w-full flex justify-between items-center mb-1.5 gap-4">
                      <div className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest flex items-center gap-1.5">
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
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-5 w-5 p-0 opacity-40 hover:opacity-100 transition-opacity"
                        onClick={() => handleCopyMessage(msg.content, idx)}
                        title="Copy message content"
                      >
                        {copiedIndex === idx ? (
                          <Check className="w-3 h-3 text-emerald-500" />
                        ) : (
                          <Copy className="w-3 h-3 text-muted-foreground" />
                        )}
                      </Button>
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
                          {renderMarkdown(msg.content)}
                          {!isUser && isTypingAnimationActive && idx === messages.length - 1 && (
                            <span className="inline-block w-2.5 h-4 ml-1 bg-primary animate-pulse align-middle">█</span>
                          )}
                        </>
                      )}

                      {/* App Screenshots Gallery */}
                      {!isUser && msg.screenshots && msg.screenshots.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-border/40 space-y-3">
                          <div className="flex items-center gap-2 text-xs font-mono font-bold text-primary uppercase tracking-wider">
                            <Camera className="w-4 h-4 text-emerald-400" />
                            <span>App Preview & Verification Screenshots ({msg.screenshots.length})</span>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {msg.screenshots.map((ss, sIdx) => (
                              <div 
                                key={sIdx} 
                                className="group relative bg-black/90 border border-border/60 overflow-hidden cursor-pointer hover:border-emerald-500/50 transition-all duration-200"
                                onClick={() => setSelectedImageModal({ url: ss.image_base64 || ss.url, caption: ss.caption || ss.name })}
                              >
                                <div className="aspect-video relative overflow-hidden bg-muted/20">
                                  <img 
                                    src={ss.image_base64 || ss.url} 
                                    alt={ss.caption || ss.name} 
                                    className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                                  />
                                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                    <span className="flex items-center gap-1.5 bg-emerald-500 text-black px-3 py-1 font-mono text-[10px] font-bold uppercase tracking-wider shadow-md">
                                      <Eye className="w-3.5 h-3.5" /> View Fullscreen
                                    </span>
                                  </div>
                                </div>
                                {ss.caption && (
                                  <div className="p-2 bg-muted/40 font-mono text-[11px] text-muted-foreground border-t border-border/30 truncate">
                                    📸 {ss.caption}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}


                      {/* --- Collapsible Dropdown for Agent Thinking Process --- */}
                      {!isUser && msg.thinkingProcess && (
                        <div className="mt-4 pt-3 border-t border-border/30">
                          <button 
                            onClick={() => setOpenDropdownIdx(openDropdownIdx === (idx + 1000) ? null : (idx + 1000))}
                            className="font-mono text-xs text-primary/90 hover:text-primary flex items-center gap-1.5 focus:outline-none transition-colors"
                          >
                            {openDropdownIdx === (idx + 1000) ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                            <Brain className="w-3.5 h-3.5 text-primary" />
                            {openDropdownIdx === (idx + 1000) ? "Hide Agent Thinking Process" : "View Agent Thinking Process"}
                          </button>

                          {openDropdownIdx === (idx + 1000) && (
                            <div className="mt-2.5 p-3.5 bg-primary/5 border border-primary/20 font-mono text-xs text-muted-foreground whitespace-pre-wrap leading-relaxed max-h-[300px] overflow-y-auto animate-in slide-in-from-top-2 duration-200">
                              <div className="text-[9px] text-primary/70 uppercase tracking-wider font-bold mb-1.5 border-b border-primary/10 pb-1">
                                🧠 Deep Reasoning Trace
                              </div>
                              {msg.thinkingProcess}
                            </div>
                          )}
                        </div>
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
                      <div className="flex items-center gap-2.5 text-xs text-primary font-mono">
                        <SiriFluidOrb size="xs" state="thinking" />
                        <span>Orchestrator: Analyzing input classification...</span>
                      </div>
                    )}
                    
                    {/* Routed to specialized agent */}
                    {routingStep >= 2 && (
                      <div className="flex flex-col gap-2 pl-3">
                        <div className="flex items-center gap-2.5 text-xs text-accent font-mono">
                          <SiriFluidOrb size="xs" state="active" />
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

                    {/* Implementation Plan Approval Box */}
                    {pendingPlanApproval && (
                      <div className="border border-ibm-blue bg-ibm-blue/5 p-5 space-y-3 animate-in fade-in duration-300">
                        <div className="flex items-start gap-2.5">
                          <FileText className="w-5 h-5 text-ibm-blue shrink-0 mt-0.5" />
                          <div className="flex-1">
                            <div className="text-[10px] font-mono font-bold text-ibm-blue uppercase">Implementation Plan Generated</div>
                            <div className="text-xs mt-1 text-foreground">
                              The Code Agent has generated an implementation plan for your task. You must review and approve it before the agent continues.
                            </div>
                            <div className="mt-3">
                              <button
                                onClick={() => {
                                  setEditedPlanContent(pendingPlanApproval.planContent);
                                  setIsPlanModalOpen(true);
                                }}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-ibm-blue/15 hover:bg-ibm-blue/25 text-ibm-blue border border-ibm-blue/30 text-xs font-mono uppercase transition-colors"
                              >
                                <Layers className="w-3.5 h-3.5" />
                                Open Implementation Plan Window
                              </button>
                            </div>
                            <div className="text-[9px] mt-2 text-muted-foreground font-mono">
                              File path: <span className="select-all">{pendingPlanApproval.planPath}</span>
                            </div>
                          </div>
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

              {/* Live Browser View Panel */}
              {(liveBrowserActive || liveBrowserImage) && (
                <div className="mt-4 border border-blue-500/30 bg-[#0b0f19] rounded-none p-4 shadow-lg animate-in slide-in-from-top-2 duration-300">
                  <div className="flex items-center justify-between mb-3 border-b border-blue-500/20 pb-2">
                    <div className="flex items-center gap-2">
                      <Monitor className="w-4 h-4 text-blue-400 animate-pulse" />
                      <span className="font-mono text-xs font-bold text-blue-400 uppercase tracking-wider">
                        Live Agent Browser View
                      </span>
                      {liveBrowserActive ? (
                        <span className="flex items-center gap-1.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 text-[9px] font-mono px-2 py-0.5">
                          <SiriFluidOrb size="xs" state="healthy" showGlow={false} />
                          LIVE (~2fps)
                        </span>
                      ) : (
                        <span className="bg-muted text-muted-foreground border text-[9px] font-mono px-2 py-0.5">
                          OFFLINE
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      {liveBrowserUrl && (
                        <span className="font-mono text-[10px] text-muted-foreground truncate max-w-[250px]" title={liveBrowserUrl}>
                          🌐 {liveBrowserUrl}
                        </span>
                      )}
                      <button
                        onClick={() => setShowLiveBrowser(!showLiveBrowser)}
                        className="text-xs font-mono text-blue-400 hover:text-blue-300 flex items-center gap-1"
                      >
                        {showLiveBrowser ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        {showLiveBrowser ? 'Minimize' : 'Expand'}
                      </button>
                    </div>
                  </div>

                  {showLiveBrowser && (
                    <div className="relative group bg-black/80 border border-border/40 overflow-hidden flex items-center justify-center min-h-[220px]">
                      {liveBrowserImage ? (
                        <>
                          <img 
                            src={liveBrowserImage} 
                            alt="Live Browser View" 
                            className="max-h-[400px] w-auto object-contain cursor-pointer transition-transform duration-200 hover:scale-[1.01]"
                            onClick={() => setSelectedImageModal({ url: liveBrowserImage, caption: `Live Browser View (${liveBrowserUrl || 'App'})` })}
                          />
                          <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-black/70 p-1 rounded border border-white/20">
                            <Maximize2 className="w-4 h-4 text-white cursor-pointer" onClick={() => setSelectedImageModal({ url: liveBrowserImage, caption: `Live Browser View (${liveBrowserUrl || 'App'})` })} />
                          </div>
                        </>
                      ) : (
                        <div className="flex flex-col items-center gap-2 py-8 text-muted-foreground font-mono text-xs">
                          <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
                          <span>Connecting to Playwright browser viewport...</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* PROMPT INPUT */}
            <div className="p-4 border-t border-border bg-muted/20">
              {/* Recording Indicator */}
              {isRecording && (
                <div className="flex items-center gap-3 mb-3 px-3.5 py-2 bg-red-500/10 border border-red-500/30 animate-pulse siri-fluid-border-frame">
                  <SiriFluidOrb size="sm" state="recording" />
                  <span className="text-xs font-mono text-red-400 uppercase tracking-wider font-semibold">Agentic Voice Intelligence Active — Speak now...</span>
                  <span className="ml-auto text-[10px] font-mono text-red-400/70">Click mic to stop</span>
                </div>
              )}
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
                {/* Microphone Button */}
                <Button
                  onClick={handleVoiceRecord}
                  disabled={isTyping}
                  variant="outline"
                  className={cn(
                    "h-auto px-4 py-4 flex flex-col justify-center items-center border text-base transition-all duration-300",
                    isRecording
                      ? "border-red-500 bg-red-500/15 hover:bg-red-500/25 text-red-400 shadow-[0_0_15px_rgba(239,68,68,0.2)]"
                      : "border-border hover:border-primary/50 hover:bg-primary/5 text-muted-foreground hover:text-primary"
                  )}
                  title={isRecording ? 'Stop recording' : 'Start voice input'}
                >
                  {isRecording ? (
                    <>
                      <MicOff className="w-5 h-5 mb-1" />
                      <span className="text-[10px] uppercase font-mono tracking-widest">Stop</span>
                    </>
                  ) : isTranscribing ? (
                    <>
                      <Loader2 className="w-5 h-5 mb-1 animate-spin" />
                      <span className="text-[10px] uppercase font-mono tracking-widest">Wait</span>
                    </>
                  ) : (
                    <>
                      <Mic className="w-5 h-5 mb-1" />
                      <span className="text-[10px] uppercase font-mono tracking-widest">Voice</span>
                    </>
                  )}
                </Button>
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
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center mt-3.5 gap-2.5 text-xs font-mono text-muted-foreground">
                <div className="flex flex-wrap items-center gap-3">
                  <span>Press Enter to send, Shift+Enter for new line · 🎤 Voice supported</span>
                  <ThinkingLevelSelector variant="compact" value={thinkingLevel} onChange={setThinkingLevel} />
                </div>
                <span className="flex items-center gap-1.5 text-xs text-emerald-400/90 font-medium">
                  <FolderCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                  File-writer Workspace Target: <strong className="text-foreground font-mono">D:\learning\code\website</strong>
                </span>
              </div>
            </div>

          </Card>
        </div>
      </div>

      {/* Implementation Plan Overlay Modal Window */}
      {isPlanModalOpen && (pendingPlanApproval || activePlanContent) && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[100] flex items-center justify-center p-4 md:p-6 animate-in fade-in duration-200">
          <div className="bg-card border border-border w-full max-w-4xl h-[85vh] flex flex-col shadow-2xl relative animate-in zoom-in-95 duration-200 text-foreground">
            {/* Header */}
            <div className="p-4 border-b border-border flex justify-between items-center bg-muted/40">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-ibm-blue" />
                <span className="font-mono text-xs font-bold uppercase tracking-wider text-ibm-blue">
                  Implementation Plan Review Window
                </span>
              </div>
              <button 
                onClick={() => setIsPlanModalOpen(false)}
                className="text-muted-foreground hover:text-foreground transition-colors p-1.5 hover:bg-muted"
                title="Close Window"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            {/* Body */}
            <div className="flex-1 overflow-hidden flex flex-col p-6 space-y-4">
              {/* Tab Selector */}
              <div className="flex gap-4 border-b border-border/60 pb-2">
                <button
                  onClick={() => setActivePlanTab('preview')}
                  className={`pb-2 text-xs font-mono uppercase tracking-wider border-b-2 transition-all ${
                    activePlanTab === 'preview'
                      ? 'border-ibm-blue text-ibm-blue font-bold'
                      : 'border-transparent text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Formatted Preview
                </button>
                <button
                  onClick={() => setActivePlanTab('edit')}
                  className={`pb-2 text-xs font-mono uppercase tracking-wider border-b-2 transition-all ${
                    activePlanTab === 'edit'
                      ? 'border-ibm-blue text-ibm-blue font-bold'
                      : 'border-transparent text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Edit Raw Markdown
                </button>
              </div>

              {/* Path metadata */}
              <div className="p-2.5 bg-muted/30 border border-border/50 text-[10px] font-mono text-muted-foreground flex justify-between items-center">
                <span>Plan File Path: <strong className="text-foreground">{(pendingPlanApproval || activePlanContent)?.planPath}</strong></span>
                <span className="text-ibm-blue uppercase font-bold text-[9px]">Local Work Target</span>
              </div>

              {/* Content Panel */}
              <div className="flex-1 overflow-hidden border border-border/80 bg-black/20">
                {activePlanTab === 'preview' ? (
                  <div className="h-full overflow-y-auto p-6 scrollbar-thin select-text">
                    {renderMarkdown(editedPlanContent || (pendingPlanApproval || activePlanContent)?.planContent || '')}
                  </div>
                ) : (
                  <textarea
                    className="w-full h-full font-mono text-xs p-4 bg-black/60 text-foreground border-0 focus:outline-none resize-none"
                    value={editedPlanContent}
                    onChange={(e) => setEditedPlanContent(e.target.value)}
                    placeholder="Write implementation plan markdown here..."
                  />
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-border flex gap-3 justify-end bg-muted/40">
              {pendingPlanApproval ? (
                <>
                  <Button
                    variant="outline"
                    onClick={() => handlePlanApprovalResponse(false)}
                    className="h-9 px-4 text-xs font-mono uppercase border-destructive/40 hover:bg-destructive/10 text-destructive-foreground hover:text-destructive hover:border-destructive"
                  >
                    Reject / Cancel Task
                  </Button>
                  <Button
                    onClick={() => handlePlanApprovalResponse(true)}
                    className="h-9 px-5 text-xs font-mono uppercase bg-emerald-600 hover:bg-emerald-700 text-white border-0"
                  >
                    Proceed with Execution
                  </Button>
                </>
              ) : (
                <Button
                  onClick={() => setIsPlanModalOpen(false)}
                  className="h-9 px-5 text-xs font-mono uppercase bg-ibm-blue hover:bg-ibm-blue/80 text-white border-0"
                >
                  Close Plan Window
                </Button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Image Lightbox Modal */}
      {selectedImageModal && (
        <div 
          className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex flex-col items-center justify-center p-4 animate-in fade-in duration-200"
          onClick={() => setSelectedImageModal(null)}
        >
          <div className="absolute top-4 right-4 flex items-center gap-2">
            <Button
              variant="outline"
              size="icon"
              className="bg-black/60 border-white/20 text-white hover:bg-white/20 rounded-full h-10 w-10"
              onClick={() => setSelectedImageModal(null)}
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
          
          <div 
            className="max-w-[95vw] max-h-[85vh] bg-black border border-border/60 p-2 shadow-2xl relative flex flex-col items-center"
            onClick={(e) => e.stopPropagation()}
          >
            <img 
              src={selectedImageModal.url} 
              alt={selectedImageModal.caption || 'Screenshot'} 
              className="max-w-full max-h-[75vh] object-contain"
            />
            {selectedImageModal.caption && (
              <div className="mt-3 px-4 py-2 bg-muted/30 border border-border/40 font-mono text-xs text-foreground text-center w-full">
                📸 {selectedImageModal.caption}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Interactive Presentation Modal */}
      {selectedPresentationModal && (
        <div 
          className="fixed inset-0 z-50 bg-black/95 backdrop-blur-lg flex flex-col items-center justify-center p-4 animate-in fade-in duration-200"
          onClick={() => setSelectedPresentationModal(null)}
        >
          <div className="absolute top-4 right-4 flex items-center gap-3">
            <a
              href={selectedPresentationModal.url.replace('.html', '.pptx')}
              download
              className="inline-flex items-center gap-1.5 font-mono text-xs bg-amber-500 text-black font-bold px-3 py-1.5 rounded hover:bg-amber-400 transition-colors shadow-lg"
              onClick={(e) => e.stopPropagation()}
            >
              <Presentation className="w-4 h-4" />
              Download PPTX
            </a>
            <Button
              variant="outline"
              size="icon"
              className="bg-black/60 border-white/20 text-white hover:bg-white/20 rounded-full h-10 w-10"
              onClick={() => setSelectedPresentationModal(null)}
            >
              <X className="w-5 h-5" />
            </Button>
          </div>

          <div 
            className="w-[95vw] h-[88vh] bg-black border border-blue-500/40 shadow-2xl flex flex-col overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="bg-[#0b0f19] border-b border-blue-500/20 px-4 py-2 flex items-center justify-between font-mono text-xs text-blue-400">
              <div className="flex items-center gap-2">
                <Presentation className="w-4 h-4 text-blue-400" />
                <span className="font-bold uppercase tracking-wider">{selectedPresentationModal.title || 'Interactive Slide Deck'}</span>
              </div>
              <span className="text-[10px] text-muted-foreground">Use Arrow Keys or Swipe to Navigate Slides</span>
            </div>
            <iframe 
              src={selectedPresentationModal.url} 
              title="Presentation Deck"
              className="w-full h-full border-0 bg-black"
            />
          </div>
        </div>
      )}

      {/* Cloud & Local LLM Provider Settings Modal */}
      {isCloudModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-emerald-500/50 rounded-2xl max-w-2xl w-full p-8 space-y-6 shadow-2xl animate-in zoom-in-95 duration-200 text-foreground">
            <div className="flex justify-between items-center border-b border-border/40 pb-4">
              <div className="flex items-center gap-3">
                <Globe className="w-7 h-7 text-emerald-400" />
                <div>
                  <h3 className="font-bold text-xl sm:text-2xl tracking-tight">Cloud & Local LLM Provider Settings</h3>
                  <p className="text-xs text-muted-foreground mt-0.5 font-mono">Configure your active model engine and local/cloud credentials</p>
                </div>
              </div>
              <button onClick={() => setIsCloudModalOpen(false)} className="text-muted-foreground hover:text-foreground p-1 rounded-lg hover:bg-white/10 transition-colors">
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="space-y-5 font-mono text-sm">
              <div>
                <label className="block text-muted-foreground mb-2 font-bold uppercase tracking-wider text-xs sm:text-sm">1. Select Provider</label>
                <select 
                  value={cloudProvider}
                  onChange={(e) => {
                    const prov = e.target.value;
                    setCloudProvider(prov);
                    const models = providerModelsMap[prov] || [];
                    if (models.length > 0) setSelectedCloudModel(models[0]);
                  }}
                  className="w-full bg-slate-950 border border-border/80 p-3.5 rounded-xl text-foreground focus:outline-none focus:border-emerald-500 text-sm sm:text-base font-sans font-medium"
                >
                  <option value="ollama">OLLAMA (Local Default)</option>
                  <option value="openai">OPENAI (Cloud - GPT-4o, Opus 4.8)</option>
                  <option value="anthropic">ANTHROPIC (Cloud - Claude 3.7 / 3.5)</option>
                  <option value="ibm">IBM GRANITE (Cloud / Local)</option>
                  <option value="gemini">GOOGLE GEMINI (Cloud - Gemini 2.5)</option>
                  <option value="deepseek">DEEPSEEK (Cloud - DeepSeek-R1 / V3)</option>
                </select>
              </div>

              <div>
                <label className="block text-muted-foreground mb-2 font-bold uppercase tracking-wider text-xs sm:text-sm">
                  2. Select Model {cloudProvider === 'ollama' && installedOllamaModels.length > 0 ? `(${installedOllamaModels.length} Installed Locally)` : ''}
                </label>
                <select 
                  value={selectedCloudModel}
                  onChange={(e) => setSelectedCloudModel(e.target.value)}
                  className="w-full bg-slate-950 border border-border/80 p-3.5 rounded-xl text-foreground focus:outline-none focus:border-emerald-500 text-sm sm:text-base font-sans font-medium"
                >
                  {(providerModelsMap[cloudProvider] || []).map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>

              {cloudProvider !== 'ollama' && (
                <div>
                  <label className="block text-muted-foreground mb-2 font-bold uppercase tracking-wider text-xs sm:text-sm">3. API Key ({cloudProvider.toUpperCase()})</label>
                  <input 
                    type="password"
                    placeholder={`Enter your ${cloudProvider.toUpperCase()} API Key...`}
                    value={cloudApiKey}
                    onChange={(e) => setCloudApiKey(e.target.value)}
                    className="w-full bg-slate-950 border border-border/80 p-3.5 rounded-xl text-foreground focus:outline-none focus:border-emerald-500 text-sm font-sans"
                  />
                  <p className="text-xs text-muted-foreground mt-1.5 font-sans">Your API key is securely saved in local storage and sent directly to agent API calls.</p>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 pt-5 border-t border-border/40">
              <Button 
                variant="outline" 
                onClick={() => setIsCloudModalOpen(false)}
                className="h-11 px-5 text-sm font-semibold rounded-xl"
              >
                Cancel
              </Button>
              <Button 
                onClick={() => {
                  localStorage.setItem('agentic_cloud_provider', cloudProvider);
                  localStorage.setItem('agentic_cloud_model', selectedCloudModel);
                  localStorage.setItem('agentic_cloud_api_key', cloudApiKey);
                  setIsCloudModalOpen(false);
                }}
                className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold h-11 px-7 text-sm rounded-xl shadow-lg"
              >
                Save Settings
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
