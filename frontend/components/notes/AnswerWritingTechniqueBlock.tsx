import React from 'react';
import { renderMath } from '@/lib/katex';
import { FieldFlagButton } from '../ui/FieldFlagButton';
import { PenTool } from 'lucide-react';

export interface AnswerWritingTechnique {
  applicable: boolean;
  min_marks_threshold?: number;
  structure?: string[];
  marks_distribution?: Record<string, string>;
  word_count_target?: number;
}

export interface AnswerWritingTechniqueBlockProps {
  answer_writing_technique: AnswerWritingTechnique | null;
  topicId: string;
}

export function AnswerWritingTechniqueBlock({ answer_writing_technique, topicId }: AnswerWritingTechniqueBlockProps) {
  if (!answer_writing_technique || !answer_writing_technique.applicable) return null;

  return (
    <div className="relative p-5 mt-6 border border-border/60 rounded-lg group">
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-2">
          <PenTool className="w-4 h-4 text-muted-foreground" />
          <h4 className="text-sm font-semibold text-foreground/80 uppercase tracking-wider">
            Answer Writing Technique
          </h4>
          {answer_writing_technique.min_marks_threshold && (
            <span className="ml-2 text-xs px-2 py-0.5 bg-muted text-muted-foreground rounded-full">
              {answer_writing_technique.min_marks_threshold}+ marks
            </span>
          )}
        </div>
        <FieldFlagButton fieldName="answer_writing_technique" topicId={topicId} />
      </div>

      {answer_writing_technique.structure && answer_writing_technique.structure.length > 0 && (
        <div className="space-y-2 mb-4">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-2">Structure</div>
          <ol className="list-decimal pl-4 space-y-1 text-sm text-foreground/90">
            {answer_writing_technique.structure.map((step, idx) => (
              <li key={idx} dangerouslySetInnerHTML={{ __html: renderMath(step) }} />
            ))}
          </ol>
        </div>
      )}

      {answer_writing_technique.marks_distribution && Object.keys(answer_writing_technique.marks_distribution).length > 0 && (
        <div className="mb-4">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-2">Marks Distribution</div>
          <div className="flex flex-wrap gap-2 text-sm">
            {Object.entries(answer_writing_technique.marks_distribution).map(([part, marks]) => (
              <span key={part} className="px-2 py-1 bg-background border border-border rounded text-foreground/80">
                {part}: <strong className="text-accent">{marks}</strong>
              </span>
            ))}
          </div>
        </div>
      )}

      {answer_writing_technique.word_count_target && (
        <div className="text-sm text-muted-foreground italic">
          Target: ~{answer_writing_technique.word_count_target} words
        </div>
      )}
    </div>
  );
}
