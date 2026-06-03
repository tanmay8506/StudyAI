import { supabase } from "./supabase";

/**
 * mutations.ts
 * ─────────────────────────────────────────────────────
 * All write operations from the frontend to Supabase.
 * 
 * FIELD WHITELIST: Only plain text fields are editable.
 * JSON blob fields (examples, pyqs, diagram_block, etc.) are never
 * exposed for direct editing to prevent schema corruption.
 */

const EDITABLE_FIELDS = new Set([
  "definition",
  "core_concept",
  "analogy",
  "examiners_note",
]);

/**
 * updateTopicField — Updates a single plain-text field on a topics row.
 *
 * @param topicId  - UUID of the topic to update
 * @param field    - Field name (must be in EDITABLE_FIELDS whitelist)
 * @param value    - New string value
 * @throws Error if field is not whitelisted or Supabase returns an error
 */
export async function updateTopicField(
  topicId: string,
  field: string,
  value: string
): Promise<void> {
  if (!EDITABLE_FIELDS.has(field)) {
    throw new Error(
      `[mutations] Field "${field}" is not in the editable whitelist. ` +
      `Allowed fields: ${[...EDITABLE_FIELDS].join(", ")}`
    );
  }

  const { error } = await supabase
    .from("topics")
    .update({ [field]: value })
    .eq("id", topicId);

  if (error) {
    console.error(`[updateTopicField] Failed to update "${field}" on topic ${topicId}:`, error.message);
    throw new Error(error.message);
  }
}
