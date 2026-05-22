import katex from "katex";

// ─────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────

/**
 * Returns true if the string contains any LaTeX delimiters.
 * Used to skip KaTeX processing on plain text for performance.
 */
export function isMathContent(text: string): boolean {
    return /\$/.test(text);
}

/**
 * Renders a single LaTeX expression as inline math.
 * For components that know they're rendering pure math (e.g. RapidRevisionCard formula).
 */
export function renderInline(latex: string): string {
    try {
        return katex.renderToString(latex, {
            throwOnError: false,
            displayMode: false,
            output: "html",
        });
    } catch {
        return latex;
    }
}

/**
 * Renders a single LaTeX expression as display (block) math.
 * For use in ExampleBlock answer boxes.
 */
export function renderDisplay(latex: string): string {
    try {
        return katex.renderToString(latex, {
            throwOnError: false,
            displayMode: true,
            output: "html",
        });
    } catch {
        return latex;
    }
}

/**
 * Scans text for $...$ (inline) and $$...$$ (display) delimiters,
 * replaces each match with KaTeX-rendered HTML.
 * Returns a string safe for dangerouslySetInnerHTML.
 *
 * Process $$...$$ first (display), then $...$ (inline)
 * to avoid double-processing.
 */
export function renderMath(text: string): string {
    if (!text) return "";
    if (!isMathContent(text)) return text;

    let result = text;

    // Display math: $$...$$
    result = result.replace(/\$\$([\s\S]+?)\$\$/g, (_match, latex: string) => {
        try {
            return katex.renderToString(latex.trim(), {
                throwOnError: false,
                displayMode: true,
                output: "html",
            });
        } catch {
            return _match;
        }
    });

    // Inline math: $...$
    result = result.replace(/\$((?!\$)[^$]+?)\$/g, (_match, latex: string) => {
        try {
            return katex.renderToString(latex.trim(), {
                throwOnError: false,
                displayMode: false,
                output: "html",
            });
        } catch {
            return _match;
        }
    });

    return result;
}