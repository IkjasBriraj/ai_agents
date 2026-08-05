import { useCallback, useEffect, useState } from 'react';
import { CircleAlert, CircleCheck, LoaderCircle, RefreshCw } from 'lucide-react';
import { getApplicationHealth } from '@/services/health';
import type { ApplicationHealth } from '@/services/health';

const messages = {
  healthy: 'All local services are ready.',
  limited: 'The app is connected, but AI conversations are unavailable until Ollama is ready.',
  unhealthy: 'The backend is not ready. Check the local setup and try again.',
} as const;

export function ServiceStatusBanner({ onHealthChange }: { onHealthChange?: (health: ApplicationHealth | null) => void }) {
  const [health, setHealth] = useState<ApplicationHealth | null>(null);
  const [checking, setChecking] = useState(true);

  const refreshHealth = useCallback(async () => {
    setChecking(true);
    try {
      const nextHealth = await getApplicationHealth();
      setHealth(nextHealth);
      onHealthChange?.(nextHealth);
    } catch {
      setHealth(null);
      onHealthChange?.(null);
    } finally {
      setChecking(false);
    }
  }, [onHealthChange]);

  useEffect(() => {
    void refreshHealth();
  }, [refreshHealth]);

  const isReady = health?.status === 'healthy';
  const text = checking
    ? 'Checking local services…'
    : health
      ? messages[health.status]
      : 'Cannot reach the backend. Start it with scripts\\start-local.ps1, then try again.';

  return (
    <div
      className={`mb-6 flex items-center justify-between gap-3 border px-4 py-3 text-sm ${isReady ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300' : 'border-amber-500/40 bg-amber-500/10 text-amber-800 dark:text-amber-200'}`}
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center gap-2">
        {checking ? <LoaderCircle className="h-4 w-4 animate-spin" /> : isReady ? <CircleCheck className="h-4 w-4" /> : <CircleAlert className="h-4 w-4" />}
        <span>{text}</span>
        {health?.components?.ollama?.status === 'unavailable' && (
          <span className="hidden sm:inline">Start Ollama at {health.components.ollama?.url || 'http://localhost:11434'}.</span>
        )}
      </div>
      <button onClick={() => void refreshHealth()} className="inline-flex shrink-0 items-center gap-1 px-2 py-1 underline underline-offset-2" aria-label="Retry service connection">
        <RefreshCw className="h-3.5 w-3.5" /> Retry
      </button>
    </div>
  );
}
