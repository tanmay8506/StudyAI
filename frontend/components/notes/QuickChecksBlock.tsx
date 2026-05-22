import React from 'react';
import { FieldFlagButton } from '../ui/FieldFlagButton';
import { renderMath } from '@/lib/katex';

export interface QuickChecksBlockProps {
  quick_checks: string[];
  topicId: string;
}

export function QuickChecksBlock({ quick_checks, topicId }: QuickChecksBlockProps) {
  if (!quick_checks || quick_checks.length === 0) return null;

  return (
    <div className="relative p-5 mt-6 border-2 border-dashed border-border/80 rounded-lg group bg-card/20">
      <div className="flex justify-between items-center mb-4">
        <h4 className="text-sm font-semibold text-foreground/80 uppercase tracking-wider">
          Quick Check
        </h4>
        <FieldFlagButton fieldName="quick_checks" topicId={topicId} />
      </div>

      <div className="space-y-6">
        {quick_checks.map((check, idx) => (
          <div key={idx} className="space-y-2">
            <div 
              className="text-sm font-medium text-foreground/90"
              dangerouslySetInnerHTML={{ __html: renderMath(check) }}
            />
            <input 
              type="text" 
              className="w-full bg-background border border-border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-accent transition-shadow placeholder:text-muted-foreground/50"
              placeholder="Type your answer here..."
            />
            <p className="text-xs text-muted-foreground text-right italic">
              Check against your notes
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
