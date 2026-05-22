"use client";

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { getPaper, getUnitsForPaper, subscribeToUnitStatus } from '@/lib/queries';
import { Paper, Unit } from '@/types/database';
import { Loader2, BookOpen, Clock, AlertCircle } from 'lucide-react';
import { TierBadge } from '@/components/ui/TierBadge';
import { PYQSubmissionBanner } from '@/components/ui/PYQSubmissionBanner';
import { PartialDeliveryNotice } from '@/components/ui/PartialDeliveryNotice';
import { Last4HoursToggle } from '@/components/ui/Last4HoursToggle';
import type { RealtimeChannel } from '@supabase/supabase-js';

export default function PaperPage({ params }: { params: { upc: string } }) {
  const [upc, setUpc] = useState<string | null>(null);
  
  const [paper, setPaper] = useState<Paper | null>(null);
  const [units, setUnits] = useState<Unit[]>([]);
  const [loading, setLoading] = useState(true);
  const [isLast4Hours, setIsLast4Hours] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.resolve(params).then(p => {
      setUpc(p.upc);
    });
  }, [params]);

  useEffect(() => {
    if (!upc) return;

    let channel: RealtimeChannel | undefined;

    async function loadData() {
      try {
        const fetchedPaper = await getPaper(upc!);
        if (fetchedPaper) {
          setPaper(fetchedPaper);
        } else {
          setError("Paper not found");
          return;
        }

        const fetchedUnits = await getUnitsForPaper(upc!);
        setUnits(fetchedUnits);

        // Subscribe to real-time unit updates
        channel = subscribeToUnitStatus(upc!, (updatedUnit) => {
          setUnits(prev => {
            const index = prev.findIndex(u => u.unit_id === updatedUnit.unit_id);
            if (index >= 0) {
              const newUnits = [...prev];
              newUnits[index] = updatedUnit;
              return newUnits;
            }
            // If it's a new unit (unlikely since we query all of them, but just in case)
            return [...prev, updatedUnit].sort((a, b) => a.unit_number - b.unit_number);
          });
        });
      } catch (err) {
        console.error(err);
        setError("Failed to load paper data");
      } finally {
        setLoading(false);
      }
    }

    loadData();

    return () => {
      if (channel) {
        channel.unsubscribe();
      }
    };
  }, [upc]);

  if (loading || !upc) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-accent animate-spin" />
      </div>
    );
  }

  if (error || !paper) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-4 text-center">
        <AlertCircle className="w-12 h-12 text-destructive mb-4" />
        <h1 className="text-2xl font-bold text-foreground mb-2">Paper Not Found</h1>
        <p className="text-muted-foreground mb-6">{error || "The requested UPC does not exist."}</p>
        <Link href="/" className="px-4 py-2 bg-accent text-accent-foreground rounded-md hover:bg-accent/90 transition-colors">
          Return Home
        </Link>
      </div>
    );
  }

  const tier = (paper.tier || 3) as 1 | 2 | 3 | 4;

  return (
    <main className="max-w-4xl mx-auto p-4 md:p-8 min-h-screen pb-24">
      <header className="mb-10 space-y-6 border-b border-border pb-8">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div className="flex flex-col gap-2">
            <span className="text-sm font-mono bg-muted text-muted-foreground px-2 py-1 rounded w-fit">
              UPC: {paper.upc}
            </span>
            <h1 className="text-3xl md:text-4xl font-serif font-bold text-foreground">
              {paper.paper_name}
            </h1>
          </div>
          <Last4HoursToggle 
            isActive={isLast4Hours} 
            onToggle={() => setIsLast4Hours(!isLast4Hours)} 
          />
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-muted-foreground">
          {paper.department && <div><span className="font-semibold block">Dept</span> {paper.department}</div>}
          {paper.programme && <div><span className="font-semibold block">Prog</span> {paper.programme}</div>}
          {paper.semester && <div><span className="font-semibold block">Sem</span> {paper.semester}</div>}
          {paper.paper_type && <div><span className="font-semibold block">Type</span> {paper.paper_type}</div>}
        </div>

        <div className="flex flex-wrap items-center gap-4 pt-4">
          <TierBadge tier={tier} pyqYearsAvailable={paper.pyq_years_available?.length || 0} />
          
          {paper.syllabus_url && (
            <a 
              href={paper.syllabus_url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-xs text-muted-foreground hover:text-accent transition-colors flex items-center gap-1"
            >
              <BookOpen className="w-3 h-3" />
              Syllabus {paper.syllabus_last_verified && `verified ${new Date(paper.syllabus_last_verified).toLocaleDateString()}`}
            </a>
          )}
        </div>

        {paper.pyq_years_available && paper.pyq_years_available.length > 0 && (
          <div className="pt-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mr-3">
              PYQs Found:
            </span>
            <div className="flex flex-wrap gap-2 inline-flex">
              {paper.pyq_years_available.map(year => (
                <span key={year} className="text-xs bg-accent/10 text-accent px-2 py-0.5 rounded-full font-mono font-medium">
                  {year}
                </span>
              ))}
            </div>
          </div>
        )}
      </header>

      {(tier === 3 || tier === 4) && (
        <div className="mb-8">
          <PYQSubmissionBanner upc={paper.upc} paperName={paper.paper_name} tier={tier} />
        </div>
      )}

      <div className="space-y-6">
        <h2 className="text-xl font-bold tracking-tight mb-4 flex items-center gap-2">
          Units 
          <span className="text-sm font-normal text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
            {units.length}
          </span>
        </h2>
        
        {units.length === 0 ? (
          <div className="text-center p-8 bg-muted/30 rounded-lg border border-dashed border-border/50">
            <p className="text-muted-foreground">No units found for this paper.</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {units.map((unit) => {
              if (unit.status === 'failed') {
                return (
                  <PartialDeliveryNotice 
                    key={unit.unit_id}
                    unitName={`Unit ${unit.unit_number}: ${unit.unit_name}`}
                    status="failed"
                    retryAvailable={true}
                  />
                );
              }
              
              if (unit.status === 'generating' || unit.status === 'queued') {
                return (
                  <div key={unit.unit_id} className="p-4 rounded-lg border border-border/50 bg-card/30 flex items-center justify-between">
                    <div>
                      <div className="text-sm text-muted-foreground mb-1">Unit {unit.unit_number}</div>
                      <div className="font-medium opacity-75">{unit.unit_name}</div>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-accent bg-accent/10 px-3 py-1.5 rounded-full">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      {unit.status === 'generating' ? 'Generating...' : 'Queued...'}
                    </div>
                  </div>
                );
              }

              return (
                <Link 
                  key={unit.unit_id} 
                  href={`/paper/${upc}/unit/${unit.unit_id}`}
                  className="block p-5 rounded-lg border border-border bg-card hover:border-accent/50 hover:shadow-sm transition-all group"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="text-sm font-semibold text-accent mb-2">
                        Unit {unit.unit_number}
                      </div>
                      <h3 className="text-lg font-bold group-hover:text-accent transition-colors mb-2">
                        {unit.unit_name}
                      </h3>
                      {unit.conceptual_summary && (
                        <p className="text-sm text-muted-foreground line-clamp-2 max-w-2xl">
                          {unit.conceptual_summary}
                        </p>
                      )}
                    </div>
                    
                    <div className="flex flex-col items-end gap-2 shrink-0">
                      {unit.estimated_study_hours && (
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/50 px-2 py-1 rounded">
                          <Clock className="w-3.5 h-3.5" />
                          ~{unit.estimated_study_hours}h
                        </div>
                      )}
                      {unit.marks_weightage && (
                        <div className="text-xs font-medium px-2 py-1 bg-background border border-border rounded">
                          {unit.marks_weightage} marks
                        </div>
                      )}
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
