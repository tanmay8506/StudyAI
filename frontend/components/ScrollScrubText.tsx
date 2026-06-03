"use client";

import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { useIsMobile } from "@/lib/hooks/useMediaQuery";

/**
 * ScrubSentence — A single sentence that highlights on scroll.
 */
function ScrubSentence({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLSpanElement>(null);
  
  // Track this specific sentence's position in the viewport
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start 65%", "start 45%"] // Highlight as it crosses the center
  });

  // Map the scroll progress to colors
  // From tertiary (dim) to primary (bright)
  const color = useTransform(
    scrollYProgress,
    [0, 1],
    ["var(--text-tertiary)", "var(--text-primary)"]
  );

  return (
    <motion.span
      ref={ref}
      style={{ color, transition: "color 0.1s ease-out" }}
      className="inline-block mr-[0.5em] last:mr-0 transition-colors"
    >
      {children}
    </motion.span>
  );
}

/**
 * ScrollScrubText — Text that highlights sentence by sentence on scroll.
 */
interface ScrollScrubTextProps {
  sentences: string[];
  className?: string;
}

export function ScrollScrubText({ sentences, className = "" }: ScrollScrubTextProps) {
  const isMobile = useIsMobile();

  return (
    <div className={`text-editorial max-w-[800px] text-center mx-auto ${className}`}>
      {sentences.map((sentence, index) => (
        isMobile ? (
          <span key={index} className="inline-block mr-[0.5em] last:mr-0 text-text-primary">
            {sentence}
          </span>
        ) : (
          <ScrubSentence key={index}>
            {sentence}
          </ScrubSentence>
        )
      ))}
    </div>
  );
}
