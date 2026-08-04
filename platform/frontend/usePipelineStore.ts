import { create } from 'zustand';
import type {
  PipelinePhase,
  PhaseStatus,
  PipelineSession,
  PhaseHistoryEntry,
  PipelineLogEntry,
  PipelineMetrics,
} from './types';

export interface ChatMessage {
  id: string;
  role: 'agent' | 'user';
  content: string;
  timestamp: string;
  confidence?: number;
  suggestions?: string[];
}

export type StreamConnectionState = 'connecting' | 'connected' | 'reconnecting' | 'disconnected' | 'error';

interface PipelineState {
  // State
  connectionState: StreamConnectionState;
  latency: number | null;
  eventsReceived: number;
  reconnects: number;
  errorMessage: string | null;

  activePipeline: PipelineSession | null;
  phaseHistory: PhaseHistoryEntry[];
  pipelineLogs: PipelineLogEntry[];
  metrics: PipelineMetrics | null;
  error: string | null;
  clarifyConversations: Record<string, ChatMessage[]>;
  specDrafts: Record<string, string[]>;

  // Actions
  setActivePipeline: (pipeline: PipelineSession | null) => void;
  updatePhaseProgress: (phase: PipelinePhase, progress: number) => void;
  transitionPhase: (newPhase: PipelinePhase, status: PhaseStatus) => void;
  addLogEntry: (entry: Omit<PipelineLogEntry, 'timestamp'> & Partial<PipelineLogEntry>) => void;
  pausePipeline: () => void;
  resumePipeline: () => void;
  abortPipeline: () => void;
  updateMetrics: (metrics: PipelineMetrics) => void;
  setError: (error: string | null) => void;
  clearPipeline: () => void;
  setClarifyConversation: (pipelineId: string, messages: ChatMessage[]) => void;
  addClarifyMessage: (pipelineId: string, message: ChatMessage) => void;
  addSpecDraft: (pipelineId: string, draft: string) => void;
  setConnectionState: (state: StreamConnectionState, errorMessage?: string | null) => void;
  updateLatency: (latency: number | null) => void;
  incrementEventsReceived: () => void;
  incrementReconnects: () => void;
  clearConnectionMetrics: () => void;
}

const createTimestamp = () => new Date().toISOString();

export const usePipelineStore = create<PipelineState>((set) => ({
  activePipeline: null,
  phaseHistory: [],
  pipelineLogs: [],
  metrics: null,
  error: null,

  clarifyConversations: {},
  specDrafts: {},

  connectionState: 'disconnected',
  latency: null,
  eventsReceived: 0,
  reconnects: 0,
  errorMessage: null,

  setActivePipeline: (pipeline) => set({ activePipeline: pipeline }),

  updatePhaseProgress: (_phase, progress) =>
    set((state) => {
      if (!state.activePipeline) return state;
      return {
        activePipeline: {
          ...state.activePipeline,
          currentPhaseProgress: progress,
        },
      };
    }),

  transitionPhase: (newPhase, status) =>
    set((state) => {
      if (!state.activePipeline) return state;
      const now = createTimestamp();
      const entry: PhaseHistoryEntry = {
        phase: newPhase,
        status,
        startedAt: now,
        completedAt: status === 'success' || status === 'failed' || status === 'escalated' ? now : undefined,
        details: `Phase transitioned to ${newPhase}: ${status}`,
      };
      return {
        activePipeline: {
          ...state.activePipeline,
          phase: newPhase,
          status: status === 'failed' ? 'failed' : status === 'escalated' ? 'escalated' : state.activePipeline.status,
          errorCount: status === 'failed' ? state.activePipeline.errorCount + 1 : state.activePipeline.errorCount,
        },
        phaseHistory: [...state.phaseHistory, entry],
      };
    }),

  addLogEntry: (entry) =>
    set((state) => {
      const newEntry: PipelineLogEntry = {
        timestamp: entry.timestamp || createTimestamp(),
        phase: entry.phase,
        message: entry.message,
        level: entry.level || 'info',
      };
      const logs = [...state.pipelineLogs, newEntry];
      // Keep only last 500 entries to prevent unbounded growth
      return logs.length > 500 ? { ...state, pipelineLogs: logs.slice(-500) } : { ...state, pipelineLogs: logs };
    }),

  pausePipeline: () =>
    set((state) => {
      if (!state.activePipeline) return state;
      return {
        activePipeline: { ...state.activePipeline, status: 'paused' },
      };
    }),

  resumePipeline: () =>
    set((state) => {
      if (!state.activePipeline) return state;
      return {
        activePipeline: { ...state.activePipeline, status: 'running' },
      };
    }),

  abortPipeline: () =>
    set((state) => {
      if (!state.activePipeline) return state;
      return {
        activePipeline: { ...state.activePipeline, status: 'failed' },
        error: 'Pipeline aborted by user',
      };
    }),

  updateMetrics: (metrics) => set({ metrics }),

  setError: (error) => set({ error }),

  clearPipeline: () =>
    set({
      activePipeline: null,
      phaseHistory: [],
      pipelineLogs: [],
      metrics: null,
      error: null,
    }),

  setClarifyConversation: (pipelineId, messages) =>
    set((state) => ({
      clarifyConversations: {
        ...state.clarifyConversations,
        [pipelineId]: messages,
      },
    })),

  addClarifyMessage: (pipelineId, message) =>
    set((state) => {
      const currentMessages = state.clarifyConversations[pipelineId] || [];
      return {
        clarifyConversations: {
          ...state.clarifyConversations,
          [pipelineId]: [...currentMessages, message],
        },
      };
    }),

  addSpecDraft: (pipelineId, draft) =>
    set((state) => {
      const currentDrafts = state.specDrafts[pipelineId] || [];
      return {
        specDrafts: {
          ...state.specDrafts,
          [pipelineId]: [...currentDrafts, draft],
        },
      };
    }),
  
  setConnectionState: (connectionState, errorMessage = null) =>
    set({ connectionState, errorMessage }),
    
  updateLatency: (latency) => set({ latency }),
  
  incrementEventsReceived: () =>
    set((state) => ({ eventsReceived: state.eventsReceived + 1 })),
    
  incrementReconnects: () =>
    set((state) => ({ reconnects: state.reconnects + 1 })),
    
  clearConnectionMetrics: () =>
    set({ latency: null, eventsReceived: 0, reconnects: 0, errorMessage: null }),
}));
