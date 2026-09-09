import React, { useState, useEffect } from 'react';
import { multiAgentService } from '../services/ollama';

interface PersonalMemory {
  id: number;
  title: string;
  content: string;
  category: string;
  tags?: string[];
  created_at?: string;
}

interface PersonalJournalModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PersonalJournalModal: React.FC<PersonalJournalModalProps> = ({ isOpen, onClose }) => {
  const [memories, setMemories] = useState<PersonalMemory[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [newContent, setNewContent] = useState<string>('');
  const [newCategory, setNewCategory] = useState<string>('preference');
  const [newTitle, setNewTitle] = useState<string>('');
  const [isAdding, setIsAdding] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string>('');

  useEffect(() => {
    if (isOpen) {
      loadMemories();
    }
  }, [isOpen, filterCategory]);

  const loadMemories = async () => {
    setLoading(true);
    try {
      const cat = filterCategory === 'all' ? undefined : filterCategory;
      const res = await multiAgentService.listPersonalMemories(cat);
      if (res.status === 'success') {
        setMemories(res.memories || []);
      }
    } catch (e: any) {
      console.error('Failed to load memories:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleAddMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;

    try {
      setStatusMessage('Saving to journal...');
      const res = await multiAgentService.addPersonalMemory(
        newContent.trim(),
        newCategory,
        newTitle.trim()
      );
      if (res.status === 'success') {
        setStatusMessage('✓ Saved to Knowledge Journal!');
        setNewContent('');
        setNewTitle('');
        setIsAdding(false);
        loadMemories();
        setTimeout(() => setStatusMessage(''), 3000);
      }
    } catch (err: any) {
      setStatusMessage('Failed to save memory.');
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Forget this memory from your personal journal?')) return;
    try {
      await multiAgentService.deletePersonalMemory(id);
      setMemories(prev => prev.filter(m => m.id !== id));
    } catch (e) {
      console.error('Failed to delete memory:', e);
    }
  };

  if (!isOpen) return null;

  const filteredMemories = memories.filter(m => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return m.content.toLowerCase().includes(q) || (m.title && m.title.toLowerCase().includes(q));
  });

  const getCategoryBadge = (cat: string) => {
    switch (cat) {
      case 'preference':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-900/50 text-purple-200 border border-purple-500/40">⚙️ Preference</span>;
      case 'personal_fact':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-900/50 text-emerald-200 border border-emerald-500/40">🧠 Personal Fact</span>;
      case 'project_note':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-900/50 text-blue-200 border border-blue-500/40">📌 Project Note</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-600">💡 Context</span>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
      <div className="relative w-full max-w-2xl max-h-[90vh] flex flex-col bg-slate-900 border-2 border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden text-slate-100">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center text-xl shadow-lg shadow-purple-500/20">
              🧠
            </div>
            <div>
              <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                Personal Knowledge Journal
              </h2>
              <p className="text-xs text-slate-400">
                Facts & preferences automatically recalled by all specialized agents
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Toolbar & Search */}
        <div className="p-5 border-b border-slate-800 space-y-4 bg-slate-950/40">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <input
                type="text"
                placeholder="Search remembered facts & preferences..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-slate-800/80 border border-slate-700 rounded-xl text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
              <span className="absolute left-3 top-2.5 text-slate-400 text-sm">🔍</span>
            </div>
            <button
              onClick={() => setIsAdding(!isAdding)}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white text-sm font-semibold rounded-xl shadow-md transition-colors flex items-center gap-1.5 whitespace-nowrap"
            >
              {isAdding ? 'Cancel' : '+ Add Note'}
            </button>
          </div>

          {/* Category Filter Chips */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {[
              { id: 'all', label: 'All Items' },
              { id: 'preference', label: '⚙️ Preferences' },
              { id: 'personal_fact', label: '🧠 Facts' },
              { id: 'project_note', label: '📌 Project Notes' },
            ].map(cat => (
              <button
                key={cat.id}
                onClick={() => setFilterCategory(cat.id)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                  filterCategory === cat.id
                    ? 'bg-purple-600/30 border border-purple-500 text-purple-200'
                    : 'bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:text-slate-200'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {statusMessage && (
            <div className="text-xs text-emerald-400 font-semibold animate-pulse">
              {statusMessage}
            </div>
          )}

          {/* Add New Memory Form */}
          {isAdding && (
            <form onSubmit={handleAddMemory} className="p-4 bg-slate-800/80 border border-slate-700 rounded-xl space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="text"
                  placeholder="Short Title (optional)"
                  value={newTitle}
                  onChange={e => setNewTitle(e.target.value)}
                  className="px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none"
                />
                <select
                  value={newCategory}
                  onChange={e => setNewCategory(e.target.value)}
                  className="px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white focus:outline-none"
                >
                  <option value="preference">⚙️ User Preference</option>
                  <option value="personal_fact">🧠 Personal Fact</option>
                  <option value="project_note">📌 Project Note</option>
                </select>
              </div>
              <textarea
                placeholder="What should the agent remember? (e.g. 'I prefer high contrast dark mode' or 'My doctor appointment is Tuesdays')"
                value={newContent}
                onChange={e => setNewContent(e.target.value)}
                rows={3}
                className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
                required
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsAdding(false)}
                  className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-xs text-slate-200 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-purple-600 hover:bg-purple-500 text-xs font-semibold text-white rounded-lg shadow"
                >
                  Save to Journal
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Memory Items List */}
        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          {loading ? (
            <div className="text-center py-10 text-slate-400 text-sm animate-pulse">
              Loading Knowledge Journal...
            </div>
          ) : filteredMemories.length === 0 ? (
            <div className="text-center py-12 space-y-2">
              <div className="text-4xl">📖</div>
              <h3 className="text-base font-semibold text-slate-300">Your Knowledge Journal is Empty</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Tell the agent in chat (e.g. <span className="text-purple-300">"Remember that I like Python"</span>) or click <span className="text-purple-300 font-semibold">+ Add Note</span> above to save persistent memories.
              </p>
            </div>
          ) : (
            filteredMemories.map(mem => (
              <div
                key={mem.id}
                className="p-4 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 rounded-xl transition-all space-y-2 group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {getCategoryBadge(mem.category)}
                    {mem.title && (
                      <span className="font-semibold text-sm text-slate-100">{mem.title}</span>
                    )}
                  </div>
                  <button
                    onClick={() => handleDelete(mem.id)}
                    className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-rose-400 text-xs transition-opacity p-1"
                    title="Delete memory"
                  >
                    🗑️ Forget
                  </button>
                </div>
                <p className="text-sm text-slate-200 leading-relaxed pl-1 border-l-2 border-purple-500/50">
                  {mem.content}
                </p>
              </div>
            ))
          )}
        </div>

        {/* Footer info note */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between text-xs text-slate-400">
          <span>🔒 100% Local Storage (SQLite + Ollama Embeddings)</span>
          <span>{filteredMemories.length} item{filteredMemories.length === 1 ? '' : 's'} in memory</span>
        </div>
      </div>
    </div>
  );
};
