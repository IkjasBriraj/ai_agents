import React, { useState, useEffect, useRef } from 'react';
import { GripVertical } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SplitPaneDividerProps {
  onResize: (newLeftPercent: number) => void;
  onReset?: () => void;
  minLeft?: number; // default 25%
  maxLeft?: number; // default 75%
  className?: string;
}

export const SplitPaneDivider: React.FC<SplitPaneDividerProps> = ({
  onResize,
  onReset,
  minLeft = 30,
  maxLeft = 70,
  className
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      // Find parent split container
      const parent = containerRef.current?.parentElement;
      if (!parent) return;

      const rect = parent.getBoundingClientRect();
      const clientX = e.clientX;
      const rawPercent = ((clientX - rect.left) / rect.width) * 100;
      const clamped = Math.min(Math.max(rawPercent, minLeft), maxLeft);
      onResize(clamped);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      document.body.style.cursor = 'default';
      document.body.style.userSelect = 'auto';
    };

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'default';
      document.body.style.userSelect = 'auto';
    };
  }, [isDragging, minLeft, maxLeft, onResize]);

  return (
    <div
      ref={containerRef}
      onMouseDown={() => setIsDragging(true)}
      onDoubleClick={onReset}
      className={cn(
        "hidden lg:flex w-2.5 relative items-center justify-center cursor-col-resize group shrink-0 select-none z-20 transition-all",
        isDragging && "bg-purple-500/20",
        className
      )}
      title="Drag to resize split panes (Double-click to reset to 50/50)"
    >
      {/* Subtle vertical border line */}
      <div className={cn(
        "w-px h-full bg-border group-hover:bg-purple-500/80 transition-colors duration-200",
        isDragging && "bg-purple-500 shadow-[0_0_10px_rgba(168,85,247,0.8)]"
      )} />

      {/* Grip handle button */}
      <div className={cn(
        "absolute top-1/2 -translate-y-1/2 w-4 h-9 rounded-full bg-secondary border border-border/80 shadow-md flex items-center justify-center group-hover:border-purple-500/80 group-hover:bg-purple-950/60 transition-all",
        isDragging && "border-purple-500 bg-purple-900 shadow-[0_0_15px_rgba(168,85,247,0.6)] scale-110"
      )}>
        <GripVertical className={cn(
          "w-3 h-3 text-muted-foreground group-hover:text-purple-300 transition-colors",
          isDragging && "text-white"
        )} />
      </div>
    </div>
  );
};
