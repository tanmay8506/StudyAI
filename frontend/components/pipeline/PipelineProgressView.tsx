"use client";

import React, { useEffect, useState } from 'react';
import { subscribeToUnitStatus, getUnitsForPaper } from '@/lib/queries';
import { Unit } from '@/types/database';
import { AgentStatusCard } from './AgentStatusCard';
import { UnitProgressBar } from './UnitProgressBar';
import Link from 'next/link';
import { ArrowRight, BookOpen } from 'lucide-react';
import { useRouter } from 'next/navigation';

export interface PipelineProgressViewProps {
  upc: string;
}

export function PipelineProgressView({ upc }: PipelineProgressViewProps) {
  const [units, setUnits] = useState<Unit[]>([]);
  const router = useRouter();

  useEffect(() => {
    let isMounted = true;
    
    // Fetch initial state
    getUnitsForPaper(upc).then(data => {
      if (isMounted) setUnits(data);
    });

    // Polling fallback every 3 seconds
    const interval = setInterval(() => {
      getUnitsForPaper(upc).then(data => {
        if (isMounted) {
          setUnits(prev => {
            // Keep realtime updates if they exist, but append new units
            const newUnits = [...prev];
            let changed = false;
            for (const d of data) {
              const idx = newUnits.findIndex(u => u.unit_id === d.unit_id);
              if (idx === -1) {
                newUnits.push(d);
                changed = true;
              } else if (d.status !== newUnits[idx].status) {
                // If polling catches a status update missed by realtime
                newUnits[idx] = d;
                changed = true;
              }
            }
            if (changed) {
              return newUnits.sort((a, b) => a.unit_number - b.unit_number);
            }
            return prev;
          });
        }
      });
    }, 3000);

    // Subscribe to realtime updates
    const channel = subscribeToUnitStatus(upc, (updatedUnit) => {
      setUnits(prev => {
        const idx = prev.findIndex(u => u.unit_id === updatedUnit.unit_id);
        if (idx === -1) return [...prev, updatedUnit].sort((a, b) => a.unit_number - b.unit_number);
        const next = [...prev];
        next[idx] = updatedUnit;
        return next;
      });
    });

    return () => {
      isMounted = false;
      clearInterval(interval);
      channel.unsubscribe();
    };
  }, [upc]);

  const completedUnits = units.filter(u => u.status === 'complete').length;
  const totalUnits = units.length || 1; // avoid divide by zero if not loaded
  const isAllComplete = units.length > 0 && completedUnits === units.length;

  useEffect(() => {
    if (isAllComplete) {
      const timer = setTimeout(() => {
        router.push(`/paper/${upc}`);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [isAllComplete, upc, router]);

  const hasUnits = units.length > 0;
  const anyUnitCompleted = units.some(u => u.status === 'complete');
  const allUnitsCompleted = isAllComplete;

  const agents: {num: number, name: string, model: string, status: 'complete' | 'running' | 'queued'}[] = [
    { num: 1, name: 'Decoder', model: 'Script', status: 'complete' },
    { num: 2, name: 'Researcher', model: 'Gemini 2.5 Pro', status: hasUnits ? 'complete' : 'running' },
    { num: 3, name: 'Paper DNA', model: 'Gemini 2.0 Flash', status: hasUnits ? 'complete' : 'queued' },
    { num: 4, name: 'Mental Model Mapper', model: 'Groq Llama 3', status: hasUnits ? 'complete' : 'queued' },
    { num: 5, name: 'Writer', model: 'Gemini 2.0 Flash', status: allUnitsCompleted ? 'complete' : (hasUnits ? 'running' : 'queued') },
    { num: 6, name: 'Coverage Checker', model: 'Groq Llama 3', status: allUnitsCompleted ? 'complete' : (anyUnitCompleted ? 'running' : 'queued') },
    { num: 7, name: 'Verifier', model: 'Gemini 2.0 Flash', status: allUnitsCompleted ? 'complete' : 'queued' },
    { num: 8, name: 'Critic', model: 'Gemini 2.0 Flash', status: allUnitsCompleted ? 'complete' : 'queued' },
    { num: 9, name: 'Rewriter', model: 'Gemini 2.0 Flash', status: allUnitsCompleted ? 'complete' : 'queued' },
    { num: 10, name: 'Final Examiner', model: 'Script', status: allUnitsCompleted ? 'complete' : 'queued' },
    { num: 11, name: 'Patcher', model: 'Script', status: allUnitsCompleted ? 'complete' : 'queued' },
    { num: 12, name: 'Consistency Checker', model: 'Groq Llama 3', status: allUnitsCompleted ? 'complete' : 'queued' }
  ];

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold font-serif mb-2">Generating Study Notes</h1>
        <p className="text-muted-foreground">We are processing UPC: <span className="font-mono text-foreground font-semibold">{upc}</span></p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
        {agents.map(a => (
          <AgentStatusCard 
            key={a.num}
            agentNumber={a.num}
            agentName={a.name}
            model={a.model}
            status={a.status}
          />
        ))}
      </div>

      <div className="mb-10 bg-card p-6 border border-border rounded-xl shadow-sm">
        <UnitProgressBar 
          totalUnits={totalUnits} 
          completedUnits={completedUnits}
          units={units.map(u => ({ unit_number: u.unit_number, unit_name: u.unit_name, status: u.status }))}
        />
        
        {isAllComplete && (
          <div className="mt-4 text-center text-sm text-success animate-pulse">
            All units completed. Redirecting to paper overview...
          </div>
        )}
      </div>

      <div className="space-y-4">
        <h3 className="font-semibold text-lg border-b border-border pb-2">Ready to Read</h3>
        {units.filter(u => u.status === 'complete').length === 0 && (
          <p className="text-sm text-muted-foreground italic">No units completed yet. They will appear here as they finish.</p>
        )}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {units.filter(u => u.status === 'complete').map(unit => (
            <Link 
              key={unit.unit_id} 
              href={`/paper/${upc}/unit/${unit.unit_id}`}
              className="group block p-4 bg-background border border-border rounded-lg hover:border-accent hover:shadow-md transition-all"
            >
              <div className="flex justify-between items-center mb-2">
                <div className="flex items-center gap-2 text-foreground">
                  <BookOpen className="w-4 h-4 text-accent" />
                  <span className="font-semibold text-sm uppercase tracking-wider">Unit {unit.unit_number}</span>
                </div>
                <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-accent group-hover:translate-x-1 transition-all" />
              </div>
              <h4 className="font-medium text-foreground/90 group-hover:text-accent transition-colors">
                {unit.unit_name}
              </h4>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
