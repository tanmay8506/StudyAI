import React from 'react';
import { renderMath } from '@/lib/katex';
import { FieldFlagButton } from '../ui/FieldFlagButton';
import { FileText, CheckCircle2 } from 'lucide-react';

export interface PYQ {
  year: number;
  year_confirmed: boolean;
  year_confidence: string;
  source: string;
  marks: number;
  question_text: string;
  key_steps?: string[];
  instruction_word?: string;
  recency_weight?: number;
}

export interface PYQBlockProps {
  pyqs: PYQ[];
  topicId: string;
}

export function PYQBlock({ pyqs, topicId }: PYQBlockProps) {
  if (!pyqs || pyqs.length === 0) return null;

  return (
    <div className="space-y-6 mt-6">
      {pyqs.map((pyq, idx) => (
        <div key={idx} className="relative p-5 bg-card/40 border border-border rounded-lg group">
          <div className="flex justify-between items-start mb-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${pyq.year_confirmed ? 'bg-success/10 text-success' : 'bg-muted text-muted-foreground'}`}>
                {pyq.year_confirmed ? <CheckCircle2 className="w-3 h-3" /> : '~'} {pyq.year} DU Exam
              </span>
              <span className="text-xs px-2 py-1 bg-background border border-border text-foreground/80 rounded font-medium">
                {pyq.marks} marks
              </span>
              {pyq.recency_weight && pyq.recency_weight >= 1.5 && (
                <span className="text-xs px-2 py-1 bg-accent/10 text-accent rounded uppercase tracking-wider font-bold">
                  Most Recent
                </span>
              )}
            </div>
            <FieldFlagButton fieldName={`pyq_${idx}`} topicId={topicId} />
          </div>

          <div 
            className="text-base font-medium text-foreground mb-4 font-serif leading-relaxed"
            dangerouslySetInnerHTML={{ __html: renderMath(pyq.question_text) }}
          />

          {pyq.instruction_word && (
            <div className="text-xs mb-3">
              <span className="text-muted-foreground uppercase tracking-wider mr-2">Instruction:</span>
              <span className="font-mono bg-muted/50 px-1 py-0.5 rounded text-foreground/80">{pyq.instruction_word}</span>
            </div>
          )}

          {pyq.key_steps && pyq.key_steps.length > 0 && (
            <div className="space-y-1.5 ml-2 mt-4">
              {pyq.key_steps.map((step, sIdx) => (
                <div key={sIdx} className="flex gap-2 text-sm text-foreground/80">
                  <span className="text-accent shrink-0">→</span>
                  <span dangerouslySetInnerHTML={{ __html: renderMath(step) }} />
                </div>
              ))}
            </div>
          )}

          <div className="mt-4 text-right text-xs text-muted-foreground italic">
            Source: {pyq.source || "Student submitted"}
          </div>
        </div>
      ))}
    </div>
  );
}
