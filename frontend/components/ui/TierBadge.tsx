import React, { useState } from 'react';
import { Info } from 'lucide-react';

export interface TierBadgeProps {
  tier: 1 | 2 | 3 | 4;
  pyqYearsAvailable?: number;
}

export function TierBadge({ tier, pyqYearsAvailable }: TierBadgeProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  
  const tierConfig = {
    1: { color: 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20', label: 'Tier 1 — Fully Calibrated', desc: `Fully calibrated — based on ${pyqYearsAvailable || 'multiple'} NEP question papers. All content exam-verified.` },
    2: { color: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20', label: 'Tier 2 — Partially Calibrated', desc: `Partially calibrated — based on ${pyqYearsAvailable || 1} NEP question paper(s). Some content estimated.` },
    3: { color: 'bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/20', label: 'Tier 3 — Syllabus Based', desc: 'Syllabus-based — no NEP question papers publicly available.' },
    4: { color: 'bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20', label: 'Tier 4 — Insufficient Data', desc: 'Insufficient data — notes cannot be generated yet.' }
  };
  
  const config = tierConfig[tier] || tierConfig[4];

  return (
    <div 
      className="relative inline-flex items-center"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      onClick={() => setShowTooltip(!showTooltip)}
    >
      <div className={`px-2.5 py-1 rounded-full border flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider cursor-pointer ${config.color}`}>
        <span>{config.label}</span>
        <Info className="w-3.5 h-3.5 opacity-70" />
      </div>
      
      {showTooltip && (
        <div className="absolute top-full left-0 mt-2 w-64 p-3 bg-popover text-popover-foreground text-sm border border-border shadow-md rounded-md z-10 animate-in fade-in zoom-in-95 duration-200">
          {config.desc}
        </div>
      )}
    </div>
  );
}
