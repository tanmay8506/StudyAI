"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

/**
 * Last4HoursButton — The high-priority filter toggle for the reading phase.
 * 
 * Features a precise 360deg spring rotation on the clock icon (not looped),
 * and a sliding "ACTIVE" pill when toggled on.
 */
export function Last4HoursButton() {
  const [isActive, setIsActive] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div className="flex flex-row-reverse sm:flex-row items-center gap-3">
      {/* The Active Pill */}
      <AnimatePresence>
        {isActive && (
          <motion.div
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -8 }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
            className="font-mono text-[10px] font-bold uppercase tracking-widest text-green bg-green-dim border border-[rgba(90,184,122,0.3)] px-3 py-1.5 rounded-full"
          >
            Active
          </motion.div>
        )}
      </AnimatePresence>

      {/* The Main Button */}
      <motion.button
        onClick={() => setIsActive(!isActive)}
        onHoverStart={() => setIsHovered(true)}
        onHoverEnd={() => setIsHovered(false)}
        whileTap={{ scale: 0.98 }}
        className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border transition-colors duration-150 ${
          isActive
            ? "bg-accent border-accent"
            : "bg-accent-dim2 border-[rgba(232,200,74,0.3)] hover:bg-[rgba(232,200,74,0.15)]"
        }`}
      >
        <motion.span
          animate={{ rotate: isHovered ? 360 : 0 }}
          transition={{ type: "spring", stiffness: 200, damping: 15 }}
          // Reset rotation instantly when hover ends so it can rotate again next hover
          style={{ display: "inline-block" }}
        >
          ⏰
        </motion.span>
        <span
          className={`font-sans text-[13px] font-bold ${
            isActive ? "text-bg-base" : "text-accent"
          }`}
        >
          Last 4 Hours
        </span>
      </motion.button>
    </div>
  );
}
