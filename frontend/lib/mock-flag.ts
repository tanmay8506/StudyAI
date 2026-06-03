/**
 * mock-flag.ts
 * ─────────────────────────────────────────────────────
 * Single source of truth for the mock/real data toggle.
 *
 * USAGE:
 *   import { USE_MOCK } from "@/lib/mock-flag";
 *   if (USE_MOCK) { ... render mock data ... } else { ... fetch real data ... }
 *
 * TO SWITCH TO REAL MODE:
 *   Set NEXT_PUBLIC_USE_MOCK=false in frontend/.env.local
 *   Then restart the dev server (next dev).
 */

export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";
