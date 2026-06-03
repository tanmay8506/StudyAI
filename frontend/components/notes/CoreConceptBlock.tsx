import React from 'react';
import { renderMath } from '@/lib/katex';
import { FieldFlagButton } from '../ui/FieldFlagButton';
import { cn } from '@/lib/utils';

export interface CoreConceptBlockProps {
  core_concept: string;
  analogy?: string;
  analogy_verified: boolean;
  topicId: string;
}

export function CoreConceptBlock({ core_concept, analogy, analogy_verified, topicId }: CoreConceptBlockProps) {
  if (!core_concept) return null;

  return (
    <div className="relative group my-8 pl-6 border-l border-border hover:border-foreground/30 transition-colors">
      <div className="flex justify-between items-start mb-4">
        <h4 className="text-[11px] font-mono tracking-widest text-muted-foreground uppercase">
          // Core Construct
        </h4>
        <div className="opacity-0 group-hover:opacity-100 transition-opacity">
          <FieldFlagButton fieldName="core_concept" topicId={topicId} />
        </div>
      </div>
      
      <div 
        className="text-base font-serif leading-relaxed text-foreground max-w-[65ch] space-y-4"
        dangerouslySetInnerHTML={{ __html: renderMath(core_concept) }}
      />

      {analogy && (
        <div className="mt-6 pt-4 border-t border-dashed border-border/50 max-w-[65ch]">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-[10px] font-mono tracking-wider text-muted-foreground uppercase">Model Analogy</span>
            {!analogy_verified && (
              <span className="px-1.5 py-0.5 bg-warning/10 text-warning text-[9px] font-mono uppercase tracking-wider">
                Unverified
              </span>
            )}
          </div>
          <p 
            className="text-[15px] font-serif italic text-muted-foreground leading-relaxed"
            dangerouslySetInnerHTML={{ __html: renderMath(analogy) }}
          />
        </div>
      )}
    </div>
  );
}
