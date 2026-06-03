"use client";

import { useEffect, useRef } from "react";
import { motion, useMotionValue, useTransform, animate, useInView } from "framer-motion";

/**
 * AgentCounterNumber — 0 to 12 animated counter for Section 3.
 * 
 * Uses a single useMotionValue animated when the section enters view.
 * No setTimeout loops. Native Framer Motion value interpolation.
 */

interface AgentCounterNumberProps {
  onComplete?: () => void;
}

export function AgentCounterNumber({ onComplete }: AgentCounterNumberProps) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-20%" });
  const count = useMotionValue(0);
  
  // Round the motion value to integers
  const rounded = useTransform(count, (latest) => Math.round(latest));

  useEffect(() => {
    if (isInView) {
      const controls = animate(count, 12, {
        duration: 1.8,
        ease: [0.16, 1, 0.3, 1], // fast end decel
        onComplete: () => {
          if (onComplete) onComplete();
        }
      });
      return controls.stop;
    }
  }, [isInView, count, onComplete]);

  return (
    <div ref={ref} className="text-center">
      <motion.span
        className="font-mono text-accent"
        style={{
          fontSize: "clamp(120px, 18vw, 240px)",
          lineHeight: 0.9,
          display: "inline-block"
        }}
      >
        {rounded}
      </motion.span>
    </div>
  );
}
