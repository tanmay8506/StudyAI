"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { motion, useSpring, useMotionValue } from "framer-motion";

/**
 * AmbientLight — Theme-aware, interactive ambient glow.
 *
 * Replaces the heavy WebGL 3D object with butter-smooth CSS gradients
 * that track the mouse position. Zero performance impact.
 */

export type AmbientLightVariant =
  | "manifesto"
  | "homepage"
  | "pipeline"
  | "overview"
  | "reading";

interface AmbientLightProps {
  variant?: AmbientLightVariant;
}

const basePositions: Record<AmbientLightVariant, { top: number; right: number }> = {
  manifesto: { top: -300, right: -300 },
  homepage:  { top: -250, right: -250 },
  pipeline:  { top: -200, right: -150 },
  overview:  { top: -300, right: -200 },
  reading:   { top: -200, right: -100 },
};

export function AmbientLight({ variant = "homepage" }: AmbientLightProps) {
  const pos = basePositions[variant];
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  
  // Mouse tracking springs for the ambient light
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { stiffness: 40, damping: 20 });
  const springY = useSpring(mouseY, { stiffness: 40, damping: 20 });
  const slowSpringX = useSpring(mouseX, { stiffness: 20, damping: 30 });
  const slowSpringY = useSpring(mouseY, { stiffness: 20, damping: 30 });

  useEffect(() => { 
    setMounted(true); 
    
    // Track mouse globally for the ambient lights
    const handleMouseMove = (e: MouseEvent) => {
      // Normalize offset relative to center of screen
      const xOffset = (e.clientX - window.innerWidth / 2) * 0.15;
      const yOffset = (e.clientY - window.innerHeight / 2) * 0.15;
      mouseX.set(xOffset);
      mouseY.set(yOffset);
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [mouseX, mouseY]);

  const isDark = !mounted || resolvedTheme === "dark";

  if (isDark) {
    return (
      <motion.div
        aria-hidden="true"
        style={{
          position:      "fixed",
          top:           pos.top,
          right:         pos.right,
          width:         "700px",
          height:        "700px",
          borderRadius:  "50%",
          background:    "radial-gradient(circle, rgba(232,200,74,0.03) 0%, transparent 70%)",
          zIndex:        0,
          pointerEvents: "none",
          x: springX,
          y: springY,
        }}
      />
    );
  }

  // Light mode: two overlapping colorful orbs (indigo and rose)
  // They move slightly differently to create a parallax/mesh effect
  return (
    <>
      {/* Indigo orb — top right */}
      <motion.div
        aria-hidden="true"
        style={{
          position:      "fixed",
          top:           pos.top,
          right:         pos.right,
          width:         "800px",
          height:        "800px",
          borderRadius:  "50%",
          background:    "radial-gradient(circle, rgba(79,82,255,0.08) 0%, transparent 65%)",
          zIndex:        0,
          pointerEvents: "none",
          x: springX,
          y: springY,
        }}
      />
      {/* Rose orb — offset, moves in inverse/slower for depth */}
      <motion.div
        aria-hidden="true"
        style={{
          position:      "fixed",
          top:           pos.top + 200,
          right:         pos.right + 150,
          width:         "600px",
          height:        "600px",
          borderRadius:  "50%",
          background:    "radial-gradient(circle, rgba(255,80,170,0.06) 0%, transparent 65%)",
          zIndex:        0,
          pointerEvents: "none",
          x: slowSpringX,
          y: slowSpringY,
        }}
      />
    </>
  );
}
