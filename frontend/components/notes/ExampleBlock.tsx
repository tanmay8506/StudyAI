import React from 'react';
import { renderMath } from '@/lib/katex';
import { FieldFlagButton } from '../ui/FieldFlagButton';
import { VerifiedBadge } from '../ui/VerifiedBadge';

export interface Example {
  type: string;
  content: string;
  steps?: string[];
  answer?: string;
  answer_boxed?: boolean;
  common_error?: string;
  verified: boolean;
  verification_mode: string;
  verification_passed: boolean;
}

export interface ExampleBlockProps {
  examples: Example[];
  paper_type: 'numerical' | 'theory' | 'mixed' | 'life_sciences';
  topicId: string;
}

export function ExampleBlock({ examples, paper_type, topicId }: ExampleBlockProps) {
  if (!examples || examples.length === 0) return null;

  return (
    <div className="space-y-6 mt-6">
      {examples.map((example, idx) => (
        <div key={idx} className="relative p-5 bg-card border border-border/50 rounded-lg group shadow-sm">
          <div className="flex justify-between items-start mb-4">
            <h4 className="text-sm font-semibold text-foreground/80 uppercase tracking-wider">
              Example {idx + 1}
            </h4>
            <div className="flex items-center gap-2">
              <VerifiedBadge 
                verified={example.verified} 
                verificationMode={example.verification_mode} 
                verificationPassed={example.verification_passed} 
              />
              <FieldFlagButton fieldName={`example_${idx}`} topicId={topicId} />
            </div>
          </div>

          <div 
            className="text-base leading-relaxed text-foreground mb-4"
            dangerouslySetInnerHTML={{ __html: renderMath(example.content) }}
          />

          {(paper_type === 'numerical' || paper_type === 'mixed') && example.steps && (
            <div className="space-y-2 mt-4 ml-4 border-l-2 border-border/50 pl-4">
              {example.steps.map((step, sIdx) => (
                <div key={sIdx} className="flex gap-3">
                  <span className="text-muted-foreground text-sm mt-0.5 font-mono">{sIdx + 1}.</span>
                  <div 
                    className="text-base text-foreground/90 overflow-x-auto"
                    dangerouslySetInnerHTML={{ __html: renderMath(step) }}
                  />
                </div>
              ))}
            </div>
          )}

          {example.answer && (
            <div className={`mt-6 overflow-x-auto ${example.answer_boxed ? 'p-4 border-2 border-accent/20 bg-accent/5 rounded-md inline-block min-w-full text-center' : ''}`}>
              <div 
                className="text-lg font-medium"
                dangerouslySetInnerHTML={{ __html: renderMath(example.answer) }}
              />
            </div>
          )}

          {example.common_error && (
            <div className="mt-4 p-3 bg-warning/10 border border-warning/20 rounded text-sm text-warning-foreground">
              <strong className="font-semibold mr-2">Common Error:</strong>
              <span dangerouslySetInnerHTML={{ __html: renderMath(example.common_error) }} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
