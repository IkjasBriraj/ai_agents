import React, { useState, useEffect } from 'react';
import { Search, Play, Bot } from 'lucide-react';
import { LiquidGlassTestPanel } from './LiquidGlassTestPanel';
import { OllamaService, type Agent } from '@/services/ollama';
import { AgentTodoList, type TodoItem } from './AgentTodoList';

// Default App Agents metadata
const DEFAULT_APP_AGENTS = [
  {
    id: 'code',
    name: 'Senior Code Agent',
    category: 'default',
    persona: 'Executive Senior Full-Stack Engineer & Software Architect',
    description: 'Generates complete, production-grade applications, performs localized code patching without overwriting entire files, and runs browser/console auto-fix protocols.',
    tools: ['file_operation', 'patch_file_content', 'browser_open_url', 'browser_get_console_errors', 'verify_app_browser_console'],
    badgeColor: 'from-blue-500 to-indigo-600',
    system_prompt: 'You are an Expert Senior Code Agent. You build production-grade, highly polished applications with zero placeholders and zero errors. For localized fixes or updates, read the file first and use file_operation(patch)...'
  },
  {
    id: 'research',
    name: 'Senior Research Agent',
    category: 'default',
    persona: 'Lead Research Scientist & Technical Analyst',
    description: 'Gathers up-to-date web information, parses full articles, summarizes complex documentation, and delivers comprehensive research breakdowns with robust fallbacks.',
    tools: ['web_search', 'fetch_web_page', 'firecrawl', 'summarize_text'],
    badgeColor: 'from-purple-500 to-pink-600',
    system_prompt: 'You are a Research Agent specialized in information gathering, web scraping, article extraction, and structured synthesis...'
  },
  {
    id: 'analysis',
    name: 'Analysis & QA Agent',
    category: 'default',
    persona: 'Principal QA Engineer & Code Inspector',
    description: 'Diagnoses runtime errors, analyzes stack traces, performs Gemma4:26b vision UI audits, and provides exact actionable code remediation specs.',
    tools: ['browser_vision_audit', 'verify_app_browser_console', 'grep_search', 'recursive_list'],
    badgeColor: 'from-amber-500 to-orange-600',
    system_prompt: 'You are an Expert Analysis & QA Agent specialized in deep code diagnostics, real browser console verification, and UI visual inspection...'
  },
  {
    id: 'business',
    name: 'Business & Finance Agent',
    category: 'default',
    persona: 'Chief Strategy Officer & Financial Analyst',
    description: 'Creates executive presentation slide decks (.pptx / .html), models financial spreadsheets (.xlsx), and formulates strategic pitch presentations.',
    tools: ['generate_presentation', 'generate_excel_sheet', 'parse_business_csv'],
    badgeColor: 'from-emerald-500 to-teal-600',
    system_prompt: 'You are a Business & Financial Modeling Agent specialized in corporate decks, financial analysis, spreadsheets, and presentation generation...'
  },
  {
    id: 'orchestrator',
    name: 'LangGraph Orchestrator',
    category: 'default',
    persona: 'Multi-Agent Network Router & Task Manager',
    description: 'Routes complex tasks across specialized agents inside a LangGraph state network and schedules background loops.',
    tools: ['route_to_code_agent', 'route_to_research_agent', 'route_to_analysis_agent'],
    badgeColor: 'from-cyan-500 to-blue-600',
    system_prompt: 'You are the SeniorAgent Orchestrator. You analyze user tasks and delegate steps to Code, Research, and Analysis agents...'
  }
];

export const AgentInspector: React.FC = () => {
  const [userAgents, setUserAgents] = useState<Agent[]>([]);
  const [filterCategory, setFilterCategory] = useState<'all' | 'default' | 'custom'>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [testingAgent, setTestingAgent] = useState<any | null>(null);
  const [todoItems] = useState<TodoItem[]>([
    { id: '1', title: 'Inspect system agent capabilities & active tools', status: 'completed', details: '5 default app agents & custom agents loaded' },
    { id: '2', title: 'Prepare Apple-style Liquid Glass testing environment', status: 'completed', details: 'Model providers & thinking levels configured' },
    { id: '3', title: 'Monitor live subagent tasks & execution progress', status: 'in_progress', details: 'Awaiting interactive agent prompt test...' }
  ]);

  useEffect(() => {
    loadUserAgents();
  }, []);

  const loadUserAgents = async () => {
    try {
      const agents = await OllamaService.getAgents();
      setUserAgents(agents);
    } catch (err) {
      console.error('Failed to load user agents', err);
    }
  };

  // Combine default app agents and custom user agents
  const customAgentsFormatted = userAgents.map((ag) => ({
    id: ag.id,
    name: ag.name,
    category: 'custom',
    persona: ag.persona || 'Custom User Agent',
    description: ag.system_prompt ? ag.system_prompt.slice(0, 140) + '...' : 'Custom defined user agent.',
    tools: ag.tools || [],
    badgeColor: 'from-indigo-500 to-purple-600',
    system_prompt: ag.system_prompt || '',
  }));

  const allAgents = [...DEFAULT_APP_AGENTS, ...customAgentsFormatted];

  const filteredAgents = allAgents.filter((agent) => {
    if (filterCategory === 'default' && agent.category !== 'default') return false;
    if (filterCategory === 'custom' && agent.category !== 'custom') return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        agent.name.toLowerCase().includes(q) ||
        agent.id.toLowerCase().includes(q) ||
        agent.persona.toLowerCase().includes(q) ||
        agent.description.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900/90 via-slate-900/60 to-slate-950 p-6 rounded-3xl border border-white/10 shadow-2xl backdrop-blur-xl">
        <div>
          <div className="flex items-center gap-2 text-indigo-400 font-mono text-xs uppercase tracking-widest mb-1">
            <Bot className="w-4 h-4" />
            <span>Agentic Intelligence Directory</span>
          </div>
          <h2 className="text-3xl font-light text-white tracking-tight">Agent Inspector & Testing Studio</h2>
          <p className="text-sm text-slate-400 mt-1 max-w-xl">
            Explore default app agents and your custom personas. Click <strong className="text-slate-200 font-semibold">Test Agent</strong> to launch the Apple-style Liquid Glass testing panel.
          </p>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {(['all', 'default', 'custom'] as const).map((cat) => (
            <button
              key={cat}
              onClick={() => setFilterCategory(cat)}
              className={`px-4 py-2 text-xs font-semibold uppercase tracking-wider rounded-xl transition-all ${
                filterCategory === cat
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20'
                  : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10'
              }`}
            >
              {cat === 'all' ? 'All Agents' : cat === 'default' ? 'Default App Agents' : 'Custom Agents'}
            </button>
          ))}
        </div>
      </div>

      {/* Live Agent To-Do List Widget */}
      {todoItems.length > 0 && (
        <AgentTodoList 
          todoItems={todoItems} 
          title="Agentic Inspection & Active Task Execution Plan"
          className="border-indigo-500/30 bg-slate-900/80 shadow-2xl"
        />
      )}

      {/* Search Input */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search agents by name, tool, or capability..."
          className="w-full py-3 pl-11 pr-4 rounded-2xl bg-slate-900/80 border border-white/10 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors shadow-inner"
        />
      </div>

      {/* Agent Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredAgents.map((agent) => (
          <div
            key={agent.id}
            className="group relative flex flex-col justify-between p-6 rounded-3xl bg-slate-900/70 border border-white/10 backdrop-blur-xl hover:border-indigo-500/40 hover:shadow-2xl hover:shadow-indigo-500/10 transition-all duration-300"
          >
            <div>
              {/* Badge & Type */}
              <div className="flex items-center justify-between mb-4">
                <span
                  className={`px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full text-white bg-gradient-to-r ${agent.badgeColor} shadow-md`}
                >
                  {agent.category === 'default' ? 'Default App Agent' : 'Custom Agent'}
                </span>
                <span className="text-xs font-mono text-slate-500">ID: {agent.id}</span>
              </div>

              {/* Title & Persona */}
              <h3 className="text-xl font-bold text-white group-hover:text-indigo-300 transition-colors mb-1">
                {agent.name}
              </h3>
              <p className="text-xs font-medium text-indigo-400/90 mb-3">{agent.persona}</p>
              <p className="text-xs text-slate-300 leading-relaxed line-clamp-3 mb-4">{agent.description}</p>

              {/* Tools list badges */}
              <div className="space-y-1.5 mb-6">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  Integrated Capabilities ({agent.tools.length}):
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {agent.tools.slice(0, 4).map((tool, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 text-[10px] font-mono rounded-md bg-white/5 border border-white/10 text-slate-300"
                    >
                      {tool}
                    </span>
                  ))}
                  {agent.tools.length > 4 && (
                    <span className="px-2 py-0.5 text-[10px] font-mono rounded-md bg-white/5 text-slate-500">
                      +{agent.tools.length - 4} more
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Test Action Button */}
            <button
              onClick={() => setTestingAgent(agent)}
              className="w-full py-3 px-4 rounded-2xl bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-600 hover:opacity-95 text-white font-semibold text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/25 transition-all group-hover:scale-[1.02]"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Test Agent</span>
            </button>
          </div>
        ))}
      </div>

      {/* Liquid Glass Test Modal */}
      {testingAgent && (
        <LiquidGlassTestPanel agent={testingAgent} onClose={() => setTestingAgent(null)} />
      )}
    </div>
  );
};
