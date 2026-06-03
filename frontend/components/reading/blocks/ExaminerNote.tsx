"use client";

import { motion } from "framer-motion";
import { parseExaminerNote } from "@/lib/parseField";
import { InlineEditField } from "../InlineEditField";
import React from "react";

/**
 * ExaminerNoteBlock — Insider knowledge formatted with a unique amber tint.
 *
 * Scans text for 4-digit years and wraps them in amber pills automatically.
 * Supports inline editing on the examiners_note field when topicId is provided.
 */

interface ExaminerNoteBlockProps {
  noteData: unknown;
  topicId?: string;
}

export function ExaminerNoteBlock({ noteData, topicId }: ExaminerNoteBlockProps) {
  const note = parseExaminerNote(noteData);

  if (!note.text) return null;

  // Regex to match 4-digit years (e.g. 2019, 2023) using a capturing group.
  // This allows string.split() to include the matched years in the resulting array.
  const yearRegex = /\b(20\d{2})\b/g;
  const parts = note.text.split(yearRegex);

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.4 }}
      className="mt-8"
    >
      <div className="bg-[rgba(232,200,74,0.05)] border border-[rgba(232,200,74,0.15)] rounded-xl p-[16px_20px] flex flex-col gap-4">

        {/* Main Text — either editable (real mode) or read-only (mock) */}
        <div className="font-sans text-[14px] text-text-primary leading-relaxed">
          {topicId ? (
            /* Real mode: full inline edit on the raw text */
            <InlineEditField
              content={note.text}
              topicId={topicId}
              field="examiners_note"
              renderMath={false}
            />
          ) : (
            /* Mock mode: render with year-pill highlights, no edit */
            parts.map((part, index) => {
              if (index % 2 !== 0) {
                return (
                  <span
                    key={index}
                    className="inline-flex items-center justify-center font-mono text-[11px] text-accent bg-accent-dim border border-[rgba(232,200,74,0.2)] rounded-full px-2 py-0.5 mx-1 translate-y-[-1px]"
                  >
                    {part}
                  </span>
                );
              }
              return <React.Fragment key={index}>{part}</React.Fragment>;
            })
          )}
        </div>

        {/* Divider and Instruction Words (If available) */}
        {note.instruction_words.length > 0 && (
          <>
            <div className="w-full h-[1px] bg-border-subtle opacity-50" />
            <div className="flex flex-row flex-wrap gap-1.5">
              {note.instruction_words.map((iw, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-1.5 font-sans text-[11px] text-text-secondary bg-[rgba(255,255,255,0.04)] border border-border-default rounded-md px-2 py-1"
                >
                  <span>{iw.word}</span>
                  <span className="font-mono text-[10px] text-accent font-medium">
                    &times;{iw.count}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </motion.section>
  );
}
