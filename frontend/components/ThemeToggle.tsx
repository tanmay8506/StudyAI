"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

/**
 * ThemeToggle — Premium animated Sun/Moon toggle.
 * Placed inside the BottomNav pill.
 */
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);
  if (!mounted) return <div style={{ width: 32, height: 20 }} />;

  const isDark = resolvedTheme === "dark";

  return (
    <button
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      onClick={() => setTheme(isDark ? "light" : "dark")}
      style={{
        display:         "flex",
        alignItems:      "center",
        justifyContent:  "center",
        width:           32,
        height:          32,
        borderRadius:    "50%",
        border:          "1px solid var(--toggle-border)",
        background:      "var(--toggle-bg)",
        cursor:          "pointer",
        flexShrink:      0,
        position:        "relative",
        overflow:        "hidden",
        transition:      "border-color 0.2s ease, background 0.2s ease",
      }}
    >
      <AnimatePresence mode="wait" initial={false}>
        {isDark ? (
          /* Moon icon */
          <motion.svg
            key="moon"
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--text-secondary)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ opacity: 0, rotate: -30, scale: 0.7 }}
            animate={{ opacity: 1, rotate: 0,   scale: 1   }}
            exit={{    opacity: 0, rotate:  30,  scale: 0.7 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            style={{ position: "absolute" }}
          >
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </motion.svg>
        ) : (
          /* Sun icon */
          <motion.svg
            key="sun"
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--accent)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ opacity: 0, rotate: 30,  scale: 0.7 }}
            animate={{ opacity: 1, rotate: 0,   scale: 1   }}
            exit={{    opacity: 0, rotate: -30,  scale: 0.7 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            style={{ position: "absolute" }}
          >
            <circle cx="12" cy="12" r="5" />
            <line x1="12" y1="1"  x2="12" y2="3"  />
            <line x1="12" y1="21" x2="12" y2="23" />
            <line x1="4.22"  y1="4.22"  x2="5.64"  y2="5.64"  />
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
            <line x1="1"     y1="12"    x2="3"     y2="12"    />
            <line x1="21"    y1="12"    x2="23"    y2="12"    />
            <line x1="4.22"  y1="19.78" x2="5.64"  y2="18.36" />
            <line x1="18.36" y1="5.64"  x2="19.78" y2="4.22"  />
          </motion.svg>
        )}
      </AnimatePresence>
    </button>
  );
}
