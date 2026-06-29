import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { OllamaService } from '@/services/ollama';
import { 
  Layers, Trophy, Network, Plus, Trash2, Download, Database, 
  CheckCircle2, Terminal, Activity, Server, Code, Copy, Check,
  Play, Send, Folder, FolderCheck, File, X, Shield, Eraser, AlertCircle
} from 'lucide-react';

interface LocalModel {
  name: string;
  details: {
    parameter_size: string;
    family: string;
  };
}

interface Hub {
  id: string;
  name: string;
  description: string;
}

interface CustomAgent {
  id: string;
  hub_id: string;
  parent_id: string | null;
  name: string;
  persona: string;
  system_prompt: string;
  base_model: string;
  tools: string[];
  mcp_servers: string[];
}

interface McpServer {
  id: string;
  name: string;
  type: string;
  command: string;
  args: string[];
  url: string | null;
  env: Record<string, string>;
  enabled: boolean;
}

interface TokenStat {
  agent_id: string;
  name: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export const HubCreator: React.FC = () => {
  // Navigation / active view state
  const [activeSubTab, setActiveSubTab] = useState<'hubs' | 'models' | 'mcp' | 'stats'>('hubs');
  
  // Data lists
  const [hubs, setHubs] = useState<Hub[]>([]);
  const [agents, setAgents] = useState<CustomAgent[]>([]);
  const [mcpServers, setMcpServers] = useState<McpServer[]>([]);
  const [localModels, setLocalModels] = useState<LocalModel[]>([]);
  const [tokenStats, setTokenStats] = useState<TokenStat[]>([]);
  
  // Selection states
  const [selectedHub, setSelectedHub] = useState<Hub | null>(null);
  
  // Forms states - Hub
  const [hubId, setHubId] = useState('');
  const [hubName, setHubName] = useState('');
  const [hubDesc, setHubDesc] = useState('');
  
  // Forms states - Custom Agent
  const [agentId, setAgentId] = useState('');
  const [agentName, setAgentName] = useState('');
  const [agentPersona, setAgentPersona] = useState('');
  const [agentSysPrompt, setAgentSysPrompt] = useState('');
  const [agentModel, setAgentModel] = useState('qwen3.5:9b');
  const [agentParent, setAgentParent] = useState<string>('');
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [selectedMcps, setSelectedMcps] = useState<string[]>([]);
  
  // Forms states - MCP Server
  const [mcpId, setMcpId] = useState('');
  const [mcpName, setMcpName] = useState('');
  const [mcpCmd, setMcpCmd] = useState('');
  const [mcpArgsStr, setMcpArgsStr] = useState('[]');
  const [mcpEnvStr, setMcpEnvStr] = useState('{}');
  
  // Forms states - Model Puller
  const [pullModelName, setPullModelName] = useState('');
  const [pullProgress, setPullProgress] = useState<string>('');
  const [pullPercent, setPullPercent] = useState<number>(0);
  const [isPulling, setIsPulling] = useState(false);
  const [pullAbortController, setPullAbortController] = useState<AbortController | null>(null);

  // Status notifications
  const [statusMsg, setStatusMsg] = useState('');
  const [statusType, setStatusType] = useState<'success' | 'error' | ''>('');

  // JSON viewer states
  const [openMcpJsonIds, setOpenMcpJsonIds] = useState<Record<string, boolean>>({});
  const [copiedMcpId, setCopiedMcpId] = useState<string | null>(null);

  const toggleMcpJson = (id: string) => {
    setOpenMcpJsonIds(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const copyToClipboard = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedMcpId(id);
    setTimeout(() => setCopiedMcpId(null), 2000);
  };

  // Daily Stats and model pull recommendations states
  const [dailyStats, setDailyStats] = useState<any | null>(null);
  const [showDailyModal, setShowDailyModal] = useState(false);
  const [showRecommendations, setShowRecommendations] = useState(false);

  // --- Test Agent Sandbox States ---
  const [testingAgent, setTestingAgent] = useState<CustomAgent | null>(null);
  const [allowedPaths, setAllowedPaths] = useState<string[]>([]);
  const [newAllowedPath, setNewAllowedPath] = useState('');
  const [chatMessages, setChatMessages] = useState<Array<{ role: 'user' | 'agent'; content: string }>>([]);
  const [chatInput, setChatInput] = useState('');
  const [isChatSending, setIsChatSending] = useState(false);
  const [isConfigSaving, setIsConfigSaving] = useState(false);
  const [mAgentConfig, setMAgentConfig] = useState<any>(null);

  const handleFetchDailyStats = async () => {
    try {
      const data = await OllamaService.getDailyTokenStats();
      setDailyStats(data);
      setShowDailyModal(true);
    } catch (err) {
      console.error("Failed to fetch daily token stats:", err);
    }
  };

  const modelRecommendations = [
    {
      name: 'gemma3:4b',
      size: '4.3B (2.6 GB)',
      desc: "Google's lightweight model. Best-in-class coding logic, general knowledge, and reasoning capabilities in a small footprint.",
      details: 'Gemma 3 Instruction-tuned'
    },
    {
      name: 'llama3.2:latest',
      size: '3.2B (2.0 GB)',
      desc: "Meta's highly popular small language model. Optimized for creative writing, summarization, and interactive chat.",
      details: 'Llama 3.2 3B Instruct'
    },
    {
      name: 'deepseek-r1:1.5b',
      size: '1.5B (1.1 GB)',
      desc: "DeepSeek's ultra-fast reasoning model. Uses advanced chain-of-thought processing for complex math and software logic.",
      details: 'DeepSeek R1 Distill Qwen'
    },
    {
      name: 'deepseek-r1:8b',
      size: '8B (4.7 GB)',
      desc: "Standard DeepSeek reasoning model. Unbelievable performance for logic tasks, debugging code, and step-by-step thinking.",
      details: 'DeepSeek R1 Distill Llama'
    },
    {
      name: 'qwen2.5-coder:1.5b',
      size: '1.5B (980 MB)',
      desc: "Alibaba's specialized code assistant. Very low system footprint with high coding proficiency across many languages.",
      details: 'Qwen 2.5 Coder Instruct'
    },
    {
      name: 'qwen2.5:0.5b',
      size: '0.5B (390 MB)',
      desc: "Alibaba's smallest general assistant. Extremely fast response, perfect for low-spec systems or lightweight tasks.",
      details: 'Qwen 2.5 0.5B Instruct'
    }
  ];

  const selectRecommendedModel = (name: string) => {
    setPullModelName(name);
    setShowRecommendations(false);
  };

  // Available default tools list
  const availableTools = [
    { id: 'file_operation', name: 'File Read/Write/List' },
    { id: 'execute_code', name: 'Execute Python Code' },
    { id: 'generate_code', name: 'Generate Code Snippets' },
    { id: 'analyze_code', name: 'Analyze Code for Bugs' },
    { id: 'web_search', name: 'Web Search (Offline Fallback)' },
    { id: 'summarize_text', name: 'Text Summarizer' }
  ];

  // Refresh lists helper
  const loadAllData = async () => {
    try {
      const [hList, aList, mList, statsList] = await Promise.all([
        OllamaService.getHubs(),
        OllamaService.getCustomAgents(),
        OllamaService.getMcpServers(),
        OllamaService.getTokenStats()
      ]);
      setHubs(hList);
      setAgents(aList);
      setMcpServers(mList);
      setTokenStats(statsList.stats || []);
      
      // Load Ollama tags
      const modelsData = await OllamaService.getLocalModels();
      if (modelsData.status === 'success') {
        setLocalModels(modelsData.models || []);
        if (modelsData.models?.length > 0 && !agentModel) {
          setAgentModel(modelsData.models[0].name);
        }
      }
    } catch (err) {
      console.error("Failed to load data in HubCreator:", err);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const triggerStatus = (msg: string, type: 'success' | 'error') => {
    setStatusMsg(msg);
    setStatusType(type);
    setTimeout(() => {
      setStatusMsg('');
      setStatusType('');
    }, 4000);
  };

  // --- Hub Handlers ---
  const handleCreateHub = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!hubId || !hubName) return;
    try {
      await OllamaService.createHub({ id: hubId, name: hubName, description: hubDesc });
      triggerStatus(`Hub '${hubName}' created successfully!`, 'success');
      setHubId('');
      setHubName('');
      setHubDesc('');
      loadAllData();
    } catch (err: any) {
      triggerStatus(err.response?.data?.detail || "Failed to create Hub", "error");
    }
  };

  const handleDeleteHub = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this Hub? All attached agents will be removed.")) return;
    try {
      await OllamaService.deleteHub(id);
      if (selectedHub?.id === id) setSelectedHub(null);
      triggerStatus("Hub deleted successfully", "success");
      loadAllData();
    } catch (err) {
      triggerStatus("Failed to delete Hub", "error");
    }
  };

  // --- Custom Agent Handlers ---
  const handleCreateAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedHub) {
      triggerStatus("Please select a Hub first", "error");
      return;
    }
    if (!agentId || !agentName || !agentSysPrompt) {
      triggerStatus("ID, Name, and System Prompt are required", "error");
      return;
    }
    try {
      const payload = {
        id: agentId,
        hub_id: selectedHub.id,
        parent_id: agentParent || null,
        name: agentName,
        persona: agentPersona,
        system_prompt: agentSysPrompt,
        base_model: agentModel,
        tools: selectedTools,
        mcp_servers: selectedMcps
      };
      await OllamaService.createCustomAgent(payload);
      triggerStatus(`Agent '${agentName}' added to Hub!`, "success");
      setAgentId('');
      setAgentName('');
      setAgentPersona('');
      setAgentSysPrompt('');
      setAgentParent('');
      setSelectedTools([]);
      setSelectedMcps([]);
      loadAllData();
    } catch (err) {
      triggerStatus("Failed to add Agent", "error");
    }
  };

  const handleDeleteAgent = async (id: string) => {
    if (!window.confirm("Delete this agent?")) return;
    try {
      await OllamaService.deleteCustomAgent(id);
      triggerStatus("Agent deleted", "success");
      loadAllData();
    } catch (err) {
      triggerStatus("Failed to delete agent", "error");
    }
  };

  // --- MCP Servers Handlers ---
  const handleCreateMcp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mcpId || !mcpName || !mcpCmd) return;
    try {
      let argsList = [];
      let envDict = {};
      try {
        argsList = JSON.parse(mcpArgsStr);
      } catch (err) {
        triggerStatus("MCP Arguments must be a valid JSON array", "error");
        return;
      }
      try {
        envDict = JSON.parse(mcpEnvStr);
      } catch (err) {
        triggerStatus("MCP Env must be a valid JSON object", "error");
        return;
      }
      
      const payload = {
        id: mcpId,
        name: mcpName,
        type: 'stdio',
        command: mcpCmd,
        args: argsList,
        url: null,
        env: envDict,
        enabled: true
      };
      await OllamaService.createMcpServer(payload);
      triggerStatus(`MCP Server '${mcpName}' registered!`, "success");
      setMcpId('');
      setMcpName('');
      setMcpCmd('');
      setMcpArgsStr('[]');
      setMcpEnvStr('{}');
      loadAllData();
    } catch (err) {
      triggerStatus("Failed to register MCP Server", "error");
    }
  };

  const handleDeleteMcp = async (id: string) => {
    if (!window.confirm("Remove this MCP Server?")) return;
    try {
      await OllamaService.deleteMcpServer(id);
      triggerStatus("MCP Server removed", "success");
      loadAllData();
    } catch (err) {
      triggerStatus("Failed to remove MCP Server", "error");
    }
  };

  // --- Model Puller Handlers ---
  const handlePullModel = async () => {
    if (!pullModelName) return;
    setIsPulling(true);
    setPullProgress('Connecting to Ollama...');
    setPullPercent(0);
    
    try {
      const controller = await OllamaService.pullModelStream(
        pullModelName,
        (progress) => {
          if (progress.error) {
            setPullProgress(`Error: ${progress.error}`);
            setIsPulling(false);
            return;
          }
          
          let pct = 0;
          if (progress.total && progress.completed) {
            pct = Math.round((progress.completed / progress.total) * 100);
            setPullPercent(pct);
          }
          
          const status = progress.status || 'Downloading...';
          setPullProgress(`${status} (${pct}%)`);
          
          if (progress.status === 'success') {
            setPullProgress('Model successfully downloaded!');
            setIsPulling(false);
            loadAllData();
          }
        },
        (err) => {
          setPullProgress(`Pull aborted or failed: ${err.message || err}`);
          setIsPulling(false);
        }
      );
      setPullAbortController(controller);
    } catch (err: any) {
      setPullProgress(`Error: ${err.message || err}`);
      setIsPulling(false);
    }
  };

  const cancelPull = () => {
    if (pullAbortController) {
      pullAbortController.abort();
      setPullAbortController(null);
      setIsPulling(false);
      setPullProgress('Model pull cancelled.');
    }
  };

  const toggleTool = (toolId: string) => {
    setSelectedTools(prev => 
      prev.includes(toolId) ? prev.filter(t => t !== toolId) : [...prev, toolId]
    );
  };

  const toggleMcp = (mcpId: string) => {
    setSelectedMcps(prev => 
      prev.includes(mcpId) ? prev.filter(m => m !== mcpId) : [...prev, mcpId]
    );
  };

  // --- Test Agent Sandbox Handlers ---
  const handleStartTestingAgent = async (agent: CustomAgent) => {
    setTestingAgent(agent);
    setChatMessages([]);
    setChatInput('');
    setIsChatSending(false);
    
    // Fetch multi-agent config to get allowed_paths
    try {
      const response = await OllamaService.getMultiAgentConfig();
      if (response && response.status === 'success') {
        setMAgentConfig(response.config);
        setAllowedPaths(response.config.allowed_paths || []);
      }
    } catch (err) {
      console.error("Failed to load multi-agent config in Test Agent:", err);
    }
  };

  const handleSendTestMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || !testingAgent) return;
    
    const userMsg = chatInput.trim();
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setIsChatSending(true);
    
    try {
      // Direct call to agent chat
      const responseText = await OllamaService.chat(testingAgent.id, userMsg);
      setChatMessages(prev => [...prev, { role: 'agent', content: responseText }]);
    } catch (err: any) {
      const errMsg = err.response?.data?.detail || err.message || "Failed to get response from agent";
      setChatMessages(prev => [...prev, { role: 'agent', content: `Error: ${errMsg}` }]);
    } finally {
      setIsChatSending(false);
    }
  };

  const handleClearTestChat = async () => {
    if (!testingAgent) return;
    if (!window.confirm("Clear all session history for this agent?")) return;
    try {
      await OllamaService.clearChat(testingAgent.id);
      setChatMessages([]);
      triggerStatus("Conversation history cleared!", "success");
    } catch (err) {
      triggerStatus("Failed to clear conversation history", "error");
    }
  };

  const handleAddAllowedPath = () => {
    if (!newAllowedPath.trim()) return;
    const pathToAdd = newAllowedPath.trim();
    if (allowedPaths.includes(pathToAdd)) {
      alert("Path is already in the allowed list.");
      return;
    }
    setAllowedPaths(prev => [...prev, pathToAdd]);
    setNewAllowedPath('');
  };

  const handleRemoveAllowedPath = (pathToRemove: string) => {
    setAllowedPaths(prev => prev.filter(p => p !== pathToRemove));
  };

  const handleSaveAllowedPaths = async () => {
    if (!mAgentConfig) return;
    setIsConfigSaving(true);
    try {
      const updatedConfig = {
        ...mAgentConfig,
        allowed_paths: allowedPaths
      };
      const response = await OllamaService.updateMultiAgentConfig(updatedConfig);
      if (response && response.status === 'success') {
        setMAgentConfig(updatedConfig);
        triggerStatus("File access permissions updated successfully!", "success");
      } else {
        triggerStatus("Failed to save permissions", "error");
      }
    } catch (err) {
      triggerStatus("Failed to save permissions due to connection error", "error");
    } finally {
      setIsConfigSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-8 max-w-7xl mx-auto">
      {/* Tab Navigation */}
      <div className="flex gap-4 border-b border-border pb-4">
        <button
          onClick={() => setActiveSubTab('hubs')}
          className={`flex items-center gap-2 px-6 py-3 font-medium text-lg border-b-2 transition-all ${
            activeSubTab === 'hubs' ? 'border-ibm-blue text-ibm-blue' : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Layers className="w-5 h-5" /> Agent Teams & Hubs
        </button>
        <button
          onClick={() => setActiveSubTab('models')}
          className={`flex items-center gap-2 px-6 py-3 font-medium text-lg border-b-2 transition-all ${
            activeSubTab === 'models' ? 'border-ibm-blue text-ibm-blue' : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Download className="w-5 h-5" /> Local Models Puller
        </button>
        <button
          onClick={() => setActiveSubTab('mcp')}
          className={`flex items-center gap-2 px-6 py-3 font-medium text-lg border-b-2 transition-all ${
            activeSubTab === 'mcp' ? 'border-ibm-blue text-ibm-blue' : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Server className="w-5 h-5" /> MCP Server Registry
        </button>
        <button
          onClick={() => setActiveSubTab('stats')}
          className={`flex items-center gap-2 px-6 py-3 font-medium text-lg border-b-2 transition-all ${
            activeSubTab === 'stats' ? 'border-ibm-blue text-ibm-blue' : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Activity className="w-5 h-5" /> Token usage Stats
        </button>
      </div>

      {/* Global Status Message */}
      {statusMsg && (
        <div className={`p-5 rounded-xl border flex items-center gap-3 text-lg font-medium animate-in fade-in slide-in-from-top-2 ${
          statusType === 'success' ? 'bg-green-500/10 border-green-500 text-green-500' : 'bg-red-500/10 border-red-500 text-red-500'
        }`}>
          <CheckCircle2 className="w-6 h-6 flex-shrink-0" />
          {statusMsg}
        </div>
      )}

      {/* Tab Contents */}
      {activeSubTab === 'hubs' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left / Center Panels: Hub selection & Custom Agent Builder */}
          <div className="lg:col-span-2 space-y-8">
            {/* Hub Selector */}
            <Card className="shadow-md">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-2xl font-light">
                  <Network className="w-6 h-6 text-ibm-blue" />
                  Select active Team Hub
                </CardTitle>
              </CardHeader>
              <CardContent>
                {hubs.length === 0 ? (
                  <div className="p-8 text-center text-muted-foreground border-2 border-dashed border-border rounded-xl">
                    No Multi-Agent Hubs created yet. Use the right panel to build one!
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {hubs.map((hub) => {
                      const count = agents.filter(a => a.hub_id === hub.id).length;
                      return (
                        <div
                          key={hub.id}
                          onClick={() => setSelectedHub(hub)}
                          className={`p-6 border-2 rounded-xl cursor-pointer transition-all hover:border-ibm-blue relative group ${
                            selectedHub?.id === hub.id ? 'border-ibm-blue bg-ibm-blue/5' : 'border-border bg-card'
                          }`}
                        >
                          <h3 className="text-xl font-medium mb-1 flex items-center gap-2">
                            {hub.name}
                            <span className="text-xs bg-muted border text-muted-foreground px-2 py-0.5 rounded-full font-mono font-light">
                              {count} {count === 1 ? 'agent' : 'agents'}
                            </span>
                          </h3>
                          <p className="text-md text-muted-foreground line-clamp-2">{hub.description || 'No description'}</p>
                          <button
                            onClick={(e) => handleDeleteHub(hub.id, e)}
                            className="absolute top-4 right-4 p-2 text-muted-foreground hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            <Trash2 className="w-5 h-5" />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Custom Agent Builder Form inside Hub */}
            {selectedHub && (
              <Card className="shadow-md border-t-4 border-ibm-blue">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-2xl font-light">
                    <Plus className="w-6 h-6 text-ibm-blue" />
                    Add Custom Agent to Hub [{selectedHub.name}]
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleCreateAgent} className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-2">
                        <label className="text-md font-medium text-foreground/80">Unique Agent ID (Slug)</label>
                        <input
                          type="text"
                          required
                          placeholder="e.g. frontend_specialist"
                          className="w-full p-4 bg-background border border-border rounded-xl text-md outline-none focus:border-ibm-blue"
                          value={agentId}
                          onChange={e => setAgentId(e.target.value.toLowerCase().replace(/\s+/g, '_'))}
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-md font-medium text-foreground/80">Agent Name</label>
                        <input
                          type="text"
                          required
                          placeholder="e.g. Frontend Specialist"
                          className="w-full p-4 bg-background border border-border rounded-xl text-md outline-none focus:border-ibm-blue"
                          value={agentName}
                          onChange={e => setAgentName(e.target.value)}
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="text-md font-medium text-foreground/80">Agent Persona / Subtitle</label>
                      <input
                        type="text"
                        placeholder="e.g. Specialized in building React components and responsive styling"
                        className="w-full p-4 bg-background border border-border rounded-xl text-md outline-none focus:border-ibm-blue"
                        value={agentPersona}
                        onChange={e => setAgentPersona(e.target.value)}
                      />
                    </div>

                    <div className="space-y-2">
                      <label className="text-md font-medium text-foreground/80">System Prompt instructions (Behavior)</label>
                      <textarea
                        required
                        rows={5}
                        placeholder="Define how the agent behaves, their workflow, and final formatting expectations..."
                        className="w-full p-4 bg-background border border-border rounded-xl text-md outline-none focus:border-ibm-blue min-h-[120px]"
                        value={agentSysPrompt}
                        onChange={e => setAgentSysPrompt(e.target.value)}
                      />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-2">
                        <label className="text-md font-medium text-foreground/80">Ollama Base Model</label>
                        <select
                          className="w-full p-4 bg-background border border-border rounded-xl text-md outline-none focus:border-ibm-blue appearance-none cursor-pointer"
                          value={agentModel}
                          onChange={e => setAgentModel(e.target.value)}
                        >
                          {localModels.map(m => (
                            <option key={m.name} value={m.name}>{m.name}</option>
                          ))}
                        </select>
                      </div>

                      <div className="space-y-2">
                        <label className="text-md font-medium text-foreground/80">Parent Delegation Agent (Hierarchy)</label>
                        <select
                          className="w-full p-4 bg-background border border-border rounded-xl text-md outline-none focus:border-ibm-blue appearance-none cursor-pointer"
                          value={agentParent}
                          onChange={e => setAgentParent(e.target.value)}
                        >
                          <option value="">No Parent (Root level)</option>
                          {agents
                            .filter(a => a.hub_id === selectedHub.id && a.id !== agentId)
                            .map(a => (
                              <option key={a.id} value={a.id}>{a.name}</option>
                            ))
                          }
                        </select>
                      </div>
                    </div>

                    {/* System Tools Checks */}
                    <div className="space-y-3">
                      <label className="text-md font-medium text-foreground/80">Enable System Tools</label>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                        {availableTools.map(t => (
                          <div
                            key={t.id}
                            onClick={() => toggleTool(t.id)}
                            className={`p-3 border rounded-xl text-md cursor-pointer select-none transition-colors text-center ${
                              selectedTools.includes(t.id) ? 'border-ibm-blue bg-ibm-blue/5 text-ibm-blue' : 'border-border bg-card'
                            }`}
                          >
                            {t.name}
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* MCP tools Checks */}
                    {mcpServers.length > 0 && (
                      <div className="space-y-3">
                        <label className="text-md font-medium text-foreground/80">Attach MCP Servers (External Tools)</label>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                          {mcpServers.map(mcp => (
                            <div
                              key={mcp.id}
                              onClick={() => toggleMcp(mcp.id)}
                              className={`p-3 border rounded-xl text-md cursor-pointer select-none transition-colors text-center ${
                                selectedMcps.includes(mcp.id) ? 'border-ibm-blue bg-ibm-blue/5 text-ibm-blue' : 'border-border bg-card'
                              }`}
                            >
                              {mcp.name}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <Button type="submit" className="w-full py-4 text-md font-medium rounded-xl">
                      <Plus className="w-5 h-5 mr-2" /> Add Agent to Hub
                    </Button>
                  </form>
                </CardContent>
              </Card>
            )}

            {/* List of Custom Agents in active Hub */}
            {selectedHub && (
              <Card className="shadow-md">
                <CardHeader>
                  <CardTitle className="text-2xl font-light flex items-center gap-2">
                    <Activity className="w-6 h-6 text-muted-foreground" />
                    Registered Agents in [{selectedHub.name}]
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {agents.filter(a => a.hub_id === selectedHub.id).length === 0 ? (
                    <div className="p-8 text-center text-muted-foreground border-2 border-dashed border-border rounded-xl">
                      No custom agents registered in this hub yet. Create one above!
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {agents.filter(a => a.hub_id === selectedHub.id).map(agent => (
                        <div key={agent.id} className="p-6 border border-border bg-card rounded-2xl flex justify-between items-start gap-4">
                          <div className="space-y-2">
                            <h4 className="text-xl font-medium flex items-center gap-2">
                              {agent.name}
                              <span className="text-xs bg-muted px-2 py-0.5 rounded font-mono font-light text-muted-foreground">
                                {agent.id}
                              </span>
                            </h4>
                            <p className="text-md text-muted-foreground">{agent.persona}</p>
                            
                            <div className="flex flex-wrap gap-4 text-xs font-mono text-muted-foreground pt-2">
                              <span>Model: {agent.base_model}</span>
                              {agent.parent_id && (
                                <span className="flex items-center gap-1 text-ibm-blue">
                                  Parent: {agent.parent_id}
                                </span>
                              )}
                              <span>Tools: {agent.tools.join(', ') || 'none'}</span>
                              {agent.mcp_servers.length > 0 && (
                                <span className="text-green-600">MCP: {agent.mcp_servers.join(', ')}</span>
                              )}
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-2 shrink-0">
                            <button
                              type="button"
                              onClick={() => handleStartTestingAgent(agent)}
                              className="flex items-center gap-1.5 px-4 py-2 border border-ibm-blue/30 hover:border-ibm-blue bg-ibm-blue/5 hover:bg-ibm-blue/10 text-ibm-blue rounded-xl text-xs font-semibold uppercase tracking-wider transition-all"
                              title="Test this agent in an interactive sandbox"
                            >
                              <Play className="w-3.5 h-3.5" />
                              Test Agent
                            </button>

                            <button
                              type="button"
                              onClick={() => handleDeleteAgent(agent.id)}
                              className="p-3 text-muted-foreground hover:text-red-500 hover:bg-red-500/5 rounded-xl transition-all"
                            >
                              <Trash2 className="w-5 h-5" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Panel: Create Hub Form */}
          <div className="space-y-8">
            <Card className="shadow-md">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-2xl font-light">
                  <Network className="w-6 h-6 text-ibm-blue" />
                  Create new Hub Team
                </CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateHub} className="space-y-6">
                  <div className="space-y-2">
                    <label className="text-md font-medium text-foreground/80">Unique Hub ID (Slug)</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. dev_team"
                      className="w-full p-4 bg-background border border-border rounded-xl text-md outline-none focus:border-ibm-blue"
                      value={hubId}
                      onChange={e => setHubId(e.target.value.toLowerCase().replace(/\s+/g, '_'))}
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-md font-medium text-foreground/80">Hub Name</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Dev Team Hub"
                      className="w-full p-4 bg-background border border-border rounded-xl text-md outline-none focus:border-ibm-blue"
                      value={hubName}
                      onChange={e => setHubName(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-md font-medium text-foreground/80">Description</label>
                    <textarea
                      rows={3}
                      placeholder="Describe what team operations are run in this Hub..."
                      className="w-full p-4 bg-background border border-border rounded-xl text-md outline-none focus:border-ibm-blue min-h-[80px]"
                      value={hubDesc}
                      onChange={e => setHubDesc(e.target.value)}
                    />
                  </div>

                  <Button type="submit" className="w-full py-4 text-md font-medium rounded-xl">
                    <Plus className="w-5 h-5 mr-2" /> Initialize Hub Team
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Model Puller Tab */}
      {activeSubTab === 'models' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* List of Local Models */}
          <div className="lg:col-span-2 space-y-8">
            <Card className="shadow-md">
              <CardHeader>
                <CardTitle className="text-2xl font-light flex items-center gap-2">
                  <Database className="w-6 h-6 text-ibm-blue" />
                  Local Downloaded Models
                </CardTitle>
              </CardHeader>
              <CardContent>
                {localModels.length === 0 ? (
                  <div className="p-8 text-center text-muted-foreground">
                    Could not query local tags. Make sure Ollama server is running.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {localModels.map(m => (
                      <div key={m.name} className="p-5 border border-border bg-card rounded-2xl flex justify-between items-center shadow-sm">
                        <div className="space-y-1">
                          <h4 className="text-lg font-medium font-mono">{m.name}</h4>
                          <div className="flex gap-4 text-xs text-muted-foreground">
                            <span>Size: {m.details?.parameter_size || 'unknown'}</span>
                            <span>Family: {m.details?.family || 'unknown'}</span>
                          </div>
                        </div>
                        <CheckCircle2 className="w-6 h-6 text-green-500" />
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Model Pull Action Card */}
          <div className="space-y-8">
            <Card className="shadow-md border-t-4 border-ibm-blue">
              <CardHeader>
                <CardTitle className="text-2xl font-light flex items-center gap-2">
                  <Download className="w-6 h-6 text-ibm-blue" />
                  Pull model from Ollama
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="bg-ibm-blue/5 border-l-4 border-ibm-blue p-4 text-md text-muted-foreground leading-relaxed">
                  Provide the model identifier tag from the Ollama model library (e.g. <code>llama3.2</code>, <code>qwen2.5:0.5b</code>).
                </div>
                
                <div className="space-y-2">
                  <label className="text-md font-medium text-foreground/80">Model Name / Tag</label>
                  <div className="relative">
                    <input
                      type="text"
                      disabled={isPulling}
                      placeholder="e.g. qwen2.5:0.5b"
                      className="w-full p-4 bg-background border border-border rounded-xl text-md outline-none focus:border-ibm-blue font-mono"
                      value={pullModelName}
                      onFocus={() => setShowRecommendations(true)}
                      onBlur={() => setTimeout(() => setShowRecommendations(false), 200)}
                      onChange={e => setPullModelName(e.target.value.trim())}
                    />
                    
                    {showRecommendations && (
                      <div className="absolute left-0 z-50 w-full mt-2 bg-[#121212] border border-border rounded-xl shadow-2xl overflow-y-auto max-h-[320px] divide-y divide-border/40 animate-in fade-in duration-200">
                        <div className="p-3 text-[10px] font-mono text-muted-foreground bg-[#1a1a1a] uppercase tracking-wider">
                          Recommended Models Library
                        </div>
                        {modelRecommendations.map(rec => (
                          <div
                            key={rec.name}
                            onMouseDown={() => selectRecommendedModel(rec.name)}
                            className="p-4 hover:bg-muted/30 cursor-pointer flex flex-col gap-1 transition-colors text-left font-sans"
                          >
                            <div className="flex justify-between items-center">
                              <span className="font-mono font-bold text-sm text-ibm-blue">{rec.name}</span>
                              <span className="text-[10px] font-mono bg-muted border px-1.5 py-0.2 rounded text-muted-foreground font-light">
                                {rec.size}
                              </span>
                            </div>
                            <div className="text-xs font-semibold text-foreground/85 mt-0.5">{rec.details}</div>
                            <div className="text-[11px] text-muted-foreground leading-normal mt-1 font-light">
                              {rec.desc}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {isPulling ? (
                  <div className="space-y-4">
                    <div className="h-4 w-full bg-muted rounded-full overflow-hidden border border-border relative">
                      <div 
                        className="h-full bg-ibm-blue transition-all duration-300 rounded-full" 
                        style={{ width: `${pullPercent}%` }}
                      ></div>
                    </div>
                    <div className="text-md text-center font-mono font-medium text-ibm-blue truncate">{pullProgress}</div>
                    
                    <Button 
                      variant="outline" 
                      className="w-full py-4 text-md text-red-500 hover:bg-red-500/5 hover:border-red-500 rounded-xl"
                      onClick={cancelPull}
                    >
                      Cancel Pull Operation
                    </Button>
                  </div>
                ) : (
                  <Button 
                    disabled={!pullModelName} 
                    className="w-full py-4 text-md font-medium rounded-xl"
                    onClick={handlePullModel}
                  >
                    <Download className="w-5 h-5 mr-2" /> Pull Model
                  </Button>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* MCP Servers Registry */}
      {activeSubTab === 'mcp' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* List of Registered Servers */}
          <div className="lg:col-span-2 space-y-8">
            <Card className="shadow-md">
              <CardHeader>
                <CardTitle className="text-2xl font-light flex items-center gap-2">
                  <Server className="w-6 h-6 text-ibm-blue" />
                  Registered MCP Server Integrations
                </CardTitle>
              </CardHeader>
              <CardContent>
                {mcpServers.length === 0 ? (
                  <div className="p-8 text-center text-muted-foreground border-2 border-dashed border-border rounded-xl">
                    No Model Context Protocol (MCP) servers registered yet. Use the right panel to register one.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {mcpServers.map(server => {
                      const isJsonOpen = openMcpJsonIds[server.id] || false;
                      const jsonText = JSON.stringify(server, null, 2);
                      return (
                        <div key={server.id} className="p-6 border border-border bg-card rounded-2xl flex flex-col gap-4 shadow-sm hover:shadow-md transition-shadow">
                          <div className="flex justify-between items-start gap-4">
                            <div className="space-y-3 flex-1">
                              <h4 className="text-xl font-medium flex items-center gap-2">
                                {server.name}
                                <span className="text-xs bg-muted px-2 py-0.5 rounded font-mono font-light text-muted-foreground">
                                  {server.id}
                                </span>
                              </h4>
                              
                              <div className="font-mono text-sm space-y-1 bg-muted/40 p-4 rounded-xl border">
                                <div className="text-muted-foreground flex items-center gap-2">
                                  <Terminal className="w-4 h-4 text-ibm-blue flex-shrink-0" />
                                  <span>Command: {server.command} {server.args.join(' ')}</span>
                                </div>
                                {Object.keys(server.env).length > 0 && (
                                  <div className="text-xs text-muted-foreground mt-2 pl-6">
                                    ENV variables configured: {Object.keys(server.env).join(', ')}
                                  </div>
                                )}
                              </div>
                            </div>

                            <div className="flex items-center gap-2 shrink-0">
                              <button
                                onClick={() => toggleMcpJson(server.id)}
                                className={`p-3 rounded-xl transition-all border ${
                                  isJsonOpen 
                                    ? 'bg-ibm-blue/10 border-ibm-blue text-ibm-blue' 
                                    : 'text-muted-foreground hover:text-foreground border-transparent hover:bg-muted'
                                }`}
                                title="Toggle JSON view"
                              >
                                <Code className="w-5 h-5" />
                              </button>
                              <button
                                onClick={() => handleDeleteMcp(server.id)}
                                className="p-3 text-muted-foreground hover:text-red-500 hover:bg-red-500/5 rounded-xl border border-transparent hover:border-red-500/20 transition-all"
                                title="Delete integration"
                              >
                                <Trash2 className="w-5 h-5" />
                              </button>
                            </div>
                          </div>

                          {/* Collapsible beautiful JSON Viewer */}
                          {isJsonOpen && (
                            <div className="animate-in slide-in-from-top-2 duration-200 border border-border bg-[#121212] rounded-xl overflow-hidden mt-2">
                              <div className="bg-[#1c1c1c] px-4 py-2 border-b border-border/50 flex justify-between items-center text-xs font-mono text-muted-foreground">
                                <span>CONFIG SCHEMA (JSON)</span>
                                <button
                                  onClick={() => copyToClipboard(server.id, jsonText)}
                                  className="flex items-center gap-1 hover:text-foreground transition-colors"
                                >
                                  {copiedMcpId === server.id ? (
                                    <>
                                      <Check className="w-3.5 h-3.5 text-green-500" />
                                      <span className="text-green-500">Copied!</span>
                                    </>
                                  ) : (
                                    <>
                                      <Copy className="w-3.5 h-3.5" />
                                      <span>Copy JSON</span>
                                    </>
                                  )}
                                </button>
                              </div>
                              <pre className="p-4 overflow-x-auto text-xs font-mono text-emerald-400 max-h-[300px] leading-relaxed whitespace-pre-wrap selection:bg-emerald-500/20">
                                {jsonText}
                              </pre>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Register server form */}
          <div className="space-y-8">
            <Card className="shadow-md">
              <CardHeader>
                <CardTitle className="text-2xl font-light flex items-center gap-2">
                  <Plus className="w-6 h-6 text-ibm-blue" />
                  Register Stdio MCP Server
                </CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateMcp} className="space-y-6">
                  <div className="space-y-2">
                    <label className="text-md font-medium text-foreground/80">Unique Server ID (Slug)</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. github_mcp"
                      className="w-full p-4 bg-background border border-border rounded-xl text-md outline-none focus:border-ibm-blue font-mono"
                      value={mcpId}
                      onChange={e => setMcpId(e.target.value.toLowerCase().replace(/\s+/g, '_'))}
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-md font-medium text-foreground/80">Server Name</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. GitHub MCP Tools"
                      className="w-full p-4 bg-background border border-border rounded-xl text-md outline-none focus:border-ibm-blue"
                      value={mcpName}
                      onChange={e => setMcpName(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-md font-medium text-foreground/80">Command Executable</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. npx or python"
                      className="w-full p-4 bg-background border border-border rounded-xl text-md outline-none focus:border-ibm-blue font-mono"
                      value={mcpCmd}
                      onChange={e => setMcpCmd(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-md font-medium text-foreground/80">Arguments (JSON Array string)</label>
                    <input
                      type="text"
                      placeholder='e.g. ["-y", "@modelcontextprotocol/server-github"]'
                      className="w-full p-4 bg-background border border-border rounded-xl text-md outline-none focus:border-ibm-blue font-mono"
                      value={mcpArgsStr}
                      onChange={e => setMcpArgsStr(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-md font-medium text-foreground/80">Environment variables (JSON Object string)</label>
                    <textarea
                      rows={3}
                      placeholder='e.g. {"GITHUB_PERSONAL_ACCESS_TOKEN": "your_token"}'
                      className="w-full p-4 bg-background border border-border rounded-xl text-md outline-none focus:border-ibm-blue font-mono min-h-[80px]"
                      value={mcpEnvStr}
                      onChange={e => setMcpEnvStr(e.target.value)}
                    />
                  </div>

                  <Button type="submit" className="w-full py-4 text-md font-medium rounded-xl">
                    <Plus className="w-5 h-5 mr-2" /> Register MCP Server
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Token Stats Tab */}
      {activeSubTab === 'stats' && (
        <Card className="shadow-md">
          <CardHeader className="flex flex-row justify-between items-center">
            <CardTitle className="text-2xl font-light flex items-center gap-2">
              <Trophy className="w-6 h-6 text-ibm-blue" />
              Token Consumption
            </CardTitle>
            <Button
              onClick={handleFetchDailyStats}
              variant="outline"
              className="h-10 font-mono text-xs uppercase"
            >
              Daily Usage
            </Button>
          </CardHeader>
          <CardContent>
            {showDailyModal && dailyStats && (
              <div className="mx-6 my-4 p-5 bg-[#121212] border border-ibm-blue/30 rounded-2xl flex flex-col gap-3 animate-in slide-in-from-top-2 duration-300">
                <div className="flex justify-between items-center border-b border-border/50 pb-2">
                  <span className="font-mono text-xs font-bold text-ibm-blue uppercase tracking-widest">
                    Total Tokens Used in the Last 24 Hours
                  </span>
                  <button 
                    onClick={() => setShowDailyModal(false)}
                    className="text-xs text-muted-foreground hover:text-foreground font-mono"
                  >
                    [CLOSE]
                  </button>
                </div>
                <div className="grid grid-cols-3 gap-4 text-center mt-2">
                  <div className="p-4 bg-muted/30 border rounded-xl">
                    <div className="text-xs text-muted-foreground uppercase font-mono mb-1">Prompt Tokens</div>
                    <div className="text-xl font-mono font-semibold text-foreground">
                      {dailyStats.prompt_tokens?.toLocaleString() || 0}
                    </div>
                  </div>
                  <div className="p-4 bg-muted/30 border rounded-xl">
                    <div className="text-xs text-muted-foreground uppercase font-mono mb-1">Completion Tokens</div>
                    <div className="text-xl font-mono font-semibold text-foreground">
                      {dailyStats.completion_tokens?.toLocaleString() || 0}
                    </div>
                  </div>
                  <div className="p-4 bg-accent/5 border border-accent/25 rounded-xl">
                    <div className="text-xs text-accent uppercase font-mono mb-1">Total Tokens</div>
                    <div className="text-xl font-mono font-bold text-accent">
                      {dailyStats.total_tokens?.toLocaleString() || 0}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {tokenStats.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground border-2 border-dashed border-border rounded-xl">
                No token consumption recorded yet. Run some tasks or test agents to see stats.
              </div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-4 gap-4 px-6 text-xs font-mono text-muted-foreground uppercase tracking-wider font-semibold">
                  <div>Agent</div>
                  <div className="text-right">Prompt Tokens</div>
                  <div className="text-right">Completion Tokens</div>
                  <div className="text-right">Total Tokens</div>
                </div>
                {tokenStats.map(stat => (
                  <div key={stat.agent_id} className="p-5 border border-border bg-card rounded-2xl flex justify-between items-center shadow-sm">
                    <div className="grid grid-cols-4 gap-4 w-full items-center">
                      <div className="space-y-1">
                        <h4 className="text-lg font-medium truncate">{stat.name || stat.agent_id}</h4>
                        <span className="text-xs bg-muted px-2 py-0.5 rounded font-mono font-light text-muted-foreground">
                          {stat.agent_id}
                        </span>
                      </div>
                      <div className="text-right font-mono font-medium text-muted-foreground">
                        {stat.prompt_tokens?.toLocaleString() || 0}
                      </div>
                      <div className="text-right font-mono font-medium text-muted-foreground">
                        {stat.completion_tokens?.toLocaleString() || 0}
                      </div>
                      <div className="text-right font-mono font-bold text-ibm-blue">
                        {stat.total_tokens?.toLocaleString() || 0}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Test Agent Sandbox Modal */}
      {testingAgent && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-[100] flex items-center justify-center p-4 md:p-6 animate-in fade-in duration-300">
          <div className="bg-[#0b0b0b] border border-border/80 w-full max-w-5xl h-[85vh] rounded-3xl overflow-hidden shadow-2xl flex flex-col animate-in zoom-in-95 duration-300">
            
            {/* Modal Header */}
            <div className="px-8 py-5 border-b border-border flex justify-between items-center bg-[#111111]/50">
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-ibm-blue font-mono text-[10px] uppercase tracking-widest">
                  <Play className="w-3 h-3" /> Sandbox Environment
                </div>
                <h3 className="text-2xl font-light tracking-tight text-foreground flex items-center gap-3">
                  Test Agent: <span className="font-semibold text-ibm-blue">{testingAgent.name}</span>
                </h3>
              </div>
              <button 
                onClick={() => setTestingAgent(null)}
                className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-full transition-all border border-transparent hover:border-border"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-5 overflow-hidden">
              
              {/* Left Column: Chat Sandbox (3/5 width) */}
              <div className="lg:col-span-3 flex flex-col h-full overflow-hidden border-r border-border bg-[#0e0e0e]/20">
                
                {/* Chat Panel Title */}
                <div className="px-6 py-3 border-b border-border/40 bg-muted/10 flex justify-between items-center">
                  <span className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                    <Terminal className="w-3.5 h-3.5 text-ibm-blue" />
                    Interaction Console
                  </span>
                  <button
                    onClick={handleClearTestChat}
                    disabled={chatMessages.length === 0}
                    className="text-[10px] font-mono text-muted-foreground hover:text-red-400 flex items-center gap-1 transition-colors uppercase disabled:opacity-50"
                  >
                    <Eraser className="w-3 h-3" /> Clear History
                  </button>
                </div>

                {/* Messages Box */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4 flex flex-col">
                  {chatMessages.length === 0 ? (
                    <div className="my-auto flex flex-col items-center justify-center text-center p-8 gap-3 max-w-sm mx-auto">
                      <div className="w-12 h-12 bg-ibm-blue/5 border border-ibm-blue/20 rounded-2xl flex items-center justify-center text-ibm-blue">
                        <Terminal className="w-6 h-6" />
                      </div>
                      <h4 className="text-md font-medium">Console Initialized</h4>
                      <p className="text-xs text-muted-foreground font-light leading-relaxed">
                        Send a message to test this agent's response, system prompt instructions, and tool executions.
                      </p>
                    </div>
                  ) : (
                    chatMessages.map((msg, idx) => (
                      <div 
                        key={idx}
                        className={`max-w-[85%] p-4 rounded-2xl text-sm leading-relaxed ${
                          msg.role === 'user' 
                            ? 'bg-ibm-blue/10 border border-ibm-blue/20 text-foreground ml-auto rounded-tr-none' 
                            : 'bg-card border border-border text-foreground mr-auto rounded-tl-none font-sans whitespace-pre-wrap'
                        }`}
                      >
                        <div className="text-[9px] font-mono font-semibold uppercase tracking-widest text-muted-foreground mb-1">
                          {msg.role === 'user' ? 'You' : testingAgent.name}
                        </div>
                        {msg.content}
                      </div>
                    ))
                  )}

                  {isChatSending && (
                    <div className="bg-card border border-border p-4 rounded-2xl text-foreground mr-auto rounded-tl-none max-w-[85%] flex items-center gap-3">
                      <div className="w-4 h-4 border-2 border-ibm-blue border-t-transparent rounded-full animate-spin"></div>
                      <span className="text-xs font-mono text-muted-foreground">Agent is thinking...</span>
                    </div>
                  )}
                </div>

                {/* Chat Input form */}
                <form onSubmit={handleSendTestMessage} className="p-4 border-t border-border bg-[#0d0d0d]">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      disabled={isChatSending}
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      placeholder={`Prompt ${testingAgent.name}...`}
                      className="flex-1 bg-background text-foreground border border-border px-4 py-3 text-sm focus:outline-none focus:border-ibm-blue rounded-xl transition-colors disabled:opacity-50"
                    />
                    <button
                      type="submit"
                      disabled={isChatSending || !chatInput.trim()}
                      className="px-5 py-3 bg-ibm-blue hover:bg-ibm-blue-hover text-white rounded-xl flex items-center justify-center transition-colors disabled:opacity-50 disabled:bg-muted"
                    >
                      <Send className="w-4 h-4" />
                    </button>
                  </div>
                </form>
              </div>

              {/* Right Column: Whitelisted File Access (2/5 width) */}
              <div className="lg:col-span-2 flex flex-col h-full overflow-hidden bg-[#111] bg-opacity-20">
                
                {/* File Access Title */}
                <div className="px-6 py-3 border-b border-border/40 bg-muted/10">
                  <span className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                    <FolderCheck className="w-3.5 h-3.5 text-ibm-blue" />
                    Agent File Permissions
                  </span>
                </div>

                {/* Allowed paths list */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                  <div className="p-4 bg-ibm-blue/5 border border-ibm-blue/20 rounded-2xl space-y-2">
                    <div className="flex items-center gap-2 text-xs font-bold text-ibm-blue font-mono uppercase tracking-wide">
                      <Shield className="w-4 h-4" /> Security Whitelist
                    </div>
                    <p className="text-xs text-muted-foreground font-light leading-relaxed">
                      Restrict which folders and files this agent can read or write. If empty, the agent is confined to the default website workspace.
                    </p>
                  </div>

                  <div className="space-y-3">
                    <h4 className="text-[10px] font-mono uppercase font-bold text-muted-foreground tracking-wider">
                      Whitelisted Directories & Files
                    </h4>

                    {allowedPaths.length === 0 ? (
                      <div className="border border-dashed border-border p-6 text-center rounded-2xl bg-card/40">
                        <AlertCircle className="w-5 h-5 mx-auto text-muted-foreground opacity-60 mb-2" />
                        <p className="text-xs text-muted-foreground font-light leading-normal">
                          No specific directories whitelisted for agents. Running under default workspace sandboxing.
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-2 max-h-48 overflow-y-auto pr-1 font-mono text-xs">
                        {allowedPaths.map(path => (
                          <div 
                            key={path}
                            className="flex items-center justify-between p-3 border border-border bg-card rounded-xl text-sm transition-all hover:bg-muted/40 group"
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              {path.includes('.') ? (
                                <File className="w-3.5 h-3.5 text-ibm-blue shrink-0" />
                              ) : (
                                <Folder className="w-3.5 h-3.5 text-ibm-blue shrink-0" />
                              )}
                              <span className="font-mono text-xs truncate" title={path}>{path}</span>
                            </div>
                            <button
                              type="button"
                              onClick={() => handleRemoveAllowedPath(path)}
                              className="text-muted-foreground hover:text-red-500 p-1 transition-colors opacity-60 group-hover:opacity-100"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Add folder input */}
                  <div className="space-y-3 pt-3 border-t border-border/30">
                    <label className="text-[10px] font-mono text-muted-foreground uppercase block font-bold tracking-wider">
                      Authorize New Folder / File path
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={newAllowedPath}
                        onChange={(e) => setNewAllowedPath(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleAddAllowedPath()}
                        placeholder="e.g. D:\learning\code\website\src"
                        className="flex-1 bg-background text-foreground border border-border px-4 py-3 text-xs font-mono rounded-xl focus:outline-none focus:border-ibm-blue transition-colors placeholder:text-muted-foreground/50"
                      />
                      <button
                        type="button"
                        onClick={handleAddAllowedPath}
                        className="px-4 py-3 bg-card border border-border hover:bg-muted rounded-xl flex items-center justify-center font-bold text-xs"
                      >
                        <Plus className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Apply button bar */}
                <div className="p-4 border-t border-border bg-[#0d0d0d] flex gap-3">
                  <button
                    type="button"
                    disabled={isConfigSaving}
                    onClick={handleSaveAllowedPaths}
                    className="flex-1 py-3 bg-ibm-blue hover:bg-ibm-blue-hover text-white rounded-xl font-mono text-xs uppercase tracking-wider font-semibold transition-all text-center flex items-center justify-center gap-1.5 disabled:opacity-50"
                  >
                    <FolderCheck className="w-4 h-4" />
                    {isConfigSaving ? 'Applying...' : 'Apply Permissions'}
                  </button>
                </div>
              </div>

            </div>
          </div>
        </div>
      )}
    </div>
  );
};
