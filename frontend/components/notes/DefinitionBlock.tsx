import React from 'react';
import { renderMath } from '@/lib/katex';
import { FieldFlagButton } from '../ui/FieldFlagButton';
import { cn } from '@/lib/utils';

export interface DefinitionBlockProps {
  definition: string;
  topic_name: string;
  topicId: string;
}

export function DefinitionBlock({ definition, topic_name, topicId }: DefinitionBlockProps) {
  if (!definition) return null;

  return (
    <div className="relative group my-8 pl-6 border-l-2 border-foreground bg-card/5 py-4 pr-4">
      <div className="flex justify-between items-start mb-3">
        <span className="text-[10px] font-mono font-bold tracking-[0.2em] text-foreground uppercase">
          [ Axiomatic Definition: {topic_name} ]
        </span>
        <div className="opacity-0 group-hover:opacity-100 transition-opacity">
          <FieldFlagButton fieldName="definition" topicId={topicId} />
        </div>
      </div>
      <p 
        className="text-lg font-serif text-foreground leading-relaxed max-w-[65ch]"
        dangerouslySetInnerHTML={{ __html: renderMath(definition) }}
      />
    </div>
  );
}
