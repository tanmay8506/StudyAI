"use client";

import { MaskReveal } from "@/components/MaskReveal";
import { TierBadge } from "./TierBadge";
import { Last4HoursButton } from "./Last4HoursButton";
import { PYQYearPills } from "./PYQYearPills";
import { PYQSubmissionBanner } from "./PYQSubmissionBanner";

/**
 * PaperHeader — The top section of the Paper Overview page.
 * 
 * Establishes authority immediately. Displays the paper title with a MaskReveal,
 * structural metadata, and status indicators (Tier, PYQs).
 */

interface PaperHeaderProps {
  upc: string;
  title: string;
  tier: 1 | 2 | 3 | 4;
  department: string;
  programme: string;
  semester: string;
  type: string;
  pyqYears?: string[];
}

export function PaperHeader({
  upc,
  title,
  tier,
  department,
  programme,
  semester,
  type,
  pyqYears = []
}: PaperHeaderProps) {
  const metadata = [
    { label: "DEPT", value: department },
    { label: "PROGRAMME", value: programme },
    { label: "SEMESTER", value: semester },
    { label: "TYPE", value: type },
  ];

  // Prevent orphaned words in headline
  const formattedTitle = title.replace(/ ([^ ]+)$/, "\u00A0$1");

  return (
    <div className="w-full flex flex-col relative">
      
      {/* Top right action: Last 4 Hours Button */}
      <div className="absolute top-0 right-0 hidden sm:block z-20">
        <Last4HoursButton />
      </div>

      <div className="font-mono text-[11px] text-text-tertiary mb-4">
        UPC · <span className="font-medium">{upc}</span>
      </div>

      {/* Title */}
      <div className="mb-8 pr-32">
        <MaskReveal 
          text={formattedTitle}
          variant="standard"
          className="font-serif text-[clamp(40px,5vw,52px)] text-text-primary tracking-[-0.02em] leading-tight"
        />
      </div>

      {/* Metadata Row */}
      <div className="flex flex-wrap gap-y-4 items-center mb-8">
        {metadata.map((item, index) => (
          <div key={item.label} className="flex items-center">
            <div className="flex flex-col gap-1 pr-6">
              <span className="font-sans text-[10px] uppercase text-text-tertiary tracking-wider">
                {item.label}
              </span>
              <span className="font-sans text-[14px] text-text-secondary">
                {item.value}
              </span>
            </div>
            {index < metadata.length - 1 && (
              <div className="w-[1px] h-8 bg-border-subtle mr-6" />
            )}
          </div>
        ))}
      </div>

      {/* Badges & Pills Row */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-10">
        <TierBadge tier={tier} />
        <PYQYearPills tier={tier} years={pyqYears} />
      </div>

      {/* Conditionally rendered banner for lower tiers */}
      <PYQSubmissionBanner tier={tier} />

      {/* Mobile Last 4 Hours Button */}
      <div className="mt-4 sm:hidden">
        <Last4HoursButton />
      </div>

    </div>
  );
}
