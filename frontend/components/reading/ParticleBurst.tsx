"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useIsMobile } from "@/lib/hooks/useMediaQuery";

/**
 * ParticleBurst — A physics-based explosion of monochrome dots.
 * 
 * Fires exactly at the provided clientX/clientY cursor coordinates.
 * Disappears automatically after the animation completes.
 * Uses strict absolute positioned divs, no external confetti libraries.
 */

interface ParticleBurstProps {
  x: number;
  y: number;
  onComplete?: () => void;
}

interface Particle {
  id: number;
  x: number;
  y: number;
  size: number;
}

export function ParticleBurst({ x, y, onComplete }: ParticleBurstProps) {
  const [particles, setParticles] = useState<Particle[]>([]);
  const isMobile = useIsMobile();

  useEffect(() => {
    // Generate 10-12 random particles (or exactly 6 on mobile)
    const count = isMobile ? 6 : Math.floor(Math.random() * 3) + 10;
    const newParticles: Particle[] = [];

    for (let i = 0; i < count; i++) {
      // Random distance outwards between 20px and 80px
      const distance = 20 + Math.random() * 60;
      // Random angle in radians
      const angle = Math.random() * Math.PI * 2;
      
      newParticles.push({
        id: i,
        x: Math.cos(angle) * distance,
        y: Math.sin(angle) * distance,
        size: 3 + Math.random() * 3 // Size between 3px and 6px
      });
    }

    setParticles(newParticles);

    // Unmount/cleanup after the 600ms animation
    const timer = setTimeout(() => {
      onComplete?.();
    }, 600);

    return () => clearTimeout(timer);
  }, [onComplete, isMobile]);

  return (
    <AnimatePresence>
      {particles.length > 0 && (
        <div 
          className="fixed pointer-events-none z-[100]" 
          style={{ left: x, top: y }}
        >
          {particles.map((p) => (
            <motion.div
              key={p.id}
              className="absolute bg-text-tertiary rounded-full"
              style={{ width: p.size, height: p.size, marginLeft: -p.size/2, marginTop: -p.size/2 }}
              initial={{ x: 0, y: 0, scale: 1, opacity: 1 }}
              animate={{ x: p.x, y: p.y, scale: 0, opacity: 0 }}
              transition={{
                duration: 0.6,
                ease: "easeOut",
              }}
            />
          ))}
        </div>
      )}
    </AnimatePresence>
  );
}
