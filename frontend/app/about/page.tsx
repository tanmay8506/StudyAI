"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { PageTransition } from "@/components/PageTransition";
import { ManifestoSection } from "@/components/ManifestoSection";
import { MaskReveal } from "@/components/MaskReveal";
import { ScrollScrubText } from "@/components/ScrollScrubText";
import { AgentCounterNumber } from "@/components/AgentCounterNumber";
import { AgentMiniCardRow } from "@/components/AgentMiniCard";
import { ReadingPreviewMock } from "@/components/ReadingPreviewMock";
import { ManifestoCTA } from "@/components/ManifestoCTA";

export default function ManifestoPage() {
  const router = useRouter();
  const [isTransitioning, setIsTransitioning] = useState(false);

  // Transition handler
  const handleTransition = (upc?: string) => {
    setIsTransitioning(true);
    // Mark as seen in localStorage
    try {
      localStorage.setItem("studyai_manifesto_seen", "true");
    } catch (e) {}

    // After the black wipe animation finishes (400ms), route to home/pipeline
    setTimeout(() => {
      if (upc) {
        // If they entered a UPC, take them to the pipeline
        router.push(`/pipeline/${upc}`);
      } else {
        // Otherwise skip to home
        router.push("/");
      }
    }, 400);
  };

  const scrubSentences = [
    "The system is broken.",
    "You are handed a syllabus written in 2004, textbook recommendations that cost more than your rent, and zero guidance on what the examiner actually wants.",
    "So you memorize PYQs blindly.",
    "You pray the pattern holds.",
    "It doesn't have to be this way.",
    "We built something better."
  ];

  return (
    <PageTransition>
      <main className="w-full bg-bg-base relative text-text-primary">
        
        {/* SECTION 1: THE OPENING */}
        <ManifestoSection>
          <div className="flex flex-col items-center text-center">
            <MaskReveal 
              text="Your university doesn't care if you fail." 
              variant="fast" 
              className="font-serif text-[clamp(32px,5vw,64px)] leading-tight mb-2"
            />
            <MaskReveal 
              text="We do." 
              variant="fast" 
              delay={120} 
              className="font-serif italic text-[clamp(32px,5vw,64px)] leading-tight"
            />
            
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.5, duration: 1 }}
              className="mt-16 flex flex-col items-center gap-4"
            >
              <div className="w-[1px] h-[40px] bg-border-strong" />
              <motion.div 
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                className="font-mono text-[9px] tracking-widest text-text-tertiary uppercase"
              >
                Scroll
              </motion.div>
            </motion.div>
          </div>
        </ManifestoSection>

        {/* SECTION 2: THE PROBLEM */}
        <ManifestoSection>
          <ScrollScrubText sentences={scrubSentences} className="text-[clamp(20px,3vw,32px)] leading-relaxed font-sans font-light" />
        </ManifestoSection>

        {/* SECTION 3: THE SCALE */}
        <ManifestoSection minHeight="80vh">
          <div className="flex flex-col items-center">
            <AgentCounterNumber />
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-10%" }}
              transition={{ delay: 0.5, duration: 0.8 }}
              className="font-sans text-[14px] text-text-secondary mt-4 max-w-sm text-center"
            >
              autonomous agents assigned to every single question paper.
            </motion.div>
          </div>
        </ManifestoSection>

        {/* SECTION 4: THE AGENTS */}
        <ManifestoSection minHeight="50vh">
          <AgentMiniCardRow />
        </ManifestoSection>

        {/* SECTION 5: THE READING PREVIEW */}
        <ManifestoSection className="py-20" minHeight="auto">
          <ReadingPreviewMock />
        </ManifestoSection>

        {/* SECTION 6: THE CTA */}
        <ManifestoSection>
          <div className="flex flex-col items-center text-center w-full relative z-10">
            <MaskReveal 
              text="Your exam is in the data." 
              variant="dramatic" 
              className="font-serif italic text-[clamp(36px,6vw,72px)] leading-tight mb-2"
            />
            <MaskReveal 
              text="Let us find it." 
              variant="dramatic" 
              delay={80} 
              className="font-serif italic text-[clamp(36px,6vw,72px)] leading-tight mb-12"
            />
            <ManifestoCTA onSubmit={handleTransition} />
            
            <button 
              onClick={() => handleTransition()}
              className="absolute top-[-40vh] right-0 sm:fixed sm:top-8 sm:right-8 font-sans text-[11px] text-text-tertiary hover:text-text-primary transition-colors z-50 p-2"
            >
              Skip
            </button>
          </div>
        </ManifestoSection>

        {/* PAGE TRANSITION OUT (BLACK WIPE) */}
        <AnimatePresence>
          {isTransitioning && (
            <motion.div
              initial={{ clipPath: "inset(50%)" }}
              animate={{ clipPath: "inset(0%)" }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              className="fixed inset-0 z-[100] bg-black pointer-events-none"
            />
          )}
        </AnimatePresence>
      </main>
    </PageTransition>
  );
}
