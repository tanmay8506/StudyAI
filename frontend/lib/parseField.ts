/**
 * STUDYAI — PARSEFIELD UTILITY
 * 
 * Critical: AI agents return JSON-encoded strings as field values.
 * Without this layer, raw JSON strings render in the UI.
 * Every content field in every block MUST pass through these parsers.
 * 
 * SECURITY NOTE:
 * parseQuickCheck returns { question } ONLY.
 * The answer field is backend-only — it NEVER touches any frontend component.
 * Self-assessment is subjective by design.
 */

// ================================================================
// TYPE DEFINITIONS
// ================================================================

export interface QuickCheckParsed {
  question: string;
}

export interface CommonMistakeParsed {
  mistake: string;
  marks_lost?: string;
}

export interface ExaminerNoteParsed {
  text: string;
  years: string[];
  instruction_words: { word: string; count: number }[];
}

export interface ExampleParsed {
  problem: string;
  steps: { number: string; text: string }[];
  answer: string;
  common_error: string | null;
  example_type: string;
  verified: boolean;
  verification_mode: string;
}

// ================================================================
// CORE PARSERS
// ================================================================

/**
 * parseField — general-purpose field parser
 * Handles: raw strings, JSON objects with .meaning/.text/.content/.definition
 * Returns the human-readable string in all cases.
 * Never throws — returns raw input on failure.
 */
export function parseField(raw: unknown): string {
  if (raw === null || raw === undefined) return "";
  if (typeof raw === "number" || typeof raw === "boolean") return String(raw);

  const str = typeof raw === "string" ? raw : JSON.stringify(raw);

  // Try parsing as JSON
  try {
    const parsed = JSON.parse(str);

    if (typeof parsed === "string") return parsed;
    if (typeof parsed !== "object" || parsed === null) return str;

    // Check known content keys in priority order
    if (typeof parsed.meaning     === "string") return parsed.meaning;
    if (typeof parsed.text        === "string") return parsed.text;
    if (typeof parsed.content     === "string") return parsed.content;
    if (typeof parsed.definition  === "string") return parsed.definition;
    if (typeof parsed.summary     === "string") return parsed.summary;
    if (typeof parsed.description === "string") return parsed.description;
    if (typeof parsed.value       === "string") return parsed.value;

    // Fallback: stringify the object for debugging
    return str;
  } catch {
    // Not JSON — return as-is
    return str;
  }
}

/**
 * parseQuickCheck — returns ONLY the question field
 * The answer field is NEVER exposed to any component. Ever.
 */
export function parseQuickCheck(raw: unknown): QuickCheckParsed | null {
  if (raw === null || raw === undefined) return null;

  const str = typeof raw === "string" ? raw : JSON.stringify(raw);

  try {
    const parsed = JSON.parse(str);

    if (typeof parsed !== "object" || parsed === null) {
      return { question: str };
    }

    const question =
      parsed.question ??
      parsed.text ??
      parsed.content ??
      parsed.prompt ??
      "";

    // answer is intentionally omitted here — backend only
    return { question: typeof question === "string" ? question : String(question) };
  } catch {
    return { question: str };
  }
}

/**
 * parseCommonMistakes — returns typed array of mistake objects
 */
export function parseCommonMistakes(raw: unknown): CommonMistakeParsed[] {
  if (raw === null || raw === undefined) return [];

  const str = typeof raw === "string" ? raw : JSON.stringify(raw);

  try {
    const parsed = JSON.parse(str);

    if (Array.isArray(parsed)) {
      return parsed.map((item) => {
        if (typeof item === "string") return { mistake: item };
        return {
          mistake:    typeof item.mistake    === "string" ? item.mistake    : String(item.mistake ?? item.text ?? item),
          marks_lost: typeof item.marks_lost === "string" ? item.marks_lost : undefined,
        };
      });
    }

    if (typeof parsed === "string") return [{ mistake: parsed }];
    if (typeof parsed === "object" && parsed !== null) {
      return [{ mistake: parsed.mistake ?? parsed.text ?? str }];
    }

    return [{ mistake: str }];
  } catch {
    return [{ mistake: str }];
  }
}

/**
 * parseExaminerNote — returns structured note with years and instruction words
 */
export function parseExaminerNote(raw: unknown): ExaminerNoteParsed {
  const fallback: ExaminerNoteParsed = { text: "", years: [], instruction_words: [] };

  if (raw === null || raw === undefined) return fallback;

  const str = typeof raw === "string" ? raw : JSON.stringify(raw);

  try {
    const parsed = JSON.parse(str);

    if (typeof parsed === "string") return { ...fallback, text: parsed };
    if (typeof parsed !== "object" || parsed === null) return { ...fallback, text: str };

    const text = parseField(parsed.text ?? parsed.content ?? parsed.note ?? str);

    const years = Array.isArray(parsed.years)
      ? parsed.years.map(String)
      : [];

    const instruction_words = Array.isArray(parsed.instruction_words)
      ? parsed.instruction_words.map((iw: unknown) => {
          if (typeof iw === "object" && iw !== null) {
            const item = iw as Record<string, unknown>;
            return {
              word:  typeof item.word  === "string" ? item.word  : String(item.word ?? ""),
              count: typeof item.count === "number" ? item.count : Number(item.count ?? 1),
            };
          }
          return { word: String(iw), count: 1 };
        })
      : [];

    return { text, years, instruction_words };
  } catch {
    return { ...fallback, text: str };
  }
}

/**
 * parseExample — returns fully typed worked example object
 */
export function parseExample(raw: unknown): ExampleParsed | null {
  if (raw === null || raw === undefined) return null;

  const str = typeof raw === "string" ? raw : JSON.stringify(raw);

  try {
    const parsed = JSON.parse(str);

    if (typeof parsed !== "object" || parsed === null) return null;

    const steps = Array.isArray(parsed.steps)
      ? parsed.steps.map((s: unknown) => {
          if (typeof s === "object" && s !== null) {
            const step = s as Record<string, unknown>;
            return {
              number: typeof step.number === "string" ? step.number : String(step.number ?? ""),
              text:   typeof step.text   === "string" ? step.text   : String(step.text   ?? ""),
            };
          }
          return { number: "", text: String(s) };
        })
      : [];

    return {
      problem:           parseField(parsed.problem ?? ""),
      steps,
      answer:            parseField(parsed.answer ?? ""),
      common_error:      parsed.common_error ? parseField(parsed.common_error) : null,
      example_type:      typeof parsed.example_type      === "string" ? parsed.example_type      : "worked",
      verified:          typeof parsed.verified           === "boolean" ? parsed.verified          : false,
      verification_mode: typeof parsed.verification_mode === "string" ? parsed.verification_mode : "none",
    };
  } catch {
    return null;
  }
}

/**
 * parseYears — extracts 4-digit year strings from any text
 * Used to auto-wrap year references in amber pills in examiner notes
 */
export function parseYears(text: string): string[] {
  const matches = text.match(/\b(19|20)\d{2}\b/g);
  return matches ? [...new Set(matches)] : [];
}
