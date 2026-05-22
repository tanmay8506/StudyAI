import React from 'react';
import { renderMath } from '@/lib/katex';
import { FieldFlagButton } from '../ui/FieldFlagButton';

export interface RapidRevisionCardProps {
  rapid_revision: {
    definition_one_line: string;
    key_formula_or_concept: string;
    examiner_pattern: string;
  };
  topic_name: string;
  topicId: string;
  priority: 'high' | 'medium' | 'low' | 'never_asked';
  isExpanded: boolean;
  onToggle: () => void;
}

export function RapidRevisionCard({
  rapid_revision,
  topic_name,
  topicId,
  priority,
  isExpanded,
  onToggle
}: RapidRevisionCardProps) {
  if (!rapid_revision) return null;

  const priorityColors = {
    high: 'border-l-red-500 bg-red-500/5',
    medium: 'border-l-amber-500 bg-amber-500/5',
    low: 'border-l-slate-400 bg-slate-500/5',
    never_asked: 'border-l-slate-200 bg-transparent opacity-75'
  };

  const priorityLabels = {
    high: 'HIGH YIELD',
    medium: 'MEDIUM YIELD',
    low: 'LOW YIELD',
    never_asked: 'NOT EXAMINED'
  };

  return (
    <div 
      className={`relative p-4 rounded-lg shadow-sm border border-border/50 border-l-4 cursor-pointer hover:bg-black/5 dark:hover:bg-white/5 transition-colors group ${priorityColors[priority]}`}
      onClick={onToggle}
    >
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-lg font-semibold text-foreground">
          {topic_name}
        </h3>
        <span className="text-xs font-bold tracking-wider text-muted-foreground">
          {priorityLabels[priority]}
        </span>
      </div>

      <div className="space-y-2 text-sm text-foreground/90">
        <p dangerouslySetInnerHTML={{ __html: renderMath(rapid_revision.definition_one_line) }} />
        <p className="font-mono text-accent" dangerouslySetInnerHTML={{ __html: renderMath(rapid_revision.key_formula_or_concept) }} />
        <p className="text-muted-foreground italic" dangerouslySetInnerHTML={{ __html: renderMath(rapid_revision.examiner_pattern) }} />
      </div>

      <div className="absolute top-2 right-2 flex items-center gap-2">
        <FieldFlagButton fieldName="rapid_revision" topicId={topicId} />
      </div>
    </div>
  );
}
