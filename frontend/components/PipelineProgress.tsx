"use client";

import { motion } from "framer-motion";

/**
 * PipelineProgress — The top header strip and progress bar.
 * 
 * Shows the paper name, UPC, and the current overall completion status
 * of the 12 agents in the pipeline.
 */

interface PipelineProgressProps {
  paperName: string;
  upc: string;
  completedAgents: number;
  totalAgents?: number;
  estimatedTime?: string;
}

export function PipelineProgress({
  paperName,
  upc,
  completedAgents,
  totalAgents = 12,
  estimatedTime = "00:45"
}: PipelineProgressProps) {
  const progressPercent = completedAgents / totalAgents;

  return (
    <div className="w-full bg-bg-raised border-b border-border-subtle">
      <div className="flex flex-row items-center justify-between px-8 py-4">
        <div className="font-sans font-bold text-[14px] text-text-primary">
          {paperName}
        </div>
        <div className="font-mono text-[12px] text-text-tertiary">
          UPC · {upc}
        </div>
      </div>

      <div className="px-8 pb-3">
        <div className="font-mono text-[10px] uppercase text-text-tertiary tracking-widest mb-2 flex justify-between">
          <span>PIPELINE EXECUTION · {completedAgents}/{totalAgents} AGENTS COMPLETE</span>
          <span>EST. {estimatedTime}</span>
        </div>
        
        {/* Progress Bar Track */}
        <div className="w-full h-[1px] bg-border-subtle relative">
          {/* Progress Bar Fill */}
          <motion.div
            className="absolute left-0 top-0 bottom-0 bg-accent origin-left"
            initial={{ scaleX: 0 }}
            animate={{ scaleX: progressPercent }}
            transition={{ type: "spring", stiffness: 100, damping: 20 }}
          />
        </div>
      </div>
    </div>
  );
}
