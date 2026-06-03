import React from 'react';
import { motion } from 'framer-motion';

export interface UnitProgressData {
  unit_number: number;
  unit_name: string;
  status: 'queued' | 'generating' | 'complete' | 'failed';
}

export interface UnitProgressBarProps {
  totalUnits: number;
  completedUnits: number;
  units: UnitProgressData[];
}

export function UnitProgressBar({ totalUnits, completedUnits, units }: UnitProgressBarProps) {
  const percentage = totalUnits === 0 ? 0 : Math.round((completedUnits / totalUnits) * 100);

  return (
    <div className="w-full">
      <div className="flex justify-between items-end mb-3">
        <div className="flex flex-col">
          <span className="text-[10px] font-mono tracking-widest text-white/40 mb-1">SYSTEM_STATUS</span>
          <h3 className="text-sm font-semibold tracking-wide text-white">Pipeline Execution</h3>
        </div>
        <span className="text-sm font-mono font-medium text-accent">{percentage}%</span>
      </div>
      
      <div className="flex gap-1 h-1.5 w-full rounded-full overflow-hidden bg-white/5">
        {units.length > 0 ? units.map((unit) => {
          let bgColor = 'bg-white/10';
          if (unit.status === 'complete') bgColor = 'bg-white shadow-[0_0_10px_rgba(255,255,255,0.8)]';
          else if (unit.status === 'failed') bgColor = 'bg-destructive shadow-[0_0_10px_rgba(255,0,0,0.8)]';
          else if (unit.status === 'generating') bgColor = 'bg-accent shadow-[0_0_10px_rgba(100,100,255,0.8)] animate-pulse';

          return (
            <motion.div 
              key={unit.unit_number} 
              layout
              className={`h-full flex-1 transition-colors duration-500 rounded-full ${bgColor}`}
              title={`Unit ${unit.unit_number}: ${unit.unit_name} (${unit.status})`}
            />
          );
        }) : (
          <div className="h-full w-full bg-white/5" />
        )}
      </div>
    </div>
  );
}
