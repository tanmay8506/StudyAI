"use client";

import { motion } from "framer-motion";
import { fadeUp } from "@/lib/animations";

/**
 * PYQSubmissionBanner — Call to action for users to upload past papers.
 * 
 * Only renders on Tier 3 and Tier 4 papers where there is insufficient
 * data for automatic calibration.
 */

interface PYQSubmissionBannerProps {
  tier: 1 | 2 | 3 | 4;
}

export function PYQSubmissionBanner({ tier }: PYQSubmissionBannerProps) {
  // Only render on Tier 3 and Tier 4
  if (tier === 1 || tier === 2) {
    return null;
  }

  return (
    <motion.div
      variants={fadeUp}
      initial="hidden"
      animate="visible"
      transition={{ delay: 0.2, duration: 0.6 }}
      className="w-full flex flex-col sm:flex-row sm:items-center justify-between p-5 border border-dashed border-border-default bg-bg-card rounded-xl gap-4 mt-6"
    >
      <div className="flex flex-col gap-1">
        <h4 className="font-sans text-[13px] font-bold text-text-primary">
          Help calibrate this paper
        </h4>
        <p className="font-sans text-[12px] text-text-secondary">
          Upload previous year questions (PYQs) to improve agent accuracy.
        </p>
      </div>

      <button className="flex items-center justify-center gap-2 px-4 py-2 bg-border-subtle hover:bg-border-default text-text-primary font-sans text-[12px] font-bold rounded-lg transition-colors duration-150">
        <svg 
          className="w-4 h-4" 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={2} 
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" 
          />
        </svg>
        Upload PYQ
      </button>
    </motion.div>
  );
}
