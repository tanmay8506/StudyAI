import React from 'react';
import { renderMath } from '@/lib/katex';
import { FieldFlagButton } from '../ui/FieldFlagButton';

export interface DefinitionBlockProps {
  definition: string;
  topic_name: string;
  topicId: string;
}

export function DefinitionBlock({ definition, topic_name, topicId }: DefinitionBlockProps) {
  if (!definition) return null;

  return (
    <div className="relative p-5 bg-card/50 rounded-md border border-border/50 group mt-4">
      <div className="flex justify-between items-center mb-2">
        <span className="text-xs font-bold tracking-wider text-muted-foreground uppercase">
          Definition
        </span>
        <FieldFlagButton fieldName="definition" topicId={topicId} />
      </div>
      <p 
        className="text-base text-foreground leading-relaxed"
        dangerouslySetInnerHTML={{ __html: renderMath(definition) }}
      />
    </div>
  );
}
