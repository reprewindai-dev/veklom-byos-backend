// @ts-nocheck
import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { motion } from 'motion/react';

interface ZenoEffectVisProps {
  nCycles: number;
  isInterrogating: boolean;
}

export const ZenoEffectVis: React.FC<ZenoEffectVisProps> = ({ nCycles, isInterrogating }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    let animationFrame: number;
    let t = 0;

    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      
      // Background glow with subtle shimmering pulse
      const shimmer = !isInterrogating ? Math.sin(t * 0.5) * 0.02 : 0;
      const gradient = ctx.createRadialGradient(width/2, height/2, 0, width/2, height/2, width/2);
      gradient.addColorStop(0, `rgba(6, 182, 212, ${0.05 + shimmer})`);
      gradient.addColorStop(1, 'transparent');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);

      // Wavefunction shimmer highlights
      if (!isInterrogating) {
        ctx.beginPath();
        const shimmerT = t * 0.2;
        const shimmerGradient = ctx.createLinearGradient(0, 0, width, 0);
        shimmerGradient.addColorStop(0, 'rgba(34, 211, 238, 0)');
        shimmerGradient.addColorStop((Math.sin(shimmerT) + 1) / 2, 'rgba(34, 211, 238, 0.15)');
        shimmerGradient.addColorStop(1, 'rgba(34, 211, 238, 0)');
        ctx.strokeStyle = shimmerGradient;
        ctx.lineWidth = 4;
        
        const amplitude = 40;
        const frequency = 0.05;

        for (let x = 0; x < width; x++) {
          const y = height / 2 + Math.sin(x * frequency + t) * amplitude;
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      // Main Wavefunction
      ctx.beginPath();
      ctx.lineWidth = 2;
      ctx.strokeStyle = isInterrogating ? '#22d3ee' : 'rgba(100, 116, 139, 0.6)';
      
      const amplitude = isInterrogating ? 20 / (Math.max(1, nCycles / 10)) : 40;
      const frequency = 0.05;

      for (let x = 0; x < width; x++) {
        const y = height / 2 + Math.sin(x * frequency + t) * amplitude;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Interrogation points
      if (isInterrogating) {
        const cycleCount = Math.min(nCycles, 50);
        ctx.fillStyle = '#22d3ee';
        for (let i = 0; i <= cycleCount; i++) {
          const x = (width / cycleCount) * i;
          const y = height / 2 + Math.sin(x * frequency + t) * amplitude;
          
          ctx.beginPath();
          ctx.arc(x, y, 2, 0, Math.PI * 2);
          ctx.fill();
          
          // Zeno "Pulse"
          if (Math.floor(t * 10) % 20 === 0) {
             ctx.beginPath();
             ctx.arc(x, y, 8 * (Math.sin(t*5) + 1), 0, Math.PI * 2);
             ctx.strokeStyle = 'rgba(34, 211, 238, 0.2)';
             ctx.stroke();
          }
        }
      }

      t += 0.05;
      animationFrame = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(animationFrame);
  }, [nCycles, isInterrogating]);

  return (
    <div className="relative w-full h-40 bg-black/40 rounded-xl border border-white/10 overflow-hidden flex flex-col items-center justify-center">
      <canvas 
        ref={canvasRef} 
        width={600} 
        height={160} 
        className="w-full h-full"
      />
      <div className="absolute top-2 left-3 flex flex-col">
        <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest">N-Cycle Interrogation</span>
        <span className="text-[14px] font-mono text-white/80">{isInterrogating ? `N = ${nCycles}` : 'UPLINK IDLE'}</span>
      </div>
      
      {isInterrogating && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="absolute bottom-2 right-3 flex items-center gap-2"
        >
          <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <span className="text-[10px] font-mono text-cyan-400 uppercase">Phase-Locked</span>
        </motion.div>
      )}
    </div>
  );
};
