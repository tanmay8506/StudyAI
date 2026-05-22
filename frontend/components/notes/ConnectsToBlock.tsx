import React from 'react';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

export interface ConnectsToBlockProps {
  connects_to_topic_id: string | null;
  connects_to_reason: string | null;
  connects_to_unit_id: string | null;
  topicName?: string;
  upc: string;
}

export function ConnectsToBlock({ connects_to_topic_id, connects_to_reason, connects_to_unit_id, topicName, upc }: ConnectsToBlockProps) {
  if (!connects_to_topic_id || !connects_to_unit_id) return null;

  const url = `/paper/${upc}/unit/${connects_to_unit_id}#topic-${connects_to_topic_id}`;

  return (
    <Link href={url} className="block mt-6 group outline-none">
      <div className="p-4 bg-muted/30 border border-border/50 rounded-lg flex items-start gap-3 hover:bg-muted/50 hover:border-accent/30 transition-colors cursor-pointer">
        <ArrowRight className="w-5 h-5 text-muted-foreground group-hover:text-accent shrink-0 mt-0.5 transition-colors" />
        <div>
          <div className="text-sm font-semibold text-foreground/90 mb-1 group-hover:text-accent transition-colors">
            {topicName || "Next Topic"}
          </div>
          {connects_to_reason && (
            <div className="text-xs text-muted-foreground group-hover:text-foreground/80 transition-colors">
              {connects_to_reason}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
