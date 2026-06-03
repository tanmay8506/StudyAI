"use client";

import { useState, useEffect } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { maskWordStandard, maskWordFast, maskWordDramatic } from "@/lib/animations";
import { useId } from "react";

/**
 * MaskReveal — Character/Word-level text reveal animation.
 *
 * Text appears to rise from below, carved from darkness.
 * Each word is wrapped in an overflow:hidden span, and animates
 * its position (y: 100% → 0) with a spring and stagger.
 *
 * SSR FIX: We use a `mounted` guard so the server and the hydration
 * pass both render with `initial={false}` (no inline opacity style),
 * then after mount the full animation runs. This eliminates the
 * style={{opacity:0}} vs style={{}} hydration mismatch.
 */

type RevealVariant = "standard" | "fast" | "dramatic";

interface MaskRevealProps {
  text: string;
  as?: any;
  className?: string;
  style?: React.CSSProperties;
  variant?: RevealVariant;
  delay?: number;
}

export function MaskReveal({
  text,
  as: Component = "h1",
  className = "",
  style,
  variant = "standard",
  delay = 0,
}: MaskRevealProps) {
  const id = useId();
  const prefersReducedMotion = useReducedMotion();

  // HYDRATION FIX: never apply animation initial styles until after mount.
  // Server renders with initial={false} → no inline style → matches client hydration.
  // After useEffect fires, mounted=true and full animations activate.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const shouldReduceMotion = mounted && (prefersReducedMotion ?? false);

  const variants = {
    standard: maskWordStandard,
    fast:     maskWordFast,
    dramatic: maskWordDramatic,
  }[variant];

  // Split into words, preserving spaces
  const words = text.split(" ").map((word, i, arr) =>
    i === arr.length - 1 ? word : word + "\u00A0"
  );

  return (
    <Component className={className} style={style} aria-label={text}>
      <span className="sr-only">{text}</span>

      {/* initial={false} before mount → no SSR/hydration style mismatch */}
      <motion.span
        initial={mounted ? (shouldReduceMotion ? { opacity: 0 } : "hidden") : false}
        whileInView={shouldReduceMotion ? { opacity: 1 } : "visible"}
        viewport={{ once: true, margin: "-100px" }}
        transition={shouldReduceMotion ? { duration: 0.6 } : undefined}
        aria-hidden="true"
        className="inline-block"
      >
        {words.map((word, i) => (
          <span
            key={`${id}-${i}`}
            style={{
              overflow:      "hidden",
              display:       "inline-block",
              verticalAlign: "bottom",
            }}
          >
            <motion.span
              variants={mounted ? variants : undefined}
              custom={i + delay * 10}
              style={{ display: "inline-block" }}
            >
              {word}
            </motion.span>
          </span>
        ))}
      </motion.span>
    </Component>
  );
}
