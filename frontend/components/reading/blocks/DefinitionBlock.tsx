"use client";

import { motion } from "framer-motion";
import { InkDrawBorder } from "../InkDrawBorder";
import { parseField } from "@/lib/parseField";
import { InlineEditField } from "../InlineEditField";

/**
 * DefinitionBlock — Presents the foundational definition of the topic.
 *
 * Supports inline editing when a real `topicId` is provided (real mode).
 * In mock mode, topicId is omitted and editing is silently disabled.
 */

interface DefinitionBlockProps {
  definitionText: unknown;
  topicId?: string;
}

export function DefinitionBlock({ definitionText, topicId }: DefinitionBlockProps) {
  const text = parseField(definitionText);

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      className="flex flex-col gap-4 mt-8 group"
    >
      {/* Section Label Row */}
      <div className="flex flex-row items-center justify-between">
        <div className="flex flex-row items-center gap-4 flex-1">
          <span className="font-sans text-[10px] uppercase tracking-widest text-text-tertiary">
            Definition
          </span>
          <div className="w-[32px] h-[1px] bg-border-default" />
        </div>

        {/* Flag Button */}
        <motion.button
          initial={{ opacity: 0 }}
          whileHover={{ scale: 0.95 }}
          className="no-print opacity-0 group-hover:opacity-100 transition-opacity duration-150 flex items-center gap-1.5 px-3 py-1 rounded border border-transparent hover:border-[rgba(232,90,74,0.3)] hover:bg-red-dim font-sans text-[10px] text-text-tertiary hover:text-red"
        >
          <span>⚑</span> Flag
        </motion.button>
      </div>

      {/* Definition Card */}
      <div className="relative bg-bg-card border border-border-default rounded-xl p-[16px_20px] pl-[24px]">

        {/* Ink Draw Border — visual only */}
        <InkDrawBorder />

        {/* Inline-editable definition text */}
        <p className="font-serif text-[18px] text-text-primary leading-relaxed">
          <InlineEditField
            content={text}
            topicId={topicId}
            field="definition"
            renderMath={true}
          />
        </p>
      </div>
    </motion.section>
  );
}
