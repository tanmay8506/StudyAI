"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useIsMobile } from "@/lib/hooks/useMediaQuery";

/**
 * DeadTimePulse — Sonar sweep animation system for the bento grid.
 * 
 * Provides a periodic pulse "tick" every 6-8 seconds.
 * Subscribing components (AgentCards) use this tick to trigger
 * their staggered opacity animations if they are in the QUEUED state.
 */

const DeadTimePulseContext = createContext<number>(0);

export function useDeadTimePulse() {
  return useContext(DeadTimePulseContext);
}

export function DeadTimePulseProvider({ children }: { children: React.ReactNode }) {
  const [pulseTick, setPulseTick] = useState(0);
  const isMobile = useIsMobile();

  useEffect(() => {
    // Fire the pulse every 7 seconds
    const interval = setInterval(() => {
      setPulseTick((prev) => prev + 1);
    }, 7000);
    
    return () => clearInterval(interval);
  }, []);

  return (
    <DeadTimePulseContext.Provider value={isMobile ? 0 : pulseTick}>
      {children}
    </DeadTimePulseContext.Provider>
  );
}
