import axios from 'axios';
import { API_BASE } from './ollama';

export type ServiceState = 'healthy' | 'unavailable' | 'unhealthy' | 'stopped' | 'unknown';

export interface ServiceHealth {
  status: ServiceState;
  message?: string;
  url?: string;
  model_count?: number;
}

export interface ApplicationHealth {
  status: 'healthy' | 'limited' | 'unhealthy';
  timestamp: string;
  components: Record<'api' | 'database' | 'scheduler' | 'ollama', ServiceHealth>;
}

export async function getApplicationHealth(): Promise<ApplicationHealth> {
  const response = await axios.get<ApplicationHealth>(`${API_BASE}/health`, { timeout: 4000 });
  return response.data;
}
