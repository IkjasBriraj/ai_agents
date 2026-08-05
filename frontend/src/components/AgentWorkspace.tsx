import { useCallback, useEffect, useState } from 'react';
import { Brain, CheckCircle2, ClipboardList, FileText, Play, Plus, Save, ShieldCheck, Users } from 'lucide-react';
import { OllamaService } from '@/services/ollama';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

type Hub = { id: string; name: string; description?: string };
type Workspace = { mission: string; success_criteria: string[]; status: string };
type Task = { id: string; title: string; description: string; assigned_role: string; status: string; result?: string };
type Run = { id: string; task_id?: string; agent_role: string; status: string; plan: string[]; result?: string; error?: string };
type WorkspaceData = { hub: Hub; workspace: Workspace; tasks: Task[]; memories: { id: number; category: string; content: string }[]; artifacts: { id: string; name: string; kind: string; summary: string }[]; runs: Run[] };

const roles = ['lead', 'code', 'research', 'reviewer', 'qa', 'business'];

export function AgentWorkspace() {
  const [hubs, setHubs] = useState<Hub[]>([]);
  const [selectedHubId, setSelectedHubId] = useState('');
  const [workspace, setWorkspace] = useState<WorkspaceData | null>(null);
  const [mission, setMission] = useState('');
  const [criteria, setCriteria] = useState('');
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDescription, setTaskDescription] = useState('');
  const [taskRole, setTaskRole] = useState('code');
  const [memory, setMemory] = useState('');
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState('');

  const loadHubs = useCallback(async () => {
    const result = await OllamaService.getHubs();
    setHubs(result);
    setSelectedHubId(current => current || result[0]?.id || '');
  }, []);

  const loadWorkspace = useCallback(async (hubId: string) => {
    if (!hubId) { setWorkspace(null); return; }
    const result = await OllamaService.getHubWorkspace(hubId) as WorkspaceData;
    setWorkspace(result);
    setMission(result.workspace.mission);
    setCriteria(result.workspace.success_criteria.join('\n'));
  }, []);

  useEffect(() => { void loadHubs().finally(() => setLoading(false)); }, [loadHubs]);
  useEffect(() => { void loadWorkspace(selectedHubId); }, [selectedHubId, loadWorkspace]);

  const refresh = async () => { await loadHubs(); await loadWorkspace(selectedHubId); };
  const saveMission = async () => {
    if (!selectedHubId) return;
    await OllamaService.updateHubWorkspace(selectedHubId, { mission, success_criteria: criteria.split('\n').map(item => item.trim()).filter(Boolean), status: mission.trim() ? 'active' : 'draft' });
    setStatus('Team goal saved.');
    await loadWorkspace(selectedHubId);
  };
  const addTask = async () => {
    if (!selectedHubId || !taskTitle.trim()) return;
    await OllamaService.createHubTask(selectedHubId, { title: taskTitle, description: taskDescription, assigned_role: taskRole });
    setTaskTitle(''); setTaskDescription(''); setStatus('Task added to the team board.');
    await loadWorkspace(selectedHubId);
  };
  const addMemory = async () => {
    if (!selectedHubId || !memory.trim()) return;
    await OllamaService.addHubMemory(selectedHubId, { content: memory, category: 'decision' });
    setMemory(''); await loadWorkspace(selectedHubId);
  };
  const prepareRun = async (taskId: string) => { await OllamaService.prepareHubTaskRun(selectedHubId, taskId); setStatus('Plan ready for your approval.'); await loadWorkspace(selectedHubId); };
  const approveRun = async (runId: string) => { await OllamaService.approveHubRun(selectedHubId, runId); setStatus('Approved run queued. Refresh shortly to see progress.'); await loadWorkspace(selectedHubId); };
  const createHub = async () => { const name = window.prompt('Name this team'); if (!name?.trim()) return; await OllamaService.createHub({ id: crypto.randomUUID(), name: name.trim(), description: 'A goal-driven agent team' }); await loadHubs(); };

  if (loading) return <p className="py-12 text-center text-muted-foreground">Loading teams…</p>;

  return <div className="space-y-6 pb-16">
    <div className="flex flex-wrap items-center justify-between gap-3 border border-border bg-card p-4">
      <div className="flex items-center gap-3"><Users className="h-5 w-5 text-ibm-blue" /><div><p className="font-medium">Agent teams</p><p className="text-xs text-muted-foreground">Set a goal, delegate work, approve plans, and review evidence.</p></div></div>
      <div className="flex gap-2"><select value={selectedHubId} onChange={event => setSelectedHubId(event.target.value)} className="border border-border bg-background px-3 py-2 text-sm">{hubs.length === 0 && <option value="">No teams yet</option>}{hubs.map(hub => <option key={hub.id} value={hub.id}>{hub.name}</option>)}</select><Button variant="outline" onClick={createHub}><Plus className="mr-1 h-4 w-4" /> Team</Button><Button variant="outline" onClick={() => void refresh()}>Refresh</Button></div>
    </div>
    {status && <div role="status" className="border border-emerald-500/35 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-700 dark:text-emerald-300">{status}</div>}
    {!workspace ? <Card><CardContent className="py-12 text-center text-muted-foreground">Create a team to start a shared agent workspace.</CardContent></Card> : <>
      <Card><CardHeader><CardTitle className="flex items-center gap-2"><Brain className="h-5 w-5 text-ibm-blue" /> Team mission</CardTitle></CardHeader><CardContent className="space-y-3"><textarea value={mission} onChange={event => setMission(event.target.value)} placeholder="What outcome should this team deliver?" className="min-h-24 w-full border border-border bg-background p-3" /><textarea value={criteria} onChange={event => setCriteria(event.target.value)} placeholder="Success criteria — one per line" className="min-h-20 w-full border border-border bg-background p-3 text-sm" /><Button onClick={() => void saveMission()}><Save className="mr-2 h-4 w-4" /> Save goal</Button></CardContent></Card>
      <div className="grid gap-6 xl:grid-cols-3"><Card className="xl:col-span-2"><CardHeader><CardTitle className="flex items-center gap-2"><ClipboardList className="h-5 w-5 text-ibm-blue" /> Team task board</CardTitle></CardHeader><CardContent className="space-y-4"><div className="grid gap-2 md:grid-cols-[1fr_150px]"><input value={taskTitle} onChange={event => setTaskTitle(event.target.value)} placeholder="Task title" className="border border-border bg-background px-3 py-2" /><select value={taskRole} onChange={event => setTaskRole(event.target.value)} className="border border-border bg-background px-3 py-2">{roles.map(role => <option key={role}>{role}</option>)}</select></div><textarea value={taskDescription} onChange={event => setTaskDescription(event.target.value)} placeholder="Context, constraints, and expected output" className="min-h-20 w-full border border-border bg-background p-3 text-sm" /><Button variant="outline" onClick={() => void addTask()}><Plus className="mr-2 h-4 w-4" /> Delegate task</Button><div className="space-y-3">{workspace.tasks.map(task => <div key={task.id} className="border border-border bg-background p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-medium">{task.title}</p><p className="mt-1 text-sm text-muted-foreground">{task.description || 'No extra details'}</p><p className="mt-2 text-xs uppercase tracking-wide text-ibm-blue">{task.assigned_role} · {task.status.replace('_', ' ')}</p></div>{task.status === 'queued' && <Button size="sm" onClick={() => void prepareRun(task.id)}><Play className="mr-1 h-3.5 w-3.5" /> Plan run</Button>}</div>{task.result && <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap border-t border-border pt-3 text-xs text-muted-foreground">{task.result}</pre>}</div>)}{workspace.tasks.length === 0 && <p className="py-6 text-center text-sm text-muted-foreground">No tasks yet. Add a clear first step for the team.</p>}</div></CardContent></Card>
      <div className="space-y-6"><Card><CardHeader><CardTitle className="text-base">Shared team context</CardTitle></CardHeader><CardContent className="space-y-3"><textarea value={memory} onChange={event => setMemory(event.target.value)} placeholder="Decision, constraint, or project fact" className="min-h-20 w-full border border-border bg-background p-2 text-sm" /><Button size="sm" variant="outline" onClick={() => void addMemory()}>Save context</Button><div className="space-y-2">{workspace.memories.map(item => <div key={item.id} className="border-l-2 border-ibm-blue pl-3 text-sm"><p>{item.content}</p><p className="text-xs text-muted-foreground">{item.category}</p></div>)}</div></CardContent></Card><Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><ShieldCheck className="h-4 w-4 text-amber-500" /> Awaiting approval</CardTitle></CardHeader><CardContent className="space-y-3">{workspace.runs.filter(run => run.status === 'awaiting_approval').map(run => <div key={run.id} className="border border-amber-500/35 bg-amber-500/5 p-3"><p className="text-sm font-medium">{run.agent_role} plan</p><ol className="mt-2 list-decimal space-y-1 pl-5 text-xs text-muted-foreground">{run.plan.map(step => <li key={step}>{step}</li>)}</ol><Button size="sm" className="mt-3" onClick={() => void approveRun(run.id)}><CheckCircle2 className="mr-1 h-3.5 w-3.5" /> Approve & run</Button></div>)}{workspace.runs.filter(run => run.status === 'awaiting_approval').length === 0 && <p className="text-sm text-muted-foreground">No plans need approval.</p>}</CardContent></Card><Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><FileText className="h-4 w-4 text-ibm-blue" /> Artifacts</CardTitle></CardHeader><CardContent className="space-y-2">{workspace.artifacts.map(artifact => <div key={artifact.id} className="border border-border p-2 text-sm"><p className="font-medium">{artifact.name}</p><p className="line-clamp-3 text-xs text-muted-foreground">{artifact.summary}</p></div>)}{workspace.artifacts.length === 0 && <p className="text-sm text-muted-foreground">Completed task evidence appears here.</p>}</CardContent></Card></div></div>
    </>}
  </div>;
}
