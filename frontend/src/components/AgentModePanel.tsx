import React, { useState, useEffect, useRef } from 'react';
import { 
  BookOpen, Bug, Wand2, TestTube2, FileText, 
  Wrench, Zap, Search, Send, Square, Trash2, 
  Bot, User
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { OllamaService } from '@/services/ollama';
import { AgentModeToolStep } from './AgentModeToolStep';

interface AgentModePanelProps {
  currentPath: string;
  selectedFile: { path: string; name: string } | null;
  fileContent: string | null;
  onFileChange?: () => void;
}

interface ToolStep {
  id: string;
  tool: string;
  target: string;
  status: 'running' | 'done' | 'error';
  result?: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  thinking?: string;
  toolSteps?: ToolStep[];
}

export function AgentModePanel({ currentPath, selectedFile, fileContent, onFileChange }: AgentModePanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [status, setStatus] = useState<{claude_code_available: boolean; ollama_model: string; mode: string} | null>(null);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sessionId = 'default';

  useEffect(() => {
    OllamaService.agentModeStatus().then(res => setStatus(res)).catch(console.error);
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const history = await OllamaService.getAgentModeHistory(sessionId);
      if (history && history.messages) {
        setMessages(history.messages);
      }
    } catch (err) {
      console.error('Failed to load history', err);
    }
  };

  const clearHistory = async () => {
    try {
      await OllamaService.clearAgentModeHistory(sessionId);
      setMessages([]);
    } catch (err) {
      console.error('Failed to clear history', err);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const handleStreamEvent = (data: any) => {
    setMessages(prev => {
      const newMessages = [...prev];
      const lastMsgIndex = newMessages.length - 1;
      
      if (lastMsgIndex >= 0 && newMessages[lastMsgIndex].role === 'assistant') {
        const lastMsg = { ...newMessages[lastMsgIndex] };
        
        if (data.type === 'thinking') {
          lastMsg.thinking = (lastMsg.thinking || '') + data.content;
        } else if (data.type === 'text') {
          lastMsg.content = (lastMsg.content || '') + data.content;
        } else if (data.type === 'tool_use') {
          if (!lastMsg.toolSteps) lastMsg.toolSteps = [];
          lastMsg.toolSteps.push({
            id: data.tool_call_id,
            tool: data.tool_name,
            target: data.target || 'system',
            status: 'running'
          });
        } else if (data.type === 'tool_result') {
          if (lastMsg.toolSteps) {
            const stepIndex = lastMsg.toolSteps.findIndex(s => s.id === data.tool_call_id);
            if (stepIndex !== -1) {
              lastMsg.toolSteps[stepIndex] = {
                ...lastMsg.toolSteps[stepIndex],
                status: data.error ? 'error' : 'done',
                result: data.result || (data.error && data.error_msg)
              };
            }
          }
          if (data.tool_name === 'Write' || data.tool_name === 'Edit' || data.tool_name === 'Bash') {
             if (onFileChange) onFileChange();
          }
        }
        
        newMessages[lastMsgIndex] = lastMsg;
      }
      return newMessages;
    });
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isStreaming) return;
    
    const userPrompt = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userPrompt }, { role: 'assistant', content: '', toolSteps: [] }]);
    setIsStreaming(true);

    try {
      const controller = await OllamaService.agentModeChatStream(
        userPrompt,
        currentPath,
        handleStreamEvent,
        (err) => {
          console.error(err);
          setIsStreaming(false);
          setAbortController(null);
        },
        selectedFile?.path,
        fileContent || undefined,
        sessionId
      );
      setAbortController(controller);
    } catch (err) {
      console.error(err);
      setIsStreaming(false);
    }
  };
  
  const handleStop = () => {
    if (abortController) {
      abortController.abort();
      setAbortController(null);
    }
    setIsStreaming(false);
  };

  const executeQuickAction = async (action: string) => {
    if (!selectedFile || isStreaming) return;
    
    setMessages(prev => [
      ...prev, 
      { role: 'user', content: `[Quick Action] ${action} on ${selectedFile.name}` },
      { role: 'assistant', content: '', toolSteps: [] }
    ]);
    setIsStreaming(true);

    try {
      const controller = await OllamaService.agentModeQuickActionStream(
        action,
        selectedFile.path,
        fileContent || '',
        currentPath,
        handleStreamEvent,
        (err) => {
          console.error(err);
          setIsStreaming(false);
          setAbortController(null);
        },
        sessionId
      );
      setAbortController(controller);
    } catch (err) {
      console.error(err);
      setIsStreaming(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const quickActions = [
    { label: 'Explain', icon: BookOpen, action: 'explain' },
    { label: 'Find Bugs', icon: Bug, action: 'find_bugs' },
    { label: 'Refactor', icon: Wand2, action: 'refactor' },
    { label: 'Add Tests', icon: TestTube2, action: 'add_tests' },
    { label: 'Document', icon: FileText, action: 'document' },
    { label: 'Fix Errors', icon: Wrench, action: 'fix_errors' },
    { label: 'Optimize', icon: Zap, action: 'optimize' },
    { label: 'Find Related', icon: Search, action: 'find_related' },
  ];

  return (
    <Card className="carbon-card rounded-none h-[600px] flex flex-col border-violet-600/30">
      <CardHeader className="py-3 px-4 border-b border-border/50 bg-[#0d0d1a] shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Bot className="w-4 h-4 text-violet-500" />
              Agent Mode
            </CardTitle>
            {status && (
              <div className="flex items-center gap-2 text-xs font-mono">
                <div className="flex items-center gap-1.5 bg-muted px-2 py-0.5 border border-border/50">
                  <div className={cn("w-2 h-2 rounded-full", status.claude_code_available ? "bg-emerald-500" : "bg-yellow-500")} />
                  <span className="text-muted-foreground uppercase tracking-wider text-[10px]">
                    {status.claude_code_available ? "Claude Connected" : "Ollama Only"}
                  </span>
                </div>
                <div className="text-[10px] bg-muted px-2 py-0.5 border border-border/50 uppercase tracking-wider text-muted-foreground">
                  {status.ollama_model}
                </div>
              </div>
            )}
          </div>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={clearHistory}
            className="h-7 px-2 text-[10px] font-mono uppercase tracking-widest text-muted-foreground hover:text-red-400"
          >
            <Trash2 className="w-3 h-3 mr-1.5" />
            Clear History
          </Button>
        </div>
        
        {selectedFile && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {quickActions.map(qa => (
              <Button
                key={qa.label}
                size="sm"
                variant="outline"
                disabled={isStreaming}
                onClick={() => executeQuickAction(qa.action)}
                className="h-6 px-2 text-[9px] font-mono uppercase tracking-widest bg-[#151525] border-border/50 hover:bg-violet-600/20 hover:text-violet-400 hover:border-violet-600/50"
              >
                <qa.icon className="w-3 h-3 mr-1" />
                {qa.label}
              </Button>
            ))}
          </div>
        )}
      </CardHeader>
      
      <CardContent className="flex-1 p-0 flex flex-col overflow-hidden bg-[#1a1a2e]">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-muted-foreground space-y-4">
              <Bot className="w-12 h-12 opacity-20" />
              <div className="text-sm font-mono text-center">
                Agent Mode is ready.<br/>
                Ask a question or select a quick action.
              </div>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div 
                key={i} 
                className={cn(
                  "flex gap-3",
                  msg.role === 'user' ? "justify-end" : "justify-start"
                )}
              >
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-none bg-violet-600/20 border border-violet-600/50 flex items-center justify-center shrink-0">
                    <Bot className="w-4 h-4 text-violet-400" />
                  </div>
                )}
                
                <div 
                  className={cn(
                    "max-w-[85%] p-3 text-sm",
                    msg.role === 'user' 
                      ? "bg-ibm-blue/10 border border-ibm-blue/20 text-foreground" 
                      : "bg-[#0d0d1a] border border-border/50"
                  )}
                >
                  {msg.thinking && (
                    <div className="text-xs text-muted-foreground italic mb-2 font-mono whitespace-pre-wrap">
                      {msg.thinking}
                    </div>
                  )}
                  
                  {msg.toolSteps && msg.toolSteps.length > 0 && (
                    <div className="mb-2 space-y-1">
                      {msg.toolSteps.map((step, idx) => (
                        <AgentModeToolStep
                          key={idx}
                          tool={step.tool}
                          target={step.target}
                          status={step.status}
                          result={step.result}
                        />
                      ))}
                    </div>
                  )}
                  
                  {msg.content && (
                    <div className="whitespace-pre-wrap font-sans leading-relaxed">
                      {msg.content}
                    </div>
                  )}
                  
                  {isStreaming && i === messages.length - 1 && msg.role === 'assistant' && !msg.content && (!msg.toolSteps || msg.toolSteps.every(s => s.status !== 'running')) && (
                    <div className="flex gap-1 items-center h-4 mt-2">
                      <div className="w-1.5 h-1.5 bg-violet-500 rounded-full animate-pulse" />
                      <div className="w-1.5 h-1.5 bg-violet-500 rounded-full animate-pulse delay-75" />
                      <div className="w-1.5 h-1.5 bg-violet-500 rounded-full animate-pulse delay-150" />
                    </div>
                  )}
                </div>
                
                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-none bg-ibm-blue/20 border border-ibm-blue/50 flex items-center justify-center shrink-0">
                    <User className="w-4 h-4 text-ibm-blue" />
                  </div>
                )}
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
        
        <div className="p-3 bg-[#0d0d1a] border-t border-border/50">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <textarea
              className="flex-1 bg-[#151525] border border-border/50 text-sm p-2.5 focus:outline-none focus:border-violet-500/50 resize-none rounded-none text-foreground placeholder:text-muted-foreground font-sans min-h-[44px] max-h-[120px]"
              placeholder="Ask about this file or codebase..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              rows={1}
              disabled={isStreaming}
            />
            {isStreaming ? (
              <Button 
                type="button" 
                variant="destructive"
                className="rounded-none px-4 h-auto shrink-0 font-mono uppercase text-xs"
                onClick={handleStop}
              >
                <Square className="w-4 h-4 mr-1.5 fill-current" />
                Stop
              </Button>
            ) : (
              <Button 
                type="submit" 
                disabled={!input.trim()}
                className="rounded-none px-4 h-auto shrink-0 bg-violet-600 hover:bg-violet-700 text-white font-mono uppercase text-xs"
              >
                <Send className="w-4 h-4 mr-1.5" />
                Send
              </Button>
            )}
          </form>
        </div>
      </CardContent>
    </Card>
  );
}
