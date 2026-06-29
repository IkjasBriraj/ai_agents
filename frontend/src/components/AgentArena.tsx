import React, { useState } from 'react';
import { type Agent, OllamaService } from '@/services/ollama';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Zap, Send, Timer, Activity } from 'lucide-react';
import { cn, formatLatency } from '@/lib/utils';

interface ArenaProps {
  agents: Agent[];
  onRefreshLeaderboard: () => void;
}

export const AgentArena: React.FC<ArenaProps> = ({ agents, onRefreshLeaderboard }) => {
  const [prompt, setPrompt] = useState('');
  const [results, setResults] = useState<Record<string, { text: string; time: number; loading: boolean }>>({});
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);

  const toggleAgent = (id: string) => {
    if (selectedAgents.includes(id)) {
      setSelectedAgents(selectedAgents.filter(a => a !== id));
    } else if (selectedAgents.length < 2) {
      setSelectedAgents([...selectedAgents, id]);
    }
  };

  const runTest = async () => {
    if (!prompt || selectedAgents.length < 2) return;

    const newResults: typeof results = {};
    selectedAgents.forEach(id => {
      newResults[id] = { text: '', time: 0, loading: true };
    });
    setResults(newResults);

    const startTime = performance.now();

    const promises = selectedAgents.map(async (id) => {
      try {
        const response = await OllamaService.chat(id, prompt);
        const endTime = performance.now();
        setResults(prev => ({
          ...prev,
          [id]: { text: response, time: endTime - startTime, loading: false }
        }));
      } catch (err) {
        setResults(prev => ({
          ...prev,
          [id]: { text: 'Error fetching response.', time: 0, loading: false }
        }));
      }
    });

    await Promise.all(promises);
    onRefreshLeaderboard();
  };

  const fastestId = Object.entries(results).reduce((acc, [id, data]) => {
    if (!acc || (data.time > 0 && data.time < results[acc].time)) return id;
    return acc;
  }, '');

  return (
    <div className="space-y-8">
      <Card>
        <CardHeader>
          <CardTitle>Arena Sandbox</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            {agents.map(agent => (
              <Button
                key={agent.id}
                variant={selectedAgents.includes(agent.id) ? "carbon" : "outline"}
                onClick={() => toggleAgent(agent.id)}
                className="h-auto p-4 flex flex-col items-start gap-1 text-left"
              >
                <span className="font-bold">{agent.name}</span>
                <span className="text-sm opacity-70">{agent.base_model}</span>
              </Button>
            ))}
          </div>

          <div className="flex gap-4">
            <textarea
              className="flex-1 p-6 bg-muted border border-border min-h-[150px] text-lg focus:outline-none focus:ring-2 focus:ring-ibm-blue transition-all"
              placeholder="Enter a prompt to test both agents..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
            <Button 
              disabled={selectedAgents.length < 2 || !prompt}
              onClick={runTest}
              className="h-auto px-8 py-4 text-lg"
            >
              <Send className="mr-2 w-5 h-5" />
              Run Arena
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-8">
        {selectedAgents.map(id => {
          const agent = agents.find(a => a.id === id);
          const result = results[id];
          const isFastest = id === fastestId && !result?.loading && result?.time > 0;

          return (
            <Card key={id} className={cn("transition-all duration-500", isFastest && "border-ibm-blue ring-2 ring-ibm-blue")}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b border-border/50">
                <CardTitle className="text-2xl font-medium">{agent?.name}</CardTitle>
                <div className="flex gap-2">
                  {isFastest && (
                    <span className="bg-ibm-blue text-white text-xs px-2 py-1 flex items-center gap-1 font-bold">
                      <Zap className="w-3 h-3" /> FASTEST
                    </span>
                  )}
                  {agent?.base_model.includes('cloud') && (
                    <span className="bg-purple-600 text-white text-xs px-2 py-1 flex items-center gap-1 font-bold">
                      <Activity className="w-3 h-3" /> CLOUD
                    </span>
                  )}
                </div>
              </CardHeader>
              <CardContent className="pt-6 space-y-6">
                <div className="flex items-center gap-4 text-sm font-mono text-muted-foreground bg-muted/30 p-2 w-fit">
                  <span className="flex items-center gap-1">
                    <Timer className="w-4 h-4" />
                    {result?.loading ? "Processing..." : result?.time ? formatLatency(result.time) : "---"}
                  </span>
                </div>
                <div className="p-6 bg-muted/20 font-sans text-xl leading-relaxed whitespace-pre-wrap min-h-[300px] border border-border/20 shadow-inner">
                  {result?.loading ? (
                    <div className="flex flex-col gap-4">
                      <div className="h-4 bg-muted-foreground/10 animate-pulse w-full"></div>
                      <div className="h-4 bg-muted-foreground/10 animate-pulse w-3/4"></div>
                      <div className="h-4 bg-muted-foreground/10 animate-pulse w-5/6"></div>
                      <div className="h-4 bg-muted-foreground/10 animate-pulse w-1/2"></div>
                    </div>
                  ) : (
                    result?.text || "Awaiting prompt..."
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
};
