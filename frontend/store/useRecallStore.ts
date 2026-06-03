import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type RecallConfidence = 'unsure' | 'partial' | 'full';

export interface RecallEntry {
  topicId: string;
  draftText: string;
  confidence: RecallConfidence;
  timestamp: number;
}

interface RecallState {
  entries: Record<string, RecallEntry>;
  
  logRecall: (topicId: string, draftText: string, confidence: RecallConfidence) => void;
  getRecallEntry: (topicId: string) => RecallEntry | undefined;
}

export const useRecallStore = create<RecallState>()(
  persist(
    (set, get) => ({
      entries: {},
      logRecall: (topicId, draftText, confidence) => set((state) => ({
        entries: {
          ...state.entries,
          [topicId]: {
            topicId,
            draftText,
            confidence,
            timestamp: Date.now()
          }
        }
      })),
      getRecallEntry: (topicId) => get().entries[topicId],
    }),
    {
      name: 'studyai-recall-storage', // The friction engine metrics are persisted locally
    }
  )
);
