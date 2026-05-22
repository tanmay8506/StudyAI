import React from 'react';

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
      <div className="flex justify-between items-end mb-2">
        <h3 className="text-sm font-bold uppercase tracking-wider text-foreground/80">Unit Generation Progress</h3>
        <span className="text-xs font-semibold text-muted-foreground">{completedUnits} / {totalUnits} ({percentage}%)</span>
      </div>
      
      <div className="flex gap-1 h-2 w-full rounded-full overflow-hidden bg-muted">
        {units.length > 0 ? units.map((unit) => {
          let bgColor = 'bg-muted-foreground/20';
          if (unit.status === 'complete') bgColor = 'bg-success';
          else if (unit.status === 'failed') bgColor = 'bg-destructive';
          else if (unit.status === 'generating') bgColor = 'bg-accent animate-pulse';

          return (
            <div 
              key={unit.unit_number} 
              className={`h-full flex-1 transition-colors duration-500 ${bgColor}`}
              title={`Unit ${unit.unit_number}: ${unit.unit_name} (${unit.status})`}
            />
          );
        }) : (
          <div className="h-full w-full bg-muted-foreground/20" />
        )}
      </div>
    </div>
  );
}
