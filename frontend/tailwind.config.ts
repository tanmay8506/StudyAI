import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      // ── COLOURS — all reference CSS custom properties ──
      // Use these as Tailwind utilities: bg-bg-base, text-accent, border-border-subtle, etc.
      colors: {
        // Backgrounds
        "bg-base":       "var(--bg-base)",
        "bg-raised":     "var(--bg-raised)",
        "bg-surface":    "var(--bg-surface)",
        "bg-card":       "var(--bg-card)",
        "bg-card-hover": "var(--bg-card-hover)",

        // Text
        "text-primary":   "var(--text-primary)",
        "text-secondary": "var(--text-secondary)",
        "text-tertiary":  "var(--text-tertiary)",

        // Borders (as color references for border utilities)
        "border-subtle":  "var(--border-subtle)",
        "border-default": "var(--border-default)",
        "border-strong":  "var(--border-strong)",

        // Accent
        accent: {
          DEFAULT: "var(--accent)",
          "2":     "var(--accent-2)",
          dim:     "var(--accent-dim)",
          dim2:    "var(--accent-dim2)",
        },

        // Semantic
        error:   "var(--red)",
        success: "var(--green)",
        info:    "var(--blue)",

        // Legacy aliases kept for backward compat during transition
        // Remove after all components are migrated
        background:  "var(--bg-base)",
        foreground:  "var(--text-primary)",
        muted: {
          DEFAULT:    "var(--bg-surface)",
          foreground: "var(--text-secondary)",
        },
        destructive: {
          DEFAULT:    "var(--red)",
          foreground: "var(--text-primary)",
        },
      },

      // ── BORDER RADIUS — 4 values, no deviations ──
      borderRadius: {
        sm:   "var(--r-sm)",   // 4px — tags, small pills
        md:   "var(--r-md)",   // 6px — inputs, small buttons
        lg:   "var(--r-lg)",   // 8px — buttons
        xl:   "var(--r-xl)",   // 12px — cards
        full: "var(--r-full)", // 9999px — badges, dots
        // Alias for default Tailwind usage
        DEFAULT: "var(--r-xl)",
      },

      // ── FONT FAMILIES — set via next/font CSS variables in layout.tsx ──
      fontFamily: {
        serif: ["var(--font-serif)", "Georgia", "serif"],
        sans:  ["var(--font-sans)", "system-ui", "sans-serif"],
        mono:  ["var(--font-mono)", "monospace"],
      },

      // ── FONT SIZES — editorial scale from spec ──
      fontSize: {
        // Labels & metadata
        "2xs":  ["9px",  { lineHeight: "1.4" }],
        "xs":   ["10px", { lineHeight: "1.4" }],
        "sm":   ["11px", { lineHeight: "1.5" }],
        "smm":  ["12px", { lineHeight: "1.5" }],
        "base": ["13px", { lineHeight: "1.5" }],
        "md":   ["14px", { lineHeight: "1.5" }],
        "lg":   ["15px", { lineHeight: "1.5" }],
        "xl":   ["17px", { lineHeight: "1.4" }],
        "2xl":  ["18px", { lineHeight: "1.4" }],
        "3xl":  ["22px", { lineHeight: "1.3" }],
        "4xl":  ["32px", { lineHeight: "1.2" }],
        "5xl":  ["40px", { lineHeight: "1.1" }],
        "6xl":  ["48px", { lineHeight: "1.05" }],
        "7xl":  ["52px", { lineHeight: "1.0" }],
        "8xl":  ["72px", { lineHeight: "0.95" }],
        "9xl":  ["120px",{ lineHeight: "0.9" }],
        // Hero / manifesto display
        "display": ["clamp(80px, 12vw, 160px)", { lineHeight: "0.9" }],
        "hero":    ["clamp(44px, 6vw, 72px)",   { lineHeight: "1.0" }],
      },

      // ── LETTER SPACING — Syne labels need minimum 0.08em ──
      letterSpacing: {
        tight:   "-0.02em",
        normal:  "0em",
        wide:    "0.08em",
        wider:   "0.12em",
        widest:  "0.20em",
      },

      // ── SPACING — 8px base unit, multiples only ──
      spacing: {
        "1":  "4px",
        "2":  "8px",
        "3":  "12px",
        "4":  "16px",
        "5":  "20px",
        "6":  "24px",
        "8":  "32px",
        "10": "40px",
        "12": "48px",
        "16": "64px",
        "20": "80px",
        "24": "96px",
        "30": "120px",
      },

      // ── ANIMATION KEYFRAMES ──
      keyframes: {
        // Accordion (keep for Radix UI components)
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        // Spinner for running agent cards
        spin: {
          from: { transform: "rotate(0deg)" },
          to:   { transform: "rotate(360deg)" },
        },
        // Sonar pulse — dead time animation (CSS fallback for non-Framer usage)
        sonar: {
          "0%, 100%": { opacity: "0.45" },
          "50%":      { opacity: "0.65" },
        },
        // Scroll indicator pulse on manifesto page
        "scroll-pulse": {
          "0%, 100%": { transform: "scaleY(0.5)", opacity: "0.4" },
          "50%":      { transform: "scaleY(1.0)", opacity: "1.0" },
        },
      },

      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up":   "accordion-up 0.2s ease-out",
        "spin-slow":      "spin 3s linear infinite",
        "sonar":          "sonar 1.2s ease-in-out infinite",
        "scroll-pulse":   "scroll-pulse 2s ease-in-out infinite",
      },

      // ── Z-INDEX SCALE ──
      zIndex: {
        "0":     "0",
        "1":     "1",
        "10":    "10",
        "20":    "20",
        "30":    "30",
        "40":    "40",
        "50":    "50",
        "nav":   "100",
        "modal": "200",
        "cursor":"10000",
        "grain": "9999",
      },

      // ── MAX WIDTH ──
      maxWidth: {
        "reading":  "720px",
        "overview": "900px",
        "hero":     "560px",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
