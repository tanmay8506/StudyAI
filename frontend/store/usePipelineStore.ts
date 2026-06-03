import { create } from 'zustand';

// Status bitmask representation for extreme fast UI updates
export enum AgentStatus {
  QUEUED = 0,
  RUNNING = 1,
  COMPLETE = 2,
  FAILED = 3,
}

export interface UnitProgress {
  unitId: string;
  unitNumber: number;
  status: 'queued' | 'generating' | 'complete' | 'failed';
  totalTopics: number;
  completedTopics: number;
}

interface PipelineState {
  upc: string | null;
  agents: Record<number, AgentStatus>; // Agent 1-12 status
  units: Record<string, UnitProgress>;
  
  // Actions
  initializePipeline: (upc: string) => void;
  updateAgentStatus: (agentId: number, status: AgentStatus) => void;
  updateUnitProgress: (unitId: string, progress: Partial<UnitProgress>) => void;
  reset: () => void;
}

export const usePipelineStore = create<PipelineState>((set) => ({
  upc: null,
  // Start all agents queued
  agents: {
    1: AgentStatus.QUEUED, 2: AgentStatus.QUEUED, 3: AgentStatus.QUEUED,
    4: AgentStatus.QUEUED, 5: AgentStatus.QUEUED, 6: AgentStatus.QUEUED,
    7: AgentStatus.QUEUED, 8: AgentStatus.QUEUED, 9: AgentStatus.QUEUED,
    10: AgentStatus.QUEUED, 11: AgentStatus.QUEUED, 12: AgentStatus.QUEUED,
  },
  units: {},

  initializePipeline: (upc) => set((state) => ({
    upc,
    // Agent 1 activates instantly on pipeline start
    agents: { ...state.agents, 1: AgentStatus.RUNNING },
  })),

  updateAgentStatus: (agentId, status) => set((state) => ({
    agents: { ...state.agents, [agentId]: status }
  })),

  updateUnitProgress: (unitId, progress) => set((state) => ({
    units: {
      ...state.units,
      [unitId]: { ...(state.units[unitId] || {}), ...progress } as UnitProgress
    }
  })),

  reset: () => set({ 
    upc: null, 
    agents: {
      1: AgentStatus.QUEUED, 2: AgentStatus.QUEUED, 3: AgentStatus.QUEUED,
      4: AgentStatus.QUEUED, 5: AgentStatus.QUEUED, 6: AgentStatus.QUEUED,
      7: AgentStatus.QUEUED, 8: AgentStatus.QUEUED, 9: AgentStatus.QUEUED,
      10: AgentStatus.QUEUED, 11: AgentStatus.QUEUED, 12: AgentStatus.QUEUED,
    }, 
    units: {} 
  })
}));
