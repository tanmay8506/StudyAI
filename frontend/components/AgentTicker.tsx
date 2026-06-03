"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { transitionFade } from "@/lib/animations";

/**
 * AgentTicker — Cycles text every 3000ms with a cross-fade.
 * 
 * Used inside the AgentCard when in the RUNNING state to provide
 * live-looking status updates to the user.
 */

const TICKER_MESSAGES = [
  "Extracting examiner phrasing from PYQ…",
  "Mapping combination risks across units…",
  "Calibrating against paper DNA…",
  "Validating topic density mappings…",
  "Structuring conceptual analogies…",
  "Retrieving past 5 year questions…"
];

export function AgentTicker() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setIndex((prev) => (prev + 1) % TICKER_MESSAGES.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative h-4 overflow-hidden mt-3">
      <AnimatePresence mode="popLayout">
        <motion.div
          key={index}
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -5 }}
          transition={transitionFade}
          className="absolute inset-0 font-mono text-[10px] italic text-text-secondary whitespace-nowrap overflow-hidden text-ellipsis"
        >
          {TICKER_MESSAGES[index]}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
