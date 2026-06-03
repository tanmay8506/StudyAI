"use client";

import { motion } from "framer-motion";

/**
 * ManifestoSection — Wrapper for each section in the Manifesto.
 * 
 * Provides consistent full-viewport height, centering, and 
 * clean unmounting for the page transition.
 */

interface ManifestoSectionProps {
  children: React.ReactNode;
  className?: string;
  minHeight?: string;
}

export function ManifestoSection({ children, className = "", minHeight = "100vh" }: ManifestoSectionProps) {
  return (
    <motion.section
      className={`flex flex-col items-center justify-center w-full px-6 relative overflow-hidden ${className}`}
      style={{ minHeight }}
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true, margin: "-10%" }}
      transition={{ duration: 0.8, ease: "easeOut" }}
    >
      {children}
    </motion.section>
  );
}
