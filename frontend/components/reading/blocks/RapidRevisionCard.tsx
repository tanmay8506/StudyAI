"use client";

import { motion } from "framer-motion";
import { parseField } from "@/lib/parseField";
import { MathText } from "@/components/MathText";

/**
 * RapidRevisionCard — The visual anchor of every topic.
 * 
 * Always visible. Clicking this card toggles the visibility of the rest
 * of the topic's content blocks.
 */

export type TopicPriority = "high" | "medium" | "low" | "none";

interface RapidRevisionData {
  topicName: string;
  priority: TopicPriority;
  oneLineDef: unknown; // Expecting string or JSON string from AI
  keyFormula: unknown;
  examinerPattern: unknown;
}

interface RapidRevisionCardProps {
  data: RapidRevisionData;
  isExpanded: boolean;
  onToggle: () => void;
}

export function RapidRevisionCard({ data, isExpanded, onToggle }: RapidRevisionCardProps) {
  const def = parseField(data.oneLineDef);
  const formula = parseField(data.keyFormula);
  const pattern = parseField(data.examinerPattern);

  const getPriorityStyles = () => {
    switch (data.priority) {
      case "high": return { border: "border-l-[rgba(232,90,74,1)]", badge: "bg-red text-bg-base", label: "HIGH YIELD" };
      case "medium": return { border: "border-l-[rgba(232,200,74,1)]", badge: "bg-accent text-bg-base", label: "MEDIUM YIELD" };
      case "low": return { border: "border-l-[rgba(255,255,255,0.4)]", badge: "bg-text-tertiary text-bg-base", label: "LOW YIELD" };
      case "none":
      default: return { border: "border-l-border-subtle", badge: "bg-border-subtle text-text-secondary", label: "NEVER ASKED" };
    }
  };

  const { border, badge, label } = getPriorityStyles();

  // MathText handles math parsing securely

  return (
    <motion.div
      onClick={onToggle}
      whileInView={{ y: 0, opacity: 1 }}
      initial={{ y: 12, opacity: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.4 }}
      className={`bg-bg-card border border-border-default rounded-xl overflow-hidden cursor-pointer transition-colors duration-150 hover:border-border-strong border-l-[3px] ${border}`}
    >
      {/* Top Strip */}
      <div className="flex flex-row justify-between items-center px-5 py-4">
        <h3 className="font-sans text-[17px] font-bold text-text-primary">
          {data.topicName}
        </h3>
        <div className="flex items-center gap-3">
          <div className={`font-sans text-[9px] uppercase font-bold tracking-wider px-2 py-1 rounded ${badge}`}>
            {label}
          </div>
          {/* Chevron indicator for expansion */}
          <motion.div
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
            className="text-text-tertiary"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </motion.div>
        </div>
      </div>

      {/* Three Column Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 border-t border-border-subtle">
        
        {/* Col 1: One-Line Def */}
        <div className="flex flex-col gap-1.5 p-[12px_20px] md:border-r border-border-subtle">
          <span className="font-sans text-[9px] uppercase tracking-widest text-text-tertiary">
            One-Line Def
          </span>
          <span className="font-sans text-[13px] text-text-primary leading-tight">
            <MathText content={def} />
          </span>
        </div>

        {/* Col 2: Key Formula */}
        <div className="flex flex-col gap-1.5 p-[12px_20px] md:border-r border-border-subtle">
          <span className="font-sans text-[9px] uppercase tracking-widest text-text-tertiary">
            Key Formula
          </span>
          <span className="font-mono text-[12px] text-accent leading-tight overflow-x-auto scrollbar-none">
            <MathText content={formula} />
          </span>
        </div>

        {/* Col 3: Examiner Pattern */}
        <div className="flex flex-col gap-1.5 p-[12px_20px]">
          <span className="font-sans text-[9px] uppercase tracking-widest text-text-tertiary">
            Examiner Pattern
          </span>
          <span className="font-serif italic text-[14px] text-text-secondary leading-tight">
            <MathText content={pattern} />
          </span>
        </div>

      </div>
    </motion.div>
  );
}
