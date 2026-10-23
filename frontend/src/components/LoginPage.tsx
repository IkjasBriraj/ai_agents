import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import {
  Lock,
  Mail,
  User,
  Eye,
  EyeOff,
  Zap,
  ShieldCheck,
  Database,
  ArrowRight,
  Sparkles,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Cpu,
  Layers,
  Compass
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface LoginPageProps {
  onSuccess?: () => void;
  onNavigateLanding?: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onSuccess, onNavigateLanding }) => {
  const {
    user,
    isAuthenticated,
    login,
    register,
    loginAsDemo,
    logout,
    mongoStatus,
    isMongoLoading,
    connectMongo
  } = useAuth();

  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);

  // Form Fields
  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [password, setPassword] = useState('');
  const [regFullName, setRegFullName] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');

  // UI States
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // MongoDB Drawer toggle
  const [showMongoDrawer, setShowMongoDrawer] = useState(false);
  const [mongoInputUrl, setMongoInputUrl] = useState(mongoStatus?.url || 'mongodb://localhost:27017/senior_agent');
  const [mongoInputDb, setMongoInputDb] = useState('senior_agent');
  const [mongoFeedback, setMongoFeedback] = useState<string | null>(null);

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    if (!usernameOrEmail.trim() || !password) {
      setErrorMessage('Please enter your username/email and password.');
      return;
    }

    setIsSubmitting(true);
    try {
      await login({ username_or_email: usernameOrEmail.trim(), password });
      setSuccessMessage('Authentication successful! Loading workspace...');
      setTimeout(() => {
        if (onSuccess) onSuccess();
      }, 500);
    } catch (err: any) {
      setErrorMessage(
        err.response?.data?.detail || 'Invalid credentials. Please verify your login details.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    if (!regUsername.trim() || !regEmail.trim() || !regPassword) {
      setErrorMessage('Please fill in all required fields.');
      return;
    }

    if (regPassword.length < 4) {
      setErrorMessage('Password must be at least 4 characters.');
      return;
    }

    setIsSubmitting(true);
    try {
      await register({
        username: regUsername.trim(),
        email: regEmail.trim(),
        password: regPassword,
        full_name: regFullName.trim() || regUsername.trim(),
      });
      setSuccessMessage('Account created and saved to MongoDB! Loading workspace...');
      setTimeout(() => {
        if (onSuccess) onSuccess();
      }, 600);
    } catch (err: any) {
      setErrorMessage(
        err.response?.data?.detail || 'Registration failed. Username or email may already be taken.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDemoLogin = async () => {
    setErrorMessage(null);
    setSuccessMessage(null);
    setIsSubmitting(true);
    try {
      await loginAsDemo();
      setSuccessMessage('Guest Researcher session initialized!');
      setTimeout(() => {
        if (onSuccess) onSuccess();
      }, 400);
    } catch (err) {
      setErrorMessage('Failed to initialize demo session. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConnectMongo = async (e: React.FormEvent) => {
    e.preventDefault();
    setMongoFeedback(null);
    try {
      const res = await connectMongo(mongoInputUrl, mongoInputDb);
      if (res.connected) {
        setMongoFeedback(`Connected successfully! Ping: ${res.latency_ms}ms`);
      } else {
        setMongoFeedback(`Connection test: ${res.message || res.error || 'Server offline'}`);
      }
    } catch (err: any) {
      setMongoFeedback(err.response?.data?.detail || 'Failed to update MongoDB URL');
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto my-4 animate-in fade-in zoom-in-95 duration-500">
      {/* Outer Card with Glassmorphism and Border Glow */}
      <div className="relative overflow-hidden rounded-3xl border border-border/80 bg-card/90 shadow-2xl backdrop-blur-xl grid grid-cols-1 lg:grid-cols-12 min-h-[640px]">
        {/* Glow Spheres */}
        <div className="absolute -top-32 -left-32 w-80 h-80 rounded-full bg-ibm-blue/15 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-32 -right-32 w-80 h-80 rounded-full bg-purple-600/15 blur-3xl pointer-events-none" />

        {/* LEFT COLUMN: Visual Branding & Value Proposition (5 Cols) */}
        <div className="lg:col-span-5 p-8 lg:p-12 flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-border/80 bg-gradient-to-br from-muted/50 via-background/40 to-muted/20 relative">
          <div className="space-y-6 relative z-10">
            {/* Top Badge */}
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-ibm-blue/10 border border-ibm-blue/20 text-ibm-blue">
                <Cpu className="w-6 h-6" />
              </div>
              <div>
                <div className="text-xs font-mono tracking-widest uppercase text-ibm-blue font-semibold">
                  SeniorAgent OS
                </div>
                <div className="text-[11px] text-muted-foreground font-mono">
                  Local-First Intelligence
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <h2 className="text-3xl font-light tracking-tight text-foreground">
                Welcome to your <br />
                <span className="font-semibold text-ibm-blue">Agentic Operating System</span>
              </h2>
              <p className="text-sm text-muted-foreground font-light leading-relaxed">
                Connect to your private local agents, orchestrate autonomous LangGraph workflows, and persist complex memory states directly inside MongoDB.
              </p>
            </div>

            {/* Feature Bullets */}
            <div className="space-y-3 pt-2">
              <div className="flex items-start gap-3 p-3 rounded-xl bg-card/60 border border-border/60">
                <ShieldCheck className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-foreground">100% Local Privacy</div>
                  <div className="text-[11px] text-muted-foreground">
                    Zero telemetry. Prompts, documents, and transcripts never leave your machine.
                  </div>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 rounded-xl bg-card/60 border border-border/60">
                <Database className="w-5 h-5 text-cyan-400 flex-shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-foreground">MongoDB Document Engine</div>
                  <div className="text-[11px] text-muted-foreground">
                    High-throughput storage for multi-agent histories, loops, and custom teams.
                  </div>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 rounded-xl bg-card/60 border border-border/60">
                <Layers className="w-5 h-5 text-purple-400 flex-shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-foreground">LangGraph Multi-Agent Teams</div>
                  <div className="text-[11px] text-muted-foreground">
                    Coordinated Code, Research, and Analysis agents working in concert.
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Diagnostics Card on Left Panel */}
          <div className="mt-8 pt-6 border-t border-border/80 space-y-3 relative z-10">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "w-2 h-2 rounded-full",
                    mongoStatus?.connected ? "bg-emerald-500 animate-pulse" : "bg-amber-500"
                  )}
                />
                <span className="text-xs font-mono font-medium text-foreground">
                  {mongoStatus?.connected ? "MongoDB Online" : "MongoDB Standby (Local Fallback)"}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setShowMongoDrawer(!showMongoDrawer)}
                className="text-[11px] font-mono text-ibm-blue hover:underline cursor-pointer"
              >
                {showMongoDrawer ? "Close" : "Configure URI"}
              </button>
            </div>

            {/* Expandable MongoDB URI Quick Config */}
            {showMongoDrawer && (
              <form onSubmit={handleConnectMongo} className="space-y-2 pt-2 animate-in fade-in">
                <input
                  type="text"
                  value={mongoInputUrl}
                  onChange={(e) => setMongoInputUrl(e.target.value)}
                  placeholder="mongodb://localhost:27017 or Atlas URI"
                  className="w-full px-2.5 py-1.5 rounded-lg bg-background border border-border text-xs font-mono focus:outline-none focus:border-ibm-blue"
                />
                <input
                  type="text"
                  value={mongoInputDb}
                  onChange={(e) => setMongoInputDb(e.target.value)}
                  placeholder="Database name (default: senior_agent)"
                  className="w-full px-2.5 py-1.5 rounded-lg bg-background border border-border text-xs font-mono focus:outline-none focus:border-ibm-blue"
                />
                <div className="flex items-center justify-between gap-2">
                  <button
                    type="submit"
                    disabled={isMongoLoading}
                    className="px-3 py-1 bg-ibm-blue text-white rounded text-[10px] font-mono uppercase tracking-wider hover:bg-ibm-blue/90"
                  >
                    {isMongoLoading ? "Testing..." : "Test Connection"}
                  </button>
                  {mongoFeedback && (
                    <span className="text-[10px] text-muted-foreground truncate">{mongoFeedback}</span>
                  )}
                </div>
              </form>
            )}

            {onNavigateLanding && (
              <button
                type="button"
                onClick={onNavigateLanding}
                className="w-full flex items-center justify-center gap-2 text-xs text-muted-foreground hover:text-foreground font-mono transition-colors pt-2 cursor-pointer"
              >
                <Compass className="w-3.5 h-3.5" />
                <span>Read "Why Choose SeniorAgent" Full Guide</span>
              </button>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: Interactive Login & Registration Form (7 Cols) */}
        <div className="lg:col-span-7 p-8 lg:p-12 flex flex-col justify-center bg-card">
          {isAuthenticated ? (
            /* Already Authenticated State */
            <div className="max-w-md mx-auto w-full space-y-6 text-center animate-in fade-in">
              <div className="w-16 h-16 rounded-full bg-ibm-blue/10 text-ibm-blue flex items-center justify-center mx-auto ring-8 ring-ibm-blue/5">
                <CheckCircle2 className="w-8 h-8" />
              </div>

              <div className="space-y-1">
                <h3 className="text-2xl font-light text-foreground">You are signed in</h3>
                <p className="text-xs text-muted-foreground">
                  Current active session authenticated via {user?.storage_type === 'mongodb' ? 'MongoDB' : 'Local Storage'}.
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-muted/50 border border-border text-left space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-muted-foreground">Full Name:</span>
                  <span className="text-xs font-medium text-foreground">{user?.full_name}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-muted-foreground">Username:</span>
                  <span className="text-xs font-mono text-foreground">@{user?.username}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-muted-foreground">Email:</span>
                  <span className="text-xs font-mono text-foreground">{user?.email}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-muted-foreground">Role:</span>
                  <span className="text-xs font-mono uppercase text-ibm-blue font-semibold">{user?.role}</span>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-3 pt-2">
                {onSuccess && (
                  <button
                    type="button"
                    onClick={onSuccess}
                    className="flex-1 py-3 bg-ibm-blue text-white rounded-xl font-medium flex items-center justify-center gap-2 shadow-lg shadow-ibm-blue/20 hover:bg-ibm-blue/90 transition-all cursor-pointer"
                  >
                    <span>Enter Agentic OS</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={logout}
                  className="px-6 py-3 border border-border text-muted-foreground hover:text-red-500 rounded-xl text-xs font-mono uppercase tracking-wider transition-colors cursor-pointer"
                >
                  Sign Out
                </button>
              </div>
            </div>
          ) : (
            /* Unauthenticated Login / Register Form */
            <div className="max-w-md mx-auto w-full space-y-6">
              {/* Mode Toggle Pills */}
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-2xl font-light text-foreground">
                    {mode === 'login' ? 'Sign In' : 'Create Account'}
                  </h3>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {mode === 'login'
                      ? 'Access your private local agent workflows.'
                      : 'Join and persist your multi-agent states in MongoDB.'}
                  </p>
                </div>

                <div className="flex rounded-xl bg-muted p-1 border border-border">
                  <button
                    type="button"
                    onClick={() => {
                      setMode('login');
                      setErrorMessage(null);
                    }}
                    className={cn(
                      "px-3.5 py-1.5 text-xs font-mono uppercase tracking-wider rounded-lg transition-all cursor-pointer",
                      mode === 'login'
                        ? "bg-card text-foreground font-semibold shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    )}
                  >
                    Sign In
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setMode('register');
                      setErrorMessage(null);
                    }}
                    className={cn(
                      "px-3.5 py-1.5 text-xs font-mono uppercase tracking-wider rounded-lg transition-all cursor-pointer",
                      mode === 'register'
                        ? "bg-card text-foreground font-semibold shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    )}
                  >
                    Register
                  </button>
                </div>
              </div>

              {/* Status & Error Alerts */}
              {errorMessage && (
                <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 text-xs flex items-center gap-2.5 animate-in fade-in">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {successMessage && (
                <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-xs flex items-center gap-2.5 animate-in fade-in">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                  <span>{successMessage}</span>
                </div>
              )}

              {/* 1-Click Instant Guest Demo Button */}
              <button
                type="button"
                onClick={handleDemoLogin}
                disabled={isSubmitting}
                className="w-full p-3 rounded-2xl bg-gradient-to-r from-purple-900/30 via-indigo-900/30 to-ibm-blue/30 border border-indigo-500/30 hover:border-indigo-500/60 text-foreground text-xs font-medium flex items-center justify-between transition-all group cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <div className="p-1.5 rounded-lg bg-amber-400/10 text-amber-400">
                    <Zap className="w-4 h-4" />
                  </div>
                  <div className="text-left">
                    <div className="font-semibold text-foreground group-hover:text-amber-300 transition-colors">
                      Instant 1-Click Guest Access
                    </div>
                    <div className="text-[10px] text-muted-foreground font-mono">
                      No password required • Full access to agents & playground
                    </div>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground group-hover:translate-x-0.5 transition-all" />
              </button>

              <div className="relative flex items-center justify-center">
                <div className="border-t border-border w-full" />
                <span className="bg-card px-3 text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                  Or continue with credentials
                </span>
                <div className="border-t border-border w-full" />
              </div>

              {/* FORM: Sign In Mode */}
              {mode === 'login' ? (
                <form onSubmit={handleLoginSubmit} className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-mono text-muted-foreground flex items-center gap-1.5">
                      <User className="w-3.5 h-3.5" />
                      <span>Username or Email</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={usernameOrEmail}
                      onChange={(e) => setUsernameOrEmail(e.target.value)}
                      placeholder="e.g. alex or alex@example.com"
                      className="w-full px-4 py-3 rounded-xl bg-background border border-border text-sm focus:outline-none focus:border-ibm-blue focus:ring-2 focus:ring-ibm-blue/20 transition-all font-sans"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-mono text-muted-foreground flex items-center gap-1.5">
                        <Lock className="w-3.5 h-3.5" />
                        <span>Password</span>
                      </label>
                    </div>
                    <div className="relative">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full px-4 py-3 pr-11 rounded-xl bg-background border border-border text-sm focus:outline-none focus:border-ibm-blue focus:ring-2 focus:ring-ibm-blue/20 transition-all font-sans"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3.5 top-3.5 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                        tabIndex={-1}
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs pt-1">
                    <label className="flex items-center gap-2 text-muted-foreground cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={rememberMe}
                        onChange={(e) => setRememberMe(e.target.checked)}
                        className="rounded border-border text-ibm-blue focus:ring-0 cursor-pointer"
                      />
                      <span>Remember this session</span>
                    </label>
                  </div>

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full py-3.5 bg-ibm-blue text-white rounded-xl font-medium shadow-lg shadow-ibm-blue/20 hover:bg-ibm-blue/90 transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 mt-2"
                  >
                    {isSubmitting ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <ArrowRight className="w-4 h-4" />
                    )}
                    <span>Sign In to Agentic OS</span>
                  </button>
                </form>
              ) : (
                /* FORM: Register Mode */
                <form onSubmit={handleRegisterSubmit} className="space-y-3.5">
                  <div className="space-y-1.5">
                    <label className="text-xs font-mono text-muted-foreground flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Full Name</span>
                    </label>
                    <input
                      type="text"
                      value={regFullName}
                      onChange={(e) => setRegFullName(e.target.value)}
                      placeholder="e.g. Dr. Arthur Miller"
                      className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-sm focus:outline-none focus:border-ibm-blue focus:ring-2 focus:ring-ibm-blue/20 transition-all"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <label className="text-xs font-mono text-muted-foreground flex items-center gap-1.5">
                        <User className="w-3.5 h-3.5" />
                        <span>Username</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={regUsername}
                        onChange={(e) => setRegUsername(e.target.value)}
                        placeholder="arthur"
                        className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-sm focus:outline-none focus:border-ibm-blue focus:ring-2 focus:ring-ibm-blue/20 transition-all"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-mono text-muted-foreground flex items-center gap-1.5">
                        <Mail className="w-3.5 h-3.5" />
                        <span>Email</span>
                      </label>
                      <input
                        type="email"
                        required
                        value={regEmail}
                        onChange={(e) => setRegEmail(e.target.value)}
                        placeholder="arthur@example.com"
                        className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-sm focus:outline-none focus:border-ibm-blue focus:ring-2 focus:ring-ibm-blue/20 transition-all"
                      />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-mono text-muted-foreground flex items-center gap-1.5">
                      <Lock className="w-3.5 h-3.5" />
                      <span>Create Password</span>
                    </label>
                    <div className="relative">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        required
                        value={regPassword}
                        onChange={(e) => setRegPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full px-4 py-2.5 pr-11 rounded-xl bg-background border border-border text-sm focus:outline-none focus:border-ibm-blue focus:ring-2 focus:ring-ibm-blue/20 transition-all"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3.5 top-3 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                        tabIndex={-1}
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    <div className="text-[10px] text-muted-foreground font-mono">
                      Stored with salted PBKDF2-SHA256 & indexed in MongoDB.
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full py-3.5 bg-ibm-blue text-white rounded-xl font-medium shadow-lg shadow-ibm-blue/20 hover:bg-ibm-blue/90 transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 mt-2"
                  >
                    {isSubmitting ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <ArrowRight className="w-4 h-4" />
                    )}
                    <span>Create Account & Enter OS</span>
                  </button>
                </form>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
