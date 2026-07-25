import React, { useState, useEffect } from 'react';
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
import { LayoutGrid, Trophy, Plus, Moon, Sun, Cpu, Brain, Network, Settings, FolderOpen, Layers, Timer, Sparkles } from 'lucide-react';
import { AnimationSelector } from '@/components/AnimationSelector';
import { cn } from '@/lib/utils';

type Tab = 'dashboard' | 'leaderboard' | 'arena' | 'builder' | 'train' | 'multi-agent' | 'settings' | 'workspace' | 'hubs' | 'loops' | 'playground';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('playground');
  const [agents, setAgents] = useState<Agent[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [darkMode, setDarkMode] = useState(true);

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

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-300 font-sans selection:bg-ibm-blue selection:text-white">
      {/* Sidebar / Navigation */}
      <nav className="fixed left-0 top-0 h-screen w-20 flex flex-col items-center py-6 border-r border-border bg-card z-50 overflow-hidden">
        <div className="mb-6 flex-shrink-0">
          <Cpu className="w-9 h-9 text-ibm-blue" />
        </div>
        
        <div className="flex-1 flex flex-col gap-3 overflow-y-auto overflow-x-hidden no-scrollbar w-full items-center py-2">
          <NavIcon 
            icon={<Network />} 
            active={activeTab === 'multi-agent'} 
            onClick={() => setActiveTab('multi-agent')} 
            label="Multi-Agent Hub"
          />
          <NavIcon 
            icon={<Sparkles />} 
            active={activeTab === 'playground'} 
            onClick={() => setActiveTab('playground')} 
            label="Play with Your Ideas"
          />
          <NavIcon 
            icon={<Layers />} 
            active={activeTab === 'hubs'} 
            onClick={() => setActiveTab('hubs')} 
            label="Agent Teams (Hubs)"
          />
          <NavIcon 
            icon={<FolderOpen />} 
            active={activeTab === 'workspace'} 
            onClick={() => setActiveTab('workspace')} 
            label="Workspace"
          />
          <NavIcon 
            icon={<Timer />} 
            active={activeTab === 'loops'} 
            onClick={() => setActiveTab('loops')} 
            label="Loops & Schedules"
          />
          <NavIcon 
            icon={<LayoutGrid />} 
            active={activeTab === 'arena'} 
            onClick={() => setActiveTab('arena')} 
            label="Arena"
          />
          <NavIcon 
            icon={<Trophy />} 
            active={activeTab === 'leaderboard'} 
            onClick={() => setActiveTab('leaderboard')} 
            label="Stats"
          />
          <NavIcon 
            icon={<Plus />} 
            active={activeTab === 'builder'} 
            onClick={() => setActiveTab('builder')} 
            label="Build"
          />
          <NavIcon 
            icon={<Brain />} 
            active={activeTab === 'train'} 
            onClick={() => setActiveTab('train')} 
            label="Train & Test"
          />
          <NavIcon 
            icon={<Settings />} 
            active={activeTab === 'settings'} 
            onClick={() => setActiveTab('settings')} 
            label="Agent Settings"
          />
        </div>

        <button 
          onClick={() => setDarkMode(!darkMode)}
          className="p-3 mt-2 flex-shrink-0 hover:bg-muted transition-colors text-muted-foreground hover:text-ibm-blue"
        >
          {darkMode ? <Sun /> : <Moon />}
        </button>
      </nav>

      {/* Main Content */}
      <main className="pl-20 pt-12 pb-24 px-12 max-w-7xl mx-auto">
        <header className="mb-10">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
            <div className="flex items-center gap-2 text-ibm-blue font-mono text-sm tracking-widest uppercase">
              <span className="w-8 h-[2px] bg-ibm-blue"></span>
              Agentic OS v1.0
            </div>

            <div className="flex items-center gap-3">
              {/* Animation Mode Selector (Liquid Core vs Slime AI Companion) */}
              <AnimationSelector variant="compact" />

              {/* Quick Switcher Tabs */}
              <div className="flex items-center gap-2 bg-card p-1.5 border border-border rounded-lg shadow-sm">
                <button
                  onClick={() => setActiveTab('multi-agent')}
                  className={cn(
                    "px-4 py-2 text-xs font-mono tracking-wider uppercase transition-all rounded-md flex items-center gap-2",
                    activeTab === 'multi-agent'
                      ? "bg-ibm-blue text-white font-semibold shadow-md"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  )}
                >
                  <Network className="w-4 h-4" />
                  Multi-Agent Hub
                </button>
                <button
                  onClick={() => setActiveTab('playground')}
                  className={cn(
                    "px-4 py-2 text-xs font-mono tracking-wider uppercase transition-all rounded-md flex items-center gap-2",
                    activeTab === 'playground'
                      ? "bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-semibold shadow-md"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  )}
                >
                  <Sparkles className="w-4 h-4 text-amber-400" />
                  Play with Your Ideas
                </button>
              </div>
            </div>
          </div>

          <h1 className="text-6xl font-light tracking-tight mb-2">
            {activeTab === 'multi-agent' && "Multi-Agent Hub"}
            {activeTab === 'hubs' && "Custom Agent Teams & Hubs"}
            {activeTab === 'workspace' && "Workspace Explorer"}
            {activeTab === 'arena' && "Agent Arena"}
            {activeTab === 'leaderboard' && "Performance Stats"}
            {activeTab === 'builder' && "Orchestrator Builder"}
            {activeTab === 'train' && "Training & Testing Center"}
            {activeTab === 'settings' && "Agent Settings & Permissions"}
            {activeTab === 'loops' && "Scheduled Loops & Tasks"}
            {activeTab === 'playground' && "Play with Your Ideas"}
          </h1>
          <p className="text-xl text-muted-foreground font-light max-w-2xl">
            {activeTab === 'multi-agent' && "Orchestrate specialized agents (Code, Research, Analysis) inside a LangGraph routing network."}
            {activeTab === 'hubs' && "Create Multi-Agent teams, register MCP servers, pull local Ollama models, and analyze token usage metrics."}
            {activeTab === 'workspace' && "Browse and inspect files inside your allowed directory whitelists."}
            {activeTab === 'arena' && "Compare local agents in real-time. Testing speed, accuracy, and senior-friendly response quality."}
            {activeTab === 'leaderboard' && "Ranking agents based on Time-to-First-Token (TTFT) and total processing latency."}
            {activeTab === 'builder' && "Define new agent personas with customized system prompts and tool integrations."}
            {activeTab === 'train' && "Inject specific knowledge into your agents and test their responses in real-time."}
            {activeTab === 'settings' && "Configure tool capabilities and folder whitelist parameters for local execution."}
            {activeTab === 'loops' && "Manage recurring loops, scheduled checks, and timed agent tasks."}
            {activeTab === 'playground' && "Experiment freely with Research & Business agents in a Google AI Studio-style workspace."}
          </p>
        </header>

        <section className="animate-in fade-in slide-in-from-bottom-4 duration-700">
          {activeTab === 'multi-agent' && (
            <MultiAgentHub onOpenPlayground={() => setActiveTab('playground')} />
          )}
          {activeTab === 'hubs' && (
            <HubCreator />
          )}
          {activeTab === 'workspace' && (
            <WorkspaceExplorer />
          )}
          {activeTab === 'arena' && (
            <AgentArena 
              agents={agents} 
              onRefreshLeaderboard={refreshData} 
            />
          )}
          {activeTab === 'leaderboard' && (
            <Leaderboard data={leaderboard} />
          )}
          {activeTab === 'builder' && (
            <AgentBuilder onAgentCreated={() => {
              refreshData();
              setActiveTab('train');
            }} />
          )}
          {activeTab === 'train' && (
            <TrainingCenter />
          )}
          {activeTab === 'settings' && (
            <MultiAgentConfig />
          )}
          {activeTab === 'loops' && (
            <ScheduledTasks />
          )}
          {activeTab === 'playground' && (
            <IdeaPlayground />
          )}
        </section>
      </main>

      {/* Footer Branding */}
      <footer className="pl-20 py-8 px-12 border-t border-border opacity-50">
        <div className="max-w-7xl mx-auto flex justify-between items-center font-mono text-xs uppercase tracking-widest">
          <span>Enterprise AI Solutions</span>
          <span>Local-First Intelligence</span>
          <span>© 2026 SeniorAgent Core</span>
        </div>
      </footer>

      {/* AI Guide - Context-aware assistant */}
      <AIGuide
        context={activeTab}
        config={{
          theme: darkMode ? 'dark' : 'light',
          primaryColor: '#0f62fe',
          autoOpen: true,
        }}
      />
    </div>
  );
};

interface NavIconProps {
  icon: React.ReactNode;
  active: boolean;
  onClick: () => void;
  label: string;
}

const NavIcon: React.FC<NavIconProps> = ({ icon, active, onClick, label }) => (
  <button 
    onClick={onClick}
    className={cn(
      "group relative p-4 transition-all duration-300",
      active ? "text-ibm-blue" : "text-muted-foreground hover:text-foreground"
    )}
  >
    <div className="w-6 h-6">{icon}</div>
    {active && (
      <div className="absolute left-0 top-0 h-full w-1 bg-ibm-blue"></div>
    )}
    <span className="absolute left-full ml-4 px-2 py-1 bg-ibm-blue text-white text-[10px] uppercase tracking-tighter opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50">
      {label}
    </span>
  </button>
);

export default App;
