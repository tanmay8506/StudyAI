import React, { useRef } from 'react';
import html2canvas from 'html2canvas';
import { Camera, Beaker } from 'lucide-react';
import { renderMath } from '@/lib/katex';
import { FormulaSheet as DBFormulaSheet } from '@/types/database';

export interface FormulaItem {
  item: string;
  application_condition: string;
  marks_value?: string;
}

export interface FormulaSheetProps {
  sheet: DBFormulaSheet | null;
  unitName: string;
}

export function FormulaSheet({ sheet, unitName }: FormulaSheetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  if (!sheet || sheet.sheet_type !== 'formula' || !sheet.content) return null;

  const items = sheet.content as FormulaItem[];
  if (!Array.isArray(items) || items.length === 0) return null;

  const handleCapture = async () => {
    if (!containerRef.current) return;
    try {
      const canvas = await html2canvas(containerRef.current, { backgroundColor: '#ffffff' });
      const dataUrl = canvas.toDataURL('image/png');
      const a = document.createElement('a');
      a.href = dataUrl;
      a.download = `StudyAI_${unitName.replace(/\s+/g, '_')}_FormulaSheet.png`;
      a.click();
    } catch (e) {
      console.error('Screenshot failed', e);
    }
  };

  return (
    <div className="mt-8 mb-4 border border-border rounded-lg bg-card overflow-hidden">
      <div className="flex justify-between items-center p-4 bg-muted/30 border-b border-border/50">
        <div className="flex items-center gap-2 text-foreground/80">
          <Beaker className="w-5 h-5 text-accent" />
          <h3 className="font-bold tracking-wider uppercase text-sm">Formula and Theorem Sheet</h3>
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
          <p className="text-center text-sm text-zinc-500 mt-1 uppercase tracking-widest">Formula Sheet</p>
        </div>

        <div className="space-y-6">
          {items.map((item, idx) => (
            <div key={idx} className="relative break-inside-avoid">
              <div 
                className="text-lg font-medium text-center py-4 bg-zinc-50 dark:bg-zinc-900 rounded-md border border-zinc-100 dark:border-zinc-800 overflow-x-auto"
                dangerouslySetInnerHTML={{ __html: renderMath(item.item) }}
              />
              <div className="mt-2 text-sm text-zinc-600 dark:text-zinc-400 italic text-center">
                Condition: <span dangerouslySetInnerHTML={{ __html: renderMath(item.application_condition) }} />
              </div>
              {item.marks_value && (
                <div className="absolute top-2 right-2 text-[10px] uppercase font-bold bg-zinc-200 dark:bg-zinc-700 px-1.5 py-0.5 rounded text-zinc-700 dark:text-zinc-300">
                  {item.marks_value}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
