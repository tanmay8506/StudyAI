import React from 'react';
import { renderMath } from '@/lib/katex';
import { FieldFlagButton } from '../ui/FieldFlagButton';

export interface CoreConceptBlockProps {
  core_concept: string;
  analogy?: string;
  analogy_verified: boolean;
  topicId: string;
}

export function CoreConceptBlock({ core_concept, analogy, analogy_verified, topicId }: CoreConceptBlockProps) {
  if (!core_concept) return null;

  return (
    <div className="relative p-5 group mt-4">
      <div className="flex justify-between items-start mb-2">
        <h4 className="text-sm font-semibold text-foreground/80 uppercase tracking-wider">
          Core Concept
        </h4>
        <FieldFlagButton fieldName="core_concept" topicId={topicId} />
      </div>
      
      <div 
        className="text-base leading-relaxed text-foreground"
        dangerouslySetInnerHTML={{ __html: renderMath(core_concept) }}
      />

      {analogy && (
        <div className="mt-4 pt-3 border-t border-border/50">
          <p className="text-sm text-muted-foreground mb-1 flex justify-between items-center">
            <span>Think of it this way:</span>
            {!analogy_verified && <span className="text-xs text-warning" title="Unverified analogy">⚠️ Unverified</span>}
          </p>
          <p 
            className="text-base italic text-foreground/90"
            dangerouslySetInnerHTML={{ __html: renderMath(analogy) }}
          />
        </div>
      )}
    </div>
  );
}
