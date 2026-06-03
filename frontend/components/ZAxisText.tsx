"use client";

import { useEffect } from "react";
import { motion, useMotionValue, useTransform, useSpring } from "framer-motion";
import { useIsMobile } from "@/lib/hooks/useMediaQuery";

/**
 * ZAxisText — Deep background typography layer for the Homepage.
 * 
 * Scattered, organic placement of subjects.
 * Glides in the opposite direction of the cursor (parallax).
 * Blurs dramatically when the main input is focused.
 */

interface ZAxisTextProps {
  isFocused: boolean;
}

export function ZAxisText({ isFocused }: ZAxisTextProps) {
  const isMobile = useIsMobile();
  
  // Raw mouse coordinates
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  // Apply spring for smooth gliding, not snapping
  const smoothMouseX = useSpring(mouseX, { stiffness: 50, damping: 20 });
  const smoothMouseY = useSpring(mouseY, { stiffness: 50, damping: 20 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      // Normalize relative to screen center (-1 to 1)
      const x = (e.clientX / window.innerWidth) * 2 - 1;
      const y = (e.clientY / window.innerHeight) * 2 - 1;
      mouseX.set(x);
      mouseY.set(y);
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [mouseX, mouseY]);

  // Translate coordinates to pixels (moves OPPOSITE to cursor: -20 to 20px)
  const x = useTransform(smoothMouseX, [-1, 1], [20, -20]);
  const y = useTransform(smoothMouseY, [-1, 1], [20, -20]);

  const words = [
    { text: "PROBABILITY", top: "10%", left: "5%" },
    { text: "STATISTICS", top: "25%", left: "60%" },
    { text: "DIFFERENTIAL", top: "45%", left: "15%" },
    { text: "EQUATIONS", top: "50%", left: "70%" },
    { text: "CALCULUS", top: "75%", left: "10%" },
    { text: "ALGEBRA", top: "85%", left: "55%" },
    { text: "TOPOLOGY", top: "35%", left: "80%" },
  ];

  if (isMobile) return null;

  return (
    <motion.div
      className="fixed inset-0 pointer-events-none select-none z-[-1] overflow-hidden"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6, ease: "easeIn" }}
      style={{ x, y }} // Apply parallax to the whole container
    >
      <motion.div
        className="w-full h-full relative"
        initial={false}
        animate={{ filter: isFocused ? "blur(4px)" : "blur(0px)" }}
        transition={{ type: "spring", stiffness: 100, damping: 20 }}
        style={{ willChange: "filter, transform" }}
      >
        {words.map((word, i) => (
          <div
            key={i}
            className="absolute font-serif text-text-primary whitespace-nowrap"
            style={{
              top: word.top,
              left: word.left,
              opacity: 0.035,
              fontSize: "clamp(60px, 9vw, 130px)",
              lineHeight: 1,
              transform: "translate(-50%, -50%)", // Center on the coordinate
            }}
          >
            {word.text}
          </div>
        ))}
      </motion.div>
    </motion.div>
  );
}
