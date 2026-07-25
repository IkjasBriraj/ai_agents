import React, { useState, useEffect } from 'react';
import { Sparkles, Droplets, Cpu, Check } from 'lucide-react';
import { cn } from '../lib/utils';

export type AnimationMode = 'liquid' | 'slime';

export const ANIMATION_MODE_KEY = 'agentic_animation_mode';
export const ANIMATION_EVENT_NAME = 'animation-mode-change';

export function getSavedAnimationMode(): AnimationMode {
  try {
    const saved = localStorage.getItem(ANIMATION_MODE_KEY);
    if (saved === 'slime' || saved === 'liquid') {
      return saved;
    }
  } catch (e) {
    // Ignore storage errors
  }
  return 'liquid';
}

export function setSavedAnimationMode(mode: AnimationMode) {
  try {
    localStorage.setItem(ANIMATION_MODE_KEY, mode);
    window.dispatchEvent(new CustomEvent(ANIMATION_EVENT_NAME, { detail: mode }));
  } catch (e) {
    console.error('Failed to save animation mode', e);
  }
}

interface AnimationSelectorProps {
  className?: string;
  variant?: 'compact' | 'full';
}

export const AnimationSelector: React.FC<AnimationSelectorProps> = ({
  className,
  variant = 'compact'
}) => {
  const [mode, setMode] = useState<AnimationMode>(getSavedAnimationMode());

  useEffect(() => {
    const handleModeChange = (e: Event) => {
      const customEvent = e as CustomEvent<AnimationMode>;
      if (customEvent.detail) {
        setMode(customEvent.detail);
      }
    };
    window.addEventListener(ANIMATION_EVENT_NAME, handleModeChange);
    return () => window.removeEventListener(ANIMATION_EVENT_NAME, handleModeChange);
  }, []);

  const handleSelect = (newMode: AnimationMode) => {
    setMode(newMode);
    setSavedAnimationMode(newMode);
  };

  if (variant === 'full') {
    return (
      <div className={cn("carbon-card p-4 bg-card/80 backdrop-blur-md border border-border rounded-xl shadow-lg", className)}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">
            <Sparkles className="w-4 h-4 text-accent" />
            Core Intelligence Visual Engine
          </div>
          <span className="text-[10px] font-mono bg-accent/20 text-accent px-2 py-0.5 border border-accent/30 rounded">
            CURRENT: {mode === 'liquid' ? 'LIQUID CORE' : 'SLIME COMPANION'}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* Liquid Core Option */}
          <button
            onClick={() => handleSelect('liquid')}
            className={cn(
              "p-3 rounded-lg border flex items-center gap-3 text-left transition-all duration-200 group relative overflow-hidden",
              mode === 'liquid'
                ? "bg-primary/15 border-primary shadow-glow shadow-primary/20 text-foreground"
                : "bg-muted/30 border-border hover:bg-muted/60 text-muted-foreground hover:text-foreground"
            )}
          >
            <div className={cn(
              "w-10 h-10 rounded-full flex items-center justify-center border transition-all",
              mode === 'liquid' ? "bg-primary text-primary-foreground border-primary" : "bg-card border-border"
            )}>
              <Cpu className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <div className="font-semibold text-xs flex items-center gap-1.5">
                Liquid Agentic Core
                {mode === 'liquid' && <Check className="w-3.5 h-3.5 text-primary" />}
              </div>
              <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-1">
                Futuristic Siri-style 3D fluid glass with 14-point wave physics
              </p>
            </div>
          </button>

          {/* Slime Companion Option */}
          <button
            onClick={() => handleSelect('slime')}
            className={cn(
              "p-3 rounded-lg border flex items-center gap-3 text-left transition-all duration-200 group relative overflow-hidden",
              mode === 'slime'
                ? "bg-accent/15 border-accent shadow-glow shadow-accent/20 text-foreground"
                : "bg-muted/30 border-border hover:bg-muted/60 text-muted-foreground hover:text-foreground"
            )}
          >
            <div className={cn(
              "w-10 h-10 rounded-full flex items-center justify-center border transition-all",
              mode === 'slime' ? "bg-accent text-accent-foreground border-accent" : "bg-card border-border"
            )}>
              <Droplets className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <div className="font-semibold text-xs flex items-center gap-1.5">
                Cute Slime Companion
                {mode === 'slime' && <Check className="w-3.5 h-3.5 text-accent" />}
              </div>
              <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-1">
                Animated blue blob avatar with squishy gelatinous physics & glowing eyes
              </p>
            </div>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("inline-flex items-center bg-card/90 border border-border rounded-lg p-1 shadow-sm gap-1", className)}>
      <button
        onClick={() => handleSelect('liquid')}
        title="Liquid Agentic Core Intelligence"
        className={cn(
          "px-2.5 py-1 text-[11px] font-mono tracking-wide rounded-md flex items-center gap-1.5 transition-all",
          mode === 'liquid'
            ? "bg-primary text-primary-foreground font-semibold shadow-sm"
            : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
        )}
      >
        <Cpu className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">Liquid Core</span>
      </button>

      <button
        onClick={() => handleSelect('slime')}
        title="Cute Slime Companion Avatar"
        className={cn(
          "px-2.5 py-1 text-[11px] font-mono tracking-wide rounded-md flex items-center gap-1.5 transition-all",
          mode === 'slime'
            ? "bg-accent text-accent-foreground font-semibold shadow-sm"
            : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
        )}
      >
        <Droplets className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">Slime AI</span>
      </button>
    </div>
  );
};
