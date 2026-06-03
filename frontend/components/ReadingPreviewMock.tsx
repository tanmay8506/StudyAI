"use client";

import { motion } from "framer-motion";
import { scaleIn } from "@/lib/animations";

/**
 * ReadingPreviewMock — Static dummy content representing the reading page.
 * 
 * Used in Section 5 of the Manifesto. Not connected to any data.
 * Built to answer "What do I actually get?" before the user converts.
 */
export function ReadingPreviewMock() {
  return (
    <div className="w-full flex flex-col items-center">
      <div className="font-sans text-[10px] uppercase text-text-tertiary tracking-wider mb-8">
        What your unit looks like
      </div>

      <motion.div
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-20%" }}
        variants={scaleIn}
        className="relative w-full max-w-[720px]"
      >
        {/* Faint amber glow behind the card */}
        <div 
          className="absolute inset-0 z-0 pointer-events-none"
          style={{
            background: "radial-gradient(circle, rgba(232,200,74,0.05) 0%, transparent 60%)",
            transform: "scale(1.2)"
          }}
        />

        {/* The Mock Card */}
        <div 
          className="relative z-10 w-full bg-bg-base border border-border-default rounded-xl overflow-hidden"
          style={{ 
            boxShadow: "0 40px 80px rgba(0,0,0,0.5)",
            transform: "scale(0.8)",
            transformOrigin: "top center"
          }}
        >
          {/* Mock Header */}
          <div className="p-8 border-b border-border-subtle bg-bg-card">
            <div className="font-sans text-[11px] uppercase text-text-tertiary mb-4">
              B.SC. (H) MATHEMATICS · SEMESTER 3
            </div>
            <div className="font-serif text-[40px] text-text-primary leading-tight mb-4">
              Riemann Integration
            </div>
            <div className="font-sans text-[14px] text-text-secondary leading-relaxed max-w-[560px]">
              Darboux sums, integrability conditions, and the fundamental theorem of calculus. Critical for advanced analysis.
            </div>
          </div>

          <div className="p-8 flex flex-col gap-8 bg-bg-base">
            {/* Mock Rapid Revision Card */}
            <div className="bg-bg-card border border-border-default rounded-xl overflow-hidden border-l-[3px] border-l-red">
              <div className="flex justify-between items-center p-4 px-5">
                <div className="font-sans font-bold text-[17px] text-text-primary">
                  Darboux Integrability
                </div>
                <div className="font-mono text-[10px] px-2 py-1 bg-red-dim text-red border border-[rgba(232,90,74,0.2)] rounded-full">
                  HIGH YIELD
                </div>
              </div>
              <div className="grid grid-cols-3 border-t border-border-subtle">
                <div className="p-3 px-5 border-r border-border-subtle">
                  <div className="font-sans text-[9px] uppercase text-text-tertiary mb-1">ONE-LINE DEF</div>
                  <div className="font-sans text-[13px] text-text-primary">Upper integral equals lower integral.</div>
                </div>
                <div className="p-3 px-5 border-r border-border-subtle">
                  <div className="font-sans text-[9px] uppercase text-text-tertiary mb-1">KEY FORMULA</div>
                  <div className="font-mono text-[12px] text-accent">U(P,f) = L(P,f)</div>
                </div>
                <div className="p-3 px-5">
                  <div className="font-sans text-[9px] uppercase text-text-tertiary mb-1">EXAMINER PATTERN</div>
                  <div className="font-serif italic text-[14px] text-text-secondary">Always tests step functions first.</div>
                </div>
              </div>
            </div>

            {/* Mock Definition Block */}
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="font-sans text-[10px] uppercase text-text-tertiary tracking-widest">DEFINITION</div>
                <div className="flex-1 h-[1px] bg-border-default" />
              </div>
              <div className="relative bg-bg-card border border-border-default rounded-xl p-5 px-6 font-serif text-[18px] text-text-primary leading-relaxed">
                <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-[rgba(232,200,74,0.6)]" />
                Let f be a bounded function on [a,b]. f is Riemann integrable if and only if for every ε &gt; 0, there exists a partition P such that U(P,f) - L(P,f) &lt; ε.
              </div>
            </div>

            {/* Mock Examiner Note */}
            <div className="bg-[rgba(232,200,74,0.05)] border border-[rgba(232,200,74,0.15)] rounded-xl p-5 px-6">
              <div className="font-sans text-[14px] text-text-primary mb-3">
                Students often confuse Darboux integrability with Riemann sums. The 2019 and 2021 papers specifically tested the equivalence proof.
              </div>
              <div className="h-[1px] bg-border-subtle opacity-50 mb-3" />
              <div className="flex gap-2">
                <div className="flex gap-1 items-center bg-[rgba(255,255,255,0.04)] px-2 py-1 rounded">
                  <span className="font-sans text-[11px] text-text-secondary">prove equivalence</span>
                  <span className="font-mono text-[10px] text-accent">×3</span>
                </div>
              </div>
            </div>
            
          </div>
        </div>
      </motion.div>
    </div>
  );
}
