"use client";

import { motion, AnimatePresence } from "framer-motion";
import { parseQuickCheck } from "@/lib/parseField";
import React, { useState } from "react";
import { ParticleBurst } from "../ParticleBurst";

/**
 * QuickCheckBlock — The subjective self-assessment friction engine.
 * 
 * Never exposes the raw backend answer.
 * Input triggers the self-assessment console.
 * "Full Marks" triggers the particle burst physics and locks the input.
 */

interface QuickCheckItem {
  id: string;
  rawData: unknown;
}

interface QuickCheckBlockProps {
  checks: QuickCheckItem[];
}

export function QuickCheckBlock({ checks }: QuickCheckBlockProps) {
  if (!checks || checks.length === 0) return null;

  return (
    <motion.section 
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.4 }}
      className="flex flex-col gap-4 mt-8"
    >
      <div className="flex flex-row items-center gap-4 mb-2">
        <span className="font-sans text-[10px] uppercase tracking-widest text-text-tertiary">
          Quick Checks
        </span>
        <div className="w-[32px] h-[1px] bg-border-default" />
      </div>

      <div className="flex flex-col gap-4">
        {checks.map((check) => (
          <QuickCheckCard key={check.id} data={check.rawData} />
        ))}
      </div>
    </motion.section>
  );
}

// -------------------------------------------------------------
// INDIVIDUAL QUESTION CARD WITH STATE
// -------------------------------------------------------------

function QuickCheckCard({ data }: { data: unknown }) {
  const parsed = parseQuickCheck(data);
  const [value, setValue] = useState("");
  const [assessment, setAssessment] = useState<"unsure" | "partial" | "full" | null>(null);
  
  // Track burst coordinates relative to the viewport
  const [burstCoords, setBurstCoords] = useState<{ x: number; y: number } | null>(null);

  if (!parsed || !parsed.question) return null;

  const isCompleted = assessment !== null;
  const isFullMarks = assessment === "full";
  
  // Determine border style
  const borderClass = isFullMarks 
    ? "border-[rgba(90,184,122,1)] bg-[rgba(90,184,122,0.05)]" 
    : isCompleted 
      ? "border-border-strong bg-bg-card"
      : "border-border-default bg-bg-card";

  const handleAssessment = (e: React.MouseEvent, type: "unsure" | "partial" | "full") => {
    setAssessment(type);
    
    if (type === "full") {
      // Fire particle burst exactly at click coordinates
      setBurstCoords({ x: e.clientX, y: e.clientY });
    }
  };

  return (
    <div className={`relative border border-dashed rounded-xl p-[12px_16px] flex flex-col gap-3 transition-colors duration-300 ${borderClass}`}>
      
      {/* Particle Burst Overlay */}
      {burstCoords && (
        <ParticleBurst 
          x={burstCoords.x} 
          y={burstCoords.y} 
          onComplete={() => setBurstCoords(null)} 
        />
      )}

      {/* The Question */}
      <div className="font-sans text-[14px] text-text-primary leading-relaxed">
        {parsed.question}
      </div>

      {/* The Input Field */}
      <textarea 
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={isCompleted}
        placeholder="Draft your answer..."
        rows={2}
        className={`w-full bg-bg-base border border-border-default rounded-md p-3 font-sans text-[13px] text-text-secondary placeholder:text-text-tertiary outline-none transition-all resize-none ${
          isCompleted ? "opacity-60 cursor-not-allowed" : "focus:border-[rgba(232,200,74,0.3)]"
        }`}
      />

      {/* Self-Assessment Console */}
      <AnimatePresence>
        {value.length > 0 && !isCompleted && (
          <motion.div 
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4, transition: { duration: 0.2 } }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
            className="flex flex-row items-center justify-between mt-2 pt-3 border-t border-border-subtle"
          >
            <span className="font-sans text-[11px] text-text-tertiary">
              How did you do?
            </span>
            <div className="flex items-center gap-2">
              <button 
                onClick={(e) => handleAssessment(e, "unsure")}
                className="px-3 py-1 font-sans text-[11px] text-text-secondary border border-border-default rounded hover:bg-bg-raised transition-colors"
              >
                Unsure
              </button>
              <button 
                onClick={(e) => handleAssessment(e, "partial")}
                className="px-3 py-1 font-sans text-[11px] text-text-secondary border border-border-default rounded hover:bg-bg-raised transition-colors"
              >
                Partial
              </button>
              <button 
                onClick={(e) => handleAssessment(e, "full")}
                className="px-3 py-1 font-sans text-[11px] font-bold text-accent border border-[rgba(232,200,74,0.3)] bg-accent-dim rounded hover:bg-accent hover:text-bg-base transition-colors"
              >
                Full Marks
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Post-Assessment Status */}
      {isCompleted && (
        <div className="flex flex-row justify-end mt-1">
          <span className={`font-sans text-[10px] uppercase font-bold tracking-widest ${
            isFullMarks ? "text-green" : "text-text-tertiary"
          }`}>
            {assessment === "full" ? "✓ Full Marks Recorded" : `${assessment} recorded`}
          </span>
        </div>
      )}
    </div>
  );
}
