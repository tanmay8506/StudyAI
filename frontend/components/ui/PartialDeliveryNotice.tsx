import React from 'react';
import { AlertCircle, Loader2, RefreshCw } from 'lucide-react';

export interface PartialDeliveryNoticeProps {
  unitName: string;
  status: 'failed' | 'generating';
  retryAvailable: boolean;
}

export function PartialDeliveryNotice({ unitName, status, retryAvailable }: PartialDeliveryNoticeProps) {
  return (
    <div className={`p-6 rounded-xl border ${status === 'failed' ? 'bg-muted/30 border-border/50' : 'bg-background border-dashed border-border'}`}>
      <div className="flex flex-col items-center text-center max-w-md mx-auto">
        {status === 'generating' ? (
          <>
            <Loader2 className="w-8 h-8 text-accent animate-spin mb-3" />
            <h3 className="font-semibold text-foreground mb-1">{unitName} is generating</h3>
            <p className="text-sm text-muted-foreground">
              This unit is still generating. Check back shortly. The page will update automatically.
            </p>
          </>
        ) : (
          <>
            <AlertCircle className="w-8 h-8 text-muted-foreground mb-3 opacity-50" />
            <h3 className="font-semibold text-foreground mb-1">{unitName} unavailable</h3>
            <p className="text-sm text-muted-foreground mb-4">
              This unit could not be generated and has been flagged for manual review. All other completed units remain accessible.
            </p>
            {retryAvailable && (
              <button className="flex items-center gap-2 px-3 py-1.5 border border-border rounded-md text-sm hover:bg-muted transition-colors">
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry Generation</span>
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
