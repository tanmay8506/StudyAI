"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { PageTransition } from "@/components/PageTransition";
import { AmbientLight } from "@/components/AmbientLight";
import { GrainOverlay } from "@/components/GrainOverlay";

import { CustomCursor } from "@/components/CustomCursor";
import { HeroHeadline } from "@/components/HeroHeadline";
import { UPCInput } from "@/components/UPCInput";
import { StatPills } from "@/components/StatPills";
import { fadeUp } from "@/lib/animations";

import { Magnetic } from "@/components/Magnetic";
import { useMotionValue, useSpring, useTransform } from "framer-motion";

// Fallback import if getPaper isn't available, but we assume it is based on previous page.tsx
// If it fails, the user will be routed to pipeline by default.
import { getPaper } from "@/lib/queries";

export default function Homepage() {
  const router = useRouter();
  const [isInputFocused, setIsInputFocused] = useState(false);

  // Parallax Tilt Setup
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  
  // Smooth the mouse movement
  const springX = useSpring(mouseX, { stiffness: 150, damping: 20 });
  const springY = useSpring(mouseY, { stiffness: 150, damping: 20 });

  // Map mouse position to rotation angles (subtle tilt)
  const rotateX = useTransform(springY, [-1, 1], [5, -5]);
  const rotateY = useTransform(springX, [-1, 1], [-5, 5]);

  const handleMouseMove = (e: React.MouseEvent) => {
    // Normalize mouse coordinates between -1 and 1
    const { clientX, clientY } = e;
    const { innerWidth, innerHeight } = window;
    mouseX.set((clientX / innerWidth) * 2 - 1);
    mouseY.set((clientY / innerHeight) * 2 - 1);
  };
  
  const handleMouseLeave = () => {
    // Reset tilt
    mouseX.set(0);
    mouseY.set(0);
  };

  const handleSubmit = async (upc: string) => {
    try {
      // Check if paper exists in the database
      const paper = await getPaper(upc);
      
      if (paper) {
        // If exists, skip pipeline, go direct to paper
        router.push(`/paper/${upc}`);
      } else {
        // Otherwise trigger backend and go to pipeline
        try {
          await fetch('http://localhost:8000/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ upc })
          });
        } catch (e) {
          // Use warn instead of error to prevent Next.js dev overlay from intercepting it
          console.warn("Failed to trigger backend, falling back to mock pipeline.", e);
        }
        router.push(`/pipeline/${upc}`);
      }
    } catch (err) {
      console.error(err);
      throw new Error("Failed to connect to database");
    }
  };

  const statItems = [
    { value: "12", label: "AGENTS" },
    { value: "EXAM", label: "CALIBRATED" },
    { value: "DU", label: "NEP 2022" }
  ];

  return (
    <PageTransition>
      <main 
        className="relative min-h-screen w-full flex flex-col items-center justify-center overflow-hidden bg-transparent text-text-primary perspective-[1000px]"
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        
        {/* GLOBAL INFRASTRUCTURE */}
        <GrainOverlay />
        <AmbientLight variant="homepage" />



        {/* FOREGROUND CONTENT WITH PARALLAX TILT */}
        <motion.div 
          className="relative z-10 flex flex-col items-center text-center max-w-3xl w-full px-6"
          style={{
            rotateX,
            rotateY,
            transformStyle: "preserve-3d"
          }}
        >
          
          {/* LOGOTYPE */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            // Fades in at 200ms
            transition={{ delay: 0.2, duration: 0.6 }}
            className="font-sans text-[11px] font-bold uppercase tracking-[0.15em] text-text-tertiary mb-12"
          >
            StudyAI
          </motion.div>

          {/* HEADLINE (300ms and 420ms delays inside component) */}
          <HeroHeadline />

          {/* SUBHEADING */}
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            // Fades up at 520ms (200ms after headline completes)
            transition={{ delay: 0.52, duration: 0.8 }}
            className="font-sans text-[15px] text-text-secondary max-w-[400px] mt-5 mb-8"
          >
            Enter your paper code. 12 agents build your exam notes.
          </motion.div>

          {/* UPC INPUT ROW (620ms delay inside component) */}
          <Magnetic strength={30} radius={60}>
            <UPCInput 
              onFocusChange={setIsInputFocused} 
              onSubmit={handleSubmit} 
            />
          </Magnetic>

        </motion.div>

        {/* STAT PILLS ROW (740ms delay inside component) */}
        <div className="absolute bottom-24 w-full">
          <StatPills items={statItems} />
        </div>

      </main>
    </PageTransition>
  );
}
