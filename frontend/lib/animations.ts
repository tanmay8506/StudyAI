/**
 * STUDYAI — ANIMATION CONSTANTS
 * All Framer Motion variants and spring presets as named exports.
 * Every animation in the app MUST reference these constants.
 * Never define one-off spring configs inline in components.
 * 
 * Rule: if an animation communicates something, it belongs here.
 * If it is just moving, remove it.
 */

import type { Variants, Transition } from "framer-motion";

// ================================================================
// SPRING PRESETS — reference these in all Framer Motion transitions
// ================================================================

export const springSnappy: Transition = {
  type: "spring",
  damping: 20,
  stiffness: 300,
};

export const springBouncy: Transition = {
  type: "spring",
  damping: 15,
  stiffness: 150,
};

export const springHeavy: Transition = {
  type: "spring",
  damping: 30,
  stiffness: 100,
};

export const springFocus: Transition = {
  type: "spring",
  damping: 25,
  stiffness: 180,
};

// Used for card tilt and glow overlay
export const TILT_SPRING: Transition = {
  type: "spring",
  damping: 30,
  stiffness: 200,
};

// ================================================================
// TILT CONSTANTS — pipeline agent cards & bento cards
// ================================================================

export const TILT_MAX = 6;          // Maximum rotation degrees
export const TILT_PERSPECTIVE = 800; // CSS perspective value in px

// ================================================================
// ANIMATION VARIANTS — use with motion.div animate/initial/exit
// ================================================================

/**
 * Stagger container — wraps children to produce cascade entrance
 * Usage: <motion.ul variants={staggerContainer} initial="hidden" animate="visible">
 */
export const staggerContainer: Variants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.06, // 60ms between each child
    },
  },
};

/**
 * Stagger container — fast version for compact UI grids
 */
export const staggerContainerFast: Variants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.03, // 30ms between each child
    },
  },
};

/**
 * fadeUp — standard entrance for UI elements
 * y 20→0, opacity 0→1, spring physics
 */
export const fadeUp: Variants = {
  hidden: {
    y: 20,
    opacity: 0,
  },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      type: "spring",
      damping: 20,
      stiffness: 100,
    },
  },
};

/**
 * fadeUpFast — compact elements, less travel distance
 * y 12→0, opacity 0→1, duration-based
 */
export const fadeUpFast: Variants = {
  hidden: {
    y: 12,
    opacity: 0,
  },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      duration: 0.3,
      ease: [0.16, 1, 0.3, 1],
    },
  },
};

/**
 * revealInView — scroll-triggered content blocks on reading page
 * y 12→0, opacity 0→1, slightly longer
 */
export const revealInView: Variants = {
  hidden: {
    y: 12,
    opacity: 0,
  },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      duration: 0.4,
      ease: [0.16, 1, 0.3, 1],
    },
  },
};

/**
 * scaleIn — cards and modals entering the screen
 * scale 0.95→1, opacity 0→1, spring physics
 */
export const scaleIn: Variants = {
  hidden: {
    scale: 0.95,
    opacity: 0,
  },
  visible: {
    scale: 1,
    opacity: 1,
    transition: {
      type: "spring",
      damping: 20,
      stiffness: 200,
    },
  },
};

/**
 * drawPath — SVG pathLength animation for checkmarks and ink borders
 * pathLength 0→1, easeOut
 * Apply to motion.path elements as: initial="hidden" animate="visible"
 */
export const drawPath: Variants = {
  hidden: {
    pathLength: 0,
    opacity: 0,
  },
  visible: {
    pathLength: 1,
    opacity: 1,
    transition: {
      pathLength: { duration: 0.4, ease: "easeOut" },
      opacity: { duration: 0.05 },
    },
  },
};

/**
 * inkDraw — specifically for definition block left border
 * Same as drawPath but with a slight delay to sequence with text reveal
 */
export const inkDraw: Variants = {
  hidden: {
    pathLength: 0,
    opacity: 0,
  },
  visible: {
    pathLength: 1,
    opacity: 1,
    transition: {
      pathLength: { duration: 0.4, ease: "easeOut" },
      opacity: { duration: 0.01 },
    },
  },
};

/**
 * sonarPulse — dead time animation on queued pipeline cards
 * opacity 0.45→0.65→0.45, 1200ms sweep
 */
export const sonarPulse: Variants = {
  idle: {
    opacity: 0.45,
  },
  pulse: {
    opacity: [0.45, 0.65, 0.45],
    transition: {
      duration: 1.2,
      ease: "easeInOut",
      repeat: Infinity,
    },
  },
};

// ================================================================
// MASK REVEAL VARIANTS — character-level text reveal
// Used in MaskReveal component. Applied per-word.
// ================================================================

/**
 * maskWord — standard word reveal (60ms stagger)
 * y 100%→0%, purely position (no opacity)
 * The overflow-hidden parent clips the word during animation.
 */
export const maskWordStandard: Variants = {
  hidden: {
    y: "100%",
  },
  visible: (i: number) => ({
    y: "0%",
    transition: {
      type: "spring",
      damping: 20,
      stiffness: 100,
      delay: i * 0.06,
    },
  }),
};

/**
 * maskWordFast — subheadings (30ms stagger)
 */
export const maskWordFast: Variants = {
  hidden: {
    y: "100%",
  },
  visible: (i: number) => ({
    y: "0%",
    transition: {
      type: "spring",
      damping: 25,
      stiffness: 200,
      delay: i * 0.03,
    },
  }),
};

/**
 * maskWordDramatic — manifesto page (80ms stagger, slower spring)
 */
export const maskWordDramatic: Variants = {
  hidden: {
    y: "100%",
  },
  visible: (i: number) => ({
    y: "0%",
    transition: {
      type: "spring",
      damping: 15,
      stiffness: 80,
      delay: i * 0.08,
    },
  }),
};

// ================================================================
// PAGE TRANSITIONS
// ================================================================

export const pageFade: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: 0.2, ease: "easeOut" } },
  exit:    { opacity: 0, transition: { duration: 0.15, ease: "easeIn" } },
};

/**
 * Manifesto → Homepage special expansion transition (400ms)
 * Only non-fade transition in the app.
 */
export const pageManifestoToHome: Variants = {
  initial: { clipPath: "inset(50%)", opacity: 1 },
  animate: { 
    clipPath: "inset(0%)", 
    opacity: 1,
    transition: { duration: 0.4, ease: "easeInOut" } 
  },
  exit: { opacity: 0, transition: { duration: 0.15, ease: "easeIn" } },
};

// ================================================================
// CURSOR ANIMATION CONSTANTS
// ================================================================

export const cursorDotSpring = { damping: 40, stiffness: 800 }; // Smooth, near-instant tracking without wobble
export const cursorRingSpring = { damping: 30, stiffness: 150 }; // Heavy, buttery trail without elastic bounce
// ================================================================
// NEWLY AUDITED SPRING PRESETS & TRANSITIONS
// ================================================================

export const springQuick: Transition = { type: 'spring', stiffness: 400, damping: 30 };
export const springNavContainer: Transition = { type: 'spring', stiffness: 150, damping: 15, mass: 0.1 };
export const springNavHover: Transition = { type: 'spring', bounce: 0.25, duration: 0.5 };
export const springNavEntrance: Transition = { type: 'spring', stiffness: 200, damping: 20, delay: 0.2 };
export const springInputSubmit: Transition = { type: 'spring', stiffness: 400, damping: 10 };

export const transitionFade: Transition = { duration: 0.4, ease: 'easeOut' };
export const transitionFadeFast: Transition = { duration: 0.2 };
export const transitionScroll: Transition = { duration: 0.8, ease: 'easeOut' };
export const transitionStatPill: Transition = { delay: 0.74, duration: 0.8 };
export const transitionInputBase: Transition = { delay: 0.62, duration: 0.8 };
export const transitionPulseLinear: Transition = { duration: 1.5, repeat: Infinity, ease: 'linear' };
export const springPulseGlow: Transition = { duration: 1.5, repeat: Infinity, repeatType: 'mirror', ease: 'easeInOut', type: 'tween' };
