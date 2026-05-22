import React, { useState } from 'react';
import { renderMath } from '@/lib/katex';
import { ProblemSet as DBProblemSet } from '@/types/database';
import { Target, Eye, EyeOff } from 'lucide-react';

export interface QuestionData {
  number: number;
  source_type: string;
  source_year?: number;
  source_book?: string;
  source_exercise?: string;
  marks: number;
  question_text: string;
  answer: {
    type: string;
    full_answer: string;
    steps?: string[];
    word_count?: number;
    common_error_callout?: string;
  };
}

export interface ProblemSetProps {
  problemSet: DBProblemSet | null;
  unitName: string;
}

export function ProblemSet({ problemSet, unitName }: ProblemSetProps) {
  const [revealed, setRevealed] = useState<Record<number, boolean>>({});

  if (!problemSet || !problemSet.content) return null;
  const questions = problemSet.content as QuestionData[];
  if (!Array.isArray(questions) || questions.length === 0) return null;

  const toggleReveal = (idx: number) => {
    setRevealed(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  return (
    <div className="mt-10 mb-8 border border-border/80 rounded-xl bg-card overflow-hidden shadow-sm">
      <div className="bg-muted/40 p-5 border-b border-border flex items-center gap-3">
        <Target className="w-6 h-6 text-accent" />
        <div>
          <h3 className="font-bold tracking-wider uppercase text-sm">Problem Set</h3>
          <p className="text-xs text-muted-foreground mt-0.5">{questions.length} QUESTIONS</p>
        </div>
      </div>

      <div className="p-1">
        {questions.map((q, idx) => {
          const isRevealed = !!revealed[idx];
          return (
            <div key={idx} className="p-5 border-b border-border/50 last:border-0 hover:bg-muted/10 transition-colors">
              <div className="flex justify-between items-start mb-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-bold text-foreground mr-2">Q{q.number || idx + 1}.</span>
                  <span className="text-xs px-2 py-1 bg-accent/10 text-accent font-medium rounded">
                    {q.source_type === 'pyq' ? `${q.source_year} DU Exam` : `Textbook: ${q.source_book}, Ex.${q.source_exercise}`}
                  </span>
                  <span className="text-xs px-2 py-1 bg-background border border-border text-foreground/80 rounded font-medium">
                    {q.marks} marks
                  </span>
                </div>
                <button 
                  onClick={() => toggleReveal(idx)}
                  className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full border border-border bg-background hover:bg-muted/50 transition-colors text-foreground/80 shrink-0 ml-2"
                >
                  {isRevealed ? (
                    <><EyeOff className="w-3.5 h-3.5" /> Hide</>
                  ) : (
                    <><Eye className="w-3.5 h-3.5" /> Answer</>
                  )}
                </button>
              </div>

              <div 
                className="text-base font-serif leading-relaxed text-foreground"
                dangerouslySetInnerHTML={{ __html: renderMath(q.question_text) }}
              />

              {isRevealed && q.answer && (
                <div className="mt-6 p-4 bg-muted/20 border border-border rounded-lg animate-in fade-in slide-in-from-top-2 duration-300">
                  <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-4 border-b border-border pb-2">
                    Solution
                  </div>
                  
                  {q.answer.steps && q.answer.steps.length > 0 ? (
                    <div className="space-y-3 mb-4">
                      {q.answer.steps.map((step, sIdx) => (
                        <div key={sIdx} className="flex gap-3">
                          <span className="text-muted-foreground font-mono text-sm mt-0.5">{sIdx + 1}.</span>
                          <div dangerouslySetInnerHTML={{ __html: renderMath(step) }} className="text-sm text-foreground/90 overflow-x-auto" />
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div 
                      className="text-sm text-foreground/90 mb-4 overflow-x-auto leading-relaxed"
                      dangerouslySetInnerHTML={{ __html: renderMath(q.answer.full_answer) }}
                    />
                  )}

                  {q.answer.word_count && (
                    <div className="text-xs text-muted-foreground italic mb-4">
                      ~{q.answer.word_count} words to DU standard
                    </div>
                  )}

                  {q.answer.common_error_callout && (
                    <div className="mt-4 p-3 bg-warning/10 border border-warning/20 rounded-md text-sm text-warning-foreground">
                      <strong className="font-semibold mr-2 uppercase text-xs tracking-wider">Common Pitfall:</strong>
                      <span dangerouslySetInnerHTML={{ __html: renderMath(q.answer.common_error_callout) }} />
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
