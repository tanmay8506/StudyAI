"use client";

import { motion, AnimatePresence } from "framer-motion";

/**
 * UnitTracker — The sticky right column of the pipeline page.
 * 
 * Shows the progress of individual units as they are compiled by the agents.
 */

export type UnitState = "queued" | "processing" | "complete";

export interface UnitProgressData {
  id: string;
  name: string;
  state: UnitState;
  progress: number; // 0 to 1
  isFirstCompleted?: boolean;
}

interface UnitTrackerProps {
  units: UnitProgressData[];
}

export function UnitTracker({ units }: UnitTrackerProps) {
  return (
    <div className="sticky top-0 h-screen overflow-y-auto border-l border-border-subtle bg-bg-raised p-6 hidden md:block">
      <div className="font-sans text-[10px] uppercase text-text-tertiary tracking-widest mb-6">
        Compiled Units
      </div>

      <div className="flex flex-col gap-6">
        {units.map((unit) => (
          <div key={unit.id} className="flex flex-col gap-2">
            <div className="flex justify-between items-center">
              <div className="font-sans text-[13px] text-text-primary">
                {unit.name}
              </div>
              <div className="font-sans text-[9px] uppercase font-bold tracking-wider">
                {unit.state === "queued" && <span className="text-text-tertiary opacity-50">QUEUED</span>}
                {unit.state === "processing" && <span className="text-accent animate-pulse">PROCESSING</span>}
                {unit.state === "complete" && <span className="text-green">COMPLETE</span>}
              </div>
            </div>

            {/* Unit Progress Bar */}
            <div className="w-full h-[2px] bg-border-subtle relative rounded overflow-hidden">
              <motion.div
                className="absolute left-0 top-0 bottom-0 bg-accent origin-left"
                initial={{ scaleX: 0 }}
                animate={{ scaleX: unit.progress }}
                transition={{ type: "spring", stiffness: 100, damping: 20 }}
              />
            </div>

            {/* Read Unit CTA (only shows when first unit completes) */}
            <AnimatePresence>
              {unit.isFirstCompleted && unit.state === "complete" && (
                <motion.button
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ type: "spring", stiffness: 300, damping: 20 }}
                  className="mt-1 text-left font-sans text-[11px] font-bold text-accent hover:text-accent-2 transition-colors cursor-pointer flex items-center gap-1"
                >
                  Read {unit.name} <span className="text-[14px]">→</span>
                </motion.button>
              )}
            </AnimatePresence>
          </div>
        ))}
      </div>
    </div>
  );
}
