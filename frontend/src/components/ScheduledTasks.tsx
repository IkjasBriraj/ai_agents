import React, { useState, useEffect, useCallback } from 'react';
import { OllamaService } from '@/services/ollama';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  Timer, Play, Pause, Trash2, Plus, Clock, RefreshCw,
  ChevronDown, ChevronUp, Zap, RotateCcw, CheckCircle2,
  XCircle, AlertCircle
} from 'lucide-react';

// ─── Types ───────────────────────────────────────────────────────────────────

interface TaskHistoryEntry {
  timestamp: string;
  status: string;
  summary: string;
}

interface ScheduledTask {
  id: string;
  name: string;
  prompt: string;
  interval_minutes: number | null;
  run_at: string;
  last_run: string | null;
  status: string; // 'active' | 'paused' | 'running' | 'completed'
  history: TaskHistoryEntry[];
  created_at: string;
}

type TaskType = 'one-time' | 'recurring';
type IntervalUnit = 'minutes' | 'hours' | 'days';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatInterval(minutes: number | null): string {
  if (minutes === null || minutes === 0) return 'One-time';
  if (minutes < 60) return `Every ${minutes} min`;
  if (minutes < 1440) {
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return m > 0 ? `Every ${h}h ${m}m` : `Every ${h}h`;
  }
  const d = Math.floor(minutes / 1440);
  return d === 1 ? 'Every day' : `Every ${d} days`;
}

function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return '—';
  const date = new Date(dateStr);
  const now = new Date();
  const diff = date.getTime() - now.getTime();
  const absDiff = Math.abs(diff);

  if (absDiff < 60_000) return diff > 0 ? 'in < 1 min' : '< 1 min ago';
  if (absDiff < 3_600_000) {
    const m = Math.round(absDiff / 60_000);
    return diff > 0 ? `in ${m} min` : `${m} min ago`;
  }
  if (absDiff < 86_400_000) {
    const h = Math.round(absDiff / 3_600_000);
    return diff > 0 ? `in ${h}h` : `${h}h ago`;
  }
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function formatTimestamp(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleString(undefined, {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  });
}

function convertToMinutes(value: number, unit: IntervalUnit): number {
  switch (unit) {
    case 'hours': return value * 60;
    case 'days': return value * 1440;
    default: return value;
  }
}

// ─── Sub-Components ──────────────────────────────────────────────────────────

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const config: Record<string, { bg: string; text: string; dot: string; pulse?: boolean }> = {
    active:    { bg: 'bg-emerald-500/10', text: 'text-emerald-400', dot: 'bg-emerald-400' },
    paused:    { bg: 'bg-amber-500/10',   text: 'text-amber-400',  dot: 'bg-amber-400' },
    running:   { bg: 'bg-blue-500/10',    text: 'text-blue-400',   dot: 'bg-blue-400', pulse: true },
    completed: { bg: 'bg-zinc-500/10',    text: 'text-zinc-400',   dot: 'bg-zinc-400' },
  };
  const c = config[status] || config.completed;
  return (
    <span className={cn('inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono uppercase tracking-wider', c.bg, c.text)}>
      <span className={cn('w-1.5 h-1.5 rounded-full', c.dot, c.pulse && 'animate-pulse')} />
      {status}
    </span>
  );
};

const HistoryStatusIcon: React.FC<{ status: string }> = ({ status }) => {
  if (status === 'success') return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />;
  if (status === 'error' || status === 'failed') return <XCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />;
  return <AlertCircle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />;
};

// ─── Task Card ───────────────────────────────────────────────────────────────

interface TaskCardProps {
  task: ScheduledTask;
  onToggle: (id: string) => void;
  onRunNow: (id: string) => void;
  onDelete: (id: string) => void;
  isToggling: boolean;
  isRunning: boolean;
}

const TaskCard: React.FC<TaskCardProps> = ({ task, onToggle, onRunNow, onDelete, isToggling, isRunning }) => {
  const [expanded, setExpanded] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  return (
    <div className="group carbon-card animate-in fade-in slide-in-from-bottom-2 duration-500">
      {/* Top accent bar */}
      <div className={cn(
        'h-[2px] -mt-6 -mx-6 mb-5 transition-colors duration-300',
        task.status === 'active' && 'bg-emerald-500',
        task.status === 'paused' && 'bg-amber-500',
        task.status === 'running' && 'bg-blue-500',
        task.status === 'completed' && 'bg-zinc-600',
      )} />

      {/* Header row */}
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-1.5">
            <h3 className="text-lg font-medium text-foreground truncate">{task.name}</h3>
            <StatusBadge status={task.status} />
          </div>
          <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">{task.prompt}</p>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={() => onToggle(task.id)}
            disabled={isToggling || task.status === 'completed'}
            className={cn(
              'p-2 transition-all duration-200 hover:bg-muted disabled:opacity-30 disabled:cursor-not-allowed',
              task.status === 'active' ? 'text-amber-400 hover:text-amber-300' : 'text-emerald-400 hover:text-emerald-300'
            )}
            title={task.status === 'active' ? 'Pause task' : 'Resume task'}
          >
            {isToggling
              ? <RefreshCw className="w-4 h-4 animate-spin" />
              : task.status === 'active' || task.status === 'running'
                ? <Pause className="w-4 h-4" />
                : <Play className="w-4 h-4" />
            }
          </button>
          <button
            onClick={() => onRunNow(task.id)}
            disabled={isRunning || task.status === 'running'}
            className="p-2 text-blue-400 hover:text-blue-300 transition-all duration-200 hover:bg-muted disabled:opacity-30 disabled:cursor-not-allowed"
            title="Run now"
          >
            {isRunning
              ? <RefreshCw className="w-4 h-4 animate-spin" />
              : <Zap className="w-4 h-4" />
            }
          </button>
          {!confirmDelete ? (
            <button
              onClick={() => setConfirmDelete(true)}
              className="p-2 text-muted-foreground hover:text-red-400 transition-all duration-200 hover:bg-muted"
              title="Delete task"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          ) : (
            <div className="flex items-center gap-1 animate-in fade-in duration-200">
              <button
                onClick={() => onDelete(task.id)}
                className="px-2 py-1 text-xs font-mono bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
              >
                CONFIRM
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="px-2 py-1 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors"
              >
                CANCEL
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Meta row */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs font-mono text-muted-foreground mb-3">
        <span className="flex items-center gap-1.5">
          <RotateCcw className="w-3 h-3" />
          {formatInterval(task.interval_minutes)}
        </span>
        <span className="flex items-center gap-1.5">
          <Clock className="w-3 h-3" />
          Next: {formatRelativeTime(task.run_at)}
        </span>
        {task.last_run && (
          <span className="flex items-center gap-1.5">
            <Timer className="w-3 h-3" />
            Last: {formatRelativeTime(task.last_run)}
          </span>
        )}
      </div>

      {/* History toggle */}
      {task.history && task.history.length > 0 && (
        <>
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-wider text-ibm-blue hover:text-blue-400 transition-colors mt-2"
          >
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            Run History ({task.history.length})
          </button>

          {expanded && (
            <div className="mt-3 border-t border-border pt-4 animate-in fade-in slide-in-from-top-2 duration-300">
              <div className="max-h-72 overflow-y-auto space-y-3 pr-1 scrollbar-thin">
                {task.history.map((entry, idx) => (
                  <div
                    key={idx}
                    className="flex flex-col gap-2 py-3 px-4 bg-muted/20 border border-border/30 hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex items-center justify-between text-xs font-mono">
                      <div className="flex items-center gap-2">
                        <HistoryStatusIcon status={entry.status} />
                        <span className={cn(
                          "uppercase tracking-wider font-semibold",
                          entry.status === 'success' ? 'text-emerald-400' : 'text-red-400'
                        )}>
                          {entry.status}
                        </span>
                      </div>
                      <span className="text-muted-foreground">
                        {formatTimestamp(entry.timestamp)}
                      </span>
                    </div>
                    <div className="text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed break-words font-mono bg-black/40 p-3 border border-border/20 mt-1 select-text">
                      {entry.summary || <span className="text-muted-foreground/50 italic">No output details</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

// ─── Create Task Form ────────────────────────────────────────────────────────

interface CreateFormProps {
  onCreated: () => void;
}

const CreateTaskForm: React.FC<CreateFormProps> = ({ onCreated }) => {
  const [name, setName] = useState('');
  const [prompt, setPrompt] = useState('');
  const [taskType, setTaskType] = useState<TaskType>('recurring');
  const [intervalValue, setIntervalValue] = useState(20);
  const [intervalUnit, setIntervalUnit] = useState<IntervalUnit>('minutes');
  const [delay, setDelay] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!name.trim() || !prompt.trim()) {
      setError('Name and prompt are required.');
      return;
    }
    setIsSubmitting(true);
    setError('');
    try {
      await OllamaService.createScheduledTask({
        name: name.trim(),
        prompt: prompt.trim(),
        interval_minutes: taskType === 'recurring' ? convertToMinutes(intervalValue, intervalUnit) : null,
        delay_minutes: delay,
      });
      setName('');
      setPrompt('');
      setIntervalValue(20);
      setIntervalUnit('minutes');
      setDelay(0);
      onCreated();
    } catch (err) {
      setError('Failed to create task. Check the backend connection.');
    }
    setIsSubmitting(false);
  };

  return (
    <Card className="border-t-4 border-ibm-blue shadow-lg">
      <CardHeader className="pb-6">
        <CardTitle className="flex items-center gap-3 text-2xl font-light">
          <Plus className="w-6 h-6 text-ibm-blue" />
          Schedule New Task
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Name */}
        <div className="space-y-2">
          <label className="text-xs font-mono uppercase tracking-wider text-muted-foreground">Task Name</label>
          <input
            className="w-full p-4 bg-background border border-border focus:border-ibm-blue text-foreground outline-none transition-colors placeholder:text-muted-foreground/40 font-sans"
            placeholder="e.g. Health Check Monitor"
            value={name}
            onChange={e => setName(e.target.value)}
          />
        </div>

        {/* Prompt */}
        <div className="space-y-2">
          <label className="text-xs font-mono uppercase tracking-wider text-muted-foreground">Agent Prompt</label>
          <textarea
            className="w-full p-4 bg-background border border-border focus:border-ibm-blue text-foreground outline-none transition-colors placeholder:text-muted-foreground/40 min-h-[120px] resize-y font-sans"
            placeholder="e.g. Scan the project for broken dependencies and report any issues..."
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
          />
        </div>

        {/* Task Type Selector */}
        <div className="space-y-2">
          <label className="text-xs font-mono uppercase tracking-wider text-muted-foreground">Task Type</label>
          <div className="flex gap-0">
            {(['one-time', 'recurring'] as TaskType[]).map(t => (
              <button
                key={t}
                onClick={() => setTaskType(t)}
                className={cn(
                  'flex-1 py-3 px-4 text-sm font-mono uppercase tracking-wider border transition-all duration-200',
                  taskType === t
                    ? 'bg-ibm-blue text-white border-ibm-blue'
                    : 'bg-background text-muted-foreground border-border hover:border-ibm-blue/50 hover:text-foreground'
                )}
              >
                {t === 'one-time' ? 'One-time' : 'Recurring'}
              </button>
            ))}
          </div>
        </div>

        {/* Interval (recurring only) */}
        {taskType === 'recurring' && (
          <div className="space-y-2 animate-in fade-in slide-in-from-top-2 duration-300">
            <label className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
              Repeat Interval
            </label>
            <div className="flex gap-0">
              <input
                type="number"
                min={1}
                className="w-24 p-4 bg-background border border-border border-r-0 focus:border-ibm-blue text-foreground outline-none transition-colors font-mono text-center"
                value={intervalValue}
                onChange={e => setIntervalValue(Math.max(1, Number(e.target.value)))}
              />
              {(['minutes', 'hours', 'days'] as IntervalUnit[]).map(u => (
                <button
                  key={u}
                  onClick={() => setIntervalUnit(u)}
                  className={cn(
                    'px-4 py-3 text-xs font-mono uppercase tracking-wider border border-l-0 transition-all duration-200',
                    intervalUnit === u
                      ? 'bg-ibm-blue/20 text-ibm-blue border-ibm-blue'
                      : 'bg-background text-muted-foreground border-border hover:text-foreground'
                  )}
                >
                  {u}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Delay */}
        <div className="space-y-2">
          <label className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
            Initial Delay (minutes from now)
          </label>
          <input
            type="number"
            min={0}
            className="w-full p-4 bg-background border border-border focus:border-ibm-blue text-foreground outline-none transition-colors font-mono"
            value={delay}
            onChange={e => setDelay(Math.max(0, Number(e.target.value)))}
            placeholder="0"
          />
          <p className="text-xs text-muted-foreground/60">
            Set to 0 to start immediately. Otherwise the task will first run after the specified delay.
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 text-sm text-red-400 font-mono animate-in fade-in duration-200">
            <XCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Submit */}
        <Button
          variant="carbon"
          className="w-full h-auto py-4 text-base font-mono uppercase tracking-wider"
          onClick={handleSubmit}
          disabled={isSubmitting || !name.trim() || !prompt.trim()}
        >
          {isSubmitting ? (
            <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Timer className="w-4 h-4 mr-2" />
          )}
          {isSubmitting ? 'Creating...' : 'Schedule Task'}
        </Button>
      </CardContent>
    </Card>
  );
};

// ─── Main Component ──────────────────────────────────────────────────────────

export const ScheduledTasks: React.FC = () => {
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [togglingIds, setTogglingIds] = useState<Set<string>>(new Set());
  const [runningIds, setRunningIds] = useState<Set<string>>(new Set());
  const [showCreate, setShowCreate] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchTasks = useCallback(async () => {
    try {
      const data = await OllamaService.getScheduledTasks();
      setTasks(data.tasks || []);
    } catch (err) {
      console.error('Failed to fetch scheduled tasks', err);
    }
    setLoading(false);
    setLastRefresh(new Date());
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(fetchTasks, 30_000);
    return () => clearInterval(interval);
  }, [fetchTasks]);

  const handleToggle = async (taskId: string) => {
    setTogglingIds(prev => new Set(prev).add(taskId));
    try {
      await OllamaService.toggleScheduledTask(taskId);
      await fetchTasks();
    } catch (err) {
      console.error('Failed to toggle task', err);
    }
    setTogglingIds(prev => {
      const next = new Set(prev);
      next.delete(taskId);
      return next;
    });
  };

  const handleRunNow = async (taskId: string) => {
    setRunningIds(prev => new Set(prev).add(taskId));
    try {
      await OllamaService.runScheduledTaskNow(taskId);
      await fetchTasks();
    } catch (err) {
      console.error('Failed to run task', err);
    }
    setRunningIds(prev => {
      const next = new Set(prev);
      next.delete(taskId);
      return next;
    });
  };

  const handleDelete = async (taskId: string) => {
    try {
      await OllamaService.deleteScheduledTask(taskId);
      await fetchTasks();
    } catch (err) {
      console.error('Failed to delete task', err);
    }
  };

  const activeTasks = tasks.filter(t => t.status === 'active' || t.status === 'running');
  const pausedTasks = tasks.filter(t => t.status === 'paused');
  const completedTasks = tasks.filter(t => t.status === 'completed');

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-6 text-xs font-mono uppercase tracking-wider text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              {activeTasks.length} Active
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              {pausedTasks.length} Paused
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-zinc-500" />
              {completedTasks.length} Done
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-mono text-muted-foreground/50 uppercase tracking-wider">
            Refreshed {lastRefresh.toLocaleTimeString()}
          </span>
          <button
            onClick={fetchTasks}
            className="p-2 text-muted-foreground hover:text-ibm-blue transition-colors"
            title="Refresh now"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <Button
            variant="carbon"
            size="sm"
            onClick={() => setShowCreate(!showCreate)}
            className="font-mono uppercase tracking-wider"
          >
            {showCreate ? (
              <>
                <ChevronUp className="w-3.5 h-3.5 mr-1.5" />
                Hide Form
              </>
            ) : (
              <>
                <Plus className="w-3.5 h-3.5 mr-1.5" />
                New Task
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="animate-in fade-in slide-in-from-top-4 duration-500">
          <CreateTaskForm
            onCreated={() => {
              fetchTasks();
              setShowCreate(false);
            }}
          />
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-24 gap-4 animate-in fade-in duration-500">
          <RefreshCw className="w-8 h-8 text-ibm-blue animate-spin" />
          <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
            Loading scheduled tasks...
          </span>
        </div>
      )}

      {/* Empty state */}
      {!loading && tasks.length === 0 && (
        <Card className="border-dashed border-2">
          <CardContent className="flex flex-col items-center justify-center py-20 gap-5">
            <div className="p-4 bg-muted/30 rounded-full">
              <Timer className="w-10 h-10 text-muted-foreground/40" />
            </div>
            <div className="text-center space-y-2">
              <p className="text-lg text-muted-foreground">No scheduled tasks yet</p>
              <p className="text-sm text-muted-foreground/60">
                Create a recurring loop or one-time task to automate your agent workflows.
              </p>
            </div>
            <Button
              variant="carbon"
              size="sm"
              onClick={() => setShowCreate(true)}
              className="font-mono uppercase tracking-wider mt-2"
            >
              <Plus className="w-3.5 h-3.5 mr-1.5" />
              Create First Task
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Active / Running Tasks */}
      {activeTasks.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-xs font-mono uppercase tracking-widest text-emerald-400 flex items-center gap-2">
            <span className="w-6 h-[1px] bg-emerald-400/40" />
            Active Tasks
            <span className="w-6 h-[1px] bg-emerald-400/40" />
          </h2>
          <div className="grid grid-cols-1 gap-4">
            {activeTasks.map(task => (
              <TaskCard
                key={task.id}
                task={task}
                onToggle={handleToggle}
                onRunNow={handleRunNow}
                onDelete={handleDelete}
                isToggling={togglingIds.has(task.id)}
                isRunning={runningIds.has(task.id)}
              />
            ))}
          </div>
        </section>
      )}

      {/* Paused Tasks */}
      {pausedTasks.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-xs font-mono uppercase tracking-widest text-amber-400 flex items-center gap-2">
            <span className="w-6 h-[1px] bg-amber-400/40" />
            Paused
            <span className="w-6 h-[1px] bg-amber-400/40" />
          </h2>
          <div className="grid grid-cols-1 gap-4">
            {pausedTasks.map(task => (
              <TaskCard
                key={task.id}
                task={task}
                onToggle={handleToggle}
                onRunNow={handleRunNow}
                onDelete={handleDelete}
                isToggling={togglingIds.has(task.id)}
                isRunning={runningIds.has(task.id)}
              />
            ))}
          </div>
        </section>
      )}

      {/* Completed Tasks */}
      {completedTasks.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-xs font-mono uppercase tracking-widest text-zinc-500 flex items-center gap-2">
            <span className="w-6 h-[1px] bg-zinc-500/40" />
            Completed
            <span className="w-6 h-[1px] bg-zinc-500/40" />
          </h2>
          <div className="grid grid-cols-1 gap-4 opacity-70">
            {completedTasks.map(task => (
              <TaskCard
                key={task.id}
                task={task}
                onToggle={handleToggle}
                onRunNow={handleRunNow}
                onDelete={handleDelete}
                isToggling={togglingIds.has(task.id)}
                isRunning={runningIds.has(task.id)}
              />
            ))}
          </div>
        </section>
      )}

      {/* Auto-refresh indicator */}
      <div className="flex justify-center pt-4 pb-2">
        <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground/30 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-ibm-blue/30 animate-pulse" />
          Auto-refreshing every 30s
        </span>
      </div>
    </div>
  );
};
