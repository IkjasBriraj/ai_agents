import React, { useState, useEffect } from 'react';
import { Zap, Scale, Brain, Rocket, ChevronDown, Sparkles } from 'lucide-react';
import { cn } from '../lib/utils';

export type ThinkingLevel = 'low' | 'medium' | 'high' | 'extended';

export const THINKING_LEVEL_KEY = 'agentic_thinking_level';
export const THINKING_LEVEL_EVENT = 'thinking-level-change';

export interface ThinkingLevelConfig {
  id: ThinkingLevel;
  label: string;
  shortLabel: string;
  icon: React.ComponentType<{ className?: string }>;
  badgeColor: string;
  activeColor: string;
  tokenBudget: string;
  description: string;
}

export const THINKING_LEVELS: ThinkingLevelConfig[] = [
  {
    id: 'low',
    label: 'Low / Speed Focus',
    shortLabel: 'Low (Fast)',
    icon: Zap,
    badgeColor: 'bg-amber-500/20 text-amber-700 dark:text-amber-300 border-amber-500/40',
    activeColor: 'bg-amber-500 text-black font-semibold',
    tokenBudget: '5k tokens',
    description: 'Fast direct responses. Minimal reasoning overhead, ideal for quick edits or simple queries.',
  },
  {
    id: 'medium',
    label: 'Medium / Balanced',
    shortLabel: 'Medium',
    icon: Scale,
    badgeColor: 'bg-blue-500/20 text-blue-700 dark:text-blue-300 border-blue-500/40',
    activeColor: 'bg-blue-600 text-white font-semibold',
    tokenBudget: '4k tokens',
    description: 'Standard step-by-step reasoning and tool plan verification (Default).',
  },
  {
    id: 'high',
    label: 'High / Deep Reasoning',
    shortLabel: 'High (Deep)',
    icon: Brain,
    badgeColor: 'bg-purple-500/20 text-purple-700 dark:text-purple-300 border-purple-500/40',
    activeColor: 'bg-purple-600 text-white font-semibold',
    tokenBudget: '8k tokens',
    description: 'Multi-pass reasoning, edge-case analysis, and self-consistency validation.',
  },
  {
    id: 'extended',
    label: 'Extended / Claude Code',
    shortLabel: 'Extended Thinking',
    icon: Rocket,
    badgeColor: 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border-emerald-500/40',
    activeColor: 'bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 text-white font-bold shadow-[0_0_20px_rgba(16,185,129,0.45)]',
    tokenBudget: '16k+ tokens',
    description: 'Exhaustive Claude Code style extended thinking with interactive thought stream breakdown.',
  },
];

export function getSavedThinkingLevel(): ThinkingLevel {
  try {
    const saved = localStorage.getItem(THINKING_LEVEL_KEY);
    if (saved && ['low', 'medium', 'high', 'extended'].includes(saved)) {
      return saved as ThinkingLevel;
    }
  } catch (e) {
    // Ignore storage errors
  }
  return 'medium';
}

export function setSavedThinkingLevel(level: ThinkingLevel) {
  try {
    localStorage.setItem(THINKING_LEVEL_KEY, level);
    window.dispatchEvent(new CustomEvent(THINKING_LEVEL_EVENT, { detail: level }));
  } catch (e) {
    console.error('Failed to save thinking level', e);
  }
}

interface ThinkingLevelSelectorProps {
  className?: string;
  variant?: 'compact' | 'full' | 'dropdown';
  value?: ThinkingLevel;
  onChange?: (level: ThinkingLevel) => void;
}

export const ThinkingLevelSelector: React.FC<ThinkingLevelSelectorProps> = ({
  className,
  variant = 'compact',
  value: propValue,
  onChange: propOnChange,
}) => {
  const [level, setLevel] = useState<ThinkingLevel>(propValue || getSavedThinkingLevel());
  const [isOpen, setIsOpen] = useState(false);
  const [extendPulseActive, setExtendPulseActive] = useState(false);

  useEffect(() => {
    if (propValue) {
      setLevel(propValue);
      return;
    }
    const handleLevelChange = (e: Event) => {
      const customEvent = e as CustomEvent<ThinkingLevel>;
      if (customEvent.detail) {
        setLevel(customEvent.detail);
      }
    };
    window.addEventListener(THINKING_LEVEL_EVENT, handleLevelChange);
    return () => window.removeEventListener(THINKING_LEVEL_EVENT, handleLevelChange);
  }, [propValue]);

  const handleSelect = (newLevel: ThinkingLevel) => {
    setLevel(newLevel);
    if (newLevel === 'extended') {
      setExtendPulseActive(true);
      setTimeout(() => setExtendPulseActive(false), 3200);
    }
    if (propOnChange) {
      propOnChange(newLevel);
    } else {
      setSavedThinkingLevel(newLevel);
    }
    setIsOpen(false);
  };

  const currentConfig = THINKING_LEVELS.find((t) => t.id === level) || THINKING_LEVELS[1];
  const IconComponent = currentConfig.icon;
  const isExtended = level === 'extended';

  if (variant === 'full') {
    return (
      <div className={cn('carbon-card p-4 bg-card/80 backdrop-blur-md border border-border rounded-xl shadow-lg relative overflow-hidden', className)}>
        {isExtended && (
          <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-emerald-400 via-cyan-400 to-purple-500 animate-pulse" />
        )}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">
            <Brain className="w-4 h-4 text-purple-400" />
            Agent Thinking Level & Reasoning Budget (Claude Code)
          </div>
          <span className={cn('text-[10px] font-mono px-2 py-0.5 border rounded uppercase transition-all duration-300', currentConfig.badgeColor)}>
            {currentConfig.shortLabel} • {currentConfig.tokenBudget}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2">
          {THINKING_LEVELS.map((item) => {
            const ItemIcon = item.icon;
            const isSelected = level === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => handleSelect(item.id)}
                className={cn(
                  'p-3 rounded-xl border text-left transition-all duration-300 flex flex-col justify-between gap-2 relative overflow-hidden group cursor-pointer',
                  isSelected
                    ? item.id === 'extended'
                      ? 'border-emerald-500 bg-emerald-500/10 shadow-[0_0_25px_rgba(16,185,129,0.28)] scale-[1.02] text-foreground'
                      : 'border-primary bg-primary/10 shadow-glow shadow-primary/20 text-foreground'
                    : 'bg-muted/30 border-border hover:bg-muted/60 text-muted-foreground hover:text-foreground'
                )}
              >
                <div className="flex items-center justify-between">
                  <div className={cn('p-1.5 rounded-md border transition-transform duration-300 group-hover:scale-110', isSelected ? item.activeColor : 'bg-card border-border')}>
                    <ItemIcon className={cn('w-4 h-4', item.id === 'extended' && isSelected && 'animate-bounce')} />
                  </div>
                  <span className="text-[9px] font-mono opacity-70">{item.tokenBudget}</span>
                </div>
                <div>
                  <div className="font-semibold text-xs flex items-center gap-1">
                    {item.label.split('/')[0]}
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-1 line-clamp-2">
                    {item.description}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  if (variant === 'dropdown') {
    return (
      <div className={cn('relative inline-block text-left', className)}>
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className={cn(
            "h-10 sm:h-11 px-3.5 py-2 border rounded-xl text-xs sm:text-sm font-mono flex items-center gap-2 shadow-sm transition-all duration-300 font-bold cursor-pointer relative overflow-hidden",
            isExtended
              ? "bg-gradient-to-r from-emerald-500/20 via-teal-500/15 to-cyan-500/20 border-emerald-500/60 text-emerald-700 dark:text-emerald-300 shadow-[0_0_22px_rgba(16,185,129,0.3)]"
              : "bg-card/90 border-border hover:border-primary/50 text-foreground"
          )}
        >
          {isExtended && (
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping shrink-0" />
          )}
          <IconComponent className={cn("w-4 h-4", isExtended ? "text-emerald-500 dark:text-emerald-400 animate-bounce" : "text-purple-500 dark:text-purple-400")} />
          <span>{currentConfig.shortLabel}</span>
          <ChevronDown className={cn("w-4 h-4 text-muted-foreground ml-1 transition-transform duration-200", isOpen && "rotate-180")} />
        </button>

        {/* Extended Thinking Surge Animation Popover Toast */}
        {extendPulseActive && (
          <div className="fixed top-20 right-8 z-[120] max-w-sm rounded-2xl border border-emerald-500/60 bg-slate-950/95 backdrop-blur-2xl p-4 shadow-[0_20px_60px_rgba(16,185,129,0.35)] animate-in zoom-in-95 slide-in-from-top-4 duration-300 pointer-events-none">
            <div className="flex items-center gap-3">
              <div className="relative w-11 h-11 rounded-xl bg-gradient-to-br from-emerald-500 via-teal-500 to-cyan-500 flex items-center justify-center shadow-lg">
                <span className="absolute inset-0 rounded-xl bg-emerald-400 animate-ping opacity-30" />
                <Rocket className="w-5 h-5 text-white animate-bounce" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                    Extended Thinking Activated
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                    16k+ Budget
                  </span>
                </div>
                <p className="text-[11px] text-slate-300 mt-0.5">
                  Deep multi-pass chain-of-thought & self-verification enabled on gemma4:31b-cloud.
                </p>
                <div className="mt-2 h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                  <div className="h-full w-full bg-gradient-to-r from-emerald-400 via-cyan-400 to-purple-400 animate-pulse" />
                </div>
              </div>
            </div>
          </div>
        )}

        {isOpen && (
          <div className="absolute right-0 mt-2 w-72 bg-card border border-border rounded-2xl shadow-2xl z-50 p-2 animate-in fade-in zoom-in-95 slide-in-from-top-2 duration-200">
            <div className="px-2.5 py-1.5 text-[10px] font-mono uppercase tracking-wider text-muted-foreground border-b border-border/50 mb-1.5 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Sparkles className="w-3 h-3 text-amber-400 animate-spin" />
                Thinking Depth & Token Budget
              </span>
              <span className="text-primary font-semibold">{currentConfig.tokenBudget}</span>
            </div>
            {THINKING_LEVELS.map((item) => {
              const ItemIcon = item.icon;
              const isSelected = level === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleSelect(item.id)}
                  className={cn(
                    'w-full text-left p-2.5 rounded-xl flex items-start gap-2.5 transition-all duration-200 mb-1 cursor-pointer',
                    isSelected
                      ? item.id === 'extended'
                        ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/40 font-semibold shadow-sm'
                        : 'bg-primary/15 text-primary border border-primary/30 font-medium'
                      : 'hover:bg-secondary/70 text-foreground border border-transparent'
                  )}
                >
                  <ItemIcon className={cn('w-4 h-4 mt-0.5 shrink-0', isSelected ? (item.id === 'extended' ? 'text-emerald-500 animate-bounce' : 'text-primary') : 'text-muted-foreground')} />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-semibold flex items-center justify-between gap-2">
                      <span>{item.label}</span>
                      <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-background/80 border border-border/60">{item.tokenBudget}</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-2 leading-relaxed">
                      {item.description}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // Segmented compact bar
  return (
    <div className={cn('inline-flex items-center bg-card/90 border border-border rounded-xl p-1 shadow-sm gap-1', className)}>
      <span className="text-[10px] font-mono text-muted-foreground uppercase px-1.5 hidden sm:inline flex items-center gap-1">
        <Brain className="w-3 h-3 text-purple-400" />
        Thinking:
      </span>
      {THINKING_LEVELS.map((item) => {
        const ItemIcon = item.icon;
        const isSelected = level === item.id;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => handleSelect(item.id)}
            title={`${item.label}: ${item.description}`}
            className={cn(
              'px-2.5 py-1 text-[11px] font-mono tracking-wide rounded-lg flex items-center gap-1.5 transition-all duration-300 cursor-pointer',
              isSelected ? item.activeColor : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
            )}
          >
            <ItemIcon className={cn("w-3 h-3", item.id === 'extended' && isSelected && "animate-bounce")} />
            <span className="capitalize text-[10px]">{item.id}</span>
          </button>
        );
      })}
    </div>
  );
};
