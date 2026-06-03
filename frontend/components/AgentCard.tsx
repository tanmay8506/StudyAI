"use client";

import { useEffect, useRef, useState } from "react";
import { TILT_MAX, TILT_PERSPECTIVE, TILT_SPRING, springPulseGlow, transitionFade } from "@/lib/animations";
import { motion, useMotionValue, useSpring, useAnimation } from "framer-motion";
import { useDeadTimePulse } from "./DeadTimePulse";
import { AgentTicker } from "./AgentTicker";
import { useIsMobile } from "@/lib/hooks/useMediaQuery";

/**
 * AgentCard — The primary component of the Pipeline grid.
 * 
 * Supports 4 states: queued, running, complete, failed.
 * Includes 3D tilt, magnetic border glow, noise texture overlay,
 * and state-specific animations.
 */

export type AgentState = "queued" | "running" | "complete" | "failed";

interface AgentCardProps {
  id: string;
  name: string;
  model: string;
  state: AgentState;
  index: number; // 0 to 11
  className?: string;
}

export function AgentCard({ id, name, model, state, index, className = "" }: AgentCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const pulseTick = useDeadTimePulse();
  const controls = useAnimation();

  // Ensure 3D tilt starts strictly at 0 to avoid flashing
  const rotateX = useSpring(0, { stiffness: 300, damping: 30 });
  const rotateY = useSpring(0, { stiffness: 300, damping: 30 });
  const [isHovered, setIsHovered] = useState(false);
  const isMobile = useIsMobile();

  // Entrance animation on mount
  useEffect(() => {
    controls.start({
      y: 0,
      opacity: state === "queued" ? 0.45 : 1,
      transition: {
        type: "spring",
        stiffness: 100,
        damping: 20,
        delay: index * 0.06,
      }
    });
  }, [controls, index, state]);

  // Dead Time Pulse (only when queued)
  useEffect(() => {
    if (state === "queued" && pulseTick > 0) {
      controls.start({
        opacity: [0.45, 0.65, 0.45],
        transition: {
          duration: 1.2,
          ease: "easeInOut",
          delay: index * 0.08,
        }
      });
    }
  }, [pulseTick, state, index, controls]);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current || isMobile) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Magnetic Border Glow
    cardRef.current.style.setProperty("--mouse-x", `${x}px`);
    cardRef.current.style.setProperty("--mouse-y", `${y}px`);

    // 3D Tilt
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    rotateX.set(((y - centerY) / rect.height) * -6);
    rotateY.set(((x - centerX) / rect.width) * 6);
  };

  const handleMouseLeave = () => {
    rotateX.set(0);
    rotateY.set(0);
    setIsHovered(false);
  };

  // State-specific styles
  const getCardStyle = () => {
    switch (state) {
      case "running":
        return {
          background: "linear-gradient(90deg, var(--accent-dim) 0%, var(--bg-card) 40%)",
          borderColor: "var(--border-subtle)", // Left border handled separately
        };
      case "complete":
        return {
          background: "var(--green-dim)",
          borderColor: "rgba(90,184,122,0.2)",
        };
      case "failed":
        return {
          background: "var(--red-dim)",
          borderColor: "rgba(232,90,74,0.2)",
        };
      case "queued":
      default:
        return {
          background: "var(--bg-card)",
          borderColor: "var(--border-subtle)",
        };
    }
  };

  return (
    <motion.div
      ref={cardRef}
      initial={{ y: 20, opacity: 0 }}
      animate={controls}
      // On state change to complete, do a brief scale pop
      whileTap={state === "failed" ? { scale: 0.98 } : {}}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onMouseEnter={() => setIsHovered(true)}
      style={{
        rotateX,
        rotateY,
        transformPerspective: 800,
        ...getCardStyle()
      }}
      className={`relative w-full rounded-xl overflow-hidden p-5 transition-colors duration-300 ${className}`}
    >
      {/* 1. Noise Texture Overlay (Below content, above bg) */}
      <div 
        className="absolute inset-0 pointer-events-none rounded-inherit"
        style={{ opacity: 0.025, mixBlendMode: "overlay" }}
      >
        <svg className="w-full h-full opacity-100">
          <filter id="noise">
            <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" stitchTiles="stitch" />
          </filter>
          <rect width="100%" height="100%" filter="url(#noise)" />
        </svg>
      </div>

      {/* 2. Magnetic Glow Overlay (Above content) - Disabled on mobile */}
      {!isMobile && (
        <div
          className="absolute inset-0 pointer-events-none rounded-inherit transition-opacity duration-300 z-10"
          style={{
            opacity: isHovered ? 1 : 0,
            background: "radial-gradient(180px at var(--mouse-x, 0) var(--mouse-y, 0), rgba(232,200,74,0.10), transparent 70%)",
            willChange: "background"
          }}
        />
      )}

      {/* 3. RUNNING Left Border Pulse */}
      {state === "running" && (
        <motion.div
          className="absolute left-0 top-0 bottom-0 w-[2px] bg-accent origin-center"
          animate={{ scaleY: [0.5, 1], opacity: [0.6, 1] }}
          transition={{ duration: 1.2, repeat: Infinity, repeatType: 'mirror', ease: 'easeInOut' }}
        />
      )}

      {/* 4. Content */}
      <div className="relative z-0 h-full flex flex-col justify-between min-h-[90px]">
        {/* Top Row */}
        <div className="flex justify-between items-center mb-4">
          <div className="font-mono font-medium text-[10px] text-text-tertiary">{id}</div>
          <div className="flex items-center justify-center w-5 h-5">
            {state === "queued" && (
              <div className="w-3 h-3 rounded-full border border-text-tertiary" />
            )}
            {state === "running" && (
              <svg className="w-4 h-4 text-accent animate-spin" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5" strokeDasharray="47 15" strokeLinecap="round" />
              </svg>
            )}
            {state === "complete" && (
              <svg className="w-4 h-4 text-green" viewBox="0 0 24 24" fill="none">
                <motion.path
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={transitionFade}
                  d="M5 13l4 4L19 7"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
            {state === "failed" && (
              <motion.svg 
                initial={{ rotate: -45, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                transition={TILT_SPRING}
                className="w-4 h-4 text-red" 
                viewBox="0 0 24 24" 
                fill="none"
              >
                <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </motion.svg>
            )}
          </div>
        </div>

        {/* Middle */}
        <div className="font-sans font-bold text-[15px] text-text-primary leading-tight">
          {name}
        </div>

        {/* Bottom */}
        <div className="mt-2 flex justify-between items-end">
          <div className="font-mono font-medium text-[10px] text-text-tertiary">
            {model}
          </div>
          <div className="font-sans text-[10px] uppercase font-bold tracking-wider">
            {state === "queued" && <span className="text-text-tertiary">QUEUED</span>}
            {state === "running" && <span className="text-accent">PROCESSING</span>}
            {state === "complete" && <span className="text-green">VERIFIED</span>}
            {state === "failed" && (
              <div className="flex flex-col items-end gap-1">
                <span className="text-red">FAILED</span>
                <button className="text-[10px] text-red border border-red/30 px-2 py-0.5 rounded uppercase hover:bg-red/10 transition-colors pointer-events-auto">
                  Retry
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Ticker for running state */}
        {state === "running" && <AgentTicker />}
      </div>
    </motion.div>
  );
}
