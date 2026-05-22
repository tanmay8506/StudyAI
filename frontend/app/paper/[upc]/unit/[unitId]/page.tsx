"use client";

import React, { useEffect, useState } from 'react';
import { getUnitsForPaper, getTopicsForUnit, getFormulaSheetsForUnit, getProblemSetForUnit } from '@/lib/queries';
import { Unit, Topic, FormulaSheet as DBFormulaSheet, ProblemSet as DBProblemSet } from '@/types/database';
import { Loader2, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

// Note components
import { RapidRevisionCard } from '@/components/notes/RapidRevisionCard';
import { DefinitionBlock } from '@/components/notes/DefinitionBlock';
import { CoreConceptBlock } from '@/components/notes/CoreConceptBlock';
import { ExampleBlock } from '@/components/notes/ExampleBlock';
import { DiagramBlock } from '@/components/notes/DiagramBlock';
import { ExaminersNoteBlock } from '@/components/notes/ExaminersNoteBlock';
import { CommonMistakesBlock } from '@/components/notes/CommonMistakesBlock';
import { AnswerWritingTechniqueBlock } from '@/components/notes/AnswerWritingTechniqueBlock';
import { PYQBlock } from '@/components/notes/PYQBlock';
import { QuickChecksBlock } from '@/components/notes/QuickChecksBlock';
import { ConnectsToBlock } from '@/components/notes/ConnectsToBlock';
import { FormulaSheet } from '@/components/notes/FormulaSheet';
import { DiagramReferenceSheet } from '@/components/notes/DiagramReferenceSheet';
import { KeyTermsSheet } from '@/components/notes/KeyTermsSheet';
import { ProblemSet } from '@/components/notes/ProblemSet';

export default function UnitPage({ params }: { params: { upc: string, unitId: string } }) {
  const [upc, setUpc] = useState<string | null>(null);
  const [unitId, setUnitId] = useState<string | null>(null);
  const [expandedTopicId, setExpandedTopicId] = useState<string | null>(null);
  
  useEffect(() => {
    Promise.resolve(params).then(p => {
      setUpc(p.upc);
      setUnitId(p.unitId);
    });
  }, [params]);

  const [unit, setUnit] = useState<Unit | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [formulaSheets, setFormulaSheets] = useState<DBFormulaSheet[]>([]);
  const [problemSet, setProblemSet] = useState<DBProblemSet | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!upc || !unitId) return;
    
    async function fetchData() {
      try {
        const units = await getUnitsForPaper(upc!);
        const currentUnit = units.find(u => u.unit_id === unitId);
        if (currentUnit) setUnit(currentUnit);
        
        const fetchedTopics = await getTopicsForUnit(unitId!);
        setTopics(fetchedTopics);

        const fetchedSheets = await getFormulaSheetsForUnit(unitId!);
        setFormulaSheets(fetchedSheets);

        const fetchedProblemSet = await getProblemSetForUnit(unitId!);
        setProblemSet(fetchedProblemSet);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [upc, unitId]);

  if (loading || !upc || !unitId) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-accent animate-spin" />
      </div>
    );
  }

  if (!unit) {
    return (
      <div className="min-h-screen flex items-center justify-center flex-col gap-4">
        <h1 className="text-2xl font-bold">Unit Not Found</h1>
        <Link href={`/paper/${upc}`} className="text-accent hover:underline">Go back to paper</Link>
      </div>
    );
  }

  return (
    <main className="max-w-3xl mx-auto p-4 md:p-8 min-h-screen pb-24">
      <Link 
        href={`/paper/${upc}`}
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-8"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Paper Overview
      </Link>

      <header className="mb-12">
        <div className="text-accent font-semibold tracking-wider uppercase text-sm mb-2">
          Unit {unit.unit_number}
        </div>
        <h1 className="text-4xl font-serif font-bold mb-6 text-foreground">{unit.unit_name}</h1>
        {unit.conceptual_summary && (
          <div className="text-lg text-muted-foreground leading-relaxed italic border-l-4 border-muted pl-4">
            {unit.conceptual_summary}
          </div>
        )}
      </header>

      {/* Render Topics */}
      <div className="space-y-16">
        {topics.map(topic => {
          const c = topic as any;
          if (!c) return null;
          
          return (
            <section key={topic.topic_id} className="scroll-mt-10">
              <h2 className="text-2xl font-bold border-b border-border pb-2 mb-6 text-foreground">
                {topic.topic_number}. {topic.topic_name}
              </h2>

              <div className="space-y-6">
                {/* 1. Rapid Revision */}
                {c.rapid_revision && (
                  <RapidRevisionCard 
                    rapid_revision={c.rapid_revision} 
                    topic_name={topic.topic_name}
                    topicId={topic.topic_id} 
                    priority={c.priority || 'medium'}
                    isExpanded={expandedTopicId === topic.topic_id}
                    onToggle={() => setExpandedTopicId(expandedTopicId === topic.topic_id ? null : topic.topic_id)}
                  />
                )}

                {/* 2. Definition */}
                {c.definition && (
                  <DefinitionBlock 
                    definition={c.definition} 
                    topic_name={topic.topic_name}
                    topicId={topic.topic_id} 
                  />
                )}

                {/* 3. Core Concept */}
                {c.core_concept && (
                  <CoreConceptBlock 
                    core_concept={c.core_concept} 
                    analogy={c.analogy}
                    analogy_verified={c.analogy_verified || false}
                    topicId={topic.topic_id} 
                  />
                )}

                {/* 4. Examples */}
                {c.examples && c.examples.length > 0 && (
                  <ExampleBlock 
                    examples={c.examples} 
                    paper_type="mixed"
                    topicId={topic.topic_id} 
                  />
                )}

                {/* 5. Diagram */}
                {c.diagram_block && (
                  <DiagramBlock 
                    diagram_block={c.diagram_block} 
                    topicId={topic.topic_id} 
                  />
                )}

                {/* 6. Examiner's Notes */}
                {c.examiners_note && (
                  <ExaminersNoteBlock 
                    examiners_note={c.examiners_note} 
                    examiners_note_pyq_refs={c.examiners_note_pyq_refs}
                    instruction_word_frequency={c.instruction_word_frequency}
                    topicId={topic.topic_id} 
                  />
                )}

                {/* 7. Common Mistakes */}
                {c.common_mistakes && c.common_mistakes.length > 0 && (
                  <CommonMistakesBlock 
                    common_mistakes={c.common_mistakes} 
                    topicId={topic.topic_id} 
                  />
                )}

                {/* 8. Answer Writing Techniques */}
                {c.answer_writing_technique && (
                  <AnswerWritingTechniqueBlock 
                    answer_writing_technique={c.answer_writing_technique} 
                    topicId={topic.topic_id} 
                  />
                )}

                {/* 9. PYQs */}
                {c.pyqs && c.pyqs.length > 0 && (
                  <PYQBlock 
                    pyqs={c.pyqs} 
                    topicId={topic.topic_id} 
                  />
                )}

                {/* 10. Quick Checks */}
                {c.quick_checks && c.quick_checks.length > 0 && (
                  <QuickChecksBlock 
                    quick_checks={c.quick_checks} 
                    topicId={topic.topic_id} 
                  />
                )}

                {/* 11. Connects To */}
                {c.connects_to && (
                  <div className="mt-8">
                    <ConnectsToBlock 
                      connects_to_topic_id={c.connects_to.topic_id}
                      connects_to_reason={c.connects_to.reason}
                      connects_to_unit_id={c.connects_to.unit_id}
                      topicName={c.connects_to.topic_name}
                      upc={upc}
                    />
                  </div>
                )}
              </div>
            </section>
          );
        })}
      </div>

      {/* Render Formula Sheets / Diagram References / Key Terms */}
      {formulaSheets.length > 0 && (
        <div className="mt-16 space-y-8">
          <h2 className="text-2xl font-bold font-serif border-b border-border pb-2 text-foreground">Unit Resources</h2>
          {formulaSheets.map((sheet, i) => {
            if (sheet.sheet_type === 'formula') {
              return <FormulaSheet key={`fs-${i}`} sheet={sheet} unitName={unit.unit_name} />;
            }
            if (sheet.sheet_type === 'diagram_reference') {
              return <DiagramReferenceSheet key={`fs-${i}`} sheet={sheet} unitName={unit.unit_name} />;
            }
            if (sheet.sheet_type === 'key_terms') {
              return <KeyTermsSheet key={`fs-${i}`} sheet={sheet} unitName={unit.unit_name} />;
            }
            return null;
          })}
        </div>
      )}

      {/* Render Problem Set */}
      {problemSet && (
        <div className="mt-16">
          <ProblemSet problemSet={problemSet} unitName={unit.unit_name} />
        </div>
      )}
    </main>
  );
}
