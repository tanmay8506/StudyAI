"use client";

import React from 'react';
import { usePipelineStore, AgentStatus } from '@/store/usePipelineStore';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

export function AgentGrid() {
  const { agents, upc } = usePipelineStore();

  const getStatusConfig = (status: AgentStatus) => {
    switch (status) {
      case AgentStatus.QUEUED:
        return { label: 'AWAITING', className: 'text-muted-foreground border-border/40' };
      case AgentStatus.RUNNING:
        return { label: 'PROCESSING', className: 'text-foreground border-foreground shadow-[inset_0_0_15px_rgba(255,255,255,0.05)]' };
      case AgentStatus.COMPLETE:
        return { label: 'VERIFIED', className: 'text-accent border-accent/50 bg-accent/5' };
      case AgentStatus.FAILED:
        return { label: 'ERROR', className: 'text-destructive border-destructive/50 bg-destructive/10' };
    }
  };

  const agentConfig = [
    { id: 1, name: 'SYLLABUS_MAP' },
    { id: 2, name: 'WEIGHT_CALC' },
    { id: 3, name: 'COMBINATORICS' },
    { id: 4, name: 'EXAMINER_DNA' },
    { id: 5, name: 'DRAFT_SYNTH' },
    { id: 6, name: 'MATH_VERIFY' },
    { id: 7, name: 'LOGIC_CHAIN' },
    { id: 8, name: 'AXIOM_CHECK' },
    { id: 9, name: 'RECALL_GEN' },
    { id: 10, name: 'TONE_MATCH' },
    { id: 11, name: 'FORMAT_KATEX' },
    { id: 12, name: 'FINAL_COMMIT' },
  ];

  return (
    <div className="w-full font-mono text-xs">
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-border text-muted-foreground">
        <span className="tracking-widest">// PIPELINE TELEMETRY</span>
        {upc && <span>TARGET_UPC: {upc}</span>}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {agentConfig.map((agent) => {
          const status = agents[agent.id] ?? AgentStatus.QUEUED;
          const { label, className } = getStatusConfig(status);

          return (
            <motion.div
              layout
              key={agent.id}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.2 }}
              className={cn(
                "p-3 border flex flex-col justify-between h-24 transition-colors duration-300 relative overflow-hidden",
                className
              )}
            >
              {/* Scanline effect for running state */}
              {status === AgentStatus.RUNNING && (
                <motion.div 
                  initial={{ top: '-10%' }}
                  animate={{ top: '110%' }}
                  transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                  className="absolute left-0 right-0 h-[1px] bg-foreground/20 z-0"
                />
              )}

              <div className="flex justify-between items-start relative z-10">
                <span className="opacity-50 text-[10px]">A-{String(agent.id).padStart(2, '0')}</span>
                {status === AgentStatus.RUNNING && (
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-foreground animate-ping" />
                )}
                {status === AgentStatus.COMPLETE && (
                  <span className="text-accent text-[10px] font-bold">✓</span>
                )}
              </div>
              <div className="space-y-1 relative z-10">
                <div className="font-semibold tracking-wider text-sm">{agent.name}</div>
                <div className="text-[9px] opacity-70 tracking-[0.2em] uppercase">{label}</div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
