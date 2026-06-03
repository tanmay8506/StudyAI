"use client";

import { useRef, useState, useEffect } from "react";
import { motion, useScroll, AnimatePresence } from "framer-motion";

import { FocusModeProvider, useFocusMode } from "@/components/reading/FocusModeProvider";
import { ScrollEdgeProgress } from "@/components/reading/ScrollEdgeProgress";
import { UnitSidebar } from "@/components/reading/UnitSidebar";
import { StickyTopbar } from "@/components/reading/StickyTopbar";

// Blocks
import { RapidRevisionCard } from "@/components/reading/blocks/RapidRevisionCard";
import { DefinitionBlock } from "@/components/reading/blocks/DefinitionBlock";
import { CoreConceptBlock } from "@/components/reading/blocks/CoreConcept";
import { ExampleBlock } from "@/components/reading/blocks/ExampleBlock";
import { ExaminerNoteBlock } from "@/components/reading/blocks/ExaminerNote";
import { CommonMistakesBlock } from "@/components/reading/blocks/CommonMistakes";
import { AnswerWritingBlock } from "@/components/reading/blocks/AnswerWriting";
import { PYQBlock } from "@/components/reading/blocks/PYQBlock";
import { QuickCheckBlock } from "@/components/reading/blocks/QuickCheck";
import { ConnectsToBlock } from "@/components/reading/blocks/ConnectsTo";
import { MaskReveal } from "@/components/MaskReveal";

// --- MOCK DATA ---
const MOCK_TOPICS = [
  { id: "t1", name: "Eigenvalues & Eigenvectors", studyTime: "45m", priority: "high" as const, isActive: true },
  { id: "t2", name: "Diagonalization", studyTime: "30m", priority: "high" as const },
  { id: "t3", name: "Orthogonal Matrices", studyTime: "25m", priority: "medium" as const },
  { id: "t4", name: "Symmetric Matrices", studyTime: "15m", priority: "low" as const },
];

const MOCK_RAPID = {
  topicName: "Eigenvalues & Eigenvectors",
  priority: "high" as const,
  oneLineDef: "Scalars $\\lambda$ and non-zero vectors $v$ where applying the matrix $A$ just scales the vector: $Av = \\lambda v$.",
  keyFormula: "$$ \\det(A - \\lambda I) = 0 $$",
  examinerPattern: "Almost always tested via 3x3 characteristic equations and finding algebraic multiplicity vs geometric multiplicity."
};

const MOCK_DEF = 'An eigenvector of a square matrix A is a non-zero vector $v$ such that multiplying by A yields a scaled version of $v$. The scalar factor $\\lambda$ is called the eigenvalue.';

const MOCK_CORE = "Understanding eigenvalues is equivalent to finding the 'principal axes' of a linear transformation. Along these specific directions, the transformation acts merely as a stretch or compression, rather than a complex rotation or shear.";
const MOCK_ANALOGY = { text: "Think of a rubber sheet being stretched. Most arrows drawn on it change direction, but the arrows pointing exactly along the directions of the stretch only get longer or shorter.", verified: true };

const MOCK_EXAMPLE = {
  problem: "Find the eigenvalues of $A = \\begin{pmatrix} 4 & 1 \\\\ 3 & 2 \\end{pmatrix}$",
  steps: [
    { number: "01.", text: "Set up the characteristic equation: $\\det(A - \\lambda I) = 0$" },
    { number: "02.", text: "$\\det\\begin{pmatrix} 4-\\lambda & 1 \\\\ 3 & 2-\\lambda \\end{pmatrix} = (4-\\lambda)(2-\\lambda) - 3 = 0$" },
    { number: "03.", text: "$\\lambda^2 - 6\\lambda + 8 - 3 = 0 \\implies \\lambda^2 - 6\\lambda + 5 = 0$" },
    { number: "04.", text: "$(\\lambda - 5)(\\lambda - 1) = 0$" }
  ],
  answer: "$\\lambda_1 = 5, \\lambda_2 = 1$",
  common_error: "Forgetting to subtract $\\lambda$ from the diagonal before taking the determinant.",
  example_type: "Worked Example",
  verified: true,
  verification_mode: "expert"
};

const MOCK_EXAMINER = {
  text: "Students consistently lose marks in 2021 and 2023 papers by not stating that eigenvectors must be non-zero. When asked to 'find' eigenvectors, you must present the general solution span, not just a single specific vector.",
  years: ["2021", "2023"],
  instruction_words: [{ word: "find", count: 3 }]
};

const MOCK_MISTAKES = [
  { mistake: "Assuming that if an eigenvalue is 0, the matrix is invertible.", marks_lost: "-2 marks" },
  { mistake: "Stating the zero vector as an eigenvector.", marks_lost: "-1 mark" }
];

const MOCK_ANSWER = {
  steps: [
    { number: "01.", text: "State the characteristic equation clearly." },
    { number: "02.", text: "Show the expansion of the determinant step-by-step." },
    { number: "03.", text: "Solve for eigenvalues and label algebraic multiplicity." },
    { number: "04.", text: "For each eigenvalue, solve $(A-\\lambda I)v = 0$ for the basis." }
  ],
  distribution: [
    { label: "Char Eq", marks: "+1" },
    { label: "Eigenvalues", marks: "+2" },
    { label: "Eigenvectors", marks: "+3" }
  ]
};

const MOCK_PYQS = [
  {
    id: "q1", year: "2023", isConfirmed: true, marks: 6, recencyWeight: 1.8,
    question: "Determine the eigenvalues and corresponding eigenvectors of the matrix A = [1 2; 2 1]. State whether A is diagonalizable.",
    keySteps: ["Find det(A-λI)=0", "Solve for λ=3, λ=-1", "Substitute λ to find null space"]
  }
];

const MOCK_QUICK = [
  { id: "qc1", rawData: { question: "Why must an eigenvector be non-zero by definition?" } }
];

const MOCK_CONNECT = {
  nextTopicName: "Diagonalization",
  bridgeReason: "Now that we have eigenvalues and eigenvectors, we can construct the matrices P and D such that A = PDP⁻¹.",
  nextTopicId: "t2"
};

// --- SUB-COMPONENT FOR READING COLUMN ---
function ReadingColumn() {
  // Use a ref on the scrollable div for Framer Motion's useScroll
  const scrollRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ container: scrollRef });
  const { isFocusMode } = useFocusMode();
  
  // Topic expansion state
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="flex-1 h-screen flex flex-col relative overflow-hidden bg-bg-base">
      <ScrollEdgeProgress scrollYProgress={scrollYProgress} />
      <StickyTopbar unitName="UNIT 01: LINEAR ALGEBRA" scrollYProgress={scrollYProgress} />
      
      {/* 
        Native scrollable container — no Lenis here.
        overflow-y-auto + scroll-smooth gives buttery scrolling
        without the complexity of Lenis binding issues.
      */}
      <div 
        ref={scrollRef} 
        id="reading-scroll-container"
        className="flex-1 overflow-y-auto overflow-x-hidden"
        style={{ scrollBehavior: "smooth" }}
        data-lenis-prevent="true"
      >
        {/* Main Reading Column Width Constraint */}
        <div className="w-full flex justify-center pb-[80px]">
          {/* The Reading Column max-width is strictly 720px */}
          <div className="w-full max-w-[720px] px-12 transition-all duration-300">
            
            {/* Unit Header */}
            <div className="py-[40px] border-b border-border-subtle flex flex-col gap-4">
              <div className="flex flex-row items-center gap-4">
                <span className="font-sans text-[11px] uppercase tracking-widest text-text-tertiary">
                  B.SC. (H) MATHEMATICS &middot; SEMESTER 3
                </span>
                <div className="w-[24px] h-[1px] bg-border-default" />
              </div>
              
              <MaskReveal 
                text="Eigenvalues & Diagonalization" 
                as="h1"
                variant="standard"
                className="font-serif text-[40px] text-text-primary tracking-tight"
              />

              <p className="font-sans text-[14px] text-text-secondary leading-relaxed max-w-[560px]">
                The study of how linear transformations behave along specific invariant directions, allowing us to decompose complex matrices into simpler, diagonal forms.
              </p>

              <div className="flex flex-row items-center gap-4 mt-2">
                <div className="flex flex-col gap-1">
                  <span className="font-sans text-[10px] uppercase text-text-tertiary">Topics</span>
                  <span className="font-mono text-[14px] text-text-primary">12</span>
                </div>
                <div className="w-[1px] h-[24px] bg-border-default" />
                <div className="flex flex-col gap-1">
                  <span className="font-sans text-[10px] uppercase text-text-tertiary">Study Time</span>
                  <span className="font-mono text-[14px] text-text-primary">4h 30m</span>
                </div>
                <div className="w-[1px] h-[24px] bg-border-default" />
                <div className="flex flex-col gap-1">
                  <span className="font-sans text-[10px] uppercase text-text-tertiary">High Yield</span>
                  <span className="font-mono text-[14px] text-red font-bold">4</span>
                </div>
              </div>
            </div>

            {/* PER-TOPIC SECTION */}
            <section id="topic-t1" className="py-[32px] border-b border-border-subtle">
              <div className="flex flex-row items-center gap-[14px] mb-[22px]">
                <span className="font-mono text-[10px] text-text-tertiary border border-border-default rounded-md px-2 py-0.5">
                  T-01
                </span>
                <div className="flex-1 h-[1px] bg-border-subtle" />
                <span className="font-mono text-[11px] text-text-tertiary">45m</span>
              </div>

              <RapidRevisionCard 
                data={MOCK_RAPID} 
                isExpanded={isExpanded} 
                onToggle={() => setIsExpanded(!isExpanded)} 
              />

              <AnimatePresence initial={false}>
                {isExpanded && (
                  <motion.div
                    key="topic-content"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
                    style={{ overflow: "hidden" }}
                  >
                    {/* Inner wrapper restores overflow for content to be fully visible when open */}
                    <div className="overflow-visible">
                      <DefinitionBlock definitionText={MOCK_DEF} />
                      <CoreConceptBlock content={MOCK_CORE} analogy={MOCK_ANALOGY} />
                      <ExampleBlock exampleData={MOCK_EXAMPLE} />
                      <ExaminerNoteBlock noteData={MOCK_EXAMINER} />
                      <CommonMistakesBlock mistakesData={MOCK_MISTAKES} />
                      <AnswerWritingBlock topicMarks={6} data={MOCK_ANSWER} />
                      <PYQBlock questions={MOCK_PYQS} />
                      <QuickCheckBlock checks={MOCK_QUICK} />
                      <ConnectsToBlock data={MOCK_CONNECT} />
                      
                      {/* UNIT CLOSER */}
                      <div className="mt-[32px] bg-bg-card border border-border-default rounded-xl p-[20px]">
                        <div className="font-sans text-[12px] font-bold uppercase tracking-widest text-text-primary mb-3">
                          Exam-Ready Checklist
                        </div>
                        <div className="h-[1px] bg-border-subtle mb-4" />
                        <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-2">
                            <span className="text-green text-sm">✓</span>
                            <span className="font-sans text-[13px] text-text-secondary">Can define eigenvector and eigenvalue mathematically.</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-green text-sm">✓</span>
                            <span className="font-sans text-[13px] text-text-secondary">Can solve the characteristic equation for a 3x3 matrix.</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

            </section>

          </div>
        </div>
      </div>

      {/* Grain Overlay */}
      <div 
        className="pointer-events-none fixed inset-0 z-[100] transition-opacity duration-300"
        style={{
          backgroundImage: "url('/grain.png')",
          opacity: isFocusMode ? 0.06 : 0.035
        }}
      />
    </div>
  );
}

// --- MAIN PAGE EXPORT ---
export default function ReadingPage() {
  useEffect(() => {
    document.title = "StudyAI · LINEAR ALGEBRA II";
  }, []);

  return (
    <FocusModeProvider>
      <div className="flex flex-row h-screen w-full overflow-hidden bg-bg-base relative">
        <UnitSidebar paperName="LINEAR ALGEBRA II" tier={1} topics={MOCK_TOPICS} />
        <ReadingColumn />
      </div>
    </FocusModeProvider>
  );
}
