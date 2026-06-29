import React from 'react';
import type { LeaderboardEntry } from '@/services/ollama';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { formatLatency } from '@/lib/utils';
import { Zap, Activity, Clock } from 'lucide-react';

interface LeaderboardProps {
  data: LeaderboardEntry[];
}

export const Leaderboard: React.FC<LeaderboardProps> = ({ data }) => {
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="text-ibm-blue" />
          Agent Performance Leaderboard
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                <th className="p-4 font-medium">Rank</th>
                <th className="p-4 font-medium">Agent Name</th>
                <th className="p-4 font-medium">Avg. TTFT</th>
                <th className="p-4 font-medium">Avg. Total Time</th>
                <th className="p-4 font-medium text-right">Interactions</th>
              </tr>
            </thead>
            <tbody>
              {data.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-muted-foreground">
                    No performance data available yet. Start a chat in the Arena!
                  </td>
                </tr>
              ) : (
                data.map((entry, index) => (
                  <tr key={entry.id} className="border-b border-border hover:bg-muted/30 transition-colors">
                    <td className="p-4">
                      <span className={`inline-flex items-center justify-center w-8 h-8 font-mono text-sm ${index === 0 ? 'bg-ibm-blue text-white' : 'bg-muted'}`}>
                        {index + 1}
                      </span>
                    </td>
                    <td className="p-4 font-medium">{entry.name}</td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-yellow-500" />
                        {formatLatency(entry.avg_ttft)}
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-ibm-blue" />
                        {formatLatency(entry.avg_total)}
                      </div>
                    </td>
                    <td className="p-4 text-right font-mono">{entry.calls}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
};
