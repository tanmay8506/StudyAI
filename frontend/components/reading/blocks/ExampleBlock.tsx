"use client";

import { motion } from "framer-motion";
import { parseExample, ExampleParsed } from "@/lib/parseField";
import { MathText } from "@/components/MathText";

/**
 * VerifiedBadge — A small checkmark icon that draws itself on mount.
 */
function VerifiedBadge() {
  return (
    <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-sm bg-[rgba(90,184,122,0.1)] border border-[rgba(90,184,122,0.2)] text-green">
      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <motion.path 
          d="M20 6L9 17l-5-5"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.5, ease: "easeOut", delay: 0.2 }}
        />
      </svg>
      <span className="font-sans text-[9px] uppercase tracking-wider font-bold">Verified</span>
    </div>
  );
}

/**
 * ExampleBlock — A structured breakdown of mathematical/logical problems.
 */
interface ExampleBlockProps {
  exampleData: unknown;
}

export function ExampleBlock({ exampleData }: ExampleBlockProps) {
  const example = parseExample(exampleData);

  if (!example) return null;

  // Render Math via MathText

  return (
    <motion.section 
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.4 }}
      className="flex flex-col mt-8"
    >
      <div className="bg-bg-card border border-border-default rounded-xl overflow-hidden">
        
        {/* Header Strip */}
        <div className="flex flex-row items-center justify-between p-[10px_16px] bg-bg-card-hover border-b border-border-subtle">
          <span className="font-sans text-[10px] uppercase tracking-widest text-text-tertiary">
            {example.example_type || "Worked Example"}
          </span>
          {example.verified && <VerifiedBadge />}
        </div>

        {/* Problem Statement */}
        <div className="p-[16px_20px] border-b border-border-subtle font-sans text-[14px] text-text-primary leading-relaxed">
          <MathText content={example.problem} />
        </div>

        {/* Steps Breakdown */}
        {example.steps.length > 0 && (
          <div className="flex flex-col py-4">
            {example.steps.map((step, idx) => {
              // Ensure number format "01.", "02."
              const stepNum = step.number ? step.number : (idx + 1).toString().padStart(2, "0") + ".";
              return (
                <div key={idx} className="flex flex-row gap-[12px] p-[6px_20px] items-start">
                  <span className="font-mono text-[10px] text-text-tertiary mt-[2px] w-[24px] flex-shrink-0">
                    {stepNum}
                  </span>
                  <span className="font-mono text-[13px] text-text-secondary overflow-x-auto scrollbar-none leading-relaxed">
                    <MathText content={step.text} />
                  </span>
                </div>
              );
            })}
          </div>
        )}

        <div className="p-[16px_20px]">
          <div className="bg-accent-dim border border-[rgba(232,200,74,0.2)] rounded-lg p-3 text-center font-mono text-[16px] font-medium text-accent overflow-x-auto scrollbar-none">
            <MathText content={example.answer} />
          </div>
        </div>

        {/* Common Error Callout */}
        {example.common_error && (
          <div className="mx-[20px] mb-[20px] bg-[rgba(255,200,50,0.05)] border border-[rgba(255,200,50,0.12)] rounded-lg p-[12px_16px] flex flex-row gap-3 items-start">
            <span className="font-sans text-[10px] uppercase font-bold text-accent tracking-wider whitespace-nowrap mt-0.5">
              ⚠ Common Error
            </span>
            <span className="font-sans text-[12px] text-text-secondary leading-snug flex-1">
              {example.common_error}
            </span>
          </div>
        )}
      </div>
    </motion.section>
  );
}
