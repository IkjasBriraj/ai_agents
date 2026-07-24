import { useState } from 'react';
import { BookOpen, Pencil, Search, Terminal, ChevronDown, ChevronRight, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ToolStepProps {
  tool: string;       // e.g., "Read", "Edit", "Grep", "Bash"
  target: string;     // e.g., "src/main.py"
  status: 'running' | 'done' | 'error';
  result?: string;    // Output/result text
}

export function AgentModeToolStep({ tool, target, status, result }: ToolStepProps) {
  const [expanded, setExpanded] = useState(false);

  // Determine icon and color based on tool name
  const getToolConfig = () => {
    const t = tool.toLowerCase();
    if (t.includes('read') || t.includes('glob') || t.includes('ls')) {
      return { icon: BookOpen, color: 'text-blue-400', bg: 'bg-blue-400/10' };
    }
    if (t.includes('write') || t.includes('edit') || t.includes('multiedit')) {
      return { icon: Pencil, color: 'text-emerald-400', bg: 'bg-emerald-400/10' };
    }
    if (t.includes('grep') || t.includes('search')) {
      return { icon: Search, color: 'text-amber-400', bg: 'bg-amber-400/10' };
    }
    if (t.includes('bash') || t.includes('run')) {
      return { icon: Terminal, color: 'text-red-400', bg: 'bg-red-400/10' };
    }
    return { icon: Terminal, color: 'text-gray-400', bg: 'bg-gray-400/10' };
  };

  const { icon: Icon, color, bg } = getToolConfig();

  return (
    <div className="my-2 border border-border/50 bg-[#151525] overflow-hidden text-sm animate-in fade-in slide-in-from-bottom-2 duration-300">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-2 hover:bg-white/5 transition-colors cursor-pointer text-left"
        disabled={!result && status !== 'error'}
      >
        <div className="flex items-center gap-3 overflow-hidden">
          <div className={cn("p-1.5 flex items-center justify-center", bg, color)}>
            {status === 'running' ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Icon className="w-4 h-4" />
            )}
          </div>
          <div className="flex flex-col truncate">
            <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              {tool}
            </span>
            <span className="font-mono text-xs truncate max-w-[250px] text-foreground">
              {target}
            </span>
          </div>
        </div>
        
        <div className="flex items-center gap-2 pr-2">
          {status === 'error' && (
            <span className="text-red-400 text-[10px] font-mono uppercase">Failed</span>
          )}
          {status === 'done' && (
            <span className="text-emerald-400 text-[10px] font-mono uppercase">Done</span>
          )}
          {(result || status === 'error') && (
            expanded ? <ChevronDown className="w-4 h-4 text-muted-foreground" /> : <ChevronRight className="w-4 h-4 text-muted-foreground" />
          )}
        </div>
      </button>

      <div 
        className={cn(
          "grid transition-all duration-200 ease-in-out",
          expanded ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
        )}
      >
        <div className="overflow-hidden">
          {result && (
            <div className="p-3 bg-black/40 border-t border-border/50">
              <pre className="font-mono text-[11px] text-gray-300 whitespace-pre-wrap max-h-[300px] overflow-y-auto">
                {result}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
