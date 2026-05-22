import React, { useRef } from 'react';
import { Camera } from 'lucide-react';

export interface PYQSubmissionBannerProps {
  upc: string;
  paperName: string;
  tier: 3 | 4;
}

export function PYQSubmissionBanner({ upc, paperName, tier }: PYQSubmissionBannerProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleCapture = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      console.log('File captured for', upc, file);
      // Logic to submit file to backend would go here
    }
  };

  return (
    <div className="bg-card border border-border/60 rounded-xl p-5 my-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-sm">
      <div>
        <h3 className="font-semibold text-foreground mb-1">Help improve {paperName}</h3>
        <p className="text-sm text-muted-foreground">
          No NEP question papers are publicly available for this paper yet.
        </p>
      </div>
      
      <div className="shrink-0">
        <input 
          type="file" 
          accept="image/*" 
          capture="environment"
          className="hidden" 
          ref={fileInputRef}
          onChange={handleCapture}
        />
        <button 
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-2 px-4 py-2 bg-foreground text-background font-medium rounded-lg hover:bg-foreground/90 transition-colors text-sm"
        >
          <Camera className="w-4 h-4" />
          <span>I have this question paper</span>
        </button>
      </div>
    </div>
  );
}
