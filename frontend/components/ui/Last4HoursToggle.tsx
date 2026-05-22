import React from 'react';
import { Clock } from 'lucide-react';

export interface Last4HoursToggleProps {
  isActive: boolean;
  onToggle: () => void;
}

export function Last4HoursToggle({ isActive, onToggle }: Last4HoursToggleProps) {
  return (
    <button 
      onClick={onToggle}
      className={`flex items-center gap-2 px-4 py-2 rounded-full border transition-all duration-300 font-semibold text-sm ${
        isActive 
          ? 'bg-accent text-accent-foreground border-accent shadow-md' 
          : 'bg-background text-foreground border-border hover:bg-muted'
      }`}
    >
      <Clock className={`w-4 h-4 ${isActive ? 'animate-pulse' : ''}`} />
      <span>Last 4 Hours</span>
    </button>
  );
}
