"use client";

import { motion } from "framer-motion";
import { useRouter, useParams } from "next/navigation";

/**
 * UnitCard — Individual unit entry in the Paper Overview list.
 * 
 * Has exactly 4 status states.
 * Incorporates priority dots to communicate yield at a glance.
 * Spring-driven translateY hover effect for complete cards.
 */

export type UnitPriority = "red" | "amber" | "gray" | "none";

export interface UnitCardData {
  id: string;
  name: string;
  summary: string;
  studyTime: string;
  marks: string; // e.g. "18 Marks"
  priorityDots: UnitPriority[];
  completedTopics: number;
  totalTopics: number;
  status: "Complete" | "Generating" | "Queued" | "Failed";
}

interface UnitCardProps {
  unit: UnitCardData;
  index: number;
}

export function UnitCard({ unit, index }: UnitCardProps) {
  const router = useRouter();
  const params = useParams();
  const upc = (params.upc as string) || "demo";
  const isComplete = unit.status === "Complete";
  const progressPercent = unit.totalTopics > 0 ? unit.completedTopics / unit.totalTopics : 0;

  const handleClick = () => {
    if (isComplete) {
      router.push(`/reading/${upc}/${unit.id}`);
    }
  };

  const getPriorityColor = (priority: UnitPriority) => {
    switch (priority) {
      case "red": return "bg-red";
      case "amber": return "bg-accent";
      case "gray": return "bg-text-tertiary";
      case "none":
      default: return "bg-border-subtle";
    }
  };

  return (
    <motion.div
      onClick={handleClick}
      // Entrance animation: header finishes first, then cards stagger
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ 
        type: "spring", 
        stiffness: 100, 
        damping: 20, 
        delay: 0.4 + (index * 0.06) 
      }}
      // Hover effect only for complete cards
      whileHover={isComplete ? { y: -2, backgroundColor: "var(--bg-raised)" } : {}}
      className={`relative w-full p-6 bg-bg-card border border-border-default rounded-xl overflow-hidden flex flex-col sm:flex-row sm:items-center justify-between gap-6 transition-colors duration-150 ${
        isComplete ? "cursor-pointer" : "opacity-80"
      }`}
    >
      {/* Left side: Content */}
      <div className="flex flex-col gap-2 flex-1">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[10px] text-text-tertiary px-2 py-0.5 border border-border-subtle rounded uppercase">
            {unit.id}
          </span>
          <span className="font-mono text-[11px] text-text-tertiary">
            {unit.studyTime} · {unit.marks}
          </span>
        </div>
        <h3 className="font-serif text-[24px] text-text-primary leading-tight">
          {unit.name}
        </h3>
        <p className="font-sans text-[13px] text-text-secondary max-w-[400px]">
          {unit.summary}
        </p>
      </div>

      {/* Middle: Priority Dots */}
      <div className="flex flex-col gap-1.5 sm:items-center min-w-[120px]">
        <span className="font-sans text-[9px] uppercase tracking-widest text-text-tertiary">
          Topic Yield
        </span>
        <div className="flex items-center gap-1.5">
          {unit.priorityDots.map((dot, i) => (
            <div 
              key={i} 
              className={`w-1.5 h-1.5 rounded-full ${getPriorityColor(dot)}`}
            />
          ))}
        </div>
      </div>

      {/* Right side: Status / CTA */}
      <div className="flex flex-col sm:items-end justify-center min-w-[140px] gap-2">
        <div className="font-sans text-[10px] uppercase font-bold tracking-wider flex items-center gap-2">
          {unit.status === "Complete" && (
            <span className="text-accent flex items-center gap-1">
              Read Unit <span className="text-[14px]">→</span>
            </span>
          )}
          {unit.status === "Generating" && (
            <span className="text-text-primary flex items-center gap-1.5">
              <span className="inline-block w-2.5 h-2.5 border border-text-primary border-t-transparent rounded-full animate-spin" />
              Generating
            </span>
          )}
          {unit.status === "Queued" && (
            <span className="text-text-tertiary">Queued</span>
          )}
          {unit.status === "Failed" && (
            <span className="text-red">Failed</span>
          )}
        </div>
        <div className="font-mono text-[10px] text-text-tertiary uppercase">
          {unit.completedTopics}/{unit.totalTopics} Topics
        </div>
      </div>

      {/* Bottom absolute Progress Bar */}
      <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-border-subtle">
        <motion.div
          className="absolute top-0 bottom-0 left-0 bg-accent origin-left"
          initial={{ scaleX: 0 }}
          animate={{ scaleX: progressPercent }}
          transition={{ type: "spring", stiffness: 100, damping: 20, delay: 0.6 + (index * 0.06) }}
        />
      </div>
    </motion.div>
  );
}
