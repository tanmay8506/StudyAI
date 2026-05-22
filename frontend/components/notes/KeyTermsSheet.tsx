import React, { useRef } from 'react';
import html2canvas from 'html2canvas';
import { Camera, Book } from 'lucide-react';
import { renderMath } from '@/lib/katex';
import { FormulaSheet as DBFormulaSheet } from '@/types/database';

export interface KeyTermItem {
  term: string;
  summary: string;
}

export interface KeyTermsSheetProps {
  sheet: DBFormulaSheet | null;
  unitName: string;
}

export function KeyTermsSheet({ sheet, unitName }: KeyTermsSheetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  if (!sheet || sheet.sheet_type !== 'key_terms' || !sheet.content) return null;

  const items = sheet.content as KeyTermItem[];
  if (!Array.isArray(items) || items.length === 0) return null;

  const handleCapture = async () => {
    if (!containerRef.current) return;
    try {
      const canvas = await html2canvas(containerRef.current, { backgroundColor: '#ffffff' });
      const dataUrl = canvas.toDataURL('image/png');
      const a = document.createElement('a');
      a.href = dataUrl;
      a.download = `StudyAI_${unitName.replace(/\s+/g, '_')}_KeyTerms.png`;
      a.click();
    } catch (e) {
      console.error('Screenshot failed', e);
    }
  };

  return (
    <div className="mt-8 mb-4 border border-border rounded-lg bg-card overflow-hidden">
      <div className="flex justify-between items-center p-4 bg-muted/30 border-b border-border/50">
        <div className="flex items-center gap-2 text-foreground/80">
          <Book className="w-5 h-5 text-accent" />
          <h3 className="font-bold tracking-wider uppercase text-sm">Key Terms and Concepts</h3>
        </div>
        <button 
          onClick={handleCapture}
          className="p-2 bg-accent text-accent-foreground rounded-md shadow hover:bg-accent/90 transition-colors flex items-center gap-2 text-xs font-medium"
        >
          <Camera className="w-4 h-4" />
          <span>Save PNG</span>
        </button>
      </div>

      <div ref={containerRef} className="p-6 bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100">
        <div className="mb-6 pb-2 border-b-2 border-zinc-200 dark:border-zinc-800">
          <h2 className="text-xl font-bold font-serif text-center">StudyAI — {unitName}</h2>
          <p className="text-center text-sm text-zinc-500 mt-1 uppercase tracking-widest">Key Terms Reference</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {items.map((item, idx) => (
            <div key={idx} className="break-inside-avoid">
              <div className="font-bold text-sm mb-1" dangerouslySetInnerHTML={{ __html: renderMath(item.term) }} />
              <div className="text-xs text-zinc-600 dark:text-zinc-400" dangerouslySetInnerHTML={{ __html: renderMath(item.summary) }} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
