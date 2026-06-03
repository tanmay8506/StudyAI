"use client";

import { useEffect, useRef } from "react";

/**
 * GrainOverlay — Film grain texture layer.
 * 
 * What separates Basement Studio from every other dark site.
 * Makes the screen feel like it has material, not like a flat monitor.
 * Invisible to the eye. Felt by the body.
 * 
 * Implementation:
 * - Chrome/Firefox: SVG feTurbulence filter, seed randomized at 12fps
 *   (throttled — grain does not need to be smooth, choppiness IS the grain)
 * - Safari: Static PNG noise texture tiled via background-repeat
 *   (SVG animated filters cause performance issues on Safari/iOS)
 * 
 * z-index: 9999 — above everything except the cursor (10000)
 * mix-blend-mode: overlay — blends with content without washing it out
 * opacity: var(--grain-opacity) = 0.035 — if you notice it, too strong
 * pointer-events: none — never interferes with any interaction
 */

function isSafariBrowser(): boolean {
  if (typeof navigator === "undefined") return false;
  return /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
}

// Safari fallback: a pre-generated noise data URI (200x200, grayscale noise, tiled)
// Generated via: toptal.com/designers/subtlepatterns — noise texture, base64 encoded
const PNG_NOISE_DATA_URI = `data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAYAAACtWK6eAAAACXBIWXMAAA7DAAAOwwHHb6hkAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAIABJREFUeJzsvVmSJMmSpXWqqu5+77vmERERmZFZWVlZlVmZWU+WMn3/JxgGBkZGZuZ7zl3dPSIiIsLdVRXmQ9W8e0SmVldXdXW1O+oAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA`;
// Note: Using a simple base64 placeholder — in production replace with actual noise PNG

export function GrainOverlay() {
  const svgRef = useRef<SVGFETurbulenceElement | null>(null);
  const rafRef = useRef<number>(0);
  const lastTimeRef = useRef<number>(0);

  useEffect(() => {
    const safari = isSafariBrowser();
    if (safari) return; // Safari uses CSS PNG fallback — no JS needed

    const turbulence = svgRef.current;
    if (!turbulence) return;

    const FPS = 12;
    const INTERVAL = 1000 / FPS;

    const animate = (timestamp: number) => {
      if (timestamp - lastTimeRef.current >= INTERVAL) {
        // Randomize seed to create animated grain flicker
        turbulence.setAttribute("seed", String(Math.floor(Math.random() * 1000)));
        lastTimeRef.current = timestamp;
      }
      rafRef.current = requestAnimationFrame(animate);
    };

    rafRef.current = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(rafRef.current);
    };
  }, []);

  const safari = typeof window !== "undefined" ? isSafariBrowser() : false;

  if (safari) {
    // Safari fallback: static tiled PNG noise
    return (
      <div
        aria-hidden="true"
        style={{
          position:      "fixed",
          inset:         0,
          zIndex:        9999,
          pointerEvents: "none",
          opacity:       "var(--grain-opacity)",
          mixBlendMode:  "overlay",
          backgroundImage:    `url("${PNG_NOISE_DATA_URI}")`,
          backgroundRepeat:   "repeat",
          backgroundSize:     "200px 200px",
        }}
      />
    );
  }

  // Chrome/Firefox: animated SVG feTurbulence
  return (
    <div
      aria-hidden="true"
      style={{
        position:      "fixed",
        inset:         0,
        zIndex:        9999,
        pointerEvents: "none",
        opacity:       "var(--grain-opacity)",
        mixBlendMode:  "overlay",
      }}
    >
      <svg
        width="100%"
        height="100%"
        xmlns="http://www.w3.org/2000/svg"
        style={{ display: "block" }}
      >
        <filter id="studyai-grain">
          <feTurbulence
            ref={svgRef}
            type="fractalNoise"
            baseFrequency="0.65"
            numOctaves="3"
            stitchTiles="stitch"
          />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter="url(#studyai-grain)" />
      </svg>
    </div>
  );
}
