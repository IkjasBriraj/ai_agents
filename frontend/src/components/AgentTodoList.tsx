import React from 'react';
import { CheckCircle2, Circle, Loader2, XCircle, ListTodo } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface TodoItem {
  id: string;
  title: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  details?: string;
}

interface AgentTodoListProps {
  todoItems: TodoItem[];
  title?: string;
  className?: string;
  compact?: boolean;
}

export const AgentTodoList: React.FC<AgentTodoListProps> = ({
  todoItems,
  title = "Live Agent Execution To-Do List",
  className,
  compact = false
}) => {
  if (!todoItems || todoItems.length === 0) return null;

  const completedCount = todoItems.filter(item => item.status === 'completed').length;
  const inProgressCount = todoItems.filter(item => item.status === 'in_progress').length;
  const totalCount = todoItems.length;
  const percentage = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  return (
    <div className={cn(
      "carbon-card p-4 rounded-xl bg-[#0d0d1a]/95 border border-emerald-500/30 shadow-2xl backdrop-blur-xl transition-all duration-300 animate-in fade-in slide-in-from-top-2",
      className
    )}>
      {/* Header & Overall Progress */}
      <div className="flex items-center justify-between mb-3 gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shrink-0">
            <ListTodo className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <h4 className="text-xs font-bold font-mono tracking-wider uppercase text-foreground truncate">
              {title}
            </h4>
            <div className="text-[10px] text-muted-foreground font-mono truncate">
              {completedCount} of {totalCount} tasks completed
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {inProgressCount > 0 && (
            <span className="flex items-center gap-1.5 text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-400 animate-pulse">
              <Loader2 className="w-3 h-3 animate-spin" />
              Active Task
            </span>
          )}
          <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-500/15 px-2.5 py-0.5 rounded-full border border-emerald-500/30 shadow-sm">
            {percentage}%
          </span>
        </div>
      </div>

      {/* Executive Progress Bar */}
      <div className="w-full bg-slate-900/90 rounded-full h-2 overflow-hidden mb-3.5 border border-emerald-500/20 p-0.5">
        <div 
          className="bg-gradient-to-r from-emerald-500 via-teal-400 to-indigo-400 h-full rounded-full transition-all duration-500 ease-out shadow-[0_0_12px_rgba(52,211,153,0.5)]"
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Task List Items */}
      <div className={cn("space-y-2", compact ? "max-h-56 overflow-y-auto pr-1" : "max-h-80 overflow-y-auto pr-1")}>
        {todoItems.map((item) => {
          const isCompleted = item.status === 'completed';
          const isInProgress = item.status === 'in_progress';
          const isFailed = item.status === 'failed';

          return (
            <div 
              key={item.id}
              className={cn(
                "flex items-start gap-3 p-2.5 rounded-lg border text-xs transition-all duration-200",
                isCompleted && "bg-emerald-950/25 border-emerald-500/40 text-emerald-100",
                isInProgress && "bg-violet-950/40 border-violet-500/60 text-foreground shadow-md shadow-violet-500/10",
                isFailed && "bg-red-950/30 border-red-500/40 text-red-200",
                item.status === 'pending' && "bg-slate-900/40 border-slate-700/40 text-slate-400 opacity-80"
              )}
            >
              {/* Status Icon */}
              <div className="shrink-0 mt-0.5">
                {isCompleted && (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.6)]" />
                )}
                {isInProgress && (
                  <Loader2 className="w-4 h-4 text-violet-400 animate-spin drop-shadow-[0_0_8px_rgba(167,139,250,0.6)]" />
                )}
                {isFailed && (
                  <XCircle className="w-4 h-4 text-red-400" />
                )}
                {item.status === 'pending' && (
                  <Circle className="w-4 h-4 text-slate-500" />
                )}
              </div>

              {/* Title & Details */}
              <div className="flex-1 min-w-0">
                <div className={cn(
                  "font-medium leading-snug",
                  isCompleted && "line-through text-emerald-300/70 font-normal"
                )}>
                  {item.title}
                </div>
                {item.details && (
                  <div className="text-[11px] text-muted-foreground mt-0.5 font-mono opacity-85 truncate">
                    {item.details}
                  </div>
                )}
              </div>

              {/* Status Badge */}
              <div className="shrink-0 font-mono text-[9px] uppercase tracking-wider px-2 py-0.5 rounded border font-semibold">
                {isCompleted && <span className="text-emerald-400 border-emerald-500/30 bg-emerald-500/10">Done</span>}
                {isInProgress && <span className="text-violet-400 border-violet-500/30 bg-violet-500/10">In Progress</span>}
                {isFailed && <span className="text-red-400 border-red-500/30 bg-red-500/10">Failed</span>}
                {item.status === 'pending' && <span className="text-slate-400 border-slate-700/40 bg-slate-800/40">Pending</span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
