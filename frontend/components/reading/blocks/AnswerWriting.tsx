"use client";

import { motion } from "framer-motion";

/**
 * AnswerWritingBlock — The blueprint for long-form answers.
 * 
 * Specifically designed for high-value questions (6+ marks).
 * If the topic marks are less than 6, this component returns null.
 */

interface AnswerStep {
  number: string;
  text: string;
}

interface MarkDistribution {
  label: string;
  marks: string; // e.g. "+2"
}

interface AnswerWritingData {
  steps: AnswerStep[];
  distribution: MarkDistribution[];
}

interface AnswerWritingBlockProps {
  topicMarks: number;
  data: AnswerWritingData;
}

export function AnswerWritingBlock({ topicMarks, data }: AnswerWritingBlockProps) {
  // Strict render gate: Only render if topic marks >= 6
  if (topicMarks < 6) return null;

  return (
    <motion.section 
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.4 }}
      className="mt-8"
    >
      <div className="bg-bg-card border border-border-default rounded-xl overflow-hidden">
        
        {/* Header Strip */}
        <div className="flex flex-row items-center justify-between p-[12px_16px] bg-bg-card-hover border-b border-border-subtle">
          <span className="font-sans text-[12px] font-bold uppercase tracking-wide text-text-primary">
            6-Mark Blueprint &middot; Answer Structure
          </span>
          <span className="font-mono text-[10px] text-blue bg-blue-dim border border-[rgba(90,154,232,0.2)] rounded-full px-2 py-0.5">
            6+ MARKS
          </span>
        </div>

        {/* Steps List */}
        <div className="flex flex-col border-b border-border-subtle">
          {data.steps.map((step, idx) => (
            <div 
              key={idx}
              className={`flex flex-row items-start gap-4 p-[12px_20px] ${
                idx !== data.steps.length - 1 ? 'border-b border-border-subtle' : ''
              }`}
            >
              <span className="font-mono text-[11px] text-accent mt-0.5 w-[24px] flex-shrink-0">
                {step.number}
              </span>
              <span className="font-sans text-[13px] text-text-secondary leading-relaxed flex-1">
                {step.text}
              </span>
            </div>
          ))}
        </div>

        {/* Marks Distribution Pills */}
        {data.distribution && data.distribution.length > 0 && (
          <div className="p-[16px_20px] flex flex-row flex-wrap gap-2 bg-bg-base">
            <span className="font-sans text-[10px] uppercase text-text-tertiary mt-1 mr-2 tracking-widest">
              Mark Distribution
            </span>
            {data.distribution.map((dist, idx) => (
              <div 
                key={idx}
                className="flex items-center gap-1.5 font-sans text-[11px] text-text-secondary bg-[rgba(255,255,255,0.04)] border border-border-default rounded-md px-2 py-1"
              >
                <span>{dist.label}</span>
                <span className="font-mono text-[10px] text-blue font-medium">
                  {dist.marks}
                </span>
              </div>
            ))}
          </div>
        )}

      </div>
    </motion.section>
  );
}
