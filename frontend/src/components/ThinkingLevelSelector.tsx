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
    badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    activeColor: 'bg-amber-500 text-black font-semibold',
    tokenBudget: '1k tokens',
    description: 'Fast direct responses. Minimal reasoning overhead, ideal for quick edits or simple queries.',
  },
  {
    id: 'medium',
    label: 'Medium / Balanced',
    shortLabel: 'Medium',
    icon: Scale,
    badgeColor: 'bg-blue-500/20 text-blue-300 border-blue-500/40',
    activeColor: 'bg-blue-600 text-white font-semibold',
    tokenBudget: '4k tokens',
    description: 'Standard step-by-step reasoning and tool plan verification (Default).',
  },
  {
    id: 'high',
    label: 'High / Deep Reasoning',
    shortLabel: 'High (Deep)',
    icon: Brain,
    badgeColor: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
    activeColor: 'bg-purple-600 text-white font-semibold',
    tokenBudget: '8k tokens',
    description: 'Multi-pass reasoning, edge-case analysis, and self-consistency validation.',
  },
  {
    id: 'extended',
    label: 'Extended / Claude Code',
    shortLabel: 'Extended Thinking',
    icon: Rocket,
    badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    activeColor: 'bg-emerald-600 text-white font-semibold',
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
    if (propOnChange) {
      propOnChange(newLevel);
    } else {
      setSavedThinkingLevel(newLevel);
    }
    setIsOpen(false);
  };

  const currentConfig = THINKING_LEVELS.find((t) => t.id === level) || THINKING_LEVELS[1];
  const IconComponent = currentConfig.icon;

  if (variant === 'full') {
    return (
      <div className={cn('carbon-card p-4 bg-card/80 backdrop-blur-md border border-border rounded-xl shadow-lg', className)}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">
            <Brain className="w-4 h-4 text-purple-400" />
            Agent Thinking Level & Reasoning Budget (Claude Code)
          </div>
          <span className={cn('text-[10px] font-mono px-2 py-0.5 border rounded uppercase', currentConfig.badgeColor)}>
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
                  'p-3 rounded-lg border text-left transition-all duration-200 flex flex-col justify-between gap-2 relative overflow-hidden group',
                  isSelected
                    ? 'border-primary bg-primary/10 shadow-glow shadow-primary/20 text-foreground'
                    : 'bg-muted/30 border-border hover:bg-muted/60 text-muted-foreground hover:text-foreground'
                )}
              >
                <div className="flex items-center justify-between">
                  <div className={cn('p-1.5 rounded-md border', isSelected ? item.activeColor : 'bg-card border-border')}>
                    <ItemIcon className="w-4 h-4" />
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
          className="px-3 py-1.5 bg-card/90 border border-border hover:border-primary/50 rounded-lg text-xs font-mono flex items-center gap-2 shadow-sm transition-all text-foreground"
        >
          <IconComponent className="w-3.5 h-3.5 text-purple-400" />
          <span className="font-semibold">{currentConfig.shortLabel}</span>
          <ChevronDown className="w-3 h-3 text-muted-foreground ml-1" />
        </button>

        {isOpen && (
          <div className="absolute right-0 mt-2 w-64 bg-card border border-border rounded-xl shadow-2xl z-50 p-1.5 animate-in fade-in zoom-in-95 duration-150">
            <div className="px-2.5 py-1.5 text-[10px] font-mono uppercase tracking-wider text-muted-foreground border-b border-border/50 mb-1 flex items-center gap-1.5">
              <Sparkles className="w-3 h-3 text-amber-400" />
              Thinking Level (Claude Code)
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
                    'w-full text-left p-2 rounded-lg flex items-start gap-2.5 transition-colors mb-0.5',
                    isSelected ? 'bg-primary/15 text-primary border border-primary/30 font-medium' : 'hover:bg-muted/60 text-foreground'
                  )}
                >
                  <ItemIcon className={cn('w-4 h-4 mt-0.5 shrink-0', isSelected ? 'text-primary' : 'text-muted-foreground')} />
                  <div>
                    <div className="text-xs font-medium flex items-center justify-between gap-2">
                      {item.label}
                      <span className="text-[9px] font-mono opacity-70">{item.tokenBudget}</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-1">
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
    <div className={cn('inline-flex items-center bg-card/90 border border-border rounded-lg p-1 shadow-sm gap-1', className)}>
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
              'px-2 py-1 text-[11px] font-mono tracking-wide rounded-md flex items-center gap-1.5 transition-all',
              isSelected ? item.activeColor : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
            )}
          >
            <ItemIcon className="w-3 h-3" />
            <span className="capitalize text-[10px]">{item.id}</span>
          </button>
        );
      })}
    </div>
  );
};
