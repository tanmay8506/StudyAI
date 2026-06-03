"use client";

/**
 * TierBadge — Communicates the confidence level of the generated notes.
 * 
 * Supports exactly 4 states (Tier 1-4) with precise token mappings.
 */

interface TierBadgeProps {
  tier: 1 | 2 | 3 | 4;
}

export function TierBadge({ tier }: TierBadgeProps) {
  const getTierStyles = () => {
    switch (tier) {
      case 1:
        return {
          bg: "bg-green-dim",
          border: "border-[rgba(90,184,122,0.3)]",
          text: "text-green",
          label: "TIER 1 · PYQ CALIBRATED"
        };
      case 2:
        return {
          bg: "bg-accent-dim2",
          border: "border-[rgba(232,200,74,0.3)]",
          text: "text-accent",
          label: "TIER 2 · PARTIAL CALIBRATION"
        };
      case 3:
        return {
          bg: "bg-red-dim",
          border: "border-[rgba(232,90,74,0.2)]",
          text: "text-red",
          label: "TIER 3 · SYLLABUS BASED"
        };
      case 4:
        return {
          bg: "bg-red-dim",
          border: "border-[rgba(232,90,74,0.2)]",
          text: "text-red",
          label: "TIER 4 · INSUFFICIENT DATA"
        };
    }
  };

  const { bg, border, text, label } = getTierStyles();

  // Split label to apply different fonts as per spec (DM Mono + Syne combo)
  const parts = label.split(" · ");

  return (
    <div className={`inline-flex items-center px-4 py-2 rounded-full border ${border} ${bg}`}>
      <span className={`font-mono text-[14px] font-bold ${text} mr-2`}>
        {parts[0]}
      </span>
      <span className={`font-sans text-[12px] font-medium ${text} opacity-90`}>
        · {parts[1]}
      </span>
    </div>
  );
}
