import React, { Fragment } from "react";
import "katex/dist/katex.min.css";
import { InlineMath, BlockMath } from "react-katex";

/**
 * MathText — Renders mixed text + LaTeX content.
 *
 * Splits content on $...$ and $$...$$ delimiters and renders
 * each segment with react-katex or as plain text.
 *
 * NOTE: This component is intentionally NOT dependent on FocusModeProvider.
 * It must be safe to render anywhere in the app (overview, pipeline, reading).
 * The previous version imported useFocusMode which crashed outside the
 * /reading route — that dependency has been removed.
 */

interface MathTextProps {
  content: string;
}

export function MathText({ content }: MathTextProps) {
  if (!content) return null;

  // Split by block math $$...$$ first, then inline math $...$
  const parts = content.split(/(\$\$[\s\S]+?\$\$|\$(?!\$)[^$]+?\$)/g);

  return (
    <span>
      {parts.map((part, i) => {
        if (part.startsWith("$$") && part.endsWith("$$")) {
          const math = part.slice(2, -2).trim();
          return (
            <span key={i} className="block my-4" aria-label={`Math formula: ${math}`}>
              <BlockMath math={math} />
            </span>
          );
        } else if (part.startsWith("$") && part.endsWith("$")) {
          const math = part.slice(1, -1).trim();
          return (
            <span key={i} aria-label={`Math formula: ${math}`}>
              <InlineMath math={math} />
            </span>
          );
        } else if (part) {
          // Plain text — preserve newlines
          return (
            <Fragment key={i}>
              {part.split("\n").map((line, j, arr) => (
                <Fragment key={j}>
                  {line}
                  {j < arr.length - 1 && <br />}
                </Fragment>
              ))}
            </Fragment>
          );
        }
        return null;
      })}
    </span>
  );
}
