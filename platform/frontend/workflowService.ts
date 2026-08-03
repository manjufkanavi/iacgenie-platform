import { apiClient } from './apiClient';
import type {
  CreatePipelineConfig,
  PipelineFilters,
} from '../types';

interface SessionListItem {
  id: string;
  build_id: string;
  status: string;
  prompt: string;
  user_id: string;
  created_at: string;
  updated_at: string;
}

interface ListSessionsResponse {
  sessions: SessionListItem[];
  total: number;
  limit: number;
  offset: number;
}

export const workflowService = {
  // New unified endpoints
  startSession: (data: any) => 
    apiClient.post(`/api/workflow/start`, data),
    
  getSessionStatus: (sessionId: string) => 
    apiClient.get(`/api/workflow/${sessionId}/status`),
    
  getSessionLogs: (sessionId: string) => 
    apiClient.get(`/api/workflow/${sessionId}/logs`),
    
  getSessionCode: (sessionId: string) =>
    apiClient.get(`/api/workflow/${sessionId}/code`),

  getFileContent: async (sessionId: string, filename: string): Promise<string> => {
    const token = localStorage.getItem('iacgenie_token');
    const res = await fetch(
      `/api/sessions/${sessionId}/file/${encodeURIComponent(filename)}?token=${token}`,
    );
    if (!res.ok) throw new Error(`Failed to fetch file: ${filename}`);
    return res.text();
  },
    
  approvePhase: (sessionId: string, comment?: string) =>
    apiClient.post(`/api/workflow/${sessionId}/human-review/approve`, {
      action: 'approve',
      comment: comment || undefined,
    }),

  clarifyPhase: (sessionId: string, response: string) =>
    apiClient.post(`/api/workflow/${sessionId}/human-review/clarify`, {
      action: 'clarify',
      comment: response,
    }),

  abortSession: (sessionId: string) =>
    apiClient.post(`/api/workflow/${sessionId}/fail`, { message: 'Aborted by user' }),

  // Generation job status (for reconciliation and heartbeat)
  getGenerationJob: (jobId: string) =>
    apiClient.get(`/api/generate/job/${jobId}`),

  getGenerationHeartbeat: (jobId: string) =>
    apiClient.get(`/api/generate/heartbeat/${jobId}`),

  // Existing endpoints to support other components
  createPipeline: (config: CreatePipelineConfig) =>
    apiClient.post<{ id: string; status: string; prompt: string }>(
      `/api/workflow/start`,
      {
        prompt: config.user_request || '',
        build_id: config.name,
        metadata: {
          workspace_id: config.workspace_id,
          deploymentMode: config.deploymentMode,
        },
      },
    ),

  getPipelineState: (pipelineId: string) =>
    apiClient.get<{ id: string; status: string; prompt: string }>(
      `/api/workflow/${pipelineId}`,
    ),

  getPipelines: (filters?: PipelineFilters) => {
    const params = new URLSearchParams();
    if (filters?.status) params.append('status', filters.status);
    if (filters?.searchQuery) params.append('search', filters.searchQuery);
    if (filters?.limit) params.append('limit', String(filters.limit));
    if (filters?.offset) params.append('offset', String(filters.offset));

    const query = params.toString();
    return apiClient.get<ListSessionsResponse>(`/api/workflow?${query}`);
  },

  resumePipeline: (pipelineId: string, answers: string[]) =>
    apiClient.post<void>(`/api/sessions/${pipelineId}/resume`, {
      answers,
    }),

  abortPipeline: (pipelineId: string) =>
    apiClient.post<void>(`/api/workflow/${pipelineId}/fail`, {
      message: 'Aborted by user',
    }),

  intervenePhase: (pipelineId: string, comment: string) =>
    apiClient.post<void>(
      `/api/workflow/${pipelineId}/human-review/clarify`,
      {
        action: 'clarify',
        comment: comment,
      },
    ),
  
  estimateCost: (_pipelineId: string) =>
    Promise.resolve({ data: null } as any),

  teardownSimulation: (_pipelineId: string) =>
    Promise.resolve(),
};

export default workflowService;
