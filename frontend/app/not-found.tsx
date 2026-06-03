"use client";

import { AmbientLight } from "@/components/AmbientLight";
import { GrainOverlay } from "@/components/GrainOverlay";
import { MaskReveal } from "@/components/MaskReveal";
import { motion } from "framer-motion";
import Link from "next/link";

export default function NotFound() {
  return (
    <main
      className="relative min-h-screen w-full flex flex-col items-center justify-center overflow-hidden"
      style={{ backgroundColor: "var(--bg-base)", color: "var(--text-primary)" }}
    >
      <GrainOverlay />
      <AmbientLight variant="reading" />

      <div className="z-10 flex flex-col items-center text-center px-6">
        <MaskReveal
          text="404."
          variant="dramatic"
          className="font-serif italic leading-none mb-4 text-accent"
          style={{ fontSize: "clamp(80px, 12vw, 160px)" } as React.CSSProperties}
        />
        <MaskReveal
          text="This paper does not exist."
          variant="standard"
          delay={100}
          className="font-sans font-bold tracking-tight mb-12"
          style={{ fontSize: "clamp(24px, 4vw, 36px)" } as React.CSSProperties}
        />

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1, duration: 0.6 }}
        >
          <Link
            href="/"
            className="relative group"
            style={{
              fontFamily:    "var(--font-mono)",
              fontSize:      "12px",
              textTransform: "uppercase",
              letterSpacing: "0.12em",
              color:         "var(--text-secondary)",
              textDecoration: "none",
            }}
          >
            <span className="relative z-10">Return to Pipeline</span>
            <div
              style={{
                position:        "absolute",
                left:            0,
                right:           0,
                bottom:          -4,
                height:          1,
                backgroundColor: "var(--accent)",
                transform:       "scaleX(0)",
                transformOrigin: "left",
                transition:      "transform 0.15s ease",
              }}
              className="group-hover:[transform:scaleX(1)]"
            />
          </Link>
        </motion.div>
      </div>
    </main>
  );
}
