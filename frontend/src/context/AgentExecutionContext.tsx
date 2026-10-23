import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { OllamaService } from '../services/ollama';

export interface ActiveAgentRun {
  id: string;
  runId?: string;
  source: 'multi-agent' | 'idea-playground' | 'scheduler' | 'direct-agent' | string;
  sourceLabel: string;
  targetTab: string;
  workerId: string | null;
  workerName: string;
  routingReason?: string;
  confidence?: number;
  executionFocus?: string;
  activeTool?: string | null;
  step: string;
  prompt: string;
  model: string;
  startedAt: number;
  canStop?: boolean;
}

interface AgentExecutionContextType {
  activeRuns: ActiveAgentRun[];
  recentRuns: any[];
  isAnyAgentRunning: boolean;
  upsertLocalRun: (run: ActiveAgentRun) => void;
  removeLocalRun: (id: string) => void;
  registerStopHandler: (id: string, handler: () => void) => void;
  stopRun: (id: string) => Promise<void>;
  refreshRunningAgents: () => Promise<void>;
}

const AgentExecutionContext = createContext<AgentExecutionContextType | undefined>(undefined);

const WORKER_DISPLAY_NAMES: Record<string, string> = {
  orchestrator: 'Orchestrator Router (gemma4:31b-cloud)',
  code: 'Code Generation Specialist',
  analyze_and_fix: 'Codebase Diagnostics & Repair Specialist',
  research: 'Deep Research & Web Intelligence Specialist',
  analysis: 'Code Audit, Architecture & Vision Specialist',
  business: 'Business Operations & Financial Ledger Specialist',
  general: 'General Reasoning & Strategy Assistant',
};

export const formatWorkerDisplayName = (workerId?: string | null, workerName?: string | null): string => {
  if (workerName && workerName.trim() && workerName !== workerId) {
    return workerName;
  }
  if (!workerId) return 'Orchestrator Router (gemma4:31b-cloud)';
  return WORKER_DISPLAY_NAMES[workerId] || workerId.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
};

export const AgentExecutionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [localRuns, setLocalRuns] = useState<Record<string, ActiveAgentRun>>({});
  const [backendRuns, setBackendRuns] = useState<ActiveAgentRun[]>([]);
  const [recentRuns, setRecentRuns] = useState<any[]>([]);
  const stopHandlersRef = useRef<Record<string, () => void>>({});

  const upsertLocalRun = useCallback((run: ActiveAgentRun) => {
    setLocalRuns((prev) => ({
      ...prev,
      [run.id]: run,
    }));
  }, []);

  const removeLocalRun = useCallback((id: string) => {
    setLocalRuns((prev) => {
      if (!prev[id]) return prev;
      const next = { ...prev };
      delete next[id];
      return next;
    });
    delete stopHandlersRef.current[id];
  }, []);

  const registerStopHandler = useCallback((id: string, handler: () => void) => {
    stopHandlersRef.current[id] = handler;
  }, []);

  const refreshRunningAgents = useCallback(async () => {
    try {
      const data = await OllamaService.getRunningAgents();
      if (data && data.status === 'success') {
        const mapped: ActiveAgentRun[] = (data.active || []).map((r) => {
          const isIdea = r.source === 'direct-agent' || r.source === 'idea-playground';
          return {
            id: r.run_id,
            runId: r.run_id,
            source: isIdea ? 'idea-playground' : 'multi-agent',
            sourceLabel: isIdea ? 'Idea Playground' : 'Multi-Agent Hub',
            targetTab: isIdea ? 'idea-playground' : 'multi-agent',
            workerId: r.selected_agent || 'orchestrator',
            workerName: formatWorkerDisplayName(r.selected_agent, r.worker_name),
            routingReason: r.routing_reason || 'Evaluating worker capabilities via gemma4:31b-cloud...',
            confidence: r.confidence || 0.92,
            activeTool: r.active_tool,
            step: r.step || 'executing',
            prompt: r.prompt || '',
            model: r.model || 'gemma4:31b-cloud',
            startedAt: r.started_at ? r.started_at * 1000 : Date.now(),
            canStop: true,
          };
        });
        setBackendRuns(mapped);
        if (Array.isArray(data.recent)) {
          setRecentRuns(data.recent);
        }
      }
    } catch {
      // Ignore transient network errors during polling
    }
  }, []);

  useEffect(() => {
    refreshRunningAgents();
    const interval = setInterval(refreshRunningAgents, 2000);
    return () => clearInterval(interval);
  }, [refreshRunningAgents]);

  // Merge localRuns (instant client-side state) with backendRuns (server-side state)
  const activeRuns: ActiveAgentRun[] = React.useMemo(() => {
    const localList = Object.values(localRuns);
    const localRunIds = new Set(localList.map((r) => r.runId).filter(Boolean));
    const localSources = new Set(localList.map((r) => r.source));

    const merged = [...localList];
    for (const bRun of backendRuns) {
      if (bRun.runId && localRunIds.has(bRun.runId)) continue;
      if (localSources.has(bRun.source)) continue;
      merged.push(bRun);
    }
    return merged;
  }, [localRuns, backendRuns]);

  const stopRun = useCallback(
    async (id: string) => {
      if (stopHandlersRef.current[id]) {
        stopHandlersRef.current[id]();
      }
      try {
        await OllamaService.stopMultiAgent('default');
      } catch {
        // ignore
      }
      removeLocalRun(id);
      setTimeout(refreshRunningAgents, 400);
    },
    [removeLocalRun, refreshRunningAgents]
  );

  return (
    <AgentExecutionContext.Provider
      value={{
        activeRuns,
        recentRuns,
        isAnyAgentRunning: activeRuns.length > 0,
        upsertLocalRun,
        removeLocalRun,
        registerStopHandler,
        stopRun,
        refreshRunningAgents,
      }}
    >
      {children}
    </AgentExecutionContext.Provider>
  );
};

export const useAgentExecution = (): AgentExecutionContextType => {
  const ctx = useContext(AgentExecutionContext);
  if (!ctx) {
    throw new Error('useAgentExecution must be used within an AgentExecutionProvider');
  }
  return ctx;
};
