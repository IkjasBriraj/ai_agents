import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authService, type User, type MongoStatus } from '@/services/auth';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  mongoStatus: MongoStatus | null;
  isMongoLoading: boolean;
  login: (credentials: { username_or_email: string; password: string }) => Promise<void>;
  register: (data: {
    username: string;
    email: string;
    password: string;
    full_name?: string;
    role?: string;
  }) => Promise<void>;
  loginAsDemo: () => Promise<void>;
  logout: () => void;
  refreshMongoStatus: () => Promise<void>;
  connectMongo: (url: string, database?: string) => Promise<MongoStatus>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => authService.getStoredUser());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [mongoStatus, setMongoStatus] = useState<MongoStatus | null>(null);
  const [isMongoLoading, setIsMongoLoading] = useState<boolean>(false);

  const refreshMongoStatus = useCallback(async () => {
    setIsMongoLoading(true);
    try {
      const status = await authService.getMongoStatus();
      setMongoStatus(status);
    } catch (err) {
      console.warn('Failed to query MongoDB status:', err);
    } finally {
      setIsMongoLoading(false);
    }
  }, []);

  const initAuth = useCallback(async () => {
    setIsLoading(true);
    try {
      const token = authService.getToken();
      if (token) {
        const me = await authService.getMe();
        setUser(me);
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    initAuth();
    refreshMongoStatus();
  }, [initAuth, refreshMongoStatus]);

  const login = async (credentials: { username_or_email: string; password: string }) => {
    const res = await authService.login(credentials);
    setUser(res.user);
    refreshMongoStatus();
  };

  const register = async (data: {
    username: string;
    email: string;
    password: string;
    full_name?: string;
    role?: string;
  }) => {
    const res = await authService.register(data);
    setUser(res.user);
    refreshMongoStatus();
  };

  const loginAsDemo = async () => {
    const res = await authService.loginAsDemo();
    setUser(res.user);
    refreshMongoStatus();
  };

  const logout = () => {
    authService.logout();
    setUser(null);
  };

  const connectMongo = async (url: string, database?: string) => {
    setIsMongoLoading(true);
    try {
      const status = await authService.connectMongo(url, database);
      setMongoStatus(status);
      return status;
    } finally {
      setIsMongoLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        mongoStatus,
        isMongoLoading,
        login,
        register,
        loginAsDemo,
        logout,
        refreshMongoStatus,
        connectMongo,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
