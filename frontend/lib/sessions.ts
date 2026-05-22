"use client";

const SESSION_ID_KEY = "studyai_session_id";
const SESSION_DATA_KEY = "studyai_session_data";
const FLAG_LIMIT = 10;

// ─────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────

export interface SessionData {
    sessionId: string;
    flagCounts: Record<string, number>; // upc -> count
    flaggedPapers: string[];            // upcs where flags were submitted
    unlockedPapers: string[];           // tier 3/4 upcs unlocked via reward
}

// ─────────────────────────────────────────
// INTERNAL HELPERS
// ─────────────────────────────────────────

function isClient(): boolean {
    return typeof window !== "undefined";
}

function generateUUID(): string {
    if (isClient() && crypto?.randomUUID) {
        return crypto.randomUUID();
    }
    // Fallback for environments without crypto.randomUUID
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        const v = c === "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
}

function defaultSessionData(sessionId: string): SessionData {
    return {
        sessionId,
        flagCounts: {},
        flaggedPapers: [],
        unlockedPapers: [],
    };
}

// ─────────────────────────────────────────
// PUBLIC API
// ─────────────────────────────────────────

/**
 * Returns the session ID, creating and persisting one if it doesn't exist.
 * SSR-safe — returns a temporary ID on the server.
 */
export function getOrCreateSessionId(): string {
    if (!isClient()) return "ssr-placeholder";

    const existing = localStorage.getItem(SESSION_ID_KEY);
    if (existing) return existing;

    const newId = generateUUID();
    localStorage.setItem(SESSION_ID_KEY, newId);
    return newId;
}

/**
 * Returns the full session data object.
 * Creates it if it doesn't exist yet.
 */
export function getSessionData(): SessionData {
    if (!isClient()) {
        return defaultSessionData("ssr-placeholder");
    }

    const raw = localStorage.getItem(SESSION_DATA_KEY);
    if (!raw) {
        const sessionId = getOrCreateSessionId();
        const data = defaultSessionData(sessionId);
        localStorage.setItem(SESSION_DATA_KEY, JSON.stringify(data));
        return data;
    }

    try {
        return JSON.parse(raw) as SessionData;
    } catch {
        const sessionId = getOrCreateSessionId();
        const data = defaultSessionData(sessionId);
        localStorage.setItem(SESSION_DATA_KEY, JSON.stringify(data));
        return data;
    }
}

function saveSessionData(data: SessionData): void {
    if (!isClient()) return;
    localStorage.setItem(SESSION_DATA_KEY, JSON.stringify(data));
}

/**
 * Increments the flag count for a paper in this session.
 * Returns false if the rate limit (10 flags per paper) has been hit.
 * Returns true if the flag is allowed.
 */
export function incrementFlagCount(upc: string): boolean {
    const data = getSessionData();
    const current = data.flagCounts[upc] ?? 0;

    if (current >= FLAG_LIMIT) return false;

    data.flagCounts[upc] = current + 1;
    if (!data.flaggedPapers.includes(upc)) {
        data.flaggedPapers.push(upc);
    }
    saveSessionData(data);
    return true;
}

/**
 * Marks a paper as unlocked for this session (tier 3/4 reward).
 */
export function unlockPaper(upc: string): void {
    const data = getSessionData();
    if (!data.unlockedPapers.includes(upc)) {
        data.unlockedPapers.push(upc);
        saveSessionData(data);
    }
}

/**
 * Returns true if the paper is accessible in this session.
 * Tier 1/2 papers are always accessible.
 * Tier 3/4 papers require an unlock via reward.
 */
export function isPaperUnlocked(
    upc: string,
    tier: 1 | 2 | 3 | 4
): boolean {
    if (tier === 1 || tier === 2) return true;
    const data = getSessionData();
    return data.unlockedPapers.includes(upc);
}

/**
 * Returns the current flag count for a paper in this session.
 */
export function getFlagCount(upc: string): number {
    const data = getSessionData();
    return data.flagCounts[upc] ?? 0;
}