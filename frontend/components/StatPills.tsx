"use client";

import { motion } from "framer-motion";

/**
 * StatPills — The data row at the bottom of the Homepage.
 * 
 * Separated by 1px vertical lines, no card background.
 */

interface StatPillItem {
  value: string;
  label: string;
}

interface StatPillsProps {
  items: StatPillItem[];
}

export function StatPills({ items }: StatPillsProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      // Delay 740ms per spec page load sequence
      transition={{ delay: 0.74, duration: 0.8 }}
      className="flex flex-row items-center justify-center mt-16"
    >
      {items.map((item, index) => (
        <div key={index} className="flex flex-row items-center">
          <div className="flex flex-col items-center sm:items-start px-6">
            <div className="font-serif italic text-[18px] text-text-primary leading-none mb-1">
              {item.value}
            </div>
            <div className="font-sans text-[10px] uppercase text-text-tertiary tracking-[0.12em] leading-none">
              {item.label}
            </div>
          </div>
          {/* Vertical line separator */}
          {index < items.length - 1 && (
            <div className="w-[1px] h-8 bg-border-default" />
          )}
        </div>
      ))}
    </motion.div>
  );
}
