"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useMotionValue, useSpring } from "framer-motion";
import { cursorDotSpring, cursorRingSpring } from "@/lib/animations";

/**
 * CustomCursor — Replaces the browser default cursor.
 *
 * Two elements:
 *   dot  — 6px warm white circle, instant tracking (1:1 with mouse)
 *   ring — 24px trailing ring with spring lag, communicates physicality
 *
 * FIXED: width/height must NOT be in both style and animate simultaneously
 *        — Framer Motion owns them exclusively via animate.
 *        Rotation uses separate tween transition to avoid spring conflict.
 */

type CursorState = "default" | "hover" | "flag" | "pyq" | "input" | "running";

function getCursorState(target: Element | null): CursorState {
  if (!target) return "default";
  let el: Element | null = target;
  while (el && el !== document.body) {
    const attr = el.getAttribute("data-cursor");
    if (attr) return attr as CursorState;
    const tag = el.tagName.toLowerCase();
    if (tag === "a" || tag === "button" || el.getAttribute("role") === "button") {
      return "hover";
    }
    el = el.parentElement;
  }
  return "default";
}

export function CustomCursor() {
  const [isMounted, setIsMounted]     = useState(false);
  const [isTouch, setIsTouch]         = useState(false);
  const [cursorState, setCursorState] = useState<CursorState>("default");
  const [isClicking, setIsClicking]   = useState(false);

  // Raw mouse position — useMotionValue bypasses React render cycle
  const rawX = useMotionValue(-200);
  const rawY = useMotionValue(-200);

  // Dot: near-instant spring
  const dotX = useSpring(rawX, cursorDotSpring);
  const dotY = useSpring(rawY, cursorDotSpring);

  // Ring: lagged spring — communicates physicality
  const ringX = useSpring(rawX, cursorRingSpring);
  const ringY = useSpring(rawY, cursorRingSpring);

  useEffect(() => {
    setIsMounted(true);
    if (
      window.matchMedia("(pointer: coarse)").matches ||
      window.innerWidth < 768
    ) {
      setIsTouch(true);
      return;
    }

    const onMove = (e: MouseEvent) => {
      rawX.set(e.clientX);
      rawY.set(e.clientY);
      const target = document.elementFromPoint(e.clientX, e.clientY);
      setCursorState(getCursorState(target));
    };
    const onDown = () => setIsClicking(true);
    const onUp   = () => setIsClicking(false);

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mousedown", onDown);
    window.addEventListener("mouseup",   onUp);

    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("mouseup",   onUp);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!isMounted || isTouch) return null;

  // ── State-driven dimensions ──
  const ringSize: Record<CursorState, number> = {
    default: 24,
    hover:   36,
    flag:    40,
    pyq:     36,
    input:   16,
    running: 32,
  };

  const dotSize: Record<CursorState, number> = {
    default: 6,
    hover:   0,
    flag:    0,
    pyq:     4,
    input:   3,
    running: 4,
  };

  const ringBorder: Record<CursorState, string> = {
    default: "rgba(240,236,224,0.25)",
    hover:   "rgba(232,200,74,0.4)",
    flag:    "rgba(232,200,74,0.4)",
    pyq:     "rgba(90,184,122,0.4)",
    input:   "rgba(240,236,224,0.20)",
    running: "rgba(232,200,74,0.4)",
  };

  const rSize = isClicking ? 20 : ringSize[cursorState];
  const dSize = isClicking ? 10 : dotSize[cursorState];
  const isRunning = cursorState === "running";

  return (
    <>
      {/* ── DOT — instant 1:1 tracking ──
          IMPORTANT: width/height only in `animate`, never also in `style`
          Otherwise Framer Motion and React fight over the value → glitch */}
      <motion.div
        aria-hidden="true"
        style={{
          position:        "fixed",
          top:             0,
          left:            0,
          x:               dotX,
          y:               dotY,
          translateX:      "-50%",
          translateY:      "-50%",
          borderRadius:    "50%",
          backgroundColor: "var(--cursor-dot)",
          pointerEvents:   "none",
          zIndex:          10001,
          willChange:      "transform",
        }}
        initial={{ width: 6, height: 6, opacity: 1 }}
        animate={{
          width:   dSize,
          height:  dSize,
          opacity: dSize === 0 ? 0 : 1,
        }}
        transition={{ type: "spring", damping: 30, stiffness: 500, mass: 0.3 }}
      />

      {/* ── RING — spring-lagged trail ──
          Rotation uses a separate tween transition (specified per-property)
          so it doesn't inherit the spring and fight with repeat:Infinity */}
      <motion.div
        aria-hidden="true"
        style={{
          position:        "fixed",
          top:             0,
          left:            0,
          x:               ringX,
          y:               ringY,
          translateX:      "-50%",
          translateY:      "-50%",
          borderRadius:    "50%",
          border:          "1px solid transparent",
          backgroundColor: "transparent",
          pointerEvents:   "none",
          zIndex:          10000,
          display:         "flex",
          alignItems:      "center",
          justifyContent:  "center",
          willChange:      "transform",
        }}
        initial={{ width: 24, height: 24, opacity: 1 }}
        animate={{
          width:       rSize,
          height:      rSize,
          borderColor: ringBorder[cursorState],
          opacity:     isClicking ? 0.5 : 1,
          rotate:      isRunning ? 360 : 0,
        }}
        transition={{
          // Size, border, opacity — use spring
          width:       { type: "spring", damping: 20, stiffness: 300 },
          height:      { type: "spring", damping: 20, stiffness: 300 },
          borderColor: { duration: 0.15 },
          opacity:     { duration: 0.15 },
          // Rotation — MUST use tween so repeat:Infinity works without spring bounce
          rotate: isRunning
            ? { duration: 3, ease: "linear", repeat: Infinity, type: "tween" }
            : { duration: 0.3, type: "tween" },
        }}
      >
        {/* FLAG label inside ring */}
        {cursorState === "flag" && (
          <motion.span
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            style={{
              fontFamily:    "var(--font-mono)",
              fontSize:      "7px",
              color:         "var(--text-tertiary)",
              userSelect:    "none",
              letterSpacing: "0.08em",
              lineHeight:    1,
            }}
          >
            FLAG
          </motion.span>
        )}
      </motion.div>
    </>
  );
}
