import React, { Fragment } from "react";
import "katex/dist/katex.min.css";
import { InlineMath, BlockMath } from "react-katex";
import { useFocusMode } from "./reading/FocusModeProvider";

interface MathTextProps {
  content: string;
}

export function MathText({ content }: MathTextProps) {
  // Gotcha 14: when Focus Mode triggers sidebar collapse, KaTeX formulas may reflow.
  // We wrap KaTeX in a key that changes on focus mode to force re-render.
  const { isFocusMode } = useFocusMode();

  if (!content) return null;

  // Split by block math $$...$$ first, then inline math $...$
  const parts = content.split(/(\$\$[\s\S]+?\$\$|\$(?!\$)[^$]+?\$)/g);

  return (
    <span key={isFocusMode ? "focus-on" : "focus-off"}>
      {parts.map((part, i) => {
        if (part.startsWith("$$") && part.endsWith("$$")) {
          const math = part.slice(2, -2);
          // Gotcha 12/Accessibility: Complex formulas need aria-label
          return (
            <span key={i} className="block my-4" aria-label={`Math formula: ${math}`}>
              <BlockMath math={math} />
            </span>
          );
        } else if (part.startsWith("$") && part.endsWith("$")) {
          const math = part.slice(1, -1);
          return (
            <span key={i} aria-label={`Math formula: ${math}`}>
              <InlineMath math={math} />
            </span>
          );
        } else if (part) {
          // Render plain text preserving newlines
          return (
            <Fragment key={i}>
              {part.split('\n').map((line, j, arr) => (
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
