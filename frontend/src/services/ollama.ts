import axios from 'axios';

const API_BASE = "http://localhost:8000";
axios.defaults.timeout = 300000; // 5-minute timeout for agent execution calls

export interface Agent {
  id: string;
  name: string;
  persona: string;
  system_prompt: string;
  tools: string[];
  base_model: string;
  training_data?: Array<{q: string, a: string}>;
}

export interface LeaderboardEntry {
  id: string;
  name: string;
  avg_ttft: number;
  avg_total: number;
  calls: number;
}

export interface OllamaModel {
  name: string;
  details: any;
}

export const OllamaService = {
  async getAgents(): Promise<Agent[]> {
    const response = await axios.get(`${API_BASE}/agents`);
    return response.data;
  },

  async createAgent(agent: Agent): Promise<Agent> {
    const response = await axios.post(`${API_BASE}/agents`, agent);
    return response.data;
  },

  async getLeaderboard(): Promise<LeaderboardEntry[]> {
    const response = await axios.get(`${API_BASE}/leaderboard`);
    return response.data;
  },

  async chat(agentId: string, prompt: string): Promise<string> {
    const response = await axios.post(`${API_BASE}/chat/${agentId}?prompt=${encodeURIComponent(prompt)}`);
    return response.data.response;
  },

  async getModels(): Promise<OllamaModel[]> {
    try {
      const response = await axios.get(`${API_BASE}/ollama/models`);
      return response.data;
    } catch (err) {
      console.error("Failed to fetch Ollama models", err);
      return [];
    }
  },

  async trainAgent(agentId: string, data: Array<{q: string, a: string}>, hyperparams?: { epochs: number; batch_size: number; learning_rate: number }): Promise<any> {
    const payload = {
      data,
      epochs: hyperparams?.epochs ?? 3,
      batch_size: hyperparams?.batch_size ?? 8,
      learning_rate: hyperparams?.learning_rate ?? 0.00002
    };
    const response = await axios.post(`${API_BASE}/agents/${agentId}/train`, payload);
    return response.data;
  },

  async getMultiAgents(): Promise<any> {
    const response = await axios.get(`${API_BASE}/api/multi-agent/agents/available`);
    return response.data;
  },

  async getMultiAgentHealth(): Promise<any> {
    const response = await axios.get(`${API_BASE}/api/multi-agent/agents/health`);
    return response.data;
  },

  async chatDirectAgent(agentType: string, task: string, context?: any): Promise<any> {
    const response = await axios.post(`${API_BASE}/api/multi-agent/agents/direct/${agentType}`, {
      agent_type: agentType,
      task,
      context
    });
    return response.data;
  },

  async chatMultiAgentStream(
    prompt: string,
    onEvent: (event: { type: string; agent?: string; content?: string; done: boolean }) => void,
    onError: (err: any) => void,
    context?: any
  ): Promise<AbortController> {
    const controller = new AbortController();
    
    fetch(`${API_BASE}/api/multi-agent/agents/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        prompt,
        context,
        stream: true
      }),
      signal: controller.signal
    })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6).trim();
              if (dataStr === '') continue;

              try {
                const data = JSON.parse(dataStr);
                onEvent(data);
              } catch (e) {
                console.error('Error parsing SSE data:', e);
              }
            }
          }
        }
      } catch (error: any) {
        if (error.name !== 'AbortError') {
          onError(error);
        }
      } finally {
        reader.releaseLock();
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err);
      }
    });

    return controller;
  },

  async getMultiAgentConfig(): Promise<any> {
    const response = await axios.get(`${API_BASE}/api/multi-agent/config`);
    return response.data;
  },

  async updateMultiAgentConfig(config: any): Promise<any> {
    const response = await axios.post(`${API_BASE}/api/multi-agent/config`, config);
    return response.data;
  },

  async stopMultiAgent(sessionId: string = 'default'): Promise<any> {
    const response = await axios.post(`${API_BASE}/api/multi-agent/agents/stop?session_id=${sessionId}`);
    return response.data;
  },

  async respondToPermission(sessionId: string, path: string, granted: boolean): Promise<any> {
    const response = await axios.post(`${API_BASE}/api/multi-agent/permission/respond`, {
      session_id: sessionId,
      path,
      granted
    });
    return response.data;
  },

  async getWorkspaceRoots(): Promise<any> {
    const response = await axios.get(`${API_BASE}/api/multi-agent/workspace/roots`);
    return response.data;
  },

  async getWorkspaceList(path?: string): Promise<any> {
    const url = path 
      ? `${API_BASE}/api/multi-agent/workspace/list?path=${encodeURIComponent(path)}`
      : `${API_BASE}/api/multi-agent/workspace/list`;
    const response = await axios.get(url);
    return response.data;
  },

  async getWorkspaceFile(path: string): Promise<any> {
    const response = await axios.get(`${API_BASE}/api/multi-agent/workspace/file?path=${encodeURIComponent(path)}`);
    return response.data;
  },

  async writeWorkspaceFile(path: string, content: string): Promise<any> {
    const response = await axios.post(`${API_BASE}/api/multi-agent/workspace/file`, {
      path,
      content
    });
    return response.data;
  },

  // --- Hubs CRUD ---
  async getHubs(): Promise<any[]> {
    const response = await axios.get(`${API_BASE}/api/multi-agent/hubs`);
    return response.data;
  },
  async createHub(hub: { id: string; name: string; description?: string }): Promise<any> {
    const response = await axios.post(`${API_BASE}/api/multi-agent/hubs`, hub);
    return response.data;
  },
  async deleteHub(hubId: string): Promise<any> {
    const response = await axios.delete(`${API_BASE}/api/multi-agent/hubs/${hubId}`);
    return response.data;
  },

  // --- Custom Agents CRUD ---
  async getCustomAgents(hubId?: string): Promise<any[]> {
    const url = hubId 
      ? `${API_BASE}/api/multi-agent/custom-agents?hub_id=${encodeURIComponent(hubId)}`
      : `${API_BASE}/api/multi-agent/custom-agents`;
    const response = await axios.get(url);
    return response.data;
  },
  async createCustomAgent(agent: any): Promise<any> {
    const response = await axios.post(`${API_BASE}/api/multi-agent/custom-agents`, agent);
    return response.data;
  },
  async deleteCustomAgent(agentId: string): Promise<any> {
    const response = await axios.delete(`${API_BASE}/api/multi-agent/custom-agents/${agentId}`);
    return response.data;
  },

  // --- MCP Servers CRUD ---
  async getMcpServers(): Promise<any[]> {
    const response = await axios.get(`${API_BASE}/api/multi-agent/mcp-servers`);
    return response.data;
  },
  async createMcpServer(server: any): Promise<any> {
    const response = await axios.post(`${API_BASE}/api/multi-agent/mcp-servers`, server);
    return response.data;
  },
  async deleteMcpServer(mcpId: string): Promise<any> {
    const response = await axios.delete(`${API_BASE}/api/multi-agent/mcp-servers/${mcpId}`);
    return response.data;
  },

  // --- Workflows CRUD ---
  async getWorkflows(): Promise<any[]> {
    const response = await axios.get(`${API_BASE}/api/multi-agent/workflows`);
    return response.data;
  },
  async createWorkflow(workflow: any): Promise<any> {
    const response = await axios.post(`${API_BASE}/api/multi-agent/workflows`, workflow);
    return response.data;
  },
  async deleteWorkflow(workflowId: string): Promise<any> {
    const response = await axios.delete(`${API_BASE}/api/multi-agent/workflows/${workflowId}`);
    return response.data;
  },

  // --- Token usage stats ---
  async getTokenStats(): Promise<any> {
    const response = await axios.get(`${API_BASE}/api/multi-agent/stats/tokens`);
    return response.data;
  },

  // --- Local Models Tags ---
  async getLocalModels(): Promise<any> {
    const response = await axios.get(`${API_BASE}/api/multi-agent/models/local`);
    return response.data;
  },

  // --- Pull Model Progress Stream ---
  async pullModelStream(
    modelName: string,
    onProgress: (status: any) => void,
    onError: (err: any) => void
  ): Promise<AbortController> {
    const controller = new AbortController();
    fetch(`${API_BASE}/api/multi-agent/models/pull?model_name=${encodeURIComponent(modelName)}`, {
      method: 'POST',
      signal: controller.signal
    })
    .then(async (response) => {
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      if (!response.body) throw new Error('No response body');
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6).trim();
              if (dataStr === '') continue;
              try {
                const data = JSON.parse(dataStr);
                onProgress(data);
              } catch (e) {
                console.error('Error parsing SSE data:', e);
              }
            }
          }
        }
      } catch (err) {
        onError(err);
      } finally {
        reader.releaseLock();
      }
    })
    .catch(onError);
    
    return controller;
  },

  async getDailyTokenStats(): Promise<any> {
    const response = await axios.get(`${API_BASE}/api/multi-agent/stats/daily`);
    return response.data;
  },

  async createWorkspaceDirectory(path: string, name: string): Promise<any> {
    const response = await axios.post(`${API_BASE}/api/multi-agent/workspace/directory`, {
      path,
      name
    });
    return response.data;
  },

  async clearChat(agentId: string): Promise<any> {
    const response = await axios.post(`${API_BASE}/chat/${agentId}/clear`);
    return response.data;
  },

  // --- Scheduled Tasks (Loops) CRUD ---
  async getScheduledTasks(): Promise<any> {
    const response = await axios.get(`${API_BASE}/api/multi-agent/scheduler/tasks`);
    return response.data;
  },

  async createScheduledTask(task: {
    name: string;
    prompt: string;
    interval_minutes?: number | null;
    delay_minutes?: number;
  }): Promise<any> {
    const response = await axios.post(`${API_BASE}/api/multi-agent/scheduler/tasks`, task);
    return response.data;
  },

  async deleteScheduledTask(taskId: string): Promise<any> {
    const response = await axios.delete(`${API_BASE}/api/multi-agent/scheduler/tasks/${taskId}`);
    return response.data;
  },

  async toggleScheduledTask(taskId: string): Promise<any> {
    const response = await axios.post(`${API_BASE}/api/multi-agent/scheduler/tasks/${taskId}/toggle`);
    return response.data;
  },

  async runScheduledTaskNow(taskId: string): Promise<any> {
    const response = await axios.post(`${API_BASE}/api/multi-agent/scheduler/tasks/${taskId}/run`);
    return response.data;
  },

  // --- Command Permission ---
  async respondToCommandPermission(sessionId: string, command: string, granted: boolean): Promise<any> {
    const response = await axios.post(`${API_BASE}/api/multi-agent/permission/command/respond`, {
      session_id: sessionId,
      command,
      granted
    });
    return response.data;
  },

  // --- Plan Approval ---
  async respondToPlanApproval(sessionId: string, planPath: string, planContent: string, approved: boolean): Promise<any> {
    const response = await axios.post(`${API_BASE}/api/multi-agent/permission/plan/respond`, {
      session_id: sessionId,
      plan_path: planPath,
      plan_content: planContent,
      approved
    });
    return response.data;
  },

  // ====== Agent Mode ======
  async agentModeStatus(): Promise<{status: string; claude_code_available: boolean; ollama_model: string; mode: string}> {
    const response = await axios.get(`${API_BASE}/api/multi-agent/agent-mode/status`);
    return response.data;
  },

  async agentModeChatStream(
    prompt: string,
    cwd: string,
    onEvent: (event: any) => void,
    onError: (err: any) => void,
    filePath?: string,
    fileContent?: string,
    sessionId?: string
  ): Promise<AbortController> {
    const controller = new AbortController();
    fetch(`${API_BASE}/api/multi-agent/agent-mode/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        cwd,
        file_path: filePath || null,
        file_content: fileContent || null,
        session_id: sessionId || 'default'
      }),
      signal: controller.signal
    })
    .then(async (response) => {
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      if (!response.body) throw new Error('No response body');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6).trim();
              if (dataStr === '') continue;
              try {
                const data = JSON.parse(dataStr);
                onEvent(data);
              } catch (e) { console.error('Error parsing SSE:', e); }
            }
          }
        }
      } catch (error: any) {
        if (error.name !== 'AbortError') onError(error);
      } finally { reader.releaseLock(); }
    })
    .catch((err) => { if (err.name !== 'AbortError') onError(err); });
    return controller;
  },

  async agentModeQuickActionStream(
    action: string,
    filePath: string,
    fileContent: string,
    cwd: string,
    onEvent: (event: any) => void,
    onError: (err: any) => void,
    sessionId?: string
  ): Promise<AbortController> {
    const controller = new AbortController();
    fetch(`${API_BASE}/api/multi-agent/agent-mode/quick-action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action,
        file_path: filePath,
        file_content: fileContent,
        cwd,
        session_id: sessionId || 'default'
      }),
      signal: controller.signal
    })
    .then(async (response) => {
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      if (!response.body) throw new Error('No response body');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6).trim();
              if (dataStr === '') continue;
              try {
                const data = JSON.parse(dataStr);
                onEvent(data);
              } catch (e) { console.error('Error parsing SSE:', e); }
            }
          }
        }
      } catch (error: any) {
        if (error.name !== 'AbortError') onError(error);
      } finally { reader.releaseLock(); }
    })
    .catch((err) => { if (err.name !== 'AbortError') onError(err); });
    return controller;
  },

  async getAgentModeHistory(sessionId: string = 'default'): Promise<any> {
    const response = await axios.get(`${API_BASE}/api/multi-agent/agent-mode/history?session_id=${sessionId}`);
    return response.data;
  },

  async clearAgentModeHistory(sessionId: string = 'default'): Promise<any> {
    const response = await axios.delete(`${API_BASE}/api/multi-agent/agent-mode/history?session_id=${sessionId}`);
    return response.data;
  },

  async transcribeVoice(audioBlob: Blob): Promise<string> {
    const formData = new FormData();
    formData.append('file', audioBlob, 'audio.wav');
    const response = await axios.post(`${API_BASE}/api/multi-agent/agents/voice/transcribe`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    if (response.data.status === 'error') {
      throw new Error(response.data.message || 'Voice transcription failed');
    }
    return response.data.text ?? '';
  }
};


