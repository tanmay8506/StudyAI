"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { PageTransition } from "@/components/PageTransition";
import { AmbientLight } from "@/components/AmbientLight";
import { GrainOverlay } from "@/components/GrainOverlay";
import { PaperHeader } from "@/components/overview/PaperHeader";
import { UnitCard, UnitCardData } from "@/components/overview/UnitCard";
import { USE_MOCK } from "@/lib/mock-flag";
import { getPaper, getUnitsForPaper } from "@/lib/queries";

// ─── Mock Data (shown when NEXT_PUBLIC_USE_MOCK=true) ──────────────────────
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

// ─── Real-Mode Types ────────────────────────────────────────────────────────
interface RealPaperData {
  upc: string;
  title: string;
  tier: 1 | 2 | 3 | 4;
  department: string;
  programme: string;
  semester: string;
  type: string;
  pyqYears: string[];
}

export default function PaperOverviewPage() {
  const params = useParams();
  const upc = (params.upc as string) || MOCK_PAPER_DATA.upc;

  // ── Real-mode state ──
  const [realPaper, setRealPaper] = useState<RealPaperData | null>(null);
  const [realUnits, setRealUnits] = useState<UnitCardData[]>([]);
  const [isLoading, setIsLoading] = useState(!USE_MOCK);

  useEffect(() => {
    document.title = `StudyAI · ${USE_MOCK ? MOCK_PAPER_DATA.title : upc}`;
  }, [upc]);

  // Fetch real data when not in mock mode
  useEffect(() => {
    if (USE_MOCK) return;

    async function fetchData() {
      setIsLoading(true);
      try {
        const [paper, units] = await Promise.all([
          getPaper(upc),
          getUnitsForPaper(upc)
        ]);

        if (paper) {
          setRealPaper({
            upc: paper.upc,
            title: paper.paper_name ?? upc,
            tier: ((paper.tier ?? 2) as 1 | 2 | 3 | 4),
            department: paper.department ?? "",
            programme: paper.programme ?? "",
            semester: `Semester ${paper.semester ?? ""}`,
            type: paper.paper_type ?? "theory",
            pyqYears: (paper.pyq_years_available ?? []).map(String),
          });
        }

        if (units.length > 0) {
          setRealUnits(
            units.map((u, i) => ({
              id: u.id,
              name: u.unit_name,
              summary: "",
              studyTime: u.estimated_study_hours ? `${u.estimated_study_hours}h` : "—",
              marks: u.marks_weightage ? `${u.marks_weightage} Marks` : "—",
              priorityDots: [],
              completedTopics: 0,
              totalTopics: 0,
              status: u.status === "complete" ? "Complete"
                : u.status === "generating" ? "Generating"
                : u.status === "failed" ? "Failed"
                : "Queued",
            }))
          );
        }
      } catch (err) {
        console.error("[PaperOverviewPage] failed to fetch real data:", err);
      } finally {
        setIsLoading(false);
      }
    }

    fetchData();
  }, [upc]);

  // Determine what to render
  const displayPaper = USE_MOCK ? MOCK_PAPER_DATA : (realPaper ?? MOCK_PAPER_DATA);
  const displayUnits = USE_MOCK ? MOCK_UNITS : (realUnits.length > 0 ? realUnits : MOCK_UNITS);

  return (
    <PageTransition>
      <main className="min-h-screen w-full bg-bg-base text-text-primary flex flex-col items-center pb-24 overflow-x-hidden relative">

        {/* Global Infrastructure */}
        <GrainOverlay />
        <AmbientLight variant="overview" />

        <div className="w-full max-w-[900px] px-6 md:px-8 mt-24 relative z-10 flex flex-col gap-16">

          {isLoading ? (
            <div className="flex items-center justify-center h-40">
              <span className="font-mono text-[12px] text-text-tertiary animate-pulse">
                Loading paper…
              </span>
            </div>
          ) : (
            <>
              <PaperHeader
                upc={upc}
                title={displayPaper.title}
                tier={displayPaper.tier}
                department={displayPaper.department}
                programme={displayPaper.programme}
                semester={displayPaper.semester}
                type={displayPaper.type}
                pyqYears={displayPaper.pyqYears}
              />

              <section>
                <div className="flex items-center gap-3 mb-6">
                  <h2 className="font-sans text-[18px] font-bold text-text-primary">
                    Units
                  </h2>
                  <div className="font-mono text-[10px] bg-bg-card border border-border-default rounded-full px-2 py-0.5 text-text-secondary">
                    {displayUnits.length}
                  </div>
                </div>

                <div className="flex flex-col gap-3">
                  {displayUnits.map((unit, index) => (
                    <UnitCard
                      key={unit.id}
                      unit={unit}
                      index={index}
                    />
                  ))}
                </div>
              </section>
            </>
          )}

        </div>
      </main>
    </PageTransition>
  );
}
