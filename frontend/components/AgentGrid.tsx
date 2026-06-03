"use client";

import { AgentCard, AgentState } from "./AgentCard";
import { DeadTimePulseProvider } from "./DeadTimePulse";

/**
 * AgentGrid — The physical bento grid of agents.
 * 
 * Uses a CSS Grid layout with specific row/column spans to communicate
 * hierarchy. The Writer (content engine) is double width. The Verifier
 * (trust layer) is double height.
 */

export interface AgentData {
  id: string;
  name: string;
  model: string;
  state: AgentState;
}

interface AgentGridProps {
  agents: AgentData[];
}

export function AgentGrid({ agents }: AgentGridProps) {
  // Sizing mapping based on the spec
  const getGridClass = (id: string) => {
    switch (id) {
      case "A-05": return "col-span-1 sm:col-span-2"; // Writer (2x1)
      case "A-07": return "row-span-1 sm:row-span-2"; // Verifier (1x2)
      default: return "col-span-1 row-span-1";
    }
  };

  return (
    <DeadTimePulseProvider>
      <div className="grid grid-cols-2 sm:grid-cols-4 auto-rows-auto gap-3 w-full">
        {agents.map((agent, index) => (
          <AgentCard
            key={agent.id}
            {...agent}
            index={index}
            className={getGridClass(agent.id)}
          />
        ))}
      </div>
    </DeadTimePulseProvider>
  );
}
