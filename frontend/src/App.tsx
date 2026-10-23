import React, { useState, useEffect, useRef } from 'react';
import { type Agent, type LeaderboardEntry, OllamaService } from '@/services/ollama';
import { Leaderboard } from '@/components/Leaderboard';
import { AgentArena } from '@/components/AgentArena';
import { AgentBuilder } from '@/components/AgentBuilder';
import { TrainingCenter } from '@/components/TrainingCenter';
import { MultiAgentHub } from '@/components/MultiAgentHub';
import { MultiAgentConfig } from '@/components/MultiAgentConfig';
import { ScheduledTasks } from '@/components/ScheduledTasks';
import { AIGuide } from '@/components/AIGuide';
import { WorkspaceExplorer } from '@/components/WorkspaceExplorer';
import { HubCreator } from '@/components/HubCreator';
import { IdeaPlayground } from '@/components/IdeaPlayground';
import { LivePreviewStudio } from '@/components/LivePreviewStudio';
import { WhyChoosePage } from '@/components/WhyChoosePage';
import { AgentMemoryVault } from '@/components/AgentMemoryVault';
import { LoginPage } from '@/components/LoginPage';
import { AuthModal } from '@/components/AuthModal';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import { AgentExecutionProvider, useAgentExecution } from '@/context/AgentExecutionContext';
import { authService } from '@/services/auth';
import {
  LayoutGrid,
  Trophy,
  Plus,
  Moon,
  Sun,
  Cpu,
  Brain,
  Network,
  Settings,
  FolderOpen,
  Layers,
  Timer,
  Sparkles,
  Compass,
  Database,
  User as UserIcon,
  LogIn,
  LogOut,
  Activity,
  ExternalLink,
  Square,
  PanelLeftClose,
  PanelLeftOpen,
  Loader2,
  Eye,
  GripHorizontal,
} from 'lucide-react';
import { AnimationSelector } from '@/components/AnimationSelector';
import { SiriFluidOrb } from '@/components/SiriFluidOrb';
import { cn } from '@/lib/utils';

type Tab =
  | 'landing'
  | 'login'
  | 'dashboard'
  | 'leaderboard'
  | 'arena'
  | 'builder'
  | 'train'
  | 'multi-agent'
  | 'settings'
  | 'workspace'
  | 'hubs'
  | 'loops'
  | 'playground'
  | 'preview'
  | 'memory';

const AppContent: React.FC = () => {
  const { user, isAuthenticated, mongoStatus, logout } = useAuth();
  const { activeRuns, isAnyAgentRunning, stopRun } = useAgentExecution();

  // Default to 'multi-agent' or 'playground' if authenticated, otherwise 'multi-agent' so user lands right in the action
  const [activeTab, setActiveTab] = useState<Tab>(() =>
    authService.getToken() ? 'multi-agent' : 'multi-agent'
  );
  const [previewFilePath, setPreviewFilePath] = useState<string | undefined>(undefined);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('senior_agent_theme_mode');
      if (saved === 'light') return false;
      if (saved === 'dark') return true;
    }
    return true;
  });
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [sidebarExpanded, setSidebarExpanded] = useState(true);
  const [nowTick, setNowTick] = useState(Date.now());
  const [memoryCount, setMemoryCount] = useState<number>(0);

  const refreshMemoryCount = async () => {
    try {
      const res = await OllamaService.listPersonalMemories();
      if (res && typeof res.count === 'number') {
        setMemoryCount(res.count);
      } else if (res && Array.isArray(res.memories)) {
        setMemoryCount(res.memories.length);
      }
    } catch {
      // silently ignore
    }
  };

  useEffect(() => {
    refreshMemoryCount();
    const interval = setInterval(refreshMemoryCount, 15000);
    return () => clearInterval(interval);
  }, []);

  // Draggable Floating Live Agent Monitor Dock state
  const [dockOffset, setDockOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDraggingDock, setIsDraggingDock] = useState(false);
  const dockDragRef = useRef<{ startX: number; startY: number; origX: number; origY: number } | null>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!dockDragRef.current) return;
      const { startX, startY, origX, origY } = dockDragRef.current;
      setDockOffset({
        x: origX + (e.clientX - startX),
        y: origY + (e.clientY - startY),
      });
    };
    const handleMouseUp = () => {
      if (dockDragRef.current) {
        dockDragRef.current = null;
        setIsDraggingDock(false);
      }
    };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  const refreshData = async () => {
    try {
      const [agentsList, leaderboardData] = await Promise.all([
        OllamaService.getAgents(),
        OllamaService.getLeaderboard()
      ]);
      setAgents(agentsList);
      setLeaderboard(leaderboardData);
    } catch (err) {
      console.error("Failed to fetch data", err);
    }
  };

  useEffect(() => {
    refreshData();
  }, []);

  // Tick every second when an agent is running so elapsed time updates smoothly
  useEffect(() => {
    if (!isAnyAgentRunning) return;
    const timer = setInterval(() => setNowTick(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [isAnyAgentRunning]);

  useEffect(() => {
    const root = document.documentElement;
    if (darkMode) {
      root.classList.add('dark');
      root.classList.remove('light');
      root.style.colorScheme = 'dark';
      localStorage.setItem('senior_agent_theme_mode', 'dark');
    } else {
      root.classList.remove('dark');
      root.classList.add('light');
      root.style.colorScheme = 'light';
      localStorage.setItem('senior_agent_theme_mode', 'light');
    }
  }, [darkMode]);

  const isMultiAgentRunning = activeRuns.some((r) => r.source === 'multi-agent');
  const isPlaygroundRunning = activeRuns.some((r) => r.source === 'idea-playground');

  const navigateToRunSource = (targetTab: string) => {
    if (targetTab === 'idea-playground' || targetTab === 'playground') {
      setActiveTab('playground');
    } else {
      setActiveTab('multi-agent');
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-300 font-sans selection:bg-primary/30 selection:text-white flex">
      {/* Professional Enterprise Sidebar */}
      <aside
        className={cn(
          "fixed left-0 top-0 h-screen flex flex-col border-r border-border/80 bg-card/95 backdrop-blur-xl z-50 transition-all duration-300 shadow-2xl",
          sidebarExpanded ? "w-60" : "w-20"
        )}
      >
        {/* Brand Header */}
        <div className="h-16 px-4 flex items-center justify-between border-b border-border/60 shrink-0">
          <button
            onClick={() => setActiveTab('multi-agent')}
            className="flex items-center gap-3 text-left group cursor-pointer min-w-0"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/25 shrink-0 border border-white/10">
              <Cpu className="w-5 h-5 text-white" />
            </div>
            {sidebarExpanded && (
              <div className="min-w-0">
                <div className="font-bold text-sm tracking-tight text-foreground truncate flex items-center gap-1.5">
                  SeniorAgent OS
                  <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-primary/20 text-primary border border-primary/30">
                    v2.4
                  </span>
                </div>
                <div className="text-[10px] font-mono text-muted-foreground truncate">
                  gemma4:31b-cloud
                </div>
              </div>
            )}
          </button>
          <button
            onClick={() => setSidebarExpanded(!sidebarExpanded)}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors cursor-pointer shrink-0"
            title={sidebarExpanded ? "Collapse Sidebar" : "Expand Sidebar"}
          >
            {sidebarExpanded ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation Groups */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden py-4 px-2.5 space-y-5">
          <div className="space-y-1">
            {sidebarExpanded && (
              <div className="px-3 pb-1 text-[10px] font-mono uppercase tracking-wider text-muted-foreground/70 font-semibold">
                Core Workspaces
              </div>
            )}
            <NavItem
              icon={<Network className="w-4 h-4" />}
              active={activeTab === 'multi-agent'}
              onClick={() => setActiveTab('multi-agent')}
              label="Multi-Agent Hub"
              expanded={sidebarExpanded}
              badge={isMultiAgentRunning ? "RUNNING" : undefined}
              badgePulse={isMultiAgentRunning}
            />
            <NavItem
              icon={<Eye className="w-4 h-4 text-emerald-400" />}
              active={activeTab === 'preview'}
              onClick={() => setActiveTab('preview')}
              label="Live Preview Studio"
              expanded={sidebarExpanded}
              badge="LIVE"
            />
            <NavItem
              icon={<Sparkles className="w-4 h-4 text-amber-400" />}
              active={activeTab === 'playground'}
              onClick={() => setActiveTab('playground')}
              label="Idea Playground"
              expanded={sidebarExpanded}
              badge={isPlaygroundRunning ? "RUNNING" : "STUDIO"}
              badgePulse={isPlaygroundRunning}
            />
            <NavItem
              icon={<Layers className="w-4 h-4" />}
              active={activeTab === 'hubs'}
              onClick={() => setActiveTab('hubs')}
              label="Agent Teams & Hubs"
              expanded={sidebarExpanded}
            />
            <NavItem
              icon={<Brain className="w-4 h-4 text-purple-400" />}
              active={activeTab === 'memory'}
              onClick={() => setActiveTab('memory')}
              label="Agent Memory"
              expanded={sidebarExpanded}
              badge={memoryCount > 0 ? String(memoryCount) : undefined}
            />
            <NavItem
              icon={<FolderOpen className="w-4 h-4" />}
              active={activeTab === 'workspace'}
              onClick={() => setActiveTab('workspace')}
              label="Workspace Explorer"
              expanded={sidebarExpanded}
            />
            <NavItem
              icon={<Timer className="w-4 h-4" />}
              active={activeTab === 'loops'}
              onClick={() => setActiveTab('loops')}
              label="Scheduled Loops"
              expanded={sidebarExpanded}
            />
          </div>

          <div className="space-y-1">
            {sidebarExpanded && (
              <div className="px-3 pb-1 text-[10px] font-mono uppercase tracking-wider text-muted-foreground/70 font-semibold">
                Engineering & Eval
              </div>
            )}
            <NavItem
              icon={<Plus className="w-4 h-4" />}
              active={activeTab === 'builder'}
              onClick={() => setActiveTab('builder')}
              label="Worker Builder"
              expanded={sidebarExpanded}
            />
            <NavItem
              icon={<Brain className="w-4 h-4" />}
              active={activeTab === 'train'}
              onClick={() => setActiveTab('train')}
              label="Training & Testing"
              expanded={sidebarExpanded}
            />
            <NavItem
              icon={<LayoutGrid className="w-4 h-4" />}
              active={activeTab === 'arena'}
              onClick={() => setActiveTab('arena')}
              label="Agent Arena"
              expanded={sidebarExpanded}
            />
            <NavItem
              icon={<Trophy className="w-4 h-4" />}
              active={activeTab === 'leaderboard'}
              onClick={() => setActiveTab('leaderboard')}
              label="Latency & Telemetry"
              expanded={sidebarExpanded}
            />
          </div>

          <div className="space-y-1">
            {sidebarExpanded && (
              <div className="px-3 pb-1 text-[10px] font-mono uppercase tracking-wider text-muted-foreground/70 font-semibold">
                System & Account
              </div>
            )}
            <NavItem
              icon={<Settings className="w-4 h-4" />}
              active={activeTab === 'settings'}
              onClick={() => setActiveTab('settings')}
              label="System Settings"
              expanded={sidebarExpanded}
            />
            <NavItem
              icon={<Compass className="w-4 h-4" />}
              active={activeTab === 'landing'}
              onClick={() => setActiveTab('landing')}
              label="Platform Overview"
              expanded={sidebarExpanded}
            />
            <NavItem
              icon={isAuthenticated ? <UserIcon className="w-4 h-4" /> : <LogIn className="w-4 h-4" />}
              active={activeTab === 'login'}
              onClick={() => setActiveTab('login')}
              label={isAuthenticated ? "Account & Storage" : "Sign In / Register"}
              expanded={sidebarExpanded}
            />
          </div>
        </div>

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-border/60 flex items-center justify-between gap-2">
          {sidebarExpanded && (
            <div className="flex items-center gap-2 min-w-0">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
              <span className="text-[11px] font-mono text-muted-foreground truncate">
                Ollama Cloud Connected
              </span>
            </div>
          )}
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="p-2 rounded-lg hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors cursor-pointer mx-auto"
            title="Toggle Theme"
          >
            {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </aside>

      {/* Main Content Wrapper */}
      <div
        className={cn(
          "flex-1 flex flex-col min-h-screen transition-all duration-300",
          sidebarExpanded ? "pl-60" : "pl-20"
        )}
      >
        {/* Top Sticky Command Header */}
        <header className="sticky top-0 z-40 h-16 px-6 md:px-10 border-b border-border/70 bg-background/85 backdrop-blur-xl flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/30 text-primary text-xs font-mono">
              <Cpu className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">LLM Router:</span>
              <strong className="font-semibold">gemma4:31b-cloud</strong>
            </div>

            {/* MongoDB Real-Time Status Pill */}
            <button
              onClick={() => setActiveTab('landing')}
              className="hidden lg:flex items-center gap-1.5 px-3 py-1 rounded-full border border-border bg-card/70 hover:bg-card text-xs font-mono transition-colors cursor-pointer"
              title="Click to view storage details"
            >
              <Database className="w-3.5 h-3.5 text-primary" />
              <span className="text-muted-foreground">DB:</span>
              <span
                className={cn(
                  "flex items-center gap-1 font-medium",
                  mongoStatus?.connected ? "text-emerald-400" : "text-amber-400"
                )}
              >
                <span className={cn("w-1.5 h-1.5 rounded-full", mongoStatus?.connected ? "bg-emerald-400 animate-pulse" : "bg-amber-400")} />
                {mongoStatus?.connected ? `${mongoStatus.latency_ms}ms` : "SQLite + Local"}
              </span>
            </button>

            {/* LIVE ACTIVE AGENT PILL IN TOP BAR */}
            {isAnyAgentRunning && activeRuns[0] && (
              <div
                onClick={() => navigateToRunSource(activeRuns[0].targetTab)}
                className="flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 text-xs font-mono cursor-pointer hover:bg-emerald-500/25 transition-all shadow-[0_0_20px_rgba(16,185,129,0.2)] animate-in fade-in duration-200"
                title="Click to jump to the active running agent"
              >
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping shrink-0" />
                <span className="font-semibold truncate max-w-[200px] sm:max-w-[280px]">
                  Running: {activeRuns[0].workerName}
                </span>
                {activeRuns[0].activeTool && (
                  <span className="hidden md:inline-block px-1.5 py-0.2 rounded bg-emerald-500/20 text-[10px] text-emerald-200">
                    {activeRuns[0].activeTool}
                  </span>
                )}
                <span className="text-[10px] text-emerald-400/90">
                  {Math.max(1, Math.floor((nowTick - activeRuns[0].startedAt) / 1000))}s
                </span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2.5">
            {/* Prominent Theme Toggle Button in Header */}
            <button
              onClick={() => setDarkMode((prev) => !prev)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-border bg-card hover:bg-secondary text-foreground text-xs font-medium transition-all cursor-pointer shadow-sm"
              title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
              {darkMode ? (
                <>
                  <Sun className="w-3.5 h-3.5 text-amber-400" />
                  <span className="hidden sm:inline">Light</span>
                </>
              ) : (
                <>
                  <Moon className="w-3.5 h-3.5 text-primary" />
                  <span className="hidden sm:inline">Dark</span>
                </>
              )}
            </button>

            <AnimationSelector variant="compact" />

            {/* Quick Workspace Switcher */}
            <div className="hidden xl:flex items-center gap-1 bg-secondary/60 p-1 border border-border/80 rounded-xl">
              <button
                onClick={() => setActiveTab('multi-agent')}
                className={cn(
                  "px-3 py-1.5 text-xs font-medium transition-all rounded-lg flex items-center gap-1.5 cursor-pointer",
                  activeTab === 'multi-agent'
                    ? "bg-primary text-white shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <Network className="w-3.5 h-3.5" />
                Multi-Agent Hub
                {isMultiAgentRunning && <span className="w-1.5 h-1.5 rounded-full bg-emerald-300 animate-ping" />}
              </button>

              <button
                onClick={() => setActiveTab('preview')}
                className={cn(
                  "px-3 py-1.5 text-xs font-medium transition-all rounded-lg flex items-center gap-1.5 cursor-pointer",
                  activeTab === 'preview'
                    ? "bg-gradient-to-r from-emerald-600 to-cyan-600 text-white shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <Eye className="w-3.5 h-3.5 text-emerald-400" />
                Preview Studio
              </button>

              <button
                onClick={() => setActiveTab('playground')}
                className={cn(
                  "px-3 py-1.5 text-xs font-medium transition-all rounded-lg flex items-center gap-1.5 cursor-pointer",
                  activeTab === 'playground'
                    ? "bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                Playground
                {isPlaygroundRunning && <span className="w-1.5 h-1.5 rounded-full bg-emerald-300 animate-ping" />}
              </button>
            </div>

            {/* User Account Pill */}
            {isAuthenticated ? (
              <div className="flex items-center gap-2 bg-card px-3 py-1.5 border border-border rounded-full">
                <div className="w-6 h-6 rounded-full bg-primary text-white flex items-center justify-center font-bold text-xs">
                  {(user?.full_name || user?.username || 'U').charAt(0).toUpperCase()}
                </div>
                <span className="text-xs font-medium text-foreground hidden sm:inline">
                  {user?.full_name || user?.username}
                </span>
                <button
                  onClick={logout}
                  className="p-1 text-muted-foreground hover:text-red-400 transition-colors cursor-pointer"
                  title="Sign Out"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setActiveTab('login')}
                className="px-3.5 py-1.5 bg-primary/15 border border-primary/40 text-primary hover:bg-primary hover:text-white text-xs font-medium rounded-xl transition-all cursor-pointer flex items-center gap-1.5"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Sign In</span>
              </button>
            )}
          </div>
        </header>

        {/* Main Workspace Container */}
        <main className="flex-1 pt-6 pb-28 px-6 md:px-10 max-w-[1440px] w-full mx-auto">
          {/* Page Title Banner */}
          <div className="mb-6 flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-border/50 pb-4">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground">
                {activeTab === 'landing' && "Platform Architecture & Overview"}
                {activeTab === 'login' && (isAuthenticated ? "Account Profile & Database Settings" : "Sign In to SeniorAgent OS")}
                {activeTab === 'multi-agent' && "Autonomous Multi-Agent Command Center"}
                {activeTab === 'preview' && "Live App & Code Preview Studio"}
                {activeTab === 'hubs' && "Custom Agent Teams & Hubs"}
                {activeTab === 'workspace' && "Workspace File Explorer"}
                {activeTab === 'arena' && "Multi-Model Evaluation Arena"}
                {activeTab === 'leaderboard' && "Real-Time Performance & Latency Telemetry"}
                {activeTab === 'builder' && "Specialized Worker Agent Builder"}
                {activeTab === 'train' && "Agent Training & Verification Studio"}
                {activeTab === 'settings' && "Security, Permissions & Model Configuration"}
                {activeTab === 'loops' && "Autonomous Scheduled Loops & Crons"}
                {activeTab === 'playground' && "AI Studio Idea Playground"}
                {activeTab === 'memory' && "Agent Memory Vault & Knowledge"}
              </h1>
              <p className="text-sm text-muted-foreground mt-1 max-w-3xl">
                {activeTab === 'landing' && "Local-first multi-agent orchestration powered by gemma4:31b-cloud, LangGraph dynamic worker spawning, and persistent background execution."}
                {activeTab === 'login' && (isAuthenticated ? "Manage your authenticated account, storage engine mode, and database connection status." : "Access your private agent teams and encrypted memory workspaces.")}
                {activeTab === 'multi-agent' && "Generic LLM-driven orchestrator dynamically evaluates your worker catalog and spawns the optimal specialist while running seamlessly in the background."}
                {activeTab === 'preview' && "Interactive live rendering canvas with draggable split-screen code editor, responsive device viewports, and smooth Extend cinema mode."}
                {activeTab === 'hubs' && "Create Multi-Agent teams, register MCP servers, pull local Ollama models, and analyze token usage metrics."}
                {activeTab === 'workspace' && "Browse, inspect, and preview files generated by your agents inside the workspace."}
                {activeTab === 'arena' && "Benchmark agents side-by-side in real-time across speed, accuracy, and reasoning depth."}
                {activeTab === 'leaderboard' && "Track Time-to-First-Token (TTFT), total completion latency, and historical call metrics."}
                {activeTab === 'builder' && "Create new custom worker personas that the Orchestrator LLM can automatically discover and spawn."}
                {activeTab === 'train' && "Inject domain-specific knowledge and few-shot training examples into your worker agents."}
                {activeTab === 'settings' && "Configure tool capabilities, LLM routing models, and folder whitelist parameters."}
                {activeTab === 'loops' && "Manage recurring autonomous loops, scheduled checks, and background agent tasks."}
                {activeTab === 'playground' && "Experiment with Research & Business agents, custom system prompts, and live web tools."}
                {activeTab === 'memory' && "Inspect, search, and manage persistent memories, user preferences, and project facts saved by your agents across sessions."}
              </p>
            </div>
          </div>

          {/* PERSISTENT BACKGROUND-SAFE AGENT WORKSPACES */}
          {/* Keeping MultiAgentHub, IdeaPlayground, and LivePreviewStudio mounted ensures active streams & state never stop when navigating between tabs */}
          <div className={cn(activeTab === 'multi-agent' ? 'block animate-in fade-in duration-300' : 'hidden')}>
            <MultiAgentHub
              onOpenPlayground={() => setActiveTab('playground')}
              onOpenPreview={(fp) => {
                if (fp) setPreviewFilePath(fp);
                setActiveTab('preview');
              }}
            />
          </div>

          <div className={cn(activeTab === 'preview' ? 'block animate-in fade-in duration-300' : 'hidden')}>
            <LivePreviewStudio initialFilePath={previewFilePath} />
          </div>

          <div className={cn(activeTab === 'playground' ? 'block animate-in fade-in duration-300' : 'hidden')}>
            <IdeaPlayground />
          </div>

          {/* OTHER TABS */}
          {activeTab === 'landing' && (
            <section className="animate-in fade-in duration-300">
              <WhyChoosePage
                onEnterApp={() => setActiveTab('multi-agent')}
                onNavigateLogin={() => setActiveTab('login')}
              />
            </section>
          )}
          {activeTab === 'login' && (
            <section className="animate-in fade-in duration-300">
              <LoginPage
                onSuccess={() => setActiveTab('multi-agent')}
                onNavigateLanding={() => setActiveTab('landing')}
              />
            </section>
          )}
          {activeTab === 'hubs' && (
            <section className="animate-in fade-in duration-300">
              <HubCreator />
            </section>
          )}
          {activeTab === 'workspace' && (
            <section className="animate-in fade-in duration-300">
              <WorkspaceExplorer />
            </section>
          )}
          {activeTab === 'arena' && (
            <section className="animate-in fade-in duration-300">
              <AgentArena agents={agents} onRefreshLeaderboard={refreshData} />
            </section>
          )}
          {activeTab === 'leaderboard' && (
            <section className="animate-in fade-in duration-300">
              <Leaderboard data={leaderboard} />
            </section>
          )}
          {activeTab === 'builder' && (
            <section className="animate-in fade-in duration-300">
              <AgentBuilder
                onAgentCreated={() => {
                  refreshData();
                  setActiveTab('train');
                }}
              />
            </section>
          )}
          {activeTab === 'train' && (
            <section className="animate-in fade-in duration-300">
              <TrainingCenter />
            </section>
          )}
          {activeTab === 'settings' && (
            <section className="animate-in fade-in duration-300">
              <MultiAgentConfig />
            </section>
          )}
          {activeTab === 'loops' && (
            <section className="animate-in fade-in duration-300">
              <ScheduledTasks />
            </section>
          )}
          {activeTab === 'memory' && (
            <section className="animate-in fade-in duration-300">
              <AgentMemoryVault onOpenHub={() => setActiveTab('multi-agent')} />
            </section>
          )}
        </main>

        {/* Footer Branding */}
        <footer className="py-5 px-10 border-t border-border/50 text-muted-foreground/70 mt-auto">
          <div className="max-w-[1440px] mx-auto flex flex-col sm:flex-row justify-between items-center gap-2 font-mono text-[11px] uppercase tracking-wider">
            <span>SeniorAgent Enterprise Orchestrator</span>
            <span>Generic LLM Worker Router • gemma4:31b-cloud</span>
            <span>Background Execution Engine Active</span>
          </div>
        </footer>
      </div>

      {/* GLOBAL FLOATING & DRAGGABLE LIVE AGENT MONITOR DOCK (Visible across ALL pages whenever any agent is running) */}
      {isAnyAgentRunning && (
        <div
          style={{
            transform: `translate3d(${dockOffset.x}px, ${dockOffset.y}px, 0)`,
            transition: isDraggingDock ? 'none' : 'transform 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
          className="fixed bottom-5 right-24 z-50 max-w-md w-full px-4 pointer-events-none animate-in slide-in-from-bottom-4 duration-300"
        >
          <div
            className={cn(
              "pointer-events-auto rounded-2xl border bg-slate-950/95 backdrop-blur-2xl p-4 space-y-3 select-none",
              isDraggingDock
                ? "border-primary shadow-[0_25px_60px_rgba(59,130,246,0.4)] ring-2 ring-primary/50 cursor-grabbing"
                : "border-emerald-500/50 shadow-[0_15px_50px_rgba(16,185,129,0.25)]"
            )}
          >
            {/* Drag Handle Bar */}
            <div
              onMouseDown={(e) => {
                dockDragRef.current = {
                  startX: e.clientX,
                  startY: e.clientY,
                  origX: dockOffset.x,
                  origY: dockOffset.y,
                };
                setIsDraggingDock(true);
              }}
              className="flex items-center justify-between border-b border-slate-800/80 pb-2 cursor-grab active:cursor-grabbing text-[10px] font-mono uppercase tracking-wider text-slate-400"
              title="Drag to move the live agent monitor anywhere on screen"
            >
              <span className="flex items-center gap-1.5">
                <GripHorizontal className="w-3.5 h-3.5 text-emerald-400" />
                Live Background Agent Monitor (Drag to Move)
              </span>
              {(dockOffset.x !== 0 || dockOffset.y !== 0) && (
                <button
                  onClick={() => setDockOffset({ x: 0, y: 0 })}
                  className="text-[9px] text-emerald-400 hover:underline cursor-pointer"
                >
                  Reset Pos
                </button>
              )}
            </div>

            {activeRuns.map((run) => {
              const elapsedSec = Math.max(1, Math.floor((nowTick - run.startedAt) / 1000));
              const isCurrentPage =
                (run.targetTab === 'multi-agent' && activeTab === 'multi-agent') ||
                ((run.targetTab === 'idea-playground' || run.targetTab === 'playground') && activeTab === 'playground');

              return (
                <div key={run.id} className="space-y-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <SiriFluidOrb size="sm" state="thinking" />
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-semibold flex items-center gap-1">
                            <Activity className="w-3 h-3 animate-pulse" />
                            {isCurrentPage ? "Live Agent Running" : "Running in Background"}
                          </span>
                          <span className="text-[11px] font-mono text-emerald-400 font-bold">
                            {elapsedSec}s
                          </span>
                        </div>
                        <div className="font-bold text-sm text-white truncate mt-0.5">
                          {run.workerName}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {!isCurrentPage && (
                        <button
                          onClick={() => navigateToRunSource(run.targetTab)}
                          className="px-2.5 py-1.5 rounded-lg bg-primary hover:bg-primary/90 text-white text-xs font-medium flex items-center gap-1 shadow cursor-pointer transition-all"
                          title="Jump to Live Agent Stream"
                        >
                          <span>View Live</span>
                          <ExternalLink className="w-3 h-3" />
                        </button>
                      )}
                      <button
                        onClick={() => stopRun(run.id)}
                        className="px-2.5 py-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-300 border border-red-500/40 text-xs font-mono uppercase flex items-center gap-1 cursor-pointer transition-all"
                        title="Stop Agent Execution"
                      >
                        <Square className="w-3 h-3 fill-current" />
                        <span>Stop</span>
                      </button>
                    </div>
                  </div>

                  {run.routingReason && (
                    <div className="text-[11px] text-slate-300 bg-slate-900/90 px-3 py-2 rounded-lg border border-slate-800 leading-relaxed">
                      <span className="text-purple-400 font-mono uppercase text-[10px] font-semibold mr-1.5">
                        LLM Router ({run.model}):
                      </span>
                      {run.routingReason}
                    </div>
                  )}

                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-1 border-t border-slate-800/80">
                    <span className="truncate flex items-center gap-1.5">
                      <Loader2 className="w-3 h-3 animate-spin text-emerald-400 shrink-0" />
                      {run.activeTool ? `Executing Tool: ${run.activeTool}` : `Status: ${run.step.toUpperCase()}`}
                    </span>
                    <span className="text-[10px] text-slate-500 uppercase">{run.sourceLabel}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* AI Guide - Context-aware assistant */}
      <AIGuide
        context={activeTab}
        config={{
          theme: darkMode ? 'dark' : 'light',
          primaryColor: '#3b82f6',
          autoOpen: false,
        }}
      />

      {/* Quick Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />
    </div>
  );
};

const App: React.FC = () => (
  <AuthProvider>
    <AgentExecutionProvider>
      <AppContent />
    </AgentExecutionProvider>
  </AuthProvider>
);

interface NavItemProps {
  icon: React.ReactNode;
  active: boolean;
  onClick: () => void;
  label: string;
  expanded: boolean;
  badge?: string;
  badgePulse?: boolean;
}

const NavItem: React.FC<NavItemProps> = ({ icon, active, onClick, label, expanded, badge, badgePulse }) => (
  <button
    onClick={onClick}
    className={cn(
      "group relative w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 cursor-pointer",
      active
        ? "bg-primary/15 text-primary border border-primary/30 shadow-sm font-semibold"
        : "text-muted-foreground hover:text-foreground hover:bg-secondary/60 border border-transparent",
      !expanded && "justify-center px-0"
    )}
    title={!expanded ? label : undefined}
  >
    <div className={cn("shrink-0 transition-transform duration-200", active && "scale-110")}>
      {icon}
    </div>
    {expanded && (
      <span className="truncate flex-1 text-left">{label}</span>
    )}
    {expanded && badge && (
      <span
        className={cn(
          "text-[9px] font-mono uppercase px-1.5 py-0.5 rounded-full font-bold shrink-0 flex items-center gap-1",
          badgePulse
            ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
            : "bg-purple-500/20 text-purple-300 border border-purple-500/30"
        )}
      >
        {badgePulse && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />}
        {badge}
      </span>
    )}
    {!expanded && badgePulse && (
      <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
    )}
  </button>
);

export default App;
