"use client";

import { useRef, useState } from "react";
import { motion, useSpring } from "framer-motion";

interface MagneticProps {
  children: React.ReactNode;
  strength?: number; // How far the element pulls (pixels)
  radius?: number;   // Hover detection radius (pixels) padding around the element
}

export function Magnetic({ children, strength = 40, radius = 100 }: MagneticProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [isHovered, setIsHovered] = useState(false);

  // Smooth springs for x and y translation
  const x = useSpring(0, { stiffness: 150, damping: 15, mass: 0.1 });
  const y = useSpring(0, { stiffness: 150, damping: 15, mass: 0.1 });

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!ref.current) return;
    
    // Get dimensions and center of the element
    const { left, top, width, height } = ref.current.getBoundingClientRect();
    const centerX = left + width / 2;
    const centerY = top + height / 2;

    // Calculate distance from center to mouse
    const distanceX = e.clientX - centerX;
    const distanceY = e.clientY - centerY;

    // Apply the translation based on strength
    // The further from center, the stronger the pull, up to 'strength' px
    x.set((distanceX / (width / 2)) * (strength / 2));
    y.set((distanceY / (height / 2)) * (strength / 2));
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    // Snap back to original position
    x.set(0);
    y.set(0);
  };

  const handleMouseEnter = () => {
    setIsHovered(true);
  };

  return (
    <div
      ref={ref}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onMouseEnter={handleMouseEnter}
      style={{
        display: "inline-flex",
        // Extend hover area to catch the mouse earlier
        padding: `${radius}px`,
        margin: `-${radius}px`,
      }}
    >
      <motion.div
        style={{ x, y }}
        // Keep z-index above ambient elements when hovered
        className={isHovered ? "z-20 relative" : "relative"}
      >
        {children}
      </motion.div>
    </div>
  );
}
