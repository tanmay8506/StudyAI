"use client";

import { motion } from "framer-motion";

/**
 * PYQBlock — Presents Previous Year Questions with an authentic, exam-paper feel.
 * 
 * Uses Instrument Serif for the question text. If the question has high
 * recency weight (>= 1.5), it gets a prominent amber border.
 */

interface PYQItem {
  id: string;
  year: string;
  isConfirmed: boolean;
  marks: number;
  question: string;
  recencyWeight: number;
  keySteps: string[];
}

interface PYQBlockProps {
  questions: PYQItem[];
}

export function PYQBlock({ questions }: PYQBlockProps) {
  if (!questions || questions.length === 0) return null;

  return (
    <motion.section 
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.4 }}
      className="flex flex-col gap-4 mt-8"
    >
      {/* Section Label Row */}
      <div className="flex flex-row items-center gap-4 mb-2">
        <span className="font-sans text-[10px] uppercase tracking-widest text-text-tertiary">
          Previous Year Questions
        </span>
        <div className="w-[32px] h-[1px] bg-border-default" />
      </div>

      <div className="flex flex-col gap-4">
        {questions.map((pyq) => {
          const isHighYield = pyq.recencyWeight >= 1.5;
          const borderClass = isHighYield 
            ? "border-[rgba(232,200,74,0.2)]" // Amber border for high recency
            : "border-border-default";
            
          return (
            <div 
              key={pyq.id}
              className={`bg-bg-card border ${borderClass} rounded-xl p-[16px_20px] flex flex-col gap-4`}
            >
              {/* Header: Year Badge + Marks */}
              <div className="flex flex-row justify-between items-center">
                <div className="flex items-center gap-2">
                  <span 
                    className={`font-mono text-[10px] uppercase font-bold px-2 py-0.5 rounded-sm flex items-center gap-1 ${
                      pyq.isConfirmed 
                        ? "bg-[rgba(90,184,122,0.1)] text-green" 
                        : "bg-bg-raised text-text-tertiary"
                    }`}
                  >
                    {pyq.isConfirmed && (
                      <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M20 6L9 17l-5-5" />
                      </svg>
                    )}
                    {pyq.year}
                  </span>
                </div>
                <span className="font-sans text-[11px] text-text-secondary bg-[rgba(255,255,255,0.04)] border border-border-default rounded-md px-2 py-0.5">
                  {pyq.marks} Marks
                </span>
              </div>

              {/* Authentic Question Text */}
              <div className="font-serif text-[15px] text-text-primary leading-relaxed tracking-wide">
                {pyq.question}
              </div>

              {/* Key Steps for Solution */}
              {pyq.keySteps && pyq.keySteps.length > 0 && (
                <div className="flex flex-col gap-1.5 pt-3 border-t border-border-subtle mt-1">
                  {pyq.keySteps.map((step, idx) => (
                    <div key={idx} className="flex flex-row items-start gap-2">
                      <span className="text-accent mt-[1px]">→</span>
                      <span className="font-mono text-[11px] text-text-tertiary leading-relaxed">
                        {step}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </motion.section>
  );
}
