"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useInView, useReducedMotion } from "framer-motion";
import { useIsMobile } from "@/lib/hooks/useMediaQuery";

/**
 * InkDrawBorder — SVG line that draws itself down the left edge of a container.
 * 
 * Uses a ResizeObserver to dynamically update the path endpoint to perfectly
 * match the container height without distorting the stroke width.
 * Triggers `onDrawComplete` after its 400ms animation so sibling components
 * (like MaskReveal) can sequence their entrance.
 */

interface InkDrawBorderProps {
  onDrawComplete?: () => void;
}

export function InkDrawBorder({ onDrawComplete }: InkDrawBorderProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(100);
  
  // Track visibility for the `whileInView` equivalent behavior
  const isInView = useInView(containerRef, { once: true, margin: "-80px" });
  const [hasDrawn, setHasDrawn] = useState(false);
  const prefersReducedMotion = useReducedMotion();
  const isMobile = useIsMobile();
  
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  
  const shouldReduceMotion = mounted && (prefersReducedMotion || isMobile);

  useEffect(() => {
    if (!containerRef.current) return;

    // Use ResizeObserver to dynamically track exact height
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setHeight(entry.contentRect.height);
      }
    });
    
    // We observe the parent element since this component is absolute positioned
    if (containerRef.current.parentElement) {
      observer.observe(containerRef.current.parentElement);
    }

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (isInView && !hasDrawn) {
      setHasDrawn(true);
      if (onDrawComplete) {
        // The draw animation takes 400ms. We trigger the callback exactly after.
        const timer = setTimeout(() => {
          onDrawComplete();
        }, 400);
        return () => clearTimeout(timer);
      }
    }
  }, [isInView, hasDrawn, onDrawComplete]);

  return (
    <div 
      ref={containerRef}
      className="absolute left-0 top-0 bottom-0 w-[3px] pointer-events-none overflow-hidden rounded-l-xl"
    >
      <svg 
        width="3" 
        height={height} 
        viewBox={`0 0 3 ${height}`} 
        className="block"
      >
        <motion.path
          d={`M 1.5 0 L 1.5 ${height}`}
          stroke="rgba(232, 200, 74, 0.6)" // var(--border-ink)
          strokeWidth="3"
          strokeLinecap="round"
          initial={mounted ? (shouldReduceMotion ? { opacity: 0, pathLength: 1 } : { opacity: 1, pathLength: 0 }) : { opacity: 1, pathLength: 0 }}
          animate={
            mounted && isInView 
              ? (shouldReduceMotion ? { opacity: 1, pathLength: 1 } : { opacity: 1, pathLength: 1 }) 
              : (mounted ? (shouldReduceMotion ? { opacity: 0, pathLength: 1 } : { opacity: 1, pathLength: 0 }) : { opacity: 1, pathLength: 0 })
          }
          transition={{ duration: 0.4, ease: "easeOut" }}
        />
      </svg>
    </div>
  );
}
