import React, { useState, useEffect, useRef } from 'react';
import { GripVertical } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SplitPaneDividerProps {
  onResize: (newLeftPercent: number) => void;
  onReset?: () => void;
  onDragStateChange?: (isDragging: boolean) => void;
  minLeft?: number; // default 20%
  maxLeft?: number; // default 80%
  className?: string;
}

export const SplitPaneDivider: React.FC<SplitPaneDividerProps> = ({
  onResize,
  onReset,
  onDragStateChange,
  minLeft = 20,
  maxLeft = 80,
  className
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const startDragging = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    setIsDragging(true);
    onDragStateChange?.(true);
  };

  useEffect(() => {
    if (!isDragging) return;

    const handleMove = (clientX: number) => {
      const parent = containerRef.current?.parentElement;
      if (!parent) return;

      const rect = parent.getBoundingClientRect();
      if (rect.width <= 0) return;

      const rawPercent = ((clientX - rect.left) / rect.width) * 100;
      const clamped = Math.min(Math.max(rawPercent, minLeft), maxLeft);
      onResize(Math.round(clamped * 10) / 10);
    };

    const onMouseMove = (e: MouseEvent) => {
      handleMove(e.clientX);
    };

    const onTouchMove = (e: TouchEvent) => {
      if (e.touches.length > 0) {
        handleMove(e.touches[0].clientX);
      }
    };

    const onEnd = () => {
      setIsDragging(false);
      onDragStateChange?.(false);
      document.body.style.cursor = 'default';
      document.body.style.userSelect = 'auto';
    };

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    window.addEventListener('mousemove', onMouseMove, { passive: false });
    window.addEventListener('mouseup', onEnd);
    window.addEventListener('touchmove', onTouchMove, { passive: false });
    window.addEventListener('touchend', onEnd);

    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onEnd);
      window.removeEventListener('touchmove', onTouchMove);
      window.removeEventListener('touchend', onEnd);
      document.body.style.cursor = 'default';
      document.body.style.userSelect = 'auto';
    };
  }, [isDragging, minLeft, maxLeft, onResize, onDragStateChange]);

  return (
    <>
      {/* Full-screen invisible overlay during dragging to prevent iframe event interception */}
      {isDragging && (
        <div
          className="fixed inset-0 z-[9999] cursor-col-resize select-none pointer-events-auto"
          style={{ cursor: 'col-resize' }}
        />
      )}

      <div
        ref={containerRef}
        onMouseDown={startDragging}
        onTouchStart={startDragging}
        onDoubleClick={onReset}
        className={cn(
          "hidden lg:flex w-4 relative items-center justify-center cursor-col-resize group shrink-0 select-none z-30 transition-colors",
          isDragging ? "bg-purple-500/30" : "hover:bg-purple-500/10",
          className
        )}
        title="Drag left or right to resize split panes (Double-click to reset to 50/50)"
      >
        {/* Subtle vertical border line */}
        <div
          className={cn(
            "w-0.5 h-full transition-all duration-200",
            isDragging
              ? "bg-purple-500 shadow-[0_0_12px_rgba(168,85,247,0.9)]"
              : "bg-border group-hover:bg-purple-400"
          )}
        />

        {/* Grip handle button */}
        <div
          className={cn(
            "absolute top-1/2 -translate-y-1/2 w-4 h-10 rounded-full bg-secondary border border-border/80 shadow-md flex items-center justify-center transition-all duration-200 cursor-col-resize",
            isDragging
              ? "border-purple-500 bg-purple-950 text-white shadow-[0_0_15px_rgba(168,85,247,0.8)] scale-110"
              : "group-hover:border-purple-400 group-hover:bg-card text-muted-foreground group-hover:text-purple-300"
          )}
        >
          <GripVertical className="w-3 h-3 pointer-events-none" />
        </div>
      </div>
    </>
  );
};
