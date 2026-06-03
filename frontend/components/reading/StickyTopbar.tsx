"use client";

import { motion, MotionValue, useTransform } from "framer-motion";
import { useFocusMode } from "./FocusModeProvider";
import { Last4HoursButton } from "../overview/Last4HoursButton";

/**
 * StickyTopbar — The primary actions header above the reading content.
 * 
 * Features a strict 12px backdrop blur (the only one on the page).
 * In Focus Mode, shrinks to 8px height, hides all content, and transforms
 * into a horizontal progress bar.
 */

interface StickyTopbarProps {
  unitName: string;
  scrollYProgress: MotionValue<number>;
}

export function StickyTopbar({ unitName, scrollYProgress }: StickyTopbarProps) {
  const { isFocusMode, toggleFocusMode } = useFocusMode();
  
  // Transform scroll progress to scaleX for the focus mode progress line
  const progressScaleX = useTransform(scrollYProgress, [0, 1], [0, 1]);

  return (
    <motion.div
      // Spring animate the height depending on focus mode
      animate={{ height: isFocusMode ? 8 : 48 }}
      transition={{ type: "spring", stiffness: 200, damping: 25 }}
      className="sticky top-0 z-50 w-full overflow-hidden"
      style={{
        // Strictly bg-base at 92% opacity with 12px blur
        backgroundColor: "rgba(10, 9, 8, 0.92)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--border-subtle)",
        willChange: "transform, backdrop-filter",
      }}
    >
      {/* 
        Inner Content Container 
        Fades out to 0 opacity when focus mode is active 
      */}
      <motion.div
        animate={{ opacity: isFocusMode ? 0 : 1 }}
        transition={{ duration: 0.2 }}
        className="flex h-full items-center justify-between px-8"
        // Disable pointer events when faded out so it doesn't block the progress line
        style={{ pointerEvents: isFocusMode ? "none" : "auto" }}
      >
        <div className="font-sans text-[11px] uppercase tracking-widest text-text-tertiary">
          {unitName}
        </div>

        <div className="flex items-center gap-4">
          <button 
            onClick={toggleFocusMode}
            className="flex items-center gap-1.5 font-sans text-[11px] text-text-tertiary hover:text-text-primary transition-colors"
          >
            ⊙ Focus
          </button>
          
          <button className="px-3 py-1.5 border border-border-default rounded-md font-sans text-[11px] text-text-secondary hover:bg-bg-card transition-colors">
            Export PDF
          </button>

          {/* Scale down the Last4HoursButton slightly for the topbar context */}
          <div className="scale-90 origin-right">
            <Last4HoursButton />
          </div>
        </div>
      </motion.div>

      {/* 
        Focus Mode Progress Line 
        Only visible when in focus mode, transforming the topbar into a progress strip.
      */}
      <motion.div
        animate={{ opacity: isFocusMode ? 1 : 0 }}
        transition={{ duration: 0.2 }}
        className="absolute bottom-0 left-0 h-full bg-accent origin-left w-full"
        style={{ scaleX: progressScaleX }}
      />
    </motion.div>
  );
}
