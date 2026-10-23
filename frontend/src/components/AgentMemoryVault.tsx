import React, { useState, useEffect } from 'react';
import { multiAgentService } from '../services/ollama';
import {
  Brain,
  Search,
  Plus,
  RefreshCw,
  Sparkles,
  Bot,
  Wrench,
  User,
  Trash2,
  Edit3,
  Copy,
  Check,
  Tag,
  Calendar,
  Layers,
  ArrowRight,
  CheckCircle2,
  X
} from 'lucide-react';
import { cn } from '../lib/utils';

export interface MemoryItem {
  id: number;
  title: string;
  content: string;
  category: string;
  tags?: string[];
  created_at?: string;
  updated_at?: string;
}

interface AgentMemoryVaultProps {
  onOpenHub?: () => void;
}

export const AgentMemoryVault: React.FC<AgentMemoryVaultProps> = ({ onOpenHub }) => {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'newest' | 'oldest' | 'title'>('newest');

  // Add Memory Modal State
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false);
  const [newTitle, setNewTitle] = useState<string>('');
  const [newContent, setNewContent] = useState<string>('');
  const [newCategory, setNewCategory] = useState<string>('preference');
  const [newTags, setNewTags] = useState<string>('');
  const [savingNew, setSavingNew] = useState<boolean>(false);

  // Edit Memory State
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState<string>('');
  const [editContent, setEditContent] = useState<string>('');
  const [editCategory, setEditCategory] = useState<string>('preference');
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  // Copied State
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>('');

  // Semantic Recall Tester State
  const [recallQuery, setRecallQuery] = useState<string>('');
  const [recallResults, setRecallResults] = useState<any[] | null>(null);
  const [testingRecall, setTestingRecall] = useState<boolean>(false);

  useEffect(() => {
    loadMemories();
  }, []);

  const loadMemories = async () => {
    setLoading(true);
    try {
      const res = await multiAgentService.listPersonalMemories();
      if (res.status === 'success' && Array.isArray(res.memories)) {
        setMemories(res.memories);
      }
    } catch (err) {
      console.error('Failed to load memories:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;

    setSavingNew(true);
    try {
      const tagsList = newTags
        .split(',')
        .map(t => t.trim())
        .filter(Boolean);
      tagsList.push('user_manual');

      const res = await multiAgentService.addPersonalMemory(
        newContent.trim(),
        newCategory,
        newTitle.trim(),
        tagsList
      );

      if (res.status === 'success') {
        setStatusMessage('✓ Memory saved to vault');
        setNewTitle('');
        setNewContent('');
        setNewCategory('preference');
        setNewTags('');
        setIsAddModalOpen(false);
        await loadMemories();
        setTimeout(() => setStatusMessage(''), 3000);
      }
    } catch (err) {
      console.error('Failed to add memory:', err);
      setStatusMessage('Error adding memory');
    } finally {
      setSavingNew(false);
    }
  };

  const handleStartEdit = (item: MemoryItem) => {
    setEditingId(item.id);
    setEditTitle(item.title || '');
    setEditContent(item.content);
    setEditCategory(item.category || 'preference');
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditTitle('');
    setEditContent('');
  };

  const handleSaveEdit = async (id: number) => {
    if (!editContent.trim()) return;
    setUpdatingId(id);
    try {
      const res = await multiAgentService.updatePersonalMemory(id, {
        title: editTitle.trim(),
        content: editContent.trim(),
        category: editCategory
      });
      if (res.status === 'success') {
        setEditingId(null);
        setStatusMessage('✓ Memory updated');
        await loadMemories();
        setTimeout(() => setStatusMessage(''), 3000);
      }
    } catch (err) {
      console.error('Failed to update memory:', err);
    } finally {
      setUpdatingId(null);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Forget this memory from the agent memory vault?')) return;
    try {
      await multiAgentService.deletePersonalMemory(id);
      setMemories(prev => prev.filter(m => m.id !== id));
      setStatusMessage('✓ Memory deleted');
      setTimeout(() => setStatusMessage(''), 3000);
    } catch (err) {
      console.error('Failed to delete memory:', err);
    }
  };

  const handleCopy = (id: number, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleTestRecall = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!recallQuery.trim()) return;

    setTestingRecall(true);
    try {
      const res = await multiAgentService.searchPersonalMemories(recallQuery.trim(), 4);
      setRecallResults(res.memories || res.results || []);
    } catch (err) {
      console.error('Recall test error:', err);
      setRecallResults([]);
    } finally {
      setTestingRecall(false);
    }
  };

  // Determine memory source
  const getMemorySource = (tags?: string[]) => {
    if (!tags || tags.length === 0) return { label: 'Manual Entry', type: 'user', icon: User };
    if (tags.includes('agent_auto_extracted')) {
      return { label: 'Agent Auto-Extracted', type: 'agent_auto', icon: Bot };
    }
    if (tags.includes('agent_tool')) {
      return { label: 'Saved via Agent Tool', type: 'agent_tool', icon: Wrench };
    }
    return { label: 'User Created', type: 'user', icon: User };
  };

  // Filter & Sort
  const filteredMemories = memories.filter(item => {
    // Category or Source filter
    if (activeFilter === 'agent_saved') {
      const isAgent = item.tags?.includes('agent_auto_extracted') || item.tags?.includes('agent_tool');
      if (!isAgent) return false;
    } else if (activeFilter === 'user_manual') {
      const isAgent = item.tags?.includes('agent_auto_extracted') || item.tags?.includes('agent_tool');
      if (isAgent) return false;
    } else if (activeFilter !== 'all') {
      if (item.category !== activeFilter) return false;
    }

    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = (item.title || '').toLowerCase().includes(q);
      const matchContent = item.content.toLowerCase().includes(q);
      const matchCategory = item.category.toLowerCase().includes(q);
      const matchTags = item.tags?.some(t => t.toLowerCase().includes(q));
      return matchTitle || matchContent || matchCategory || matchTags;
    }

    return true;
  }).sort((a, b) => {
    if (sortBy === 'newest') {
      return (b.created_at || '').localeCompare(a.created_at || '');
    }
    if (sortBy === 'oldest') {
      return (a.created_at || '').localeCompare(b.created_at || '');
    }
    if (sortBy === 'title') {
      return (a.title || a.content).localeCompare(b.title || b.content);
    }
    return 0;
  });

  // Calculate statistics
  const totalCount = memories.length;
  const agentSavedCount = memories.filter(
    m => m.tags?.includes('agent_auto_extracted') || m.tags?.includes('agent_tool')
  ).length;
  const preferencesCount = memories.filter(m => m.category === 'preference').length;
  const projectNotesCount = memories.filter(m => m.category === 'project_note').length;
  const factsCount = memories.filter(m => m.category === 'personal_fact').length;

  const formatTimestamp = (dateStr?: string) => {
    if (!dateStr) return '';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="flex-1 min-h-screen bg-background text-foreground flex flex-col overflow-y-auto">
      {/* Top Banner & Header */}
      <div className="border-b border-border/80 bg-card/60 backdrop-blur-xl px-6 py-6 sticky top-0 z-30 shadow-sm">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-blue-500 flex items-center justify-center shadow-lg shadow-purple-500/25 shrink-0 border border-white/10 text-white">
              <Brain className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-2xl font-bold tracking-tight text-foreground">
                  Agent Memory Vault
                </h1>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/15 text-purple-400 border border-purple-500/30">
                  {totalCount} Memor{totalCount === 1 ? 'y' : 'ies'} Saved
                </span>
                {statusMessage && (
                  <span className="text-xs font-semibold text-emerald-400 animate-in fade-in flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> {statusMessage}
                  </span>
                )}
              </div>
              <p className="text-xs sm:text-sm text-muted-foreground mt-1 max-w-2xl">
                Persistent long-term knowledge, preferences, and project facts automatically remembered by your AI agents or recorded manually. All memories are recalled across all sessions.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            <button
              onClick={loadMemories}
              disabled={loading}
              className="p-2.5 rounded-xl border border-border/80 bg-secondary/40 hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
              title="Refresh memories from database"
            >
              <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
            </button>

            <button
              onClick={() => setIsAddModalOpen(true)}
              className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold text-xs sm:text-sm shadow-md shadow-purple-500/20 flex items-center gap-2 transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Add Memory</span>
            </button>

            {onOpenHub && (
              <button
                onClick={onOpenHub}
                className="px-4 py-2.5 rounded-xl border border-border/80 bg-secondary/60 hover:bg-secondary text-foreground font-semibold text-xs sm:text-sm flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <span>Open Agent Chat</span>
                <ArrowRight className="w-4 h-4 text-muted-foreground" />
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto w-full px-6 py-6 space-y-6 flex-1">
        {/* Memory Stats Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-2xl bg-card/80 border border-border/70 backdrop-blur-sm shadow-sm flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400">
              <Brain className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold tracking-tight text-foreground">{totalCount}</div>
              <div className="text-[11px] font-medium text-muted-foreground">Total Memories</div>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-card/80 border border-border/70 backdrop-blur-sm shadow-sm flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold tracking-tight text-foreground">{agentSavedCount}</div>
              <div className="text-[11px] font-medium text-muted-foreground">Saved by Agent</div>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-card/80 border border-border/70 backdrop-blur-sm shadow-sm flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold tracking-tight text-foreground">{preferencesCount}</div>
              <div className="text-[11px] font-medium text-muted-foreground">Preferences</div>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-card/80 border border-border/70 backdrop-blur-sm shadow-sm flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xl font-bold tracking-tight text-foreground">{projectNotesCount + factsCount}</div>
              <div className="text-[11px] font-medium text-muted-foreground">Project Notes & Facts</div>
            </div>
          </div>
        </div>

        {/* Live Semantic Recall Tester Box */}
        <div className="p-4 rounded-2xl bg-gradient-to-r from-purple-950/30 via-slate-900/60 to-indigo-950/30 border border-purple-500/30 shadow-md">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-purple-500/20 text-purple-300 flex items-center justify-center text-xs font-mono">
                🔍
              </div>
              <span className="text-xs font-bold uppercase tracking-wider text-purple-300">
                Agent Semantic Recall Inspector
              </span>
            </div>
            <span className="text-[11px] text-muted-foreground">
              Test how the agent recalls your memories for any question
            </span>
          </div>

          <form onSubmit={handleTestRecall} className="flex gap-2.5">
            <div className="relative flex-1">
              <input
                type="text"
                value={recallQuery}
                onChange={e => setRecallQuery(e.target.value)}
                placeholder="Ask what the agent knows (e.g. 'What framework do I use?' or 'What is my tech stack?')..."
                className="w-full px-3.5 py-2 rounded-xl bg-background/80 border border-border text-xs sm:text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <button
              type="submit"
              disabled={testingRecall || !recallQuery.trim()}
              className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-semibold text-xs sm:text-sm transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5 shadow"
            >
              {testingRecall ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Searching...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Test Recall</span>
                </>
              )}
            </button>
          </form>

          {recallResults !== null && (
            <div className="mt-3 pt-3 border-t border-purple-500/20 space-y-2 animate-in fade-in">
              <div className="flex items-center justify-between text-xs text-purple-300">
                <span className="font-semibold">
                  {recallResults.length > 0
                    ? `Matched ${recallResults.length} relevant memor${recallResults.length === 1 ? 'y' : 'ies'} that will be injected into agent prompt:`
                    : 'No matching memories found for this query.'}
                </span>
                <button
                  onClick={() => setRecallResults(null)}
                  className="text-muted-foreground hover:text-foreground text-[10px]"
                >
                  Clear
                </button>
              </div>

              {recallResults.map((r, i) => (
                <div
                  key={i}
                  className="p-2.5 rounded-xl bg-slate-900/80 border border-purple-500/30 text-xs flex items-start justify-between gap-3"
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-purple-900/60 text-purple-200 border border-purple-500/40 uppercase">
                        {r.category || 'Preference'}
                      </span>
                      {r.title && <span className="font-semibold text-foreground">{r.title}</span>}
                    </div>
                    <p className="text-slate-200 italic font-sans pl-2 border-l-2 border-purple-500">
                      "{r.content}"
                    </p>
                  </div>
                  {r.score && (
                    <span className="text-[10px] font-mono text-purple-400 shrink-0">
                      Score: {(r.score * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Search, Filter & Controls */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Search Bar */}
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 absolute left-3.5 top-3 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search memories by keyword, title, tag..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-xl bg-card border border-border/80 text-xs sm:text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground text-xs"
              >
                ✕
              </button>
            )}
          </div>

          {/* Filter Chips */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
            {[
              { id: 'all', label: 'All', count: totalCount },
              { id: 'agent_saved', label: '🤖 Agent Saved', count: agentSavedCount },
              { id: 'preference', label: '⚙️ Preferences', count: preferencesCount },
              { id: 'personal_fact', label: '🧠 Facts', count: factsCount },
              { id: 'project_note', label: '📌 Notes', count: projectNotesCount },
              { id: 'user_manual', label: '👤 Added by Me', count: totalCount - agentSavedCount }
            ].map(f => (
              <button
                key={f.id}
                onClick={() => setActiveFilter(f.id)}
                className={cn(
                  "px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all cursor-pointer flex items-center gap-1.5",
                  activeFilter === f.id
                    ? "bg-purple-600 text-white shadow-sm shadow-purple-500/20"
                    : "bg-secondary/60 hover:bg-secondary text-muted-foreground hover:text-foreground border border-border/50"
                )}
              >
                <span>{f.label}</span>
                <span
                  className={cn(
                    "text-[10px] font-mono px-1.5 py-0.2 rounded-full",
                    activeFilter === f.id ? "bg-white/20 text-white" : "bg-muted text-muted-foreground"
                  )}
                >
                  {f.count}
                </span>
              </button>
            ))}
          </div>

          {/* Sort Selector */}
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-xs text-muted-foreground hidden sm:inline">Sort:</span>
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value as any)}
              className="px-3 py-1.5 rounded-xl bg-card border border-border/80 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
              <option value="title">Alphabetical</option>
            </select>
          </div>
        </div>

        {/* Memories Grid */}
        {loading ? (
          <div className="p-16 text-center text-muted-foreground text-sm flex flex-col items-center justify-center gap-3">
            <RefreshCw className="w-8 h-8 animate-spin text-purple-500" />
            <span>Loading agent memories...</span>
          </div>
        ) : filteredMemories.length === 0 ? (
          <div className="p-12 rounded-3xl border border-dashed border-border/80 bg-card/40 text-center max-w-lg mx-auto space-y-4 my-8">
            <div className="w-16 h-16 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-3xl mx-auto text-purple-400">
              🧠
            </div>
            <h3 className="text-lg font-bold text-foreground">
              {searchQuery ? 'No matching memories found' : 'No memories saved yet'}
            </h3>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              {searchQuery
                ? 'Try a different search term or clear the filter.'
                : 'Your agents can automatically remember information you share in chat! Tell them: "Remember that I prefer TypeScript and TailwindCSS", or click below to add a memory manually.'}
            </p>
            <div className="pt-2 flex items-center justify-center gap-3">
              {searchQuery ? (
                <button
                  onClick={() => setSearchQuery('')}
                  className="px-4 py-2 rounded-xl bg-secondary hover:bg-secondary/80 text-foreground text-xs font-semibold"
                >
                  Clear Search
                </button>
              ) : (
                <button
                  onClick={() => setIsAddModalOpen(true)}
                  className="px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-md flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add First Memory</span>
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredMemories.map(item => {
              const source = getMemorySource(item.tags);
              const SourceIcon = source.icon;
              const isEditing = editingId === item.id;

              return (
                <div
                  key={item.id}
                  className="p-5 rounded-2xl bg-card border border-border/80 hover:border-purple-500/40 transition-all shadow-sm hover:shadow-md flex flex-col justify-between group space-y-4 relative overflow-hidden"
                >
                  {/* Top Category & Source Tags */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {/* Category Badge */}
                        <span
                          className={cn(
                            "px-2.5 py-0.5 rounded-full text-[11px] font-semibold border",
                            item.category === 'preference' && "bg-purple-500/10 text-purple-400 border-purple-500/30",
                            item.category === 'personal_fact' && "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
                            item.category === 'project_note' && "bg-blue-500/10 text-blue-400 border-blue-500/30",
                            item.category !== 'preference' && item.category !== 'personal_fact' && item.category !== 'project_note' && "bg-slate-500/10 text-slate-300 border-slate-500/30"
                          )}
                        >
                          {item.category === 'preference' && '⚙️ Preference'}
                          {item.category === 'personal_fact' && '🧠 Fact'}
                          {item.category === 'project_note' && '📌 Project Note'}
                          {item.category !== 'preference' && item.category !== 'personal_fact' && item.category !== 'project_note' && item.category}
                        </span>

                        {/* Source Badge */}
                        <span
                          className={cn(
                            "px-2 py-0.5 rounded-full text-[10px] font-medium border flex items-center gap-1",
                            source.type === 'agent_auto' && "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
                            source.type === 'agent_tool' && "bg-indigo-500/10 text-indigo-300 border-indigo-500/30",
                            source.type === 'user' && "bg-secondary text-muted-foreground border-border/60"
                          )}
                        >
                          <SourceIcon className="w-3 h-3" />
                          <span>{source.label}</span>
                        </span>
                      </div>

                      {/* Card Action Buttons */}
                      <div className="flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => handleCopy(item.id, item.content)}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                          title="Copy memory content"
                        >
                          {copiedId === item.id ? (
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                        <button
                          onClick={() => handleStartEdit(item)}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-purple-400 hover:bg-secondary transition-colors"
                          title="Edit memory"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(item.id)}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-rose-400 hover:bg-secondary transition-colors"
                          title="Delete memory"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Content View / Edit Mode */}
                    {isEditing ? (
                      <div className="space-y-3 pt-1">
                        <input
                          type="text"
                          value={editTitle}
                          onChange={e => setEditTitle(e.target.value)}
                          placeholder="Title"
                          className="w-full px-3 py-1.5 rounded-lg bg-background border border-purple-500/50 text-xs font-semibold text-foreground focus:outline-none"
                        />
                        <select
                          value={editCategory}
                          onChange={e => setEditCategory(e.target.value)}
                          className="w-full px-3 py-1.5 rounded-lg bg-background border border-purple-500/50 text-xs text-foreground focus:outline-none"
                        >
                          <option value="preference">⚙️ User Preference</option>
                          <option value="personal_fact">🧠 Personal Fact</option>
                          <option value="project_note">📌 Project Note</option>
                        </select>
                        <textarea
                          value={editContent}
                          onChange={e => setEditContent(e.target.value)}
                          rows={3}
                          className="w-full p-2.5 rounded-lg bg-background border border-purple-500/50 text-xs text-foreground focus:outline-none resize-none"
                          required
                        />
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={handleCancelEdit}
                            className="px-3 py-1 rounded-lg bg-secondary text-xs text-muted-foreground hover:text-foreground"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleSaveEdit(item.id)}
                            disabled={updatingId === item.id}
                            className="px-3.5 py-1 rounded-lg bg-purple-600 hover:bg-purple-500 text-xs font-semibold text-white shadow flex items-center gap-1"
                          >
                            {updatingId === item.id && <RefreshCw className="w-3 h-3 animate-spin" />}
                            <span>Save</span>
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {item.title && (
                          <h4 className="text-sm font-bold text-foreground tracking-tight leading-snug">
                            {item.title}
                          </h4>
                        )}
                        <p className="text-xs sm:text-sm text-foreground/90 font-sans leading-relaxed pl-3 border-l-2 border-purple-500/60 break-words whitespace-pre-wrap">
                          {item.content}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Footer Timestamps and Tags */}
                  <div className="pt-3 border-t border-border/50 flex items-center justify-between text-[11px] text-muted-foreground">
                    <div className="flex items-center gap-1 font-mono">
                      <Calendar className="w-3 h-3 text-muted-foreground/60" />
                      <span>{formatTimestamp(item.created_at)}</span>
                    </div>

                    {item.tags && item.tags.length > 0 && (
                      <div className="flex items-center gap-1 text-[10px] text-purple-400 font-mono">
                        <Tag className="w-2.5 h-2.5" />
                        <span>{item.tags.filter(t => !['user_manual', 'agent_auto_extracted', 'agent_tool'].includes(t)).slice(0, 2).join(', ') || 'saved'}</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Add Memory Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="relative w-full max-w-lg bg-card border border-border/80 rounded-2xl shadow-2xl p-6 space-y-5 text-foreground">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-purple-600 flex items-center justify-center text-white">
                  <Brain className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-bold text-base">Add New Memory</h3>
                  <p className="text-xs text-muted-foreground">Teach your agents a permanent fact or preference</p>
                </div>
              </div>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleAddMemory} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-muted-foreground mb-1.5">
                  Category
                </label>
                <select
                  value={newCategory}
                  onChange={e => setNewCategory(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-background border border-border text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="preference">⚙️ User Preference (e.g. style, tools, formatting)</option>
                  <option value="personal_fact">🧠 Personal Fact (e.g. background, role, skills)</option>
                  <option value="project_note">📌 Project Note (e.g. tech stack, architecture, ports)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-muted-foreground mb-1.5">
                  Title (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Preferred Frontend Framework"
                  value={newTitle}
                  onChange={e => setNewTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-background border border-border text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-muted-foreground mb-1.5">
                  Content <span className="text-purple-400">*</span>
                </label>
                <textarea
                  placeholder="e.g. 'I prefer writing clean React code with TailwindCSS and TypeScript. Always include comments on non-trivial functions.'"
                  value={newContent}
                  onChange={e => setNewContent(e.target.value)}
                  rows={4}
                  className="w-full p-3 rounded-xl bg-background border border-border text-xs sm:text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-muted-foreground mb-1.5">
                  Tags (comma separated, optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. react, tailwind, coding-style"
                  value={newTags}
                  onChange={e => setNewTags(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-background border border-border text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div className="flex justify-end gap-2.5 pt-3 border-t border-border/60">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-secondary hover:bg-secondary/80 text-xs font-semibold text-foreground transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingNew || !newContent.trim()}
                  className="px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md transition-all flex items-center gap-1.5"
                >
                  {savingNew && <RefreshCw className="w-3 h-3 animate-spin" />}
                  <span>Save to Memory Vault</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
