import React, { useEffect, useRef, useState } from 'react';
import { cn } from '../lib/utils';
import { type AnimationMode, getSavedAnimationMode, ANIMATION_EVENT_NAME } from './AnimationSelector';
import './SiriFluidGlow.css';

export interface SiriFluidOrbProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  state?: 'idle' | 'thinking' | 'active' | 'recording' | 'healthy' | 'offline' | 'destructive';
  showGlow?: boolean;
  children?: React.ReactNode;
  className?: string;
  glowPulse?: boolean;
  mode?: AnimationMode; // Optional mode override. Uses global animation selector if omitted.
}

export const SiriFluidOrb: React.FC<SiriFluidOrbProps> = ({
  size = 'md',
  state = 'active',
  showGlow = true,
  children,
  className,
  glowPulse = true,
  mode: propMode,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [globalMode, setGlobalMode] = useState<AnimationMode>(getSavedAnimationMode());

  const activeMode = propMode || globalMode;

  useEffect(() => {
    const handleModeChange = (e: Event) => {
      const customEvent = e as CustomEvent<AnimationMode>;
      if (customEvent.detail) {
        setGlobalMode(customEvent.detail);
      }
    };
    window.addEventListener(ANIMATION_EVENT_NAME, handleModeChange);
    return () => window.removeEventListener(ANIMATION_EVENT_NAME, handleModeChange);
  }, []);

  // Setup animated Canvas liquid blob / Slime companion engine
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let time = 0;

    const sizePxMap: Record<string, number> = {
      xs: 24,
      sm: 36,
      md: 56,
      lg: 116,
      xl: 160,
    };

    const dimension = sizePxMap[size] || 56;
    canvas.width = dimension * 2; // High DPI resolution
    canvas.height = dimension * 2;

    // --- MODE A: LIQUID AGENTIC CORE INTELLIGENCE (Futuristic Siri Glass & 14-Dots Mesh) ---
    const getStateColors = () => {
      switch (state) {
        case 'recording':
          return [
            { r: 239, g: 68, b: 68 },   // Crimson Red
            { r: 217, g: 70, b: 239 },  // Fuchsia
            { r: 244, g: 63, b: 94 },   // Rose
            { r: 168, g: 85, b: 247 }   // Purple
          ];
        case 'thinking':
          return [
            { r: 168, g: 85, b: 247 },  // Purple
            { r: 59, g: 130, b: 246 },   // Electric Blue
            { r: 236, g: 72, b: 153 },  // Hot Pink
            { r: 6, g: 182, b: 212 }    // Cyan
          ];
        case 'healthy':
          return [
            { r: 16, g: 185, b: 129 },  // Emerald Green
            { r: 6, g: 182, b: 212 },   // Cyan
            { r: 59, g: 130, b: 246 },  // Blue
            { r: 168, g: 85, b: 247 }   // Violet
          ];
        case 'offline':
        case 'destructive':
          return [
            { r: 239, g: 68, b: 68 },   // Red
            { r: 245, g: 158, b: 11 },  // Amber
            { r: 185, g: 28, b: 28 },   // Dark Red
            { r: 147, g: 51, b: 234 }   // Purple
          ];
        case 'idle':
        case 'active':
        default:
          return [
            { r: 236, g: 72, b: 153 },  // Siri Pink
            { r: 168, g: 85, b: 247 },  // Violet
            { r: 59, g: 130, b: 246 },   // Cyan-Blue
            { r: 6, g: 182, b: 212 },    // Bright Cyan
            { r: 245, g: 158, b: 11 }   // Amber Siri shimmer
          ];
      }
    };

    const colors = getStateColors();

    const renderLiquid = () => {
      time += state === 'thinking' ? 0.018 : state === 'recording' ? 0.022 : 0.009;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const baseRadius = (canvas.width / 2) * 0.84;

      // 1. LIQUID GLASS SPHERE BASE VOLUME (Translucent 3D Glass Depth)
      const glassVolumeGrad = ctx.createRadialGradient(
        centerX - baseRadius * 0.3, centerY - baseRadius * 0.3, baseRadius * 0.05,
        centerX, centerY, baseRadius
      );
      glassVolumeGrad.addColorStop(0, 'rgba(255, 255, 255, 0.35)');
      glassVolumeGrad.addColorStop(0.35, 'rgba(30, 38, 60, 0.8)');
      glassVolumeGrad.addColorStop(0.75, 'rgba(14, 18, 32, 0.92)');
      glassVolumeGrad.addColorStop(1, 'rgba(4, 6, 14, 0.98)');

      ctx.beginPath();
      ctx.arc(centerX, centerY, baseRadius, 0, Math.PI * 2);
      ctx.fillStyle = glassVolumeGrad;
      ctx.fill();

      // Clip canvas to glass sphere
      ctx.save();
      ctx.beginPath();
      ctx.arc(centerX, centerY, baseRadius * 0.97, 0, Math.PI * 2);
      ctx.clip();

      // 2. INTERNAL IRIDESCENT LIQUID WAVE HORIZON
      const waveYOffset = Math.sin(time * 1.2) * (baseRadius * 0.09);
      const waveY = centerY + waveYOffset;

      ctx.globalCompositeOperation = 'screen';

      // Wave Layer 1
      ctx.beginPath();
      ctx.moveTo(centerX - baseRadius, waveY);
      for (let x = -baseRadius; x <= baseRadius; x += 2) {
        const waveHeight = Math.sin(x * 0.035 + time * 2) * (baseRadius * 0.14) +
                           Math.cos(x * 0.018 - time * 1.5) * (baseRadius * 0.09);
        ctx.lineTo(centerX + x, waveY + waveHeight - baseRadius * 0.07);
      }
      ctx.lineTo(centerX + baseRadius, centerY + baseRadius);
      ctx.lineTo(centerX - baseRadius, centerY + baseRadius);
      ctx.closePath();
      
      const amberWaveGrad = ctx.createLinearGradient(centerX, waveY - baseRadius * 0.25, centerX, waveY + baseRadius * 0.25);
      amberWaveGrad.addColorStop(0, 'rgba(245, 158, 11, 0.9)');
      amberWaveGrad.addColorStop(0.45, 'rgba(236, 72, 153, 0.75)');
      amberWaveGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = amberWaveGrad;
      ctx.fill();

      // Wave Layer 2
      ctx.beginPath();
      ctx.moveTo(centerX - baseRadius, waveY);
      for (let x = -baseRadius; x <= baseRadius; x += 2) {
        const waveHeight = Math.sin(x * 0.03 - time * 2.2) * (baseRadius * 0.15);
        ctx.lineTo(centerX + x, waveY + waveHeight);
      }
      ctx.lineTo(centerX + baseRadius, centerY + baseRadius);
      ctx.lineTo(centerX - baseRadius, centerY + baseRadius);
      ctx.closePath();

      const cyanVioletGrad = ctx.createLinearGradient(centerX, waveY - baseRadius * 0.12, centerX, waveY + baseRadius * 0.35);
      cyanVioletGrad.addColorStop(0, 'rgba(255, 255, 255, 0.98)');
      cyanVioletGrad.addColorStop(0.2, 'rgba(6, 182, 212, 0.92)');
      cyanVioletGrad.addColorStop(0.55, 'rgba(59, 130, 246, 0.85)');
      cyanVioletGrad.addColorStop(1, 'rgba(168, 85, 247, 0.75)');
      ctx.fillStyle = cyanVioletGrad;
      ctx.fill();

      // 3. 14 DOTS GEOMETRIC FLUID ENGINE
      const totalCircularDots = 8;
      const totalTriangularDots = 6;
      const dotRadius = Math.max(3.2, baseRadius * 0.12);

      const allDotPositions: Array<{ x: number; y: number; color: { r: number; g: number; b: number } }> = [];

      const circularRadius = baseRadius * (0.56 + 0.05 * Math.sin(time * 1.5));
      const circularSpeed = time * 0.3;

      for (let i = 0; i < totalCircularDots; i++) {
        const angle = (i / totalCircularDots) * Math.PI * 2 + circularSpeed;
        const radialOffset = Math.sin(time * 2 + i) * (baseRadius * 0.05);
        const currentRadius = circularRadius + radialOffset;

        const x = centerX + Math.cos(angle) * currentRadius;
        const y = centerY + Math.sin(angle) * currentRadius;

        const color = colors[i % colors.length];
        allDotPositions.push({ x, y, color });
      }

      const triRadius = baseRadius * (0.69 + 0.04 * Math.cos(time * 1.2));
      const triRotation = -Math.PI / 2 + time * 0.1;
      
      const v1 = {
        x: centerX + Math.cos(triRotation) * triRadius,
        y: centerY + Math.sin(triRotation) * triRadius
      };
      const v2 = {
        x: centerX + Math.cos(triRotation + (2 * Math.PI) / 3) * triRadius,
        y: centerY + Math.sin(triRotation + (2 * Math.PI) / 3) * triRadius
      };
      const v3 = {
        x: centerX + Math.cos(triRotation + (4 * Math.PI) / 3) * triRadius,
        y: centerY + Math.sin(triRotation + (4 * Math.PI) / 3) * triRadius
      };

      const triangleVertices = [v1, v2, v3];

      const getTrianglePosition = (progress: number) => {
        const p = ((progress % 1) + 1) % 1;
        const side = Math.floor(p * 3);
        const sideProgress = (p * 3) - side;

        const startV = triangleVertices[side];
        const endV = triangleVertices[(side + 1) % 3];

        return {
          x: startV.x + (endV.x - startV.x) * sideProgress,
          y: startV.y + (endV.y - startV.y) * sideProgress
        };
      };

      const triangularSpeed = time * 0.08;

      for (let j = 0; j < totalTriangularDots; j++) {
        const progress = (j / totalTriangularDots) + triangularSpeed;
        const pos = getTrianglePosition(progress);

        const wobbleX = Math.sin(time * 2 + j) * (baseRadius * 0.03);
        const wobbleY = Math.cos(time * 2 + j) * (baseRadius * 0.03);

        const color = colors[(j + 2) % colors.length];
        allDotPositions.push({ x: pos.x + wobbleX, y: pos.y + wobbleY, color });
      }

      for (let a = 0; a < allDotPositions.length; a++) {
        for (let b = a + 1; b < allDotPositions.length; b++) {
          const p1 = allDotPositions[a];
          const p2 = allDotPositions[b];

          const dx = p2.x - p1.x;
          const dy = p2.y - p1.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const maxConnectDist = baseRadius * 0.72;

          if (dist < maxConnectDist) {
            const alpha = (1 - dist / maxConnectDist) * 0.4;
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(${p1.color.r}, ${p1.color.g}, ${p1.color.b}, ${alpha})`;
            ctx.lineWidth = Math.max(0.9, dotRadius * 0.35 * (1 - dist / maxConnectDist));
            ctx.stroke();
          }
        }
      }

      for (let d = 0; d < allDotPositions.length; d++) {
        const dot = allDotPositions[d];
        const pulseRatio = 1 + 0.22 * Math.sin(time * 2.5 + d);
        const currentDotRadius = dotRadius * pulseRatio;

        const auraGradient = ctx.createRadialGradient(
          dot.x, dot.y, 0,
          dot.x, dot.y, currentDotRadius * 2.4
        );
        auraGradient.addColorStop(0, `rgba(${dot.color.r}, ${dot.color.g}, ${dot.color.b}, 0.98)`);
        auraGradient.addColorStop(0.5, `rgba(${dot.color.r}, ${dot.color.g}, ${dot.color.b}, 0.45)`);
        auraGradient.addColorStop(1, 'rgba(0,0,0,0)');

        ctx.beginPath();
        ctx.arc(dot.x, dot.y, currentDotRadius * 2.4, 0, Math.PI * 2);
        ctx.fillStyle = auraGradient;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(dot.x, dot.y, Math.max(1.3, currentDotRadius * 0.45), 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255, 255, 255, 1)';
        ctx.fill();
      }

      ctx.restore();

      ctx.globalCompositeOperation = 'source-over';

      ctx.beginPath();
      ctx.arc(centerX - baseRadius * 0.05, centerY - baseRadius * 0.05, baseRadius * 0.91, Math.PI * 1.1, Math.PI * 1.9);
      const topHighlightGrad = ctx.createLinearGradient(centerX - baseRadius, centerY - baseRadius, centerX + baseRadius, centerY);
      topHighlightGrad.addColorStop(0, 'rgba(255, 255, 255, 0.92)');
      topHighlightGrad.addColorStop(0.5, 'rgba(255, 255, 255, 0.5)');
      topHighlightGrad.addColorStop(1, 'rgba(255, 255, 255, 0.08)');
      ctx.strokeStyle = topHighlightGrad;
      ctx.lineWidth = Math.max(2, baseRadius * 0.06);
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(centerX + baseRadius * 0.02, centerY + baseRadius * 0.02, baseRadius * 0.93, Math.PI * 0.2, Math.PI * 0.8);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.45)';
      ctx.lineWidth = Math.max(1.2, baseRadius * 0.035);
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(centerX, centerY, baseRadius * 0.97, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.35)';
      ctx.lineWidth = 1.2;
      ctx.stroke();
    };

    // --- MODE B: CUTE SLIME AI COMPANION (Gelatinous Blob Avatar matching uploaded image) ---
    const renderSlime = () => {
      time += state === 'thinking' ? 0.025 : state === 'recording' ? 0.035 : 0.014;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const baseRadius = (canvas.width / 2) * 0.76;

      // Gelatinous vertical squish & horizontal wobble physics
      const bounce = Math.sin(time * 2.8);
      const squishY = 1 + bounce * 0.045;
      const squishX = 1 - bounce * 0.03;

      ctx.save();
      ctx.translate(centerX, centerY + bounce * (baseRadius * 0.03));
      ctx.scale(squishX, squishY);

      // 1. Ambient Luminous Aura (Drop Glow)
      const auraGrad = ctx.createRadialGradient(0, 0, baseRadius * 0.2, 0, 0, baseRadius * 1.25);
      if (state === 'recording') {
        auraGrad.addColorStop(0, 'rgba(239, 68, 68, 0.7)');
        auraGrad.addColorStop(1, 'rgba(239, 68, 68, 0)');
      } else if (state === 'thinking') {
        auraGrad.addColorStop(0, 'rgba(168, 85, 247, 0.7)');
        auraGrad.addColorStop(1, 'rgba(168, 85, 247, 0)');
      } else if (state === 'healthy') {
        auraGrad.addColorStop(0, 'rgba(16, 185, 129, 0.7)');
        auraGrad.addColorStop(1, 'rgba(16, 185, 129, 0)');
      } else {
        // Signature Periwinkle Blue Glow matching photo!
        auraGrad.addColorStop(0, 'rgba(96, 165, 250, 0.8)');
        auraGrad.addColorStop(0.55, 'rgba(59, 130, 246, 0.35)');
        auraGrad.addColorStop(1, 'rgba(37, 99, 235, 0)');
      }

      ctx.beginPath();
      ctx.arc(0, 0, baseRadius * 1.2, 0, Math.PI * 2);
      ctx.fillStyle = auraGrad;
      ctx.fill();

      // 2. Volumetric Translucent Slime Body
      const bodyGrad = ctx.createRadialGradient(
        -baseRadius * 0.3, -baseRadius * 0.35, baseRadius * 0.08,
        0, 0, baseRadius * 1.02
      );

      if (state === 'recording') {
        bodyGrad.addColorStop(0, '#f87171');
        bodyGrad.addColorStop(0.35, '#ef4444');
        bodyGrad.addColorStop(0.8, '#b91c1c');
        bodyGrad.addColorStop(1, '#450a0a');
      } else if (state === 'thinking') {
        bodyGrad.addColorStop(0, '#e879f9');
        bodyGrad.addColorStop(0.35, '#c084fc');
        bodyGrad.addColorStop(0.8, '#7e22ce');
        bodyGrad.addColorStop(1, '#3b0764');
      } else if (state === 'healthy') {
        bodyGrad.addColorStop(0, '#6ee7b7');
        bodyGrad.addColorStop(0.35, '#10b981');
        bodyGrad.addColorStop(0.8, '#047857');
        bodyGrad.addColorStop(1, '#064e3b');
      } else {
        // Vibrant Periwinkle Blue Slime matching user uploaded image exactly!
        bodyGrad.addColorStop(0, '#bfdbfe');   // Specular periwinkle top
        bodyGrad.addColorStop(0.35, '#60a5fa'); // Electric sky blue
        bodyGrad.addColorStop(0.78, '#2563eb'); // Deep vibrant blue
        bodyGrad.addColorStop(1, '#1e3a8a');   // Soft dark rim
      }

      // Draw organic fluid perimeter
      ctx.beginPath();
      const numPoints = 28;
      for (let i = 0; i <= numPoints; i++) {
        const angle = (i / numPoints) * Math.PI * 2;
        const organicWobble = Math.sin(angle * 3 + time * 2) * (baseRadius * 0.018) +
                              Math.cos(angle * 2 - time * 1.5) * (baseRadius * 0.012);
        const r = baseRadius + organicWobble;
        const x = Math.cos(angle) * r;
        const y = Math.sin(angle) * r;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.fillStyle = bodyGrad;
      ctx.fill();

      // Subtle dark translucent border (matching image rim)
      ctx.lineWidth = Math.max(1.8, baseRadius * 0.045);
      ctx.strokeStyle = 'rgba(15, 23, 42, 0.45)';
      ctx.stroke();

      // 3. Top Specular Glare (3D Glass Reflection)
      ctx.beginPath();
      ctx.arc(-baseRadius * 0.08, -baseRadius * 0.08, baseRadius * 0.88, Math.PI * 1.12, Math.PI * 1.88);
      const glareGrad = ctx.createLinearGradient(-baseRadius, -baseRadius, baseRadius, 0);
      glareGrad.addColorStop(0, 'rgba(255, 255, 255, 0.88)');
      glareGrad.addColorStop(0.45, 'rgba(255, 255, 255, 0.35)');
      glareGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.lineWidth = Math.max(2, baseRadius * 0.065);
      ctx.strokeStyle = glareGrad;
      ctx.stroke();

      // 4. Expressive Anime Eyes (Bright White Oval Pills matching uploaded photo)
      const blinkCycle = (time * 0.85) % (Math.PI * 2);
      const isBlinking = blinkCycle > 5.85;
      const eyeScaleY = isBlinking ? 0.08 : 1.0;

      // Position eyes slightly to the right side (3/4 perspective matching user image)
      const leftEyeX = baseRadius * 0.22;
      const rightEyeX = baseRadius * 0.52;
      const eyeY = -baseRadius * 0.08 + Math.sin(time * 1.8) * (baseRadius * 0.02);

      const eyeWidth = Math.max(3.2, baseRadius * 0.115);
      const eyeHeight = Math.max(5.5, baseRadius * 0.23) * eyeScaleY;

      // Left Eye
      ctx.save();
      ctx.translate(leftEyeX, eyeY);
      ctx.rotate(0.09); // Cute tilted anime eye angle
      ctx.beginPath();
      ctx.ellipse(0, 0, eyeWidth, eyeHeight, 0, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.shadowColor = 'rgba(255, 255, 255, 0.95)';
      ctx.shadowBlur = Math.max(4, baseRadius * 0.18);
      ctx.fill();
      ctx.restore();

      // Right Eye
      ctx.save();
      ctx.translate(rightEyeX, eyeY);
      ctx.rotate(0.09);
      ctx.beginPath();
      ctx.ellipse(0, 0, eyeWidth, eyeHeight, 0, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.shadowColor = 'rgba(255, 255, 255, 0.95)';
      ctx.shadowBlur = Math.max(4, baseRadius * 0.18);
      ctx.fill();
      ctx.restore();

      // 5. Thinking / Recording Floating Micro-Sparkles
      if (state === 'thinking' || state === 'recording') {
        const sparkleCount = 4;
        for (let s = 0; s < sparkleCount; s++) {
          const spProgress = ((time * 1.5 + s * 0.5) % 1);
          const spY = -baseRadius * (0.6 + spProgress * 0.7);
          const spX = Math.sin(time * 2 + s) * (baseRadius * 0.4);
          const spAlpha = 1 - spProgress;
          ctx.beginPath();
          ctx.arc(spX, spY, Math.max(1.2, baseRadius * 0.035) * spAlpha, 0, Math.PI * 2);
          ctx.fillStyle = state === 'recording'
            ? `rgba(254, 202, 202, ${spAlpha})`
            : `rgba(224, 231, 255, ${spAlpha})`;
          ctx.fill();
        }
      }

      ctx.restore(); // Restore squish scale & translate
    };

    // Render Loop
    const mainRenderLoop = () => {
      if (activeMode === 'slime') {
        renderSlime();
      } else {
        renderLiquid();
      }
      animationFrameId = requestAnimationFrame(mainRenderLoop);
    };

    mainRenderLoop();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [size, state, activeMode]);

  // Dimension classes for container
  const dimensionClasses: Record<string, string> = {
    xs: 'w-5 h-5',
    sm: 'w-8 h-8',
    md: 'w-14 h-14',
    lg: 'w-28 h-28',
    xl: 'w-44 h-44',
  };

  // Outer ambient glow color filter map
  const getGlowColor = () => {
    switch (state) {
      case 'recording': return 'shadow-[0_0_20px_rgba(239,68,68,0.7)] border-red-500/50';
      case 'thinking': return 'shadow-[0_0_25px_rgba(168,85,247,0.7)] border-purple-500/50';
      case 'healthy': return 'shadow-[0_0_20px_rgba(16,185,129,0.7)] border-emerald-500/50';
      case 'offline':
      case 'destructive': return 'shadow-[0_0_20px_rgba(239,68,68,0.7)] border-red-500/50';
      default:
        return activeMode === 'slime'
          ? 'shadow-[0_0_25px_rgba(96,165,250,0.7)] border-blue-400/40'
          : 'shadow-[0_0_25px_rgba(236,72,153,0.6)] border-pink-500/40';
    }
  };

  return (
    <div
      className={cn(
        'siri-orb-base relative group overflow-visible',
        dimensionClasses[size] || dimensionClasses.md,
        showGlow && getGlowColor(),
        glowPulse && 'animate-pulse',
        className
      )}
    >
      {/* Background ambient Siri glow blur backdrop */}
      {showGlow && (
        <div 
          className={cn(
            'siri-fluid-glow-backdrop',
            state === 'thinking' && 'scale-125 duration-300',
            state === 'recording' && 'bg-red-500/40',
            activeMode === 'slime' && 'bg-blue-500/30'
          )} 
        />
      )}

      {/* HTML5 Canvas Siri Liquid Fluid Mesh / Slime AI Companion */}
      <canvas
        ref={canvasRef}
        className="w-full h-full rounded-full object-cover pointer-events-none z-0 filter contrast-125 saturate-150"
      />

      {/* Embedded Children (e.g. CPU Icon, Agent Avatar) */}
      {children && (
        <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none">
          {children}
        </div>
      )}
    </div>
  );
};
