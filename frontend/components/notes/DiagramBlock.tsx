import React, { useRef, useState } from 'react';
import html2canvas from 'html2canvas';
import { Camera, ChevronDown, ChevronUp } from 'lucide-react';
import { FieldFlagButton } from '../ui/FieldFlagButton';
import { renderMath } from '@/lib/katex';

export interface DiagramBlockData {
  diagram_name: string;
  svg_source?: string;
  svg_file_path?: string;
  svg_code?: string;
  labeled_parts?: Array<{
    part_name: string;
    explanation: string;
    du_expected_label: string;
  }>;
  marks_value?: string;
  draw_instructions?: string;
  source_book?: string;
  source_edition?: string;
  source_page?: string;
}

export interface DiagramBlockProps {
  diagram_block: DiagramBlockData | null;
  topicId: string;
}

export function DiagramBlock({ diagram_block, topicId }: DiagramBlockProps) {
  const [instructionsOpen, setInstructionsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  if (!diagram_block) return null;

  const handleCapture = async () => {
    if (!containerRef.current) return;
    try {
      const canvas = await html2canvas(containerRef.current, { backgroundColor: '#ffffff' });
      const dataUrl = canvas.toDataURL('image/png');
      const a = document.createElement('a');
      a.href = dataUrl;
      a.download = `StudyAI_Diagram_${diagram_block.diagram_name.replace(/\s+/g, '_')}.png`;
      a.click();
    } catch (e) {
      console.error('Screenshot failed', e);
    }
  };

  return (
    <div className="relative p-5 mt-6 border border-border rounded-lg group" ref={containerRef}>
      <div className="flex justify-between items-start mb-4">
        <h4 className="text-sm font-semibold text-foreground/80 uppercase tracking-wider">
          Diagram
        </h4>
        <div className="flex items-center gap-2">
          {diagram_block.marks_value && (
            <span className="text-xs px-2 py-1 bg-accent/10 text-accent rounded-full font-medium">
              ~{diagram_block.marks_value} marks
            </span>
          )}
          <button 
            onClick={handleCapture}
            className="text-muted-foreground hover:text-foreground transition-colors"
            title="Save Diagram as PNG"
          >
            <Camera className="w-4 h-4" />
          </button>
          <FieldFlagButton fieldName="diagram_block" topicId={topicId} />
        </div>
      </div>

      <div className="mb-4 bg-white rounded-md flex justify-center items-center overflow-hidden min-h-[150px]">
        {diagram_block.svg_code ? (
          <div dangerouslySetInnerHTML={{ __html: diagram_block.svg_code }} />
        ) : diagram_block.svg_file_path ? (
          <img src={diagram_block.svg_file_path} alt={diagram_block.diagram_name} className="max-w-full h-auto" />
        ) : (
          <div className="text-muted-foreground italic text-sm">
            Placeholder for: {diagram_block.diagram_name}
          </div>
        )}
      </div>

      {diagram_block.labeled_parts && diagram_block.labeled_parts.length > 0 && (
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          {diagram_block.labeled_parts.map((part, idx) => (
            <div key={idx} className="text-sm">
              <div className="font-semibold text-foreground">{idx + 1}. {part.part_name}</div>
              <div className="text-muted-foreground mt-1" dangerouslySetInnerHTML={{ __html: renderMath(part.explanation) }} />
              <div className="text-accent mt-1 text-xs font-mono bg-accent/5 inline-block px-1 rounded">
                DU label: {part.du_expected_label}
              </div>
            </div>
          ))}
        </div>
      )}

      {diagram_block.draw_instructions && (
        <div className="mt-4 border border-border rounded-md overflow-hidden">
          <button 
            className="w-full flex justify-between items-center p-3 bg-muted/30 text-sm font-medium hover:bg-muted/50 transition-colors"
            onClick={() => setInstructionsOpen(!instructionsOpen)}
          >
            <span>How to draw in exam</span>
            {instructionsOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          {instructionsOpen && (
            <div 
              className="p-3 text-sm text-foreground/90 bg-card"
              dangerouslySetInnerHTML={{ __html: renderMath(diagram_block.draw_instructions) }}
            />
          )}
        </div>
      )}

      {(diagram_block.source_book || diagram_block.source_edition || diagram_block.source_page) && (
        <div className="mt-4 text-xs text-muted-foreground italic text-right">
          Source: {[diagram_block.source_book, diagram_block.source_edition, diagram_block.source_page ? `p.${diagram_block.source_page}` : null].filter(Boolean).join(', ')}
        </div>
      )}
    </div>
  );
}
