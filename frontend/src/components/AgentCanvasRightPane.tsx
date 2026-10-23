import React, { useState, useEffect, useRef } from 'react';
import {
  Monitor,
  Tablet,
  Smartphone,
  Laptop,
  Maximize2,
  Minimize2,
  RefreshCw,
  Code2,
  Eye,
  Brain,
  ListTodo,
  Activity,
  Copy,
  Check,
  ExternalLink,
  FileCode,
  X,
  Terminal
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { type TodoItem } from './AgentTodoList';

export type CanvasTab = 'preview' | 'code' | 'memory' | 'trace' | 'todo';

interface AgentCanvasRightPaneProps {
  activeTab: CanvasTab;
  onTabChange: (tab: CanvasTab) => void;
  onClose: () => void;
  isExpanded: boolean;
  onToggleExpand: () => void;
  // Dynamic Content Data
  previewHtml?: string;
  codeSnippet?: string;
  codeFilename?: string;
  todoItems: TodoItem[];
  onToggleTodoItem?: (id: string) => void;
  toolsExecuted?: Array<{
    tool: string;
    input?: any;
    output?: any;
    timestamp?: string;
    duration?: number;
    status?: 'success' | 'running' | 'error';
  }>;
  memoriesRecalled?: Array<{
    id?: number;
    title?: string;
    content: string;
    category?: string;
    score?: number;
  }>;
  memoriesSaved?: Array<{
    id?: number;
    title?: string;
    content: string;
    category?: string;
  }>;
  onOpenMemoryVault?: () => void;
  onReloadApp?: () => void;
}

export const AgentCanvasRightPane: React.FC<AgentCanvasRightPaneProps> = ({
  activeTab,
  onTabChange,
  onClose,
  isExpanded,
  onToggleExpand,
  previewHtml = '',
  codeSnippet = '',
  codeFilename = 'workspace/index.html',
  todoItems = [],
  onToggleTodoItem,
  toolsExecuted = [],
  memoriesRecalled = [],
  memoriesSaved = [],
  onOpenMemoryVault,
  onReloadApp
}) => {
  // Device Viewport for Preview
  const [deviceViewport, setDeviceViewport] = useState<'desktop' | 'laptop' | 'tablet' | 'mobile'>('desktop');
  const [copiedCode, setCopiedCode] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Auto-switch to preview or code if agent generates new content
  useEffect(() => {
    if (previewHtml && activeTab !== 'preview' && activeTab !== 'code') {
      onTabChange('preview');
    }
  }, [previewHtml]);

  // Handle Copying Code
  const handleCopyCode = () => {
    if (!codeSnippet && !previewHtml) return;
    navigator.clipboard.writeText(codeSnippet || previewHtml);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  // Viewport width styling
  const getViewportWidth = () => {
    switch (deviceViewport) {
      case 'mobile':
        return 'max-w-[375px]';
      case 'tablet':
        return 'max-w-[768px]';
      case 'laptop':
        return 'max-w-[1024px]';
      default:
        return 'w-full';
    }
  };

  // Formatted srcDoc with base tag pointing to live workspace server
  const formattedSrcDoc = React.useMemo(() => {
    if (!previewHtml) return undefined;
    const baseTag = '<base href="http://localhost:8000/api/workspace/live/">';
    if (previewHtml.includes('<base')) return previewHtml;
    if (previewHtml.includes('<head>')) {
      return previewHtml.replace('<head>', `<head>${baseTag}`);
    }
    return `<head>${baseTag}</head>${previewHtml}`;
  }, [previewHtml]);

  // Open Preview in External Window
  const handleOpenExternal = () => {
    window.open('http://localhost:8000/api/workspace/live/index.html', '_blank');
  };

  // Todo Completion Statistics
  const completedTodos = todoItems.filter(t => t.status === 'completed').length;
  const totalTodos = todoItems.length;
  const todoPercent = totalTodos > 0 ? Math.round((completedTodos / totalTodos) * 100) : 0;

  return (
    <div className="h-full flex flex-col bg-card/95 backdrop-blur-2xl border-l border-border/70 overflow-hidden shadow-2xl relative select-none">
      {/* Top Canvas Command Header */}
      <div className="h-13 px-4 border-b border-border/80 flex items-center justify-between gap-2 shrink-0 bg-secondary/30">
        {/* Tab Buttons */}
        <div className="flex items-center gap-1 overflow-x-auto py-1 scrollbar-none">
          <button
            onClick={() => onTabChange('preview')}
            className={cn(
              "px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap",
              activeTab === 'preview'
                ? "bg-purple-600 text-white shadow-md shadow-purple-500/20"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
            )}
          >
            <Eye className="w-3.5 h-3.5" />
            <span>Live Preview</span>
            {previewHtml && (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            )}
          </button>

          <button
            onClick={() => onTabChange('code')}
            className={cn(
              "px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap",
              activeTab === 'code'
                ? "bg-purple-600 text-white shadow-md shadow-purple-500/20"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
            )}
          >
            <Code2 className="w-3.5 h-3.5" />
            <span>Code Canvas</span>
            {(codeSnippet || previewHtml) && (
              <span className="text-[10px] font-mono opacity-80">
                {codeFilename.split('/').pop()}
              </span>
            )}
          </button>

          <button
            onClick={() => onTabChange('memory')}
            className={cn(
              "px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap",
              activeTab === 'memory'
                ? "bg-purple-600 text-white shadow-md shadow-purple-500/20"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
            )}
          >
            <Brain className="w-3.5 h-3.5 text-purple-400" />
            <span>Memory</span>
            {(memoriesRecalled.length > 0 || memoriesSaved.length > 0) && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-purple-500/30 text-purple-200 font-mono">
                {memoriesRecalled.length + memoriesSaved.length}
              </span>
            )}
          </button>

          <button
            onClick={() => onTabChange('trace')}
            className={cn(
              "px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap",
              activeTab === 'trace'
                ? "bg-purple-600 text-white shadow-md shadow-purple-500/20"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
            )}
          >
            <Activity className="w-3.5 h-3.5 text-blue-400" />
            <span>Execution Trace</span>
            {toolsExecuted.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-blue-500/30 text-blue-200 font-mono">
                {toolsExecuted.length}
              </span>
            )}
          </button>

          <button
            onClick={() => onTabChange('todo')}
            className={cn(
              "px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap",
              activeTab === 'todo'
                ? "bg-purple-600 text-white shadow-md shadow-purple-500/20"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
            )}
          >
            <ListTodo className="w-3.5 h-3.5 text-amber-400" />
            <span>Task Board</span>
            {totalTodos > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-amber-500/30 text-amber-200 font-mono">
                {completedTodos}/{totalTodos}
              </span>
            )}
          </button>
        </div>

        {/* Action Buttons: Fullscreen, Close */}
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={onToggleExpand}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors cursor-pointer"
            title={isExpanded ? "Restore Panel Width" : "Maximize Canvas (Cinema Mode)"}
          >
            {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors cursor-pointer"
            title="Collapse Canvas"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Canvas Body */}
      <div className="flex-1 overflow-hidden flex flex-col relative select-text">
        {/* ========================================================= */}
        {/* 1. LIVE PREVIEW TAB */}
        {/* ========================================================= */}
        {activeTab === 'preview' && (
          <div className="flex-1 flex flex-col h-full overflow-hidden bg-background">
            {/* Preview Toolbar */}
            <div className="h-11 px-4 border-b border-border/70 flex items-center justify-between gap-3 bg-secondary/20 text-xs text-muted-foreground">
              {/* Viewport switchers */}
              <div className="flex items-center gap-1 bg-secondary/60 p-0.5 rounded-xl border border-border/60">
                <button
                  onClick={() => setDeviceViewport('desktop')}
                  className={cn(
                    "p-1.5 rounded-lg transition-colors cursor-pointer",
                    deviceViewport === 'desktop' ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                  )}
                  title="Desktop (100%)"
                >
                  <Monitor className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setDeviceViewport('laptop')}
                  className={cn(
                    "p-1.5 rounded-lg transition-colors cursor-pointer",
                    deviceViewport === 'laptop' ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                  )}
                  title="Laptop (1024px)"
                >
                  <Laptop className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setDeviceViewport('tablet')}
                  className={cn(
                    "p-1.5 rounded-lg transition-colors cursor-pointer",
                    deviceViewport === 'tablet' ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                  )}
                  title="Tablet (768px)"
                >
                  <Tablet className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setDeviceViewport('mobile')}
                  className={cn(
                    "p-1.5 rounded-lg transition-colors cursor-pointer",
                    deviceViewport === 'mobile' ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                  )}
                  title="Mobile (375px)"
                >
                  <Smartphone className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Status and External Actions */}
              <div className="flex items-center gap-2">
                <a
                  href="http://localhost:8000/api/workspace/live/index.html"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hidden sm:flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 hover:bg-emerald-500/20 transition-all cursor-pointer"
                  title="Direct Workspace Live Server: http://localhost:8000/api/workspace/live/index.html"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span>Live App (Port 8000)</span>
                </a>
                <button
                  onClick={() => {
                    setRefreshKey(prev => prev + 1);
                    onReloadApp?.();
                  }}
                  className="p-1.5 rounded-xl hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                  title="Reload Live App Sandbox"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={handleOpenExternal}
                  className="p-1.5 rounded-xl hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                  title="Open App in New Browser Tab"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Iframe Preview Container */}
            <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-muted/20">
              <div
                className={cn(
                  "h-full mx-auto bg-card rounded-2xl shadow-xl border border-border/80 overflow-hidden transition-all duration-300 flex flex-col",
                  getViewportWidth()
                )}
              >
                {previewHtml || true ? (
                  <iframe
                    key={refreshKey}
                    ref={iframeRef}
                    title="Live Agent Component Preview"
                    srcDoc={formattedSrcDoc}
                    src={!previewHtml ? `http://localhost:8000/api/workspace/live/index.html?t=${refreshKey}` : undefined}
                    sandbox="allow-scripts allow-modals allow-forms allow-same-origin"
                    className="w-full h-full border-none bg-white dark:bg-slate-950"
                  />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center p-8 text-center space-y-3 text-muted-foreground">
                    <div className="w-14 h-14 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 text-2xl shadow-sm">
                      🎨
                    </div>
                    <h4 className="font-bold text-foreground text-sm">Live Preview Canvas Ready</h4>
                    <p className="text-xs max-w-sm leading-relaxed">
                      Ask the agent to build a UI component, HTML landing page, or dashboard. The interactive result will render live here!
                    </p>
                    <div className="text-[11px] font-mono px-3 py-1 rounded-lg bg-secondary text-purple-400 border border-purple-500/20">
                      e.g. "Create an interactive Pomodoro timer with sound effects"
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* 2. CODE CANVAS TAB */}
        {/* ========================================================= */}
        {activeTab === 'code' && (
          <div className="flex-1 flex flex-col h-full overflow-hidden bg-background">
            <div className="h-11 px-4 border-b border-border/70 flex items-center justify-between bg-secondary/20 text-xs">
              <div className="flex items-center gap-2 text-foreground font-mono">
                <FileCode className="w-4 h-4 text-purple-400" />
                <span className="font-semibold text-xs">{codeFilename}</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopyCode}
                  className="px-2.5 py-1 rounded-lg bg-secondary hover:bg-secondary/80 text-foreground font-medium text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  {copiedCode ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  <span>{copiedCode ? 'Copied' : 'Copy Code'}</span>
                </button>
                <button
                  onClick={() => onTabChange('preview')}
                  className="px-2.5 py-1 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-medium text-xs flex items-center gap-1 transition-colors cursor-pointer"
                >
                  <Eye className="w-3 h-3" />
                  <span>Preview</span>
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-auto p-4 bg-slate-950 font-mono text-xs text-slate-200 leading-relaxed">
              <pre className="whitespace-pre-wrap select-text">
                {codeSnippet || previewHtml || '// No code generated yet. Prompt an agent to create files.'}
              </pre>
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* 3. AGENT MEMORY TAB */}
        {/* ========================================================= */}
        {activeTab === 'memory' && (
          <div className="flex-1 flex flex-col h-full overflow-y-auto p-5 space-y-5 bg-background">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div>
                <h3 className="font-bold text-sm text-foreground flex items-center gap-2">
                  <Brain className="w-4 h-4 text-purple-400" />
                  Active Session Knowledge & Memory
                </h3>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  Memories recalled and saved during this conversation turn
                </p>
              </div>
              {onOpenMemoryVault && (
                <button
                  onClick={onOpenMemoryVault}
                  className="px-3 py-1 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow transition-all cursor-pointer"
                >
                  Open Full Vault
                </button>
              )}
            </div>

            {/* Recalled Context Section */}
            <div className="space-y-2.5">
              <div className="text-xs font-bold font-mono uppercase tracking-wider text-purple-400 flex items-center gap-1.5">
                <span>💡</span>
                <span>Recalled by Agent for this Task ({memoriesRecalled.length})</span>
              </div>
              {memoriesRecalled.length === 0 ? (
                <div className="p-3.5 rounded-xl border border-dashed border-border/70 text-xs text-muted-foreground bg-muted/10">
                  No memories actively triggered for current prompt. Prompt the agent about your preferences or tech stack to trigger recall.
                </div>
              ) : (
                memoriesRecalled.map((m, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl bg-secondary/40 border border-purple-500/30 text-xs space-y-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-semibold text-purple-300 uppercase">{m.category || 'Preference'}</span>
                      {m.score && <span className="font-mono text-muted-foreground">Match: {(m.score * 100).toFixed(0)}%</span>}
                    </div>
                    <p className="text-foreground italic font-sans pl-2 border-l-2 border-purple-500">
                      "{m.content}"
                    </p>
                  </div>
                ))
              )}
            </div>

            {/* Memories Saved Section */}
            <div className="space-y-2.5 pt-2">
              <div className="text-xs font-bold font-mono uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                <span>🧠</span>
                <span>Committed to Memory this Session ({memoriesSaved.length})</span>
              </div>
              {memoriesSaved.length === 0 ? (
                <div className="p-3.5 rounded-xl border border-dashed border-border/70 text-xs text-muted-foreground bg-muted/10">
                  No new memories saved in this turn. Tell the agent: <em>"Remember that I like TailwindCSS"</em>.
                </div>
              ) : (
                memoriesSaved.map((m, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-500/40 text-xs space-y-1">
                    <div className="flex items-center justify-between text-[11px] text-emerald-300">
                      <span className="font-semibold uppercase">{m.category || 'Fact'}</span>
                      <span className="font-mono">Saved ✓</span>
                    </div>
                    <p className="text-emerald-100 italic font-sans pl-2 border-l-2 border-emerald-500">
                      "{m.content}"
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* 4. EXECUTION TRACE TAB */}
        {/* ========================================================= */}
        {activeTab === 'trace' && (
          <div className="flex-1 flex flex-col h-full overflow-y-auto p-5 space-y-4 bg-background">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div>
                <h3 className="font-bold text-sm text-foreground flex items-center gap-2">
                  <Activity className="w-4 h-4 text-blue-400" />
                  Live Agent Execution Trace
                </h3>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  Detailed timeline of tools, file operations, and terminal executions
                </p>
              </div>
              <span className="text-xs font-mono text-muted-foreground">
                {toolsExecuted.length} steps executed
              </span>
            </div>

            {toolsExecuted.length === 0 ? (
              <div className="p-8 text-center text-xs text-muted-foreground space-y-2">
                <Terminal className="w-8 h-8 mx-auto text-muted-foreground/50" />
                <p>No tools executed yet. When the agent uses tools, every step will appear here live.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {toolsExecuted.map((step, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl bg-card border border-border/80 hover:border-blue-500/40 transition-all text-xs space-y-2 shadow-sm"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 font-mono">
                        <span className="w-5 h-5 rounded-md bg-blue-500/10 text-blue-400 flex items-center justify-center font-bold text-[10px]">
                          {idx + 1}
                        </span>
                        <span className="font-bold text-foreground">{step.tool}</span>
                      </div>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        {step.status || 'success'}
                      </span>
                    </div>

                    {step.input && (
                      <div className="bg-secondary/40 p-2 rounded-lg font-mono text-[11px] text-muted-foreground overflow-x-auto">
                        <span className="text-blue-400 font-bold block mb-0.5">Input:</span>
                        {typeof step.input === 'string' ? step.input : JSON.stringify(step.input, null, 2)}
                      </div>
                    )}

                    {step.output && (
                      <div className="bg-secondary/60 p-2 rounded-lg font-mono text-[11px] text-foreground/90 overflow-x-auto max-h-32">
                        <span className="text-emerald-400 font-bold block mb-0.5">Output:</span>
                        {typeof step.output === 'string' ? step.output : JSON.stringify(step.output, null, 2)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ========================================================= */}
        {/* 5. TASK BOARD TAB */}
        {/* ========================================================= */}
        {activeTab === 'todo' && (
          <div className="flex-1 flex flex-col h-full overflow-y-auto p-5 space-y-4 bg-background">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div>
                <h3 className="font-bold text-sm text-foreground flex items-center gap-2">
                  <ListTodo className="w-4 h-4 text-amber-400" />
                  Agent Task Board & Progress
                </h3>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  Subtasks automatically broken down and checked off by the agent
                </p>
              </div>
              <div className="text-right">
                <span className="text-xs font-bold font-mono text-foreground">{todoPercent}%</span>
                <span className="text-[10px] text-muted-foreground block">Completed</span>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="w-full h-2 rounded-full bg-secondary overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-amber-500 to-emerald-500 transition-all duration-500"
                style={{ width: `${todoPercent}%` }}
              />
            </div>

            {todoItems.length === 0 ? (
              <div className="p-8 text-center text-xs text-muted-foreground space-y-2">
                <ListTodo className="w-8 h-8 mx-auto text-muted-foreground/50" />
                <p>No active tasks in the queue. Ask the agent to plan and execute a multi-step project.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {todoItems.map(item => (
                  <div
                    key={item.id}
                    onClick={() => onToggleTodoItem?.(item.id)}
                    className={cn(
                      "p-3 rounded-xl border transition-all flex items-start gap-3 cursor-pointer",
                      item.status === 'completed'
                        ? "bg-emerald-950/20 border-emerald-500/30 text-emerald-100"
                        : item.status === 'in_progress'
                        ? "bg-amber-950/20 border-amber-500/40 text-amber-100 shadow-sm"
                        : "bg-card border-border/80 text-foreground hover:bg-secondary/40"
                    )}
                  >
                    <div className="mt-0.5 shrink-0">
                      {item.status === 'completed' ? (
                        <div className="w-4 h-4 rounded bg-emerald-500 text-white flex items-center justify-center text-[10px]">
                          ✓
                        </div>
                      ) : item.status === 'in_progress' ? (
                        <div className="w-4 h-4 rounded border-2 border-amber-400 animate-pulse" />
                      ) : (
                        <div className="w-4 h-4 rounded border border-border" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className={cn(
                          "text-xs font-semibold leading-tight",
                          item.status === 'completed' && "line-through opacity-70"
                        )}>
                          {item.title}
                        </span>
                        <span className={cn(
                          "px-2 py-0.2 rounded-full text-[10px] font-mono shrink-0 uppercase",
                          item.status === 'completed' && "bg-emerald-500/20 text-emerald-300",
                          item.status === 'in_progress' && "bg-amber-500/20 text-amber-300 font-bold",
                          item.status === 'pending' && "bg-secondary text-muted-foreground"
                        )}>
                          {item.status.replace('_', ' ')}
                        </span>
                      </div>
                      {item.details && (
                        <p className="text-[11px] text-muted-foreground mt-1">
                          {item.details}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
