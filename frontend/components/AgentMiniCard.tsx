"use client";

import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";

/**
 * AgentMiniCard — Small, dense representation of an agent for Section 4.
 */
interface AgentMiniCardProps {
  id: string;
  name: string;
  model: string;
}

export function AgentMiniCard({ id, name, model }: AgentMiniCardProps) {
  return (
    <div className="w-[140px] h-[80px] bg-bg-card border border-border-subtle rounded-xl p-3 flex flex-col justify-between shrink-0">
      <div className="font-mono text-[9px] text-text-tertiary">
        {id}
      </div>
      <div>
        <div className="font-sans font-bold text-[12px] text-text-primary leading-tight">
          {name}
        </div>
        <div className="font-mono text-[9px] text-text-tertiary mt-1">
          {model}
        </div>
      </div>
    </div>
  );
}

/**
 * AgentMiniCardRow — Horizontal scroll row of all 12 agents.
 * 
 * Uses scroll parallax to translate right to left at 0.3x scroll speed.
 * Not a marquee. Tied strictly to scroll progress.
 */
export function AgentMiniCardRow() {
  const containerRef = useRef<HTMLDivElement>(null);
  
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"]
  });

  // Parallax translation: moves horizontally as user scrolls vertically
  const x = useTransform(scrollYProgress, [0, 1], ["10%", "-30%"]);

  const agents = [
    { id: "A-01", name: "Syllabus Map", model: "o1-mini" },
    { id: "A-02", name: "Researcher", model: "claude-3-5-sonnet" },
    { id: "A-03", name: "Paper DNA", model: "gpt-4o" },
    { id: "A-04", name: "Mental Mapper", model: "claude-3-5-sonnet" },
    { id: "A-05", name: "Writer", model: "claude-3-5-sonnet" },
    { id: "A-06", name: "Coverage", model: "o1-mini" },
    { id: "A-07", name: "Verifier", model: "claude-3-5-sonnet" },
    { id: "A-08", name: "Critic", model: "gpt-4o" },
    { id: "A-09", name: "Rewriter", model: "claude-3-5-sonnet" },
    { id: "A-10", name: "Final Examiner", model: "o1-mini" },
    { id: "A-11", name: "Patcher", model: "gpt-4o-mini" },
    { id: "A-12", name: "Consistency", model: "claude-3-5-sonnet" },
  ];

  return (
    <div ref={containerRef} className="w-full overflow-hidden py-10 relative">
      <motion.div 
        className="flex gap-4 px-6 md:px-[20vw] w-max"
        style={{ x }}
      >
        {agents.map((agent) => (
          <AgentMiniCard key={agent.id} {...agent} />
        ))}
      </motion.div>
    </div>
  );
}
