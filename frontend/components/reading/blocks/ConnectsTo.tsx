"use client";

import { motion } from "framer-motion";

/**
 * ConnectsToBlock — The bridge linking this topic to the next one.
 * 
 * Features a full-width card with a hover effect on the arrow to draw
 * the student forward through the syllabus logically.
 */

interface ConnectsToData {
  nextTopicName: string;
  bridgeReason: string;
  nextTopicId?: string;
}

interface ConnectsToBlockProps {
  data: ConnectsToData;
  onNavigate?: (id: string) => void;
}

export function ConnectsToBlock({ data, onNavigate }: ConnectsToBlockProps) {
  if (!data) return null;

  return (
    <motion.section 
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.4 }}
      className="mt-[24px]"
    >
      <div 
        onClick={() => {
          if (data.nextTopicId && onNavigate) onNavigate(data.nextTopicId);
        }}
        className="group bg-bg-card border border-border-default rounded-xl p-[14px_20px] flex flex-row items-center justify-between cursor-pointer transition-colors hover:border-border-strong hover:bg-bg-card-hover"
      >
        <div className="flex flex-col gap-1.5">
          <span className="font-sans text-[10px] uppercase tracking-widest text-text-tertiary">
            Next Topic
          </span>
          <span className="font-sans text-[14px] font-semibold text-text-primary">
            {data.nextTopicName}
          </span>
          <span className="font-sans text-[12px] text-text-secondary leading-snug">
            {data.bridgeReason}
          </span>
        </div>

        {/* The Arrow */}
        <motion.div 
          className="text-text-tertiary group-hover:text-accent p-2"
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          variants={{
            initial: { x: 0 },
            hover: { x: 4 }
          }}
          initial="initial"
          whileHover="hover"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </motion.div>
      </div>
    </motion.section>
  );
}
