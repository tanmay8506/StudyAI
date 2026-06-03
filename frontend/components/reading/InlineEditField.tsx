"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { updateTopicField } from "@/lib/mutations";
import { MathText } from "@/components/MathText";

/**
 * InlineEditField
 * ─────────────────────────────────────────────────────
 * Wraps a text content block to allow inline editing with an explicit Save button.
 *
 * BEHAVIOUR:
 *   - Default:       Renders the content as-is (no visual change)
 *   - Double-click:  Transitions into an edit mode with a textarea + Save/Cancel buttons
 *   - Save button:   Saves to Supabase via updateTopicField(), shows "Saved ✓" flash
 *   - Cancel button: Reverts to original content, no save
 *   - Escape key:    Same as Cancel
 *
 * DISABLED STATES:
 *   - If `topicId` is undefined → edit mode never activates (mock mode safe)
 *   - If `field` is not in the whitelist → save will throw a clear error
 */

type SaveStatus = "idle" | "saving" | "saved" | "error";

interface InlineEditFieldProps {
  /** The raw text content to display and edit */
  content: string;
  /** Supabase topics.id — omit in mock mode to disable editing */
  topicId?: string;
  /** The column name in the topics table (must be in EDITABLE_FIELDS whitelist) */
  field: string;
  /** Optional class for the display text wrapper */
  className?: string;
  /** Use MathText renderer for content with LaTeX (default: true) */
  renderMath?: boolean;
}

export function InlineEditField({
  content,
  topicId,
  field,
  className = "",
  renderMath = true,
}: InlineEditFieldProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draftValue, setDraftValue] = useState(content);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [errorMsg, setErrorMsg] = useState<string>("");

  const canEdit = !!topicId;

  const handleDoubleClick = useCallback(() => {
    if (!canEdit) return;
    setDraftValue(content);
    setSaveStatus("idle");
    setErrorMsg("");
    setIsEditing(true);
  }, [canEdit, content]);

  const handleCancel = useCallback(() => {
    setIsEditing(false);
    setDraftValue(content);
    setSaveStatus("idle");
    setErrorMsg("");
  }, [content]);

  const handleSave = useCallback(async () => {
    if (!topicId) return;
    setSaveStatus("saving");
    try {
      await updateTopicField(topicId, field, draftValue.trim());
      setSaveStatus("saved");
      // Close editor after a brief "Saved ✓" flash
      setTimeout(() => {
        setIsEditing(false);
        setSaveStatus("idle");
      }, 1200);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setErrorMsg(msg);
      setSaveStatus("error");
    }
  }, [topicId, field, draftValue]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Escape") handleCancel();
    },
    [handleCancel]
  );

  // ── EDIT MODE ──
  if (isEditing) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col gap-3"
      >
        <textarea
          autoFocus
          value={draftValue}
          onChange={(e) => setDraftValue(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={Math.max(4, draftValue.split("\n").length + 1)}
          className="w-full bg-bg-surface border border-accent/40 rounded-lg px-4 py-3 font-sans text-[14px] text-text-primary leading-relaxed resize-y focus:outline-none focus:border-accent transition-colors"
          style={{ minHeight: "80px" }}
        />

        {/* Action row */}
        <div className="flex items-center gap-3">
          {/* Save button */}
          <button
            onClick={handleSave}
            disabled={saveStatus === "saving"}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-accent text-bg-base font-sans text-[11px] font-bold uppercase tracking-widest rounded-md hover:bg-accent-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saveStatus === "saving" ? "Saving…" : "Save"}
          </button>

          {/* Cancel button */}
          <button
            onClick={handleCancel}
            disabled={saveStatus === "saving"}
            className="px-4 py-1.5 border border-border-default font-sans text-[11px] text-text-secondary rounded-md hover:bg-bg-card transition-colors disabled:opacity-50"
          >
            Cancel
          </button>

          {/* Status feedback */}
          <AnimatePresence>
            {saveStatus === "saved" && (
              <motion.span
                key="saved"
                initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                className="font-mono text-[11px] text-green"
              >
                ✓ Saved
              </motion.span>
            )}
            {saveStatus === "error" && (
              <motion.span
                key="error"
                initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                className="font-mono text-[11px] text-red max-w-[260px] truncate"
                title={errorMsg}
              >
                ✕ {errorMsg}
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    );
  }

  // ── READ MODE ──
  return (
    <span
      onDoubleClick={handleDoubleClick}
      title={canEdit ? "Double-click to edit" : undefined}
      className={`${className} ${canEdit ? "cursor-text hover:bg-accent-dim rounded transition-colors duration-150" : ""}`}
    >
      {renderMath ? <MathText content={content} /> : content}
    </span>
  );
}
