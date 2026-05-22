import React from 'react';
import { renderMath } from '@/lib/katex';
import { FieldFlagButton } from '../ui/FieldFlagButton';
import { AlertOctagon } from 'lucide-react';

export interface CommonMistakesBlockProps {
  common_mistakes: Array<{ description: string; marks_impact: string }>;
  topicId: string;
}

export function CommonMistakesBlock({ common_mistakes, topicId }: CommonMistakesBlockProps) {
  if (!common_mistakes || common_mistakes.length === 0) return null;

  return (
    <div className="relative p-5 mt-6 bg-red-500/5 border border-red-500/10 rounded-lg group">
      <div className="flex justify-between items-center mb-3">
        <div className="flex items-center gap-2 text-red-500/80">
          <AlertOctagon className="w-4 h-4" />
          <span className="text-xs font-bold tracking-widest uppercase">
            Common Mistakes
          </span>
        </div>
        <FieldFlagButton fieldName="common_mistakes" topicId={topicId} />
      </div>

      <div className="space-y-3">
        {common_mistakes.map((mistake, idx) => (
          <div key={idx} className="flex gap-3 items-start">
            <span className="text-red-500/60 font-mono text-sm mt-0.5">{idx + 1}.</span>
            <div className="flex-1">
              <div 
                className="text-sm text-foreground/90"
                dangerouslySetInnerHTML={{ __html: renderMath(mistake.description) }}
              />
            </div>
            {mistake.marks_impact && (
              <span className="shrink-0 text-xs px-2 py-1 bg-red-500/10 text-red-500/80 rounded font-medium whitespace-nowrap">
                {mistake.marks_impact}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
