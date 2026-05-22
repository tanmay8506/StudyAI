import React from 'react';
import { renderMath } from '@/lib/katex';
import { FieldFlagButton } from '../ui/FieldFlagButton';
import { Eye } from 'lucide-react';

export interface ExaminersNoteBlockProps {
  examiners_note: string;
  examiners_note_pyq_refs?: string[];
  instruction_word_frequency?: Record<string, number>;
  topicId: string;
}

export function ExaminersNoteBlock({
  examiners_note,
  examiners_note_pyq_refs,
  instruction_word_frequency,
  topicId
}: ExaminersNoteBlockProps) {
  if (!examiners_note) return null;

  let formattedNote = renderMath(examiners_note);
  
  if (examiners_note_pyq_refs && examiners_note_pyq_refs.length > 0) {
    examiners_note_pyq_refs.forEach(year => {
      const pill = `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-accent/20 text-accent mx-0.5 shadow-sm">[${year}]</span>`;
      formattedNote = formattedNote.replace(new RegExp(year, 'g'), pill);
    });
  }

  return (
    <div className="relative p-5 mt-6 bg-accent/5 border border-accent/20 rounded-lg group">
      <div className="flex justify-between items-center mb-3">
        <div className="flex items-center gap-2 text-accent">
          <Eye className="w-4 h-4" />
          <span className="text-xs font-bold tracking-widest uppercase">
            Examiner's Note
          </span>
        </div>
        <FieldFlagButton fieldName="examiners_note" topicId={topicId} />
      </div>

      <div 
        className="text-base leading-relaxed text-foreground"
        dangerouslySetInnerHTML={{ __html: formattedNote }}
      />

      {instruction_word_frequency && Object.keys(instruction_word_frequency).length > 0 && (
        <div className="mt-4 pt-3 border-t border-accent/10 flex flex-wrap gap-3">
          <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider flex items-center">
            DU says:
          </span>
          <div className="flex flex-wrap gap-2">
            {Object.entries(instruction_word_frequency).map(([word, count]) => (
              <span key={word} className="text-xs px-2 py-1 bg-background/50 border border-border rounded-full text-foreground/80">
                {word} <span className="text-accent ml-1 font-mono">(×{count})</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
