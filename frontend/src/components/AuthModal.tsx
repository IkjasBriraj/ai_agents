import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import {
  X,
  Lock,
  LogIn,
  UserPlus,
  Zap,
  RefreshCw,
  AlertCircle,
  Eye,
  EyeOff,
  Mail,
  User,
  Sparkles,
  ArrowRight
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose }) => {
  const { login, register, loginAsDemo } = useAuth();
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [showPassword, setShowPassword] = useState(false);

  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [password, setPassword] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regFullName, setRegFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login({ username_or_email: usernameOrEmail.trim(), password });
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid username or password.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await register({
        username: regUsername.trim(),
        email: regEmail.trim(),
        password: regPassword,
        full_name: regFullName.trim() || regUsername.trim(),
      });
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed. Username or email may already exist.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDemo = async () => {
    setError(null);
    setIsSubmitting(true);
    try {
      await loginAsDemo();
      onClose();
    } catch (err) {
      setError('Demo login failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-md rounded-3xl border border-border/80 bg-card/95 p-8 shadow-2xl space-y-6 backdrop-blur-xl">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 text-muted-foreground hover:text-foreground rounded-full hover:bg-muted transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="text-center space-y-1.5">
          <div className="inline-flex p-3 rounded-2xl bg-ibm-blue/10 text-ibm-blue mb-1">
            <Lock className="w-6 h-6" />
          </div>
          <h3 className="text-2xl font-light tracking-tight text-foreground">
            {authMode === 'login' ? 'Sign In to SeniorAgent' : 'Create an Account'}
          </h3>
          <p className="text-xs text-muted-foreground">
            {authMode === 'login'
              ? 'Access your private agents and MongoDB workspace.'
              : 'Register to store workflows and memories in MongoDB.'}
          </p>
        </div>

        {/* 1-Click Guest Demo Button */}
        <button
          type="button"
          onClick={handleDemo}
          disabled={isSubmitting}
          className="w-full p-2.5 rounded-xl bg-gradient-to-r from-purple-900/30 to-ibm-blue/30 border border-indigo-500/30 hover:border-indigo-500/60 text-foreground text-xs font-medium flex items-center justify-between transition-all group cursor-pointer"
        >
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" />
            <span className="font-semibold text-foreground group-hover:text-amber-300">
              1-Click Instant Guest Access
            </span>
          </div>
          <ArrowRight className="w-3.5 h-3.5 text-muted-foreground group-hover:translate-x-0.5 transition-all" />
        </button>

        <div className="relative flex items-center justify-center">
          <div className="border-t border-border w-full" />
          <span className="bg-card px-3 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
            Or continue with credentials
          </span>
          <div className="border-t border-border w-full" />
        </div>

        {/* Tab Selector */}
        <div className="flex rounded-xl bg-muted p-1 border border-border">
          <button
            type="button"
            onClick={() => {
              setAuthMode('login');
              setError(null);
            }}
            className={cn(
              'flex-1 py-1.5 text-xs font-mono uppercase tracking-wider rounded-lg transition-all flex items-center justify-center gap-1.5 cursor-pointer',
              authMode === 'login' ? 'bg-card text-foreground shadow-sm font-semibold' : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>Sign In</span>
          </button>
          <button
            type="button"
            onClick={() => {
              setAuthMode('register');
              setError(null);
            }}
            className={cn(
              'flex-1 py-1.5 text-xs font-mono uppercase tracking-wider rounded-lg transition-all flex items-center justify-center gap-1.5 cursor-pointer',
              authMode === 'register' ? 'bg-card text-foreground shadow-sm font-semibold' : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>Register</span>
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {authMode === 'login' ? (
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-mono text-muted-foreground flex items-center gap-1">
                <User className="w-3 h-3" />
                <span>Username or Email</span>
              </label>
              <input
                type="text"
                required
                value={usernameOrEmail}
                onChange={(e) => setUsernameOrEmail(e.target.value)}
                placeholder="e.g. john or john@example.com"
                className="w-full px-3.5 py-2.5 rounded-xl bg-background border border-border text-sm focus:outline-none focus:border-ibm-blue focus:ring-2 focus:ring-ibm-blue/20 transition-all font-sans"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-mono text-muted-foreground flex items-center gap-1">
                <Lock className="w-3 h-3" />
                <span>Password</span>
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3.5 py-2.5 pr-10 rounded-xl bg-background border border-border text-sm focus:outline-none focus:border-ibm-blue focus:ring-2 focus:ring-ibm-blue/20 transition-all font-sans"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 bg-ibm-blue text-white rounded-xl text-sm font-medium hover:bg-ibm-blue/90 shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
            >
              {isSubmitting ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <ArrowRight className="w-4 h-4" />
              )}
              <span>Sign In</span>
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegister} className="space-y-3">
            <div className="space-y-1">
              <label className="text-xs font-mono text-muted-foreground flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                <span>Full Name</span>
              </label>
              <input
                type="text"
                value={regFullName}
                onChange={(e) => setRegFullName(e.target.value)}
                placeholder="e.g. Eleanor Vance"
                className="w-full px-3.5 py-2 rounded-xl bg-background border border-border text-sm focus:outline-none focus:border-ibm-blue focus:ring-2 focus:ring-ibm-blue/20 transition-all"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-mono text-muted-foreground flex items-center gap-1">
                <User className="w-3 h-3" />
                <span>Username</span>
              </label>
              <input
                type="text"
                required
                value={regUsername}
                onChange={(e) => setRegUsername(e.target.value)}
                placeholder="eleanor"
                className="w-full px-3.5 py-2 rounded-xl bg-background border border-border text-sm focus:outline-none focus:border-ibm-blue focus:ring-2 focus:ring-ibm-blue/20 transition-all"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-mono text-muted-foreground flex items-center gap-1">
                <Mail className="w-3 h-3" />
                <span>Email</span>
              </label>
              <input
                type="email"
                required
                value={regEmail}
                onChange={(e) => setRegEmail(e.target.value)}
                placeholder="eleanor@example.com"
                className="w-full px-3.5 py-2 rounded-xl bg-background border border-border text-sm focus:outline-none focus:border-ibm-blue focus:ring-2 focus:ring-ibm-blue/20 transition-all"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-mono text-muted-foreground flex items-center gap-1">
                <Lock className="w-3 h-3" />
                <span>Password</span>
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3.5 py-2 pr-10 rounded-xl bg-background border border-border text-sm focus:outline-none focus:border-ibm-blue focus:ring-2 focus:ring-ibm-blue/20 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 bg-ibm-blue text-white rounded-xl text-sm font-medium hover:bg-ibm-blue/90 shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 mt-1"
            >
              {isSubmitting ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <ArrowRight className="w-4 h-4" />
              )}
              <span>Create Account</span>
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
