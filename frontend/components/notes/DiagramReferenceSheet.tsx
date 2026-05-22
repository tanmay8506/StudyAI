import React, { useRef } from 'react';
import html2canvas from 'html2canvas';
import { Camera, Image as ImageIcon } from 'lucide-react';
import { renderMath } from '@/lib/katex';
import { FormulaSheet as DBFormulaSheet } from '@/types/database';

export interface DiagramReferenceItem {
  diagram_name: string;
  labeled_parts_summary: string;
  marks_value?: string;
}

export interface DiagramReferenceSheetProps {
  sheet: DBFormulaSheet | null;
  unitName: string;
}

export function DiagramReferenceSheet({ sheet, unitName }: DiagramReferenceSheetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  if (!sheet || sheet.sheet_type !== 'diagram_reference' || !sheet.content) return null;

  const items = sheet.content as DiagramReferenceItem[];
  if (!Array.isArray(items) || items.length === 0) return null;

  const handleCapture = async () => {
    if (!containerRef.current) return;
    try {
      const canvas = await html2canvas(containerRef.current, { backgroundColor: '#ffffff' });
      const dataUrl = canvas.toDataURL('image/png');
      const a = document.createElement('a');
      a.href = dataUrl;
      a.download = `StudyAI_${unitName.replace(/\s+/g, '_')}_Diagrams.png`;
      a.click();
    } catch (e) {
      console.error('Screenshot failed', e);
    }
  };

  return (
    <div className="mt-8 mb-4 border border-border rounded-lg bg-card overflow-hidden">
      <div className="flex justify-between items-center p-4 bg-muted/30 border-b border-border/50">
        <div className="flex items-center gap-2 text-foreground/80">
          <ImageIcon className="w-5 h-5 text-accent" />
          <h3 className="font-bold tracking-wider uppercase text-sm">Diagram Reference Sheet</h3>
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
          <p className="text-center text-sm text-zinc-500 mt-1 uppercase tracking-widest">Diagram Reference Sheet</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {items.map((item, idx) => (
            <div key={idx} className="break-inside-avoid border border-zinc-200 dark:border-zinc-800 rounded-md p-4 bg-zinc-50 dark:bg-zinc-900/50 relative">
              <div className="flex justify-between items-start mb-2 pr-10">
                <h4 className="font-bold text-base" dangerouslySetInnerHTML={{ __html: renderMath(item.diagram_name) }} />
              </div>
              {item.marks_value && (
                <div className="absolute top-4 right-4 text-[10px] uppercase font-bold bg-zinc-200 dark:bg-zinc-700 px-1.5 py-0.5 rounded text-zinc-700 dark:text-zinc-300">
                  {item.marks_value}
                </div>
              )}
              <div className="text-sm text-zinc-600 dark:text-zinc-400 mt-2">
                <strong className="text-zinc-700 dark:text-zinc-300 block mb-1">Key Labels:</strong>
                <div dangerouslySetInnerHTML={{ __html: renderMath(item.labeled_parts_summary) }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
