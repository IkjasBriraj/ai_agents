import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import {
  ShieldCheck,
  Database,
  Eye,
  EyeOff,
  Zap,
  Layers,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Server,
  Lock,
  LogIn,
  UserPlus,
  AlertCircle,
  Compass,
  FileCode,
  User,
  Mail
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface WhyChoosePageProps {
  onEnterApp: () => void;
  onNavigateLogin?: () => void;
}

export const WhyChoosePage: React.FC<WhyChoosePageProps> = ({ onEnterApp, onNavigateLogin }) => {
  const {
    user,
    isAuthenticated,
    login,
    register,
    loginAsDemo,
    logout,
    mongoStatus,
    isMongoLoading,
    refreshMongoStatus,
    connectMongo
  } = useAuth();

  // Auth Form State
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [showPassword, setShowPassword] = useState(false);
  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [password, setPassword] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regFullName, setRegFullName] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSuccess, setAuthSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Active Interactive Tour Tab
  const [activeTourTab, setActiveTourTab] = useState<'agents' | 'privacy' | 'mongo' | 'accessibility'>('agents');

  // MongoDB Config State
  const [showMongoConfig, setShowMongoConfig] = useState(false);
  const [customMongoUrl, setCustomMongoUrl] = useState(mongoStatus?.url || 'mongodb://localhost:27017/senior_agent');
  const [customMongoDb, setCustomMongoDb] = useState('senior_agent');
  const [mongoMessage, setMongoMessage] = useState<string | null>(null);

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setAuthSuccess(null);
    if (!usernameOrEmail.trim() || !password) {
      setAuthError('Please enter your username/email and password.');
      return;
    }
    setIsSubmitting(true);
    try {
      await login({ username_or_email: usernameOrEmail.trim(), password });
      setAuthSuccess('Signed in successfully! Entering workspace...');
      setTimeout(() => onEnterApp(), 400);
    } catch (err: any) {
      setAuthError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setAuthSuccess(null);
    if (!regUsername.trim() || !regEmail.trim() || !regPassword) {
      setAuthError('Please fill in all required fields.');
      return;
    }
    if (regPassword.length < 4) {
      setAuthError('Password must be at least 4 characters.');
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
      setAuthSuccess('Account registered & saved to MongoDB! Loading workspace...');
      setTimeout(() => onEnterApp(), 500);
    } catch (err: any) {
      setAuthError(err.response?.data?.detail || 'Registration failed. Username or email may already be taken.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDemoAccess = async () => {
    setAuthError(null);
    setAuthSuccess(null);
    setIsSubmitting(true);
    try {
      await loginAsDemo();
      setAuthSuccess('Guest Researcher session ready! Launching...');
      setTimeout(() => onEnterApp(), 400);
    } catch (err: any) {
      setAuthError('Failed to sign in as guest demo user.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleMongoConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    setMongoMessage(null);
    try {
      const res = await connectMongo(customMongoUrl, customMongoDb);
      if (res.connected) {
        setMongoMessage(`Connected successfully! Ping: ${res.latency_ms}ms • Collections: ${res.collections.length}`);
      } else {
        setMongoMessage(`Connection attempt: ${res.message || res.error || 'Server standby'}`);
      }
    } catch (err: any) {
      setMongoMessage(err.response?.data?.detail || 'Failed to update MongoDB URL');
    }
  };

  return (
    <div className="space-y-16 py-4 animate-in fade-in duration-500 max-w-7xl mx-auto">
      {/* Hero Section */}
      <section className="relative overflow-hidden rounded-3xl border border-border/80 bg-gradient-to-br from-card via-card/70 to-background p-8 md:p-14 shadow-2xl backdrop-blur-xl">
        {/* Glow Spheres */}
        <div className="absolute top-0 right-0 -mt-16 -mr-16 w-[450px] h-[450px] rounded-full bg-ibm-blue/15 blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/4 -mb-16 w-80 h-80 rounded-full bg-purple-500/10 blur-3xl pointer-events-none" />

        <div className="relative z-10 max-w-4xl space-y-6">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-ibm-blue/10 border border-ibm-blue/20 text-ibm-blue text-xs font-mono tracking-widest uppercase shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>The Local-First Agentic Operating System</span>
          </div>

          <h1 className="text-4xl sm:text-5xl md:text-6xl font-light tracking-tight leading-[1.15] text-foreground">
            Why Choose <br className="hidden sm:inline" />
            <span className="font-semibold text-ibm-blue">SeniorAgent Orchestrator</span>?
          </h1>

          <p className="text-lg md:text-xl text-muted-foreground font-light leading-relaxed max-w-3xl">
            A private, high-performance multi-agent ecosystem engineered for <strong className="text-foreground font-medium">100% local privacy</strong>, <strong className="text-foreground font-medium">autonomous LangGraph collaboration</strong>, <strong className="text-foreground font-medium">MongoDB database persistence</strong>, and <strong className="text-foreground font-medium">accessible cognitive design</strong>.
          </p>

          <div className="flex flex-wrap items-center gap-4 pt-4">
            {isAuthenticated ? (
              <button
                type="button"
                onClick={onEnterApp}
                className="px-7 py-4 bg-ibm-blue text-white rounded-2xl font-medium flex items-center gap-3 shadow-xl shadow-ibm-blue/25 hover:bg-ibm-blue/90 hover:scale-[1.01] transition-all cursor-pointer"
              >
                <span>Enter Agentic OS Workspace</span>
                <ArrowRight className="w-5 h-5" />
              </button>
            ) : (
              <>
                <a
                  href="#auth-section"
                  className="px-7 py-4 bg-ibm-blue text-white rounded-2xl font-medium flex items-center gap-3 shadow-xl shadow-ibm-blue/25 hover:bg-ibm-blue/90 hover:scale-[1.01] transition-all cursor-pointer"
                >
                  <LogIn className="w-5 h-5" />
                  <span>Get Started & Log In</span>
                </a>

                {onNavigateLogin && (
                  <button
                    type="button"
                    onClick={onNavigateLogin}
                    className="px-5 py-4 bg-card hover:bg-muted border border-border text-foreground rounded-2xl font-medium flex items-center gap-2 transition-all cursor-pointer"
                  >
                    <span>Dedicated Login Page</span>
                  </button>
                )}
              </>
            )}

            <button
              type="button"
              onClick={handleDemoAccess}
              disabled={isSubmitting}
              className="px-6 py-4 bg-gradient-to-r from-purple-900/40 via-indigo-900/30 to-ibm-blue/40 hover:from-purple-900/60 hover:to-ibm-blue/60 border border-indigo-500/30 text-foreground rounded-2xl font-medium flex items-center gap-2.5 transition-all cursor-pointer group"
            >
              <Zap className="w-4 h-4 text-amber-400 group-hover:scale-110 transition-transform" />
              <span>1-Click Instant Guest Access</span>
            </button>
          </div>

          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-6 border-t border-border/70">
            <div className="space-y-1">
              <div className="text-2xl font-light text-foreground flex items-center gap-2">
                <span>100% Local</span>
              </div>
              <div className="text-xs text-muted-foreground font-mono">Zero Cloud Telemetry</div>
            </div>
            <div className="space-y-1">
              <div className="text-2xl font-light text-foreground flex items-center gap-2">
                <span>Multi-Agent</span>
              </div>
              <div className="text-xs text-muted-foreground font-mono">LangGraph State Routing</div>
            </div>
            <div className="space-y-1">
              <div className="text-2xl font-light text-foreground flex items-center gap-2">
                <span>MongoDB</span>
              </div>
              <div className="text-xs text-muted-foreground font-mono">Document Store & Logs</div>
            </div>
            <div className="space-y-1">
              <div className="text-2xl font-light text-foreground flex items-center gap-2">
                <span>AAA Contrast</span>
              </div>
              <div className="text-xs text-muted-foreground font-mono">Accessible Senior Design</div>
            </div>
          </div>
        </div>
      </section>

      {/* Interactive Feature Showcase Tabs */}
      <section className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div className="space-y-1">
            <div className="text-xs font-mono uppercase tracking-widest text-ibm-blue">Explore Capabilities</div>
            <h2 className="text-3xl font-light">Engineered for Freedom & Power</h2>
          </div>

          {/* Tour Tabs */}
          <div className="flex rounded-xl bg-card border border-border p-1">
            <button
              type="button"
              onClick={() => setActiveTourTab('agents')}
              className={cn(
                "px-3.5 py-1.5 text-xs font-mono uppercase tracking-wider rounded-lg transition-all cursor-pointer",
                activeTourTab === 'agents' ? "bg-ibm-blue text-white font-semibold" : "text-muted-foreground hover:text-foreground"
              )}
            >
              Multi-Agent
            </button>
            <button
              type="button"
              onClick={() => setActiveTourTab('privacy')}
              className={cn(
                "px-3.5 py-1.5 text-xs font-mono uppercase tracking-wider rounded-lg transition-all cursor-pointer",
                activeTourTab === 'privacy' ? "bg-ibm-blue text-white font-semibold" : "text-muted-foreground hover:text-foreground"
              )}
            >
              Local Privacy
            </button>
            <button
              type="button"
              onClick={() => setActiveTourTab('mongo')}
              className={cn(
                "px-3.5 py-1.5 text-xs font-mono uppercase tracking-wider rounded-lg transition-all cursor-pointer",
                activeTourTab === 'mongo' ? "bg-ibm-blue text-white font-semibold" : "text-muted-foreground hover:text-foreground"
              )}
            >
              MongoDB Core
            </button>
            <button
              type="button"
              onClick={() => setActiveTourTab('accessibility')}
              className={cn(
                "px-3.5 py-1.5 text-xs font-mono uppercase tracking-wider rounded-lg transition-all cursor-pointer",
                activeTourTab === 'accessibility' ? "bg-ibm-blue text-white font-semibold" : "text-muted-foreground hover:text-foreground"
              )}
            >
              Accessibility
            </button>
          </div>
        </div>

        {/* Tab Detail Card */}
        <div className="p-8 rounded-3xl border border-border bg-card shadow-lg transition-all">
          {activeTourTab === 'agents' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-in fade-in">
              <div className="space-y-3 p-5 rounded-2xl bg-muted/40 border border-border/60">
                <div className="p-2.5 rounded-xl bg-ibm-blue/10 text-ibm-blue w-fit">
                  <FileCode className="w-5 h-5" />
                </div>
                <h4 className="text-base font-medium">Code Generation Agent</h4>
                <p className="text-xs text-muted-foreground font-light leading-relaxed">
                  Writes, refactors, and validates source code across allowed directories with safety whitelisting.
                </p>
              </div>

              <div className="space-y-3 p-5 rounded-2xl bg-muted/40 border border-border/60">
                <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-400 w-fit">
                  <Compass className="w-5 h-5" />
                </div>
                <h4 className="text-base font-medium">Research & Web Agent</h4>
                <p className="text-xs text-muted-foreground font-light leading-relaxed">
                  Conducts web investigations, parses PDF documents, and extracts insights via Playwright headless browser.
                </p>
              </div>

              <div className="space-y-3 p-5 rounded-2xl bg-muted/40 border border-border/60">
                <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 w-fit">
                  <Layers className="w-5 h-5" />
                </div>
                <h4 className="text-base font-medium">Business & Strategy Agent</h4>
                <p className="text-xs text-muted-foreground font-light leading-relaxed">
                  Compiles polished Excel workbooks, PowerPoint slides, and structured business summaries autonomously.
                </p>
              </div>
            </div>
          )}

          {activeTourTab === 'privacy' && (
            <div className="space-y-4 animate-in fade-in">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-2xl bg-emerald-500/10 text-emerald-500">
                  <ShieldCheck className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="text-lg font-medium">Absolute Local Privacy & Air-Gap Readiness</h4>
                  <p className="text-xs text-muted-foreground">Zero cloud telemetry. Absolute ownership of your data.</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground font-light leading-relaxed max-w-3xl">
                Unlike cloud-dependent chatbots that pipe your company documents, health records, and private communications to external servers, SeniorAgent runs LLMs on your device via Ollama. All embeddings, task graphs, and memory indices remain within your storage directory.
              </p>
            </div>
          )}

          {activeTourTab === 'mongo' && (
            <div className="space-y-4 animate-in fade-in">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-2xl bg-cyan-500/10 text-cyan-400">
                  <Database className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="text-lg font-medium">Enterprise MongoDB Persistence & Hybrid SQLite Fallback</h4>
                  <p className="text-xs text-muted-foreground">Scalable JSON document persistence for multi-agent ecosystems.</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground font-light leading-relaxed max-w-3xl">
                SeniorAgent natively integrates with MongoDB for flexible, high-speed document indexing across user sessions, agent conversations, hub graphs, and scheduled cron loops. If your MongoDB server is offline, an automatic SQLite engine acts as a fail-safe so your work never halts.
              </p>
            </div>
          )}

          {activeTourTab === 'accessibility' && (
            <div className="space-y-4 animate-in fade-in">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-2xl bg-purple-500/10 text-purple-400">
                  <Eye className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="text-lg font-medium">Inclusive, Cognitive & Senior-Friendly Design</h4>
                  <p className="text-xs text-muted-foreground">High contrast, tactile buttons, and natural voice interaction.</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground font-light leading-relaxed max-w-3xl">
                Built from the ground up to eliminate visual clutter, cognitive fatigue, and tiny click targets. With IBM Carbon high-contrast typography, an interactive voice companion, and clear affirmative step-by-step actions, SeniorAgent ensures users of all ages and abilities thrive with AI.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* Live System Diagnostics & MongoDB Status Bar */}
      <section className="p-7 rounded-3xl border border-border bg-card shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="p-3.5 rounded-2xl bg-muted flex-shrink-0">
              <Database className="w-6 h-6 text-ibm-blue" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-base">MongoDB Database Connection</h3>
                <span
                  className={cn(
                    'px-2.5 py-0.5 rounded-full text-[11px] font-mono uppercase tracking-wider',
                    mongoStatus?.connected
                      ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/30'
                      : 'bg-amber-500/10 text-amber-500 border border-amber-500/30'
                  )}
                >
                  {mongoStatus?.connected ? 'Online' : 'Standby (Local Fallback)'}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                {mongoStatus?.connected
                  ? `Active on ${mongoStatus.url} (${mongoStatus.latency_ms}ms ping) • ${mongoStatus.counts?.users ?? 0} users stored`
                  : `Configured for ${mongoStatus?.url || 'mongodb://localhost:27017'}. Local SQLite fallback is currently keeping all data safe.`}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => refreshMongoStatus()}
              disabled={isMongoLoading}
              className="px-3.5 py-2 text-xs font-mono uppercase bg-muted hover:bg-muted/80 text-foreground rounded-xl border border-border flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <RefreshCw className={cn('w-3.5 h-3.5', isMongoLoading && 'animate-spin')} />
              <span>{isMongoLoading ? 'Checking...' : 'Refresh Status'}</span>
            </button>

            <button
              type="button"
              onClick={() => setShowMongoConfig(!showMongoConfig)}
              className="px-3.5 py-2 text-xs font-mono uppercase bg-ibm-blue/10 hover:bg-ibm-blue/20 text-ibm-blue rounded-xl border border-ibm-blue/30 flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Server className="w-3.5 h-3.5" />
              <span>{showMongoConfig ? 'Hide Settings' : 'Configure MongoDB URI'}</span>
            </button>
          </div>
        </div>

        {/* Expandable MongoDB Configuration Card */}
        {showMongoConfig && (
          <form onSubmit={handleMongoConnect} className="mt-6 pt-6 border-t border-border space-y-4 animate-in fade-in duration-300">
            <div className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
              Configure Custom MongoDB Instance (Local, Docker, or MongoDB Atlas Cloud)
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-2 space-y-1">
                <label className="text-xs font-mono text-muted-foreground">MongoDB Connection String</label>
                <input
                  type="text"
                  value={customMongoUrl}
                  onChange={(e) => setCustomMongoUrl(e.target.value)}
                  placeholder="mongodb://localhost:27017/senior_agent or mongodb+srv://..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-background border border-border text-sm font-mono focus:outline-none focus:border-ibm-blue"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-mono text-muted-foreground">Database Name</label>
                <input
                  type="text"
                  value={customMongoDb}
                  onChange={(e) => setCustomMongoDb(e.target.value)}
                  placeholder="senior_agent"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-background border border-border text-sm font-mono focus:outline-none focus:border-ibm-blue"
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <div className="text-xs text-muted-foreground">
                {mongoMessage && <span className="text-ibm-blue font-medium">{mongoMessage}</span>}
              </div>
              <button
                type="submit"
                disabled={isMongoLoading}
                className="px-5 py-2.5 bg-ibm-blue text-white rounded-xl text-xs font-mono uppercase tracking-wider hover:bg-ibm-blue/90 transition-colors flex items-center gap-2 cursor-pointer"
              >
                {isMongoLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>Save & Test Connection</span>
              </button>
            </div>
          </form>
        )}
      </section>

      {/* Platform Comparison Matrix */}
      <section className="space-y-6">
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <div className="text-xs font-mono uppercase tracking-widest text-ibm-blue">Platform Comparison</div>
          <h2 className="text-3xl font-light">SeniorAgent OS vs Commercial Cloud AI</h2>
        </div>

        <div className="overflow-x-auto rounded-3xl border border-border bg-card shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="bg-muted/60 border-b border-border text-xs font-mono uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="py-4 px-6">Capability</th>
                <th className="py-4 px-6 text-ibm-blue font-semibold">SeniorAgent OS</th>
                <th className="py-4 px-6">Commercial Cloud Chatbots</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border font-light">
              <tr>
                <td className="py-4 px-6 font-medium text-foreground">Data Privacy & Ownership</td>
                <td className="py-4 px-6 text-emerald-500 font-medium flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4" /> 100% on your local machine
                </td>
                <td className="py-4 px-6 text-muted-foreground flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-amber-500" /> Stored on third-party cloud servers
                </td>
              </tr>
              <tr>
                <td className="py-4 px-6 font-medium text-foreground">Multi-Agent Collaboration</td>
                <td className="py-4 px-6 text-emerald-500 font-medium flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4" /> Built-in LangGraph Agent Hubs
                </td>
                <td className="py-4 px-6 text-muted-foreground flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-amber-500" /> Isolated single-agent chat threads
                </td>
              </tr>
              <tr>
                <td className="py-4 px-6 font-medium text-foreground">Monthly Subscriptions</td>
                <td className="py-4 px-6 text-emerald-500 font-medium flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4" /> $0 Free & Unlimited local compute
                </td>
                <td className="py-4 px-6 text-muted-foreground flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-amber-500" /> $20 to $200+ / mo per user
                </td>
              </tr>
              <tr>
                <td className="py-4 px-6 font-medium text-foreground">Database Storage</td>
                <td className="py-4 px-6 text-emerald-500 font-medium flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4" /> MongoDB + SQLite with full export
                </td>
                <td className="py-4 px-6 text-muted-foreground flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-amber-500" /> Locked inside corporate database
                </td>
              </tr>
              <tr>
                <td className="py-4 px-6 font-medium text-foreground">Accessible UI Design</td>
                <td className="py-4 px-6 text-emerald-500 font-medium flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4" /> AAA High contrast & Voice companion
                </td>
                <td className="py-4 px-6 text-muted-foreground flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-amber-500" /> Standard generic small font layouts
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Embedded Authentication / Login & Signup Section */}
      <section id="auth-section" className="max-w-xl mx-auto rounded-3xl border border-border/80 bg-card p-8 md:p-10 shadow-2xl backdrop-blur-xl">
        <div className="text-center space-y-2 mb-6">
          <div className="inline-flex p-3 rounded-2xl bg-ibm-blue/10 text-ibm-blue mb-1">
            <Lock className="w-6 h-6" />
          </div>
          <h3 className="text-2xl font-light tracking-tight text-foreground">
            {isAuthenticated ? 'Welcome Back to SeniorAgent' : authMode === 'login' ? 'Sign In to Your Workspace' : 'Create an Account'}
          </h3>
          <p className="text-xs text-muted-foreground font-light">
            {isAuthenticated
              ? `You are authenticated as ${user?.full_name || user?.username} (${user?.role})`
              : 'Sign in to access your custom agent teams, memories, and MongoDB workspaces.'}
          </p>
        </div>

        {isAuthenticated ? (
          <div className="space-y-4 text-center">
            <div className="p-4 rounded-2xl bg-muted/60 border border-border text-sm space-y-1 text-left">
              <div className="font-semibold text-foreground">{user?.full_name}</div>
              <div className="text-xs text-muted-foreground font-mono">@{user?.username} • {user?.email}</div>
              <div className="text-[11px] text-ibm-blue font-mono mt-1">
                Storage: {user?.storage_type === 'mongodb' ? 'MongoDB Primary' : 'Local SQLite Fallback'}
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <button
                type="button"
                onClick={onEnterApp}
                className="flex-1 py-3.5 bg-ibm-blue text-white rounded-2xl font-medium flex items-center justify-center gap-2 shadow-lg shadow-ibm-blue/20 hover:bg-ibm-blue/90 transition-all cursor-pointer"
              >
                <span>Open Agentic OS</span>
                <ArrowRight className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={logout}
                className="px-6 py-3.5 border border-border text-muted-foreground hover:text-red-500 hover:bg-muted rounded-2xl text-xs font-mono uppercase transition-colors cursor-pointer"
              >
                Sign Out
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            {/* Quick Demo Access Button */}
            <button
              type="button"
              onClick={handleDemoAccess}
              disabled={isSubmitting}
              className="w-full p-3 rounded-2xl bg-gradient-to-r from-purple-900/30 to-ibm-blue/30 border border-indigo-500/30 hover:border-indigo-500/60 text-foreground text-xs font-medium flex items-center justify-between transition-all group cursor-pointer"
            >
              <div className="flex items-center gap-2.5">
                <div className="p-1.5 rounded-lg bg-amber-400/10 text-amber-400">
                  <Zap className="w-4 h-4" />
                </div>
                <div className="text-left">
                  <div className="font-semibold text-foreground group-hover:text-amber-300">
                    Instant 1-Click Guest Access
                  </div>
                  <div className="text-[10px] text-muted-foreground font-mono">
                    No password required • Full access to agents & playground
                  </div>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:translate-x-0.5 transition-all" />
            </button>

            <div className="relative flex items-center justify-center">
              <div className="border-t border-border w-full" />
              <span className="bg-card px-3 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                Or sign in with account
              </span>
              <div className="border-t border-border w-full" />
            </div>

            {/* Tabs */}
            <div className="flex rounded-xl bg-muted p-1 border border-border">
              <button
                type="button"
                onClick={() => {
                  setAuthMode('login');
                  setAuthError(null);
                }}
                className={cn(
                  'flex-1 py-2 text-xs font-mono uppercase tracking-wider rounded-lg transition-all flex items-center justify-center gap-1.5 cursor-pointer',
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
                  setAuthError(null);
                }}
                className={cn(
                  'flex-1 py-2 text-xs font-mono uppercase tracking-wider rounded-lg transition-all flex items-center justify-center gap-1.5 cursor-pointer',
                  authMode === 'register' ? 'bg-card text-foreground shadow-sm font-semibold' : 'text-muted-foreground hover:text-foreground'
                )}
              >
                <UserPlus className="w-3.5 h-3.5" />
                <span>Register</span>
              </button>
            </div>

            {authError && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-500 text-xs flex items-center gap-2 animate-in fade-in">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{authError}</span>
              </div>
            )}

            {authSuccess && (
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-500 text-xs flex items-center gap-2 animate-in fade-in">
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                <span>{authSuccess}</span>
              </div>
            )}

            {authMode === 'login' ? (
              <form onSubmit={handleLoginSubmit} className="space-y-4">
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
                    className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-sm focus:outline-none focus:border-ibm-blue focus:ring-2 focus:ring-ibm-blue/20 transition-all font-sans"
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
                      className="w-full px-4 py-2.5 pr-10 rounded-xl bg-background border border-border text-sm focus:outline-none focus:border-ibm-blue focus:ring-2 focus:ring-ibm-blue/20 transition-all font-sans"
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
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full py-3.5 bg-ibm-blue text-white rounded-2xl font-medium shadow-lg shadow-ibm-blue/20 hover:bg-ibm-blue/90 transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {isSubmitting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
                  <span>Sign In to Agentic OS</span>
                </button>
              </form>
            ) : (
              <form onSubmit={handleRegisterSubmit} className="space-y-3.5">
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
                    className="w-full px-4 py-2 rounded-xl bg-background border border-border text-sm focus:outline-none focus:border-ibm-blue focus:ring-2 focus:ring-ibm-blue/20 transition-all"
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
                    className="w-full px-4 py-2 rounded-xl bg-background border border-border text-sm focus:outline-none focus:border-ibm-blue focus:ring-2 focus:ring-ibm-blue/20 transition-all"
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
                    className="w-full px-4 py-2 rounded-xl bg-background border border-border text-sm focus:outline-none focus:border-ibm-blue focus:ring-2 focus:ring-ibm-blue/20 transition-all"
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
                      className="w-full px-4 py-2 pr-10 rounded-xl bg-background border border-border text-sm focus:outline-none focus:border-ibm-blue focus:ring-2 focus:ring-ibm-blue/20 transition-all"
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
                  className="w-full py-3.5 bg-ibm-blue text-white rounded-2xl font-medium shadow-lg shadow-ibm-blue/20 hover:bg-ibm-blue/90 transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 mt-1"
                >
                  {isSubmitting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
                  <span>Create Account & Log In</span>
                </button>
              </form>
            )}
          </div>
        )}
      </section>
    </div>
  );
};
