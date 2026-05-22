import React from 'react';
import { Flag } from 'lucide-react';

export function FieldFlagButton({ fieldName, topicId }: { fieldName: string, topicId: string }) {
  return (
    <button 
      className="text-muted-foreground hover:text-accent opacity-0 group-hover:opacity-100 transition-opacity ml-2"
      title="Report issue with this content"
      onClick={(e) => {
        e.stopPropagation();
        console.log('Flag clicked:', fieldName, topicId);
      }}
    >
      <Flag className="w-4 h-4" />
    </button>
  );
}
