import React, { useState, useEffect } from 'react';
import { OllamaService } from '@/services/ollama';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  Settings, 
  ShieldAlert, 
  Trash2, 
  Plus, 
  Save, 
  RotateCcw, 
  Folder, 
  File, 
  FolderCheck,
  AlertTriangle,
  Info,
  CheckCircle2
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface AgentTools {
  code: string[];
  research: string[];
  analysis: string[];
}

interface MultiAgentConfigState {
  agent_tools: AgentTools;
  allowed_paths: string[];
}

export const MultiAgentConfig: React.FC = () => {
  const [config, setConfig] = useState<MultiAgentConfigState>({
    agent_tools: {
      code: [],
      research: [],
      analysis: []
    },
    allowed_paths: []
  });
  
  const [allTools, setAllTools] = useState<AgentTools>({
    code: ["execute_code", "generate_code", "file_operation", "create_project", "analyze_code"],
    research: ["web_search", "summarize_text"],
    analysis: ["analyze_code", "file_operation"]
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [newPath, setNewPath] = useState('');
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Fetch configuration on component mount
  const fetchConfig = async () => {
    setLoading(true);
    try {
      const response = await OllamaService.getMultiAgentConfig();
      if (response && response.status === 'success') {
        setConfig(response.config);
        if (response.all_tools) {
          setAllTools(response.all_tools);
        }
      }
    } catch (err) {
      console.error("Failed to load multi-agent configuration", err);
      setStatusMessage({ type: 'error', text: 'Failed to load configuration from backend.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  // Save config to backend
  const handleSave = async () => {
    setSaving(true);
    setStatusMessage(null);
    try {
      const response = await OllamaService.updateMultiAgentConfig(config);
      if (response && response.status === 'success') {
        setStatusMessage({ type: 'success', text: 'Configuration saved successfully!' });
        setTimeout(() => setStatusMessage(null), 4000);
      } else {
        setStatusMessage({ type: 'error', text: 'Failed to update configuration.' });
      }
    } catch (err) {
      console.error("Failed to save config", err);
      setStatusMessage({ type: 'error', text: 'Network error: could not save configuration.' });
    } finally {
      setSaving(false);
    }
  };

  // Reset/Revert config back to server state
  const handleReset = () => {
    setStatusMessage(null);
    fetchConfig();
  };

  // Toggle tool state for a specific agent
  const handleToggleTool = (agent: keyof AgentTools, tool: string) => {
    setConfig(prev => {
      const currentTools = prev.agent_tools[agent] || [];
      const updatedTools = currentTools.includes(tool)
        ? currentTools.filter(t => t !== tool)
        : [...currentTools, tool];
      
      return {
        ...prev,
        agent_tools: {
          ...prev.agent_tools,
          [agent]: updatedTools
        }
      };
    });
  };

  // Add path to allowed whitelists
  const handleAddPath = () => {
    if (!newPath.trim()) return;
    const pathToAdd = newPath.trim();
    
    if (config.allowed_paths.includes(pathToAdd)) {
      setStatusMessage({ type: 'error', text: 'Path is already in the allowed list.' });
      return;
    }

    setConfig(prev => ({
      ...prev,
      allowed_paths: [...prev.allowed_paths, pathToAdd]
    }));
    setNewPath('');
    setStatusMessage(null);
  };

  // Remove path from whitelist
  const handleRemovePath = (pathToRemove: string) => {
    setConfig(prev => ({
      ...prev,
      allowed_paths: prev.allowed_paths.filter(p => p !== pathToRemove)
    }));
    setStatusMessage(null);
  };

  // Determine warnings dynamically
  const getWarnings = () => {
    const warnings: string[] = [];
    const codeTools = config.agent_tools.code || [];
    const researchTools = config.agent_tools.research || [];
    const analysisTools = config.agent_tools.analysis || [];

    if (!codeTools.includes('file_operation')) {
      warnings.push("Code Agent: 'file_operation' is disabled. The agent will not be able to write or modify single files.");
    }
    if (!codeTools.includes('create_project')) {
      warnings.push("Code Agent: 'create_project' is disabled. The agent will not be able to bootstrap multi-file structures.");
    }
    if (!codeTools.includes('execute_code')) {
      warnings.push("Code Agent: 'execute_code' is disabled. The agent will be unable to run script test suites locally.");
    }
    if (!researchTools.includes('web_search')) {
      warnings.push("Research Agent: 'web_search' is disabled. The agent will have no active internet connection for web searches.");
    }
    if (!analysisTools.includes('file_operation')) {
      warnings.push("Analysis Agent: 'file_operation' is disabled. The agent will be unable to read workspace files to check for errors.");
    }
    return warnings;
  };

  const warningsList = getWarnings();

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <div className="w-12 h-12 border-2 border-ibm-blue border-t-transparent rounded-full animate-spin"></div>
        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Loading Configuration...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500 pb-20">
      
      {/* Dynamic Status Banner */}
      {statusMessage && (
        <div className={cn(
          "p-4 border flex items-start gap-3 animate-in fade-in slide-in-from-top-2 duration-300",
          statusMessage.type === 'success' 
            ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" 
            : "bg-destructive/10 border-destructive/30 text-destructive-foreground"
        )}>
          {statusMessage.type === 'success' ? (
            <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          )}
          <div>
            <div className="font-bold text-xs uppercase tracking-wide">
              {statusMessage.type === 'success' ? 'Operation Success' : 'Operation Failed'}
            </div>
            <div className="text-sm mt-0.5 font-light">{statusMessage.text}</div>
          </div>
        </div>
      )}

      {/* Main Settings Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        
        {/* Left Column: Tool Manager Grid */}
        <div className="lg:col-span-3 space-y-6">
          <Card className="carbon-card">
            <CardHeader className="pb-3 border-b border-border/30">
              <div className="flex justify-between items-center">
                <CardTitle className="text-sm font-semibold tracking-wider font-mono text-muted-foreground uppercase flex items-center gap-2">
                  <Settings className="w-4 h-4 text-ibm-blue" />
                  Tool Permissions Manager
                </CardTitle>
                <span className="text-[10px] font-mono bg-muted px-2 py-0.5 border">
                  ROLE CONTROLS
                </span>
              </div>
            </CardHeader>
            <CardContent className="pt-6 space-y-6">
              <p className="text-xs text-muted-foreground font-light leading-relaxed">
                Configure which tools are dynamically exposed to the multi-agent system. Disabling a tool prevents the designated agent from making tool calls for that specific capability.
              </p>

              {/* Code Agent Block */}
              <div className="border border-border/40 p-4 bg-muted/20 hover:border-border/80 transition-colors duration-300">
                <h3 className="font-bold text-xs uppercase tracking-wider font-mono text-ibm-blue mb-3 flex items-center justify-between">
                  <span>Code Agent Tools</span>
                  <span className="text-[9px] text-muted-foreground font-normal lowercase">({config.agent_tools.code?.length ?? 0} enabled)</span>
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {allTools.code.map(tool => {
                    const isChecked = config.agent_tools.code?.includes(tool);
                    return (
                      <button
                        key={tool}
                        onClick={() => handleToggleTool('code', tool)}
                        className={cn(
                          "flex items-center justify-between p-3 border text-left transition-all duration-200 group text-xs",
                          isChecked 
                            ? "border-ibm-blue/40 bg-ibm-blue/5 text-foreground hover:bg-ibm-blue/10" 
                            : "border-border/40 bg-card hover:bg-muted text-muted-foreground"
                        )}
                      >
                        <div className="font-mono">{tool}</div>
                        <div className={cn(
                          "w-4 h-4 border flex items-center justify-center transition-all",
                          isChecked 
                            ? "bg-ibm-blue border-ibm-blue text-white" 
                            : "border-muted-foreground group-hover:border-foreground"
                        )}>
                          {isChecked && <span className="text-[10px] font-bold">✓</span>}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Research Agent Block */}
              <div className="border border-border/40 p-4 bg-muted/20 hover:border-border/80 transition-colors duration-300">
                <h3 className="font-bold text-xs uppercase tracking-wider font-mono text-ibm-blue mb-3 flex items-center justify-between">
                  <span>Research Agent Tools</span>
                  <span className="text-[9px] text-muted-foreground font-normal lowercase">({config.agent_tools.research?.length ?? 0} enabled)</span>
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {allTools.research.map(tool => {
                    const isChecked = config.agent_tools.research?.includes(tool);
                    return (
                      <button
                        key={tool}
                        onClick={() => handleToggleTool('research', tool)}
                        className={cn(
                          "flex items-center justify-between p-3 border text-left transition-all duration-200 group text-xs",
                          isChecked 
                            ? "border-ibm-blue/40 bg-ibm-blue/5 text-foreground hover:bg-ibm-blue/10" 
                            : "border-border/40 bg-card hover:bg-muted text-muted-foreground"
                        )}
                      >
                        <div className="font-mono">{tool}</div>
                        <div className={cn(
                          "w-4 h-4 border flex items-center justify-center transition-all",
                          isChecked 
                            ? "bg-ibm-blue border-ibm-blue text-white" 
                            : "border-muted-foreground group-hover:border-foreground"
                        )}>
                          {isChecked && <span className="text-[10px] font-bold">✓</span>}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Analysis Agent Block */}
              <div className="border border-border/40 p-4 bg-muted/20 hover:border-border/80 transition-colors duration-300">
                <h3 className="font-bold text-xs uppercase tracking-wider font-mono text-ibm-blue mb-3 flex items-center justify-between">
                  <span>Analysis Agent Tools</span>
                  <span className="text-[9px] text-muted-foreground font-normal lowercase">({config.agent_tools.analysis?.length ?? 0} enabled)</span>
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {allTools.analysis.map(tool => {
                    const isChecked = config.agent_tools.analysis?.includes(tool);
                    return (
                      <button
                        key={tool}
                        onClick={() => handleToggleTool('analysis', tool)}
                        className={cn(
                          "flex items-center justify-between p-3 border text-left transition-all duration-200 group text-xs",
                          isChecked 
                            ? "border-ibm-blue/40 bg-ibm-blue/5 text-foreground hover:bg-ibm-blue/10" 
                            : "border-border/40 bg-card hover:bg-muted text-muted-foreground"
                        )}
                      >
                        <div className="font-mono">{tool}</div>
                        <div className={cn(
                          "w-4 h-4 border flex items-center justify-center transition-all",
                          isChecked 
                            ? "bg-ibm-blue border-ibm-blue text-white" 
                            : "border-muted-foreground group-hover:border-foreground"
                        )}>
                          {isChecked && <span className="text-[10px] font-bold">✓</span>}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

            </CardContent>
          </Card>
        </div>

        {/* Right Column: Whitelisted File Access Controller */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="carbon-card">
            <CardHeader className="pb-4 border-b border-border/30">
              <CardTitle className="text-base font-semibold tracking-wider font-mono text-muted-foreground uppercase flex items-center gap-2.5">
                <FolderCheck className="w-5 h-5 text-ibm-blue" />
                File Access Whitelist
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6 space-y-6">
              <p className="text-sm text-muted-foreground font-light leading-relaxed">
                Restrict the files and folders agents can read or write. If left empty, agents fallback to access the default workspace directory: <code className="bg-muted px-1.5 py-0.5 border text-xs font-mono break-all font-bold">D:\learning\code\website</code>.
              </p>

              {/* Current Allowed Paths Whitelist */}
              <div className="space-y-2">
                <label className="text-[11px] font-mono text-muted-foreground uppercase block font-bold">
                  Whitelisted Locations
                </label>
                
                {config.allowed_paths.length === 0 ? (
                  <div className="border border-dashed border-border/60 p-6 text-center bg-card">
                    <Info className="w-6 h-6 mx-auto text-muted-foreground opacity-60 mb-2" />
                    <p className="text-xs text-muted-foreground leading-normal font-light">
                      No paths whitelisted. Running under sandbox fallback to the default website workspace.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {config.allowed_paths.map(path => (
                      <div 
                        key={path}
                        className="flex items-center justify-between p-2.5 border border-border bg-card/60 hover:bg-muted text-sm transition-colors group"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          {path.includes('.') ? (
                            <File className="w-4 h-4 text-ibm-blue shrink-0" />
                          ) : (
                            <Folder className="w-4 h-4 text-ibm-blue shrink-0" />
                          )}
                          <span className="font-mono text-xs truncate" title={path}>{path}</span>
                        </div>
                        <button
                          onClick={() => handleRemovePath(path)}
                          className="text-muted-foreground hover:text-destructive p-1 transition-colors opacity-60 group-hover:opacity-100"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Add New Whitelist Path Input */}
              <div className="space-y-3 pt-3 border-t border-border/30">
                <label className="text-[11px] font-mono text-muted-foreground uppercase block font-bold">
                  Add Allowed Folder or File
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newPath}
                    onChange={(e) => setNewPath(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAddPath()}
                    placeholder="e.g. D:\learning\code\website\src"
                    className="flex-1 bg-background text-foreground border border-border px-4 py-3 text-sm font-mono focus:outline-none focus:border-ibm-blue transition-colors placeholder:text-muted-foreground/50"
                  />
                  <Button
                    onClick={handleAddPath}
                    variant="outline"
                    className="shrink-0 px-4 py-3 border hover:bg-muted font-bold text-sm"
                  >
                    <Plus className="w-5 h-5" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Configuration Actions */}
          <div className="flex flex-col sm:flex-row gap-4">
            <Button
              onClick={handleSave}
              disabled={saving}
              variant="carbon"
              className="flex-1 flex items-center justify-center gap-2.5 uppercase tracking-wider text-sm font-mono py-7 border"
            >
              <Save className={cn("w-5 h-5", saving && "animate-pulse")} />
              {saving ? 'Saving...' : 'Save Config'}
            </Button>
            <Button
              onClick={handleReset}
              variant="outline"
              className="flex-1 flex items-center justify-center gap-2.5 uppercase tracking-wider text-sm font-mono py-7 border"
            >
              <RotateCcw className="w-5 h-5" />
              Revert Changes
            </Button>
          </div>

          {/* Status Warnings Panel */}
          {warningsList.length > 0 && (
            <Card className="border-amber-500/20 bg-amber-500/5">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-mono text-amber-400 uppercase flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4" />
                  System Warnings ({warningsList.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {warningsList.map((warning, index) => (
                  <div key={index} className="flex gap-2 text-[10px] text-amber-300 font-light leading-normal">
                    <span className="text-amber-500 shrink-0 font-bold">•</span>
                    <span>{warning}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

        </div>

      </div>

    </div>
  );
};
