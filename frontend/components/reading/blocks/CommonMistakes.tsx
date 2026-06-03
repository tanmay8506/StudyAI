"use client";

import { motion } from "framer-motion";
import { parseCommonMistakes } from "@/lib/parseField";

/**
 * CommonMistakesBlock — Highlights typical student errors.
 * 
 * Uses the harsh var(--red-dim) to clearly delineate from standard instruction.
 */

interface CommonMistakesBlockProps {
  mistakesData: unknown;
}

export function CommonMistakesBlock({ mistakesData }: CommonMistakesBlockProps) {
  const mistakes = parseCommonMistakes(mistakesData);

  if (!mistakes || mistakes.length === 0) return null;

  return (
    <motion.section 
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.4 }}
      className="flex flex-col gap-3 mt-8"
    >
      <div className="flex flex-row items-center gap-4 mb-2">
        <span className="font-sans text-[10px] uppercase tracking-widest text-text-tertiary">
          Common Mistakes
        </span>
        <div className="w-[32px] h-[1px] bg-border-default" />
      </div>

      <div className="flex flex-col gap-3">
        {mistakes.map((item, idx) => (
          <div 
            key={idx}
            className="bg-red-dim border border-[rgba(232,90,74,0.12)] rounded-lg p-[14px_16px] flex flex-row items-center gap-4"
          >
            {/* The bold red cross icon */}
            <div className="flex-shrink-0 text-red">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </div>

            {/* The Mistake Text */}
            <div className="flex-1 font-sans text-[13px] text-text-secondary leading-snug">
              {item.mistake}
            </div>

            {/* Marks Lost Pill */}
            {item.marks_lost && (
              <div className="flex-shrink-0 font-sans text-[10px] font-bold text-red bg-[rgba(232,90,74,0.1)] border border-[rgba(232,90,74,0.2)] rounded-full px-2.5 py-1 uppercase tracking-wide">
                {item.marks_lost}
              </div>
            )}
          </div>
        ))}
      </div>
    </motion.section>
  );
}
