"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { PageTransition } from "@/components/PageTransition";
import { AmbientLight } from "@/components/AmbientLight";
import { GrainOverlay } from "@/components/GrainOverlay";

import { PipelineProgress } from "@/components/PipelineProgress";
import { AgentGrid, AgentData } from "@/components/AgentGrid";
import { UnitTracker, UnitProgressData } from "@/components/UnitTracker";
import { USE_MOCK } from "@/lib/mock-flag";
import { getUnitsForPaper } from "@/lib/queries";
import { subscribeToUnitStatus } from "@/lib/queries";

const INITIAL_AGENTS: AgentData[] = [
  { id: "A-01", name: "Syllabus Map", model: "o1-mini", state: "queued" },
  { id: "A-02", name: "Researcher", model: "claude-3-5-sonnet", state: "queued" },
  { id: "A-03", name: "Paper DNA", model: "gpt-4o", state: "queued" },
  { id: "A-04", name: "Mental Mapper", model: "claude-3-5-sonnet", state: "queued" },
  { id: "A-05", name: "Writer", model: "claude-3-5-sonnet", state: "queued" },
  { id: "A-06", name: "Coverage", model: "o1-mini", state: "queued" },
  { id: "A-07", name: "Verifier", model: "claude-3-5-sonnet", state: "queued" },
  { id: "A-08", name: "Critic", model: "gpt-4o", state: "queued" },
  { id: "A-09", name: "Rewriter", model: "claude-3-5-sonnet", state: "queued" },
  { id: "A-10", name: "Final Examiner", model: "o1-mini", state: "queued" },
  { id: "A-11", name: "Patcher", model: "gpt-4o-mini", state: "queued" },
  { id: "A-12", name: "Consistency", model: "claude-3-5-sonnet", state: "queued" },
];

const INITIAL_UNITS: UnitProgressData[] = [
  { id: "U-01", name: "Unit 1: Fundamentals", state: "queued", progress: 0, isFirstCompleted: true },
  { id: "U-02", name: "Unit 2: Core Analysis", state: "queued", progress: 0 },
  { id: "U-03", name: "Unit 3: Applications", state: "queued", progress: 0 },
  { id: "U-04", name: "Unit 4: Advanced Theory", state: "queued", progress: 0 },
];

export default function PipelinePage() {
  const params = useParams();
  const upc = (params.upc as string) || "2352203601";
  
  const [agents, setAgents] = useState<AgentData[]>(INITIAL_AGENTS);
  const [units, setUnits] = useState<UnitProgressData[]>(INITIAL_UNITS);
  const [isStopped, setIsStopped] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Document Title
  useEffect(() => {
    document.title = USE_MOCK
      ? "StudyAI · Simulated Mock Paper"
      : `StudyAI · Generating ${upc}`;
  }, [upc]);

  // Mock Pipeline Simulation
  useEffect(() => {
    let currentAgentIndex = 0;

    intervalRef.current = setInterval(() => {
      setAgents((prev) => {
        const next = [...prev];
        
        // Mark previous as complete
        if (currentAgentIndex > 0 && currentAgentIndex <= next.length) {
          next[currentAgentIndex - 1].state = "complete";
        }
        
        // Mark current as running
        if (currentAgentIndex < next.length) {
          // Introduce a mock failure state for A-08 just to show off the UI
          if (currentAgentIndex === 7 && next[currentAgentIndex].state !== "failed") {
            next[currentAgentIndex].state = "failed";
            // Wait a bit before retrying automatically
            setTimeout(() => {
              setAgents(a => {
                const newA = [...a];
                newA[7].state = "running";
                return newA;
              });
            }, 3000);
          } else {
            next[currentAgentIndex].state = "running";
            currentAgentIndex++;
          }
        }
        
        return next;
      });

      // Update unit mock progress based on agent completion
      setUnits((prev) => {
        const next = [...prev];
        if (currentAgentIndex > 2) {
          next[0].state = "processing";
          next[0].progress = Math.min((currentAgentIndex - 2) * 0.25, 1);
          if (next[0].progress === 1) next[0].state = "complete";
        }
        if (currentAgentIndex > 5) {
          next[1].state = "processing";
          next[1].progress = Math.min((currentAgentIndex - 5) * 0.25, 1);
          if (next[1].progress === 1) next[1].state = "complete";
        }
        return next;
      });

      if (currentAgentIndex > agents.length + 1) {
        if (intervalRef.current) clearInterval(intervalRef.current);
      }
    }, 4500);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [agents.length]);

  const handleStop = () => {
    setIsStopped(true);
    if (intervalRef.current) clearInterval(intervalRef.current);
    
    // Halt any running animations by changing state
    setAgents(prev => prev.map(agent => 
      agent.state === "running" ? { ...agent, state: "failed" } : agent
    ));
    setUnits(prev => prev.map(unit =>
      unit.state === "processing" ? { ...unit, state: "queued" } : unit
    ));
  };

  const completedCount = agents.filter(a => a.state === "complete").length;

  return (
    <PageTransition>
      <div className="h-screen w-full flex flex-col bg-bg-base overflow-hidden">
        
        <GrainOverlay />
        <AmbientLight variant="pipeline" />

        {/* PROGRESS HEADER */}
        <div className="z-10 relative">
          <PipelineProgress 
            paperName="Simulated Mock Paper" 
            upc={upc} 
            completedAgents={completedCount} 
          />
        </div>

        {/* MAIN TWO-COLUMN CONTENT */}
        <div className="flex-1 flex flex-row overflow-hidden relative z-0">
          
          {/* AGENT GRID COLUMN (65%) */}
          <div className="flex-[0.65] h-full overflow-y-auto overflow-x-hidden p-6 md:p-10 scrollbar-none">
            <div className="max-w-4xl mx-auto">
              <AgentGrid agents={agents} />
            </div>
          </div>

          {/* UNIT TRACKER COLUMN (35%) */}
          <div className="flex-[0.35] h-full hidden md:block">
            <UnitTracker units={units} />
          </div>

        </div>

        {/* STOP GENERATION BUTTON */}
        {!isStopped && completedCount < agents.length && (
          <button
            onClick={handleStop}
            className="fixed bottom-6 right-6 z-[110] bg-bg-raised border border-border-subtle text-text-secondary px-5 py-2 rounded-full font-sans text-[11px] font-bold uppercase tracking-widest hover:text-red hover:border-red/50 transition-colors shadow-lg"
          >
            Stop Generation
          </button>
        )}
      </div>
    </PageTransition>
  );
}
