import React from 'react';
import { CheckCircle2, XCircle, Loader2, Circle } from 'lucide-react';

export interface AgentStatusCardProps {
  agentNumber: number;
  agentName: string;
  status: 'queued' | 'running' | 'complete' | 'failed';
  model?: string;
}

export function AgentStatusCard({ agentNumber, agentName, status, model }: AgentStatusCardProps) {
  const statusConfig = {
    queued: { icon: Circle, color: 'text-muted-foreground opacity-50', bg: 'bg-muted/30' },
    running: { icon: Loader2, color: 'text-accent animate-spin', bg: 'bg-accent/10 border-accent/30' },
    complete: { icon: CheckCircle2, color: 'text-success', bg: 'bg-success/10 border-success/30' },
    failed: { icon: XCircle, color: 'text-destructive', bg: 'bg-destructive/10 border-destructive/30' }
  };
  
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div className={`p-3 rounded-lg border flex items-center gap-3 transition-colors ${config.bg}`}>
      <div className="shrink-0">
        <Icon className={`w-5 h-5 ${config.color}`} />
      </div>
      <div>
        <h4 className="text-sm font-semibold text-foreground/90">
          Agent {agentNumber} — {agentName}
        </h4>
        {model && (
          <p className="text-xs text-muted-foreground">
            {model}
          </p>
        )}
      </div>
    </div>
  );
}
