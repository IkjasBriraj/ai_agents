import axios from 'axios';
import { API_BASE } from './ollama';

export interface User {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  role: string;
  created_at?: string;
  last_login?: string;
  storage_type: 'mongodb' | 'sqlite';
}

export interface AuthResponse {
  status: string;
  token: string;
  user: User;
  mongo_connected: boolean;
}

export interface MongoStatus {
  connected: boolean;
  status: string;
  url: string;
  database: string;
  latency_ms: number;
  collections: string[];
  counts: Record<string, number>;
  error?: string;
  message?: string;
}

const TOKEN_KEY = 'senior_agent_auth_token';
const USER_KEY = 'senior_agent_user_profile';

export const authService = {
  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },

  saveToken(token: string) {
    localStorage.setItem(TOKEN_KEY, token);
  },

  removeToken() {
    localStorage.removeItem(TOKEN_KEY);
  },

  getStoredUser(): User | null {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as User;
    } catch {
      return null;
    }
  },

  saveStoredUser(user: User) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },

  removeStoredUser() {
    localStorage.removeItem(USER_KEY);
  },

  async register(data: {
    username: string;
    email: string;
    password: string;
    full_name?: string;
    role?: string;
  }): Promise<AuthResponse> {
    const res = await axios.post<AuthResponse>(`${API_BASE}/api/auth/register`, data);
    if (res.data.token) {
      this.saveToken(res.data.token);
      this.saveStoredUser(res.data.user);
    }
    return res.data;
  },

  async login(data: { username_or_email: string; password: string }): Promise<AuthResponse> {
    const res = await axios.post<AuthResponse>(`${API_BASE}/api/auth/login`, data);
    if (res.data.token) {
      this.saveToken(res.data.token);
      this.saveStoredUser(res.data.user);
    }
    return res.data;
  },

  async loginAsDemo(): Promise<AuthResponse> {
    const res = await axios.post<AuthResponse>(`${API_BASE}/api/auth/demo`);
    if (res.data.token) {
      this.saveToken(res.data.token);
      this.saveStoredUser(res.data.user);
    }
    return res.data;
  },

  async getMe(): Promise<User | null> {
    const token = this.getToken();
    if (!token) return null;
    try {
      const res = await axios.get<User>(`${API_BASE}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      this.saveStoredUser(res.data);
      return res.data;
    } catch {
      this.removeToken();
      this.removeStoredUser();
      return null;
    }
  },

  logout() {
    this.removeToken();
    this.removeStoredUser();
  },

  async getMongoStatus(): Promise<MongoStatus> {
    const res = await axios.get<MongoStatus>(`${API_BASE}/api/database/status`);
    return res.data;
  },

  async connectMongo(url: string, database?: string): Promise<MongoStatus> {
    const res = await axios.post<MongoStatus>(`${API_BASE}/api/database/connect`, {
      url,
      database: database || 'senior_agent'
    });
    return res.data;
  }
};
