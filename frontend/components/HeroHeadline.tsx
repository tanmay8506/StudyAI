"use client";

import { MaskReveal } from "@/components/MaskReveal";

/**
 * HeroHeadline — Typographic centerpiece of the Homepage.
 * 
 * Uses the standard MaskReveal variant for an editorial appearance.
 * Line 1 reveals first. Line 2 follows with a 120ms stagger.
 */
export function HeroHeadline() {
  return (
    <div className="flex flex-col items-center sm:items-start text-center sm:text-left mb-6">
      <MaskReveal
        text="Your DU exam,"
        variant="standard"
        // 300ms base delay per sequence
        delay={30} // Will map to 300ms depending on mask reveal internals
        className="font-serif text-[clamp(44px,7vw,72px)] leading-[1.1] tracking-[-0.02em] text-text-primary"
      />
      <MaskReveal
        text="precisely decoded."
        variant="standard"
        // 420ms delay (120ms after line 1)
        delay={42} 
        className="font-serif italic text-[clamp(44px,7vw,72px)] leading-[1.1] tracking-[-0.02em] text-text-primary mt-1"
      />
    </div>
  );
}
