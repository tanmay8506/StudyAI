"use client";

import { useParams } from "next/navigation";
import { useEffect } from "react";
import { PageTransition } from "@/components/PageTransition";
import { AmbientLight } from "@/components/AmbientLight";
import { GrainOverlay } from "@/components/GrainOverlay";

import { PaperHeader } from "@/components/overview/PaperHeader";
import { UnitCard, UnitCardData } from "@/components/overview/UnitCard";

// Mock Data for the Paper Overview
const MOCK_PAPER_DATA = {
  upc: "2352203601",
  title: "Riemann Integration & Series of Functions",
  tier: 1 as const,
  department: "Mathematics",
  programme: "B.Sc. (Hons)",
  semester: "Semester 3",
  type: "Core",
  pyqYears: ["2023", "2022", "2021", "2019"]
};

const MOCK_UNITS: UnitCardData[] = [
  {
    id: "U-01",
    name: "Riemann Integration",
    summary: "Darboux sums, integrability conditions, and the fundamental theorem.",
    studyTime: "4h 15m",
    marks: "18 Marks",
    priorityDots: ["red", "red", "amber", "gray", "none"],
    completedTopics: 5,
    totalTopics: 5,
    status: "Complete"
  },
  {
    id: "U-02",
    name: "Improper Integrals",
    summary: "Convergence tests, Beta and Gamma functions.",
    studyTime: "3h 45m",
    marks: "15 Marks",
    priorityDots: ["amber", "amber", "gray", "none"],
    completedTopics: 2,
    totalTopics: 4,
    status: "Generating"
  },
  {
    id: "U-03",
    name: "Sequence of Functions",
    summary: "Pointwise and uniform convergence, Weierstrass M-test.",
    studyTime: "5h 30m",
    marks: "22 Marks",
    priorityDots: ["red", "amber", "amber", "amber", "gray", "gray"],
    completedTopics: 0,
    totalTopics: 6,
    status: "Queued"
  },
  {
    id: "U-04",
    name: "Power Series",
    summary: "Radius of convergence, differentiation and integration of power series.",
    studyTime: "4h 00m",
    marks: "20 Marks",
    priorityDots: ["red", "red", "gray"],
    completedTopics: 0,
    totalTopics: 3,
    status: "Failed"
  }
];

export default function PaperOverviewPage() {
  const params = useParams();
  const upc = (params.upc as string) || MOCK_PAPER_DATA.upc;
  
  useEffect(() => {
    document.title = `StudyAI · ${MOCK_PAPER_DATA.title}`;
  }, []);

  return (
    <PageTransition>
      <main className="min-h-screen w-full bg-bg-base text-text-primary flex flex-col items-center pb-24 overflow-x-hidden relative">
        
        {/* Global Infrastucture */}
        <GrainOverlay />
        <AmbientLight variant="overview" />

        <div className="w-full max-w-[900px] px-6 md:px-8 mt-24 relative z-10 flex flex-col gap-16">
          
          <PaperHeader 
            upc={upc}
            title={MOCK_PAPER_DATA.title}
            tier={MOCK_PAPER_DATA.tier}
            department={MOCK_PAPER_DATA.department}
            programme={MOCK_PAPER_DATA.programme}
            semester={MOCK_PAPER_DATA.semester}
            type={MOCK_PAPER_DATA.type}
            pyqYears={MOCK_PAPER_DATA.pyqYears}
          />

          <section>
            <div className="flex items-center gap-3 mb-6">
              <h2 className="font-sans text-[18px] font-bold text-text-primary">
                Units
              </h2>
              <div className="font-mono text-[10px] bg-bg-card border border-border-default rounded-full px-2 py-0.5 text-text-secondary">
                {MOCK_UNITS.length}
              </div>
            </div>

            <div className="flex flex-col gap-3">
              {MOCK_UNITS.map((unit, index) => (
                <UnitCard 
                  key={unit.id} 
                  unit={unit} 
                  index={index} 
                />
              ))}
            </div>
          </section>

        </div>
      </main>
    </PageTransition>
  );
}
