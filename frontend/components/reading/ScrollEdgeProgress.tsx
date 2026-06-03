"use client";

import { useEffect, useState } from "react";
import { motion, MotionValue, useTransform, AnimatePresence } from "framer-motion";
import { useIsMobile } from "@/lib/hooks/useMediaQuery";

/**
 * ScrollEdgeProgress — A 2px amber line fixed to the left edge of the viewport.
 * 
 * Replaces the traditional top-bar progress bar. Lives in the margin and does
 * not compete with the content. At 100% completion, it emits a soft radial pulse.
 */

interface ScrollEdgeProgressProps {
  scrollYProgress: MotionValue<number>;
}

export function ScrollEdgeProgress({ scrollYProgress }: ScrollEdgeProgressProps) {
  const heightPercent = useTransform(scrollYProgress, [0, 1], ["0%", "100%"]);
  const [isComplete, setIsComplete] = useState(false);
  const isMobile = useIsMobile();

  useEffect(() => {
    return scrollYProgress.on("change", (latest) => {
      // Trigger the completion pulse only when hitting exactly 1 (100%)
      if (latest >= 0.999 && !isComplete) {
        setIsComplete(true);
      } else if (latest < 0.999 && isComplete) {
        setIsComplete(false); // Reset if they scroll back up
      }
    });
  }, [scrollYProgress, isComplete]);

  if (isMobile) return null;

  return (
    <>
      {/* The literal left-edge progress line */}
      <motion.div
        className="fixed left-0 top-0 w-[2px] bg-accent z-50 origin-top pointer-events-none"
        style={{ height: heightPercent }}
      />

      {/* The 100% completion radial pulse */}
      <AnimatePresence>
        {isComplete && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ type: "spring", stiffness: 200, damping: 20 }}
            className="fixed left-0 bottom-0 pointer-events-none z-40"
            style={{
              width: "80px",
              height: "80px",
              transform: "translate(-50%, 50%)", // Centered at the bottom left corner
              background: "radial-gradient(circle, rgba(232,200,74,0.15) 0%, transparent 70%)"
            }}
          />
        )}
      </AnimatePresence>
    </>
  );
}
