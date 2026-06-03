"use client";

/**
 * PYQYearPills — Displays the years of past papers that have been successfully calibrated.
 * 
 * Only renders on Tier 1 and Tier 2 papers where PYQ calibration was actually successful.
 */

interface PYQYearPillsProps {
  tier: 1 | 2 | 3 | 4;
  years: string[];
}

export function PYQYearPills({ tier, years }: PYQYearPillsProps) {
  // Only render on Tier 1 and Tier 2
  if (tier === 3 || tier === 4 || years.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-row flex-wrap gap-2">
      {years.map((year) => (
        <div 
          key={year}
          className="font-mono text-[11px] font-bold text-accent bg-accent-dim border border-[rgba(232,200,74,0.2)] rounded-full px-3 py-1.5"
        >
          {year}
        </div>
      ))}
    </div>
  );
}
