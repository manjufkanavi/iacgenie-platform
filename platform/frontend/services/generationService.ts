/**
 * @deprecated Generation service deprecated. GenerationHistoryPage removed per business decision.
 * Generations are now surfaced through the unified PipelineDashboard with type filter.
 * This file is kept for reference and can be deleted after confirming no rollback needed.
 */

import { getAuthHeaders } from "./authHeaders";

export interface Generation {
  id: string;
  userId: string;
  projectId: string;
  prompt: string;
  modelId: string;
  provider: string;
  status: 'COMPLETED' | 'FAILED' | 'IN_PROGRESS' | 'HUMAN_REVIEW';
  jobId: string;
  files: Array<{
    name: string;
    language: string;
    content: string;
  }>;
  logs: Array<{
    stage: string;
    status: 'running' | 'success' | 'error' | 'retrying';
    message: string;
    timestamp: string;
  }>;
  stateHistory?: Array<{
    fromState: string;
    toState: string;
    timestamp: string;
    duration?: number;
    eventDescription: string;
  }>;
  createdAt: string;
  updatedAt: string;
  // LiteLLM gateway metadata
  modelUsed?: string;
  totalCost?: number;
  promptTokens?: number;
  completionTokens?: number;
  totalTokens?: number;
  cached?: boolean;
  latencyMs?: number;
  failoverFrom?: string;
  failoverTo?: string;
}

export interface GenerationListResponse {
  generations: Generation[];
  pagination?: {
    page: number;
    limit: number;
    totalItems: number;
    totalPages: number;
  };
}

export interface GenerationFilter {
  status?: 'COMPLETED' | 'FAILED' | 'IN_PROGRESS' | 'HUMAN_REVIEW';
  dateFrom?: string; // ISO 8601 string
  dateTo?: string; // ISO 8601 string
  modelId?: string;
  provider?: string;
  searchQuery?: string;
}

export interface GenerationRetryRequest {
  modelId?: string; // Optional override of model
}

export interface GenerationStateHistory {
  id: string;
  stateHistory: Array<{
    fromState: string;
    toState: string;
    timestamp: string;
    duration?: number;
    eventDescription: string;
  }>;
}

export interface GenerationEstimatedTimeRemaining {
  currentState: string;
  currentIteration?: number;
  maxIterations?: number;
  estimatedTimeRemaining: number; // in seconds
  confidenceInterval: {
    low: number;
    high: number;
  };
  historicalAverageForSimilarPrompt?: number; // in seconds, optional
}

export interface LLMCompletionResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: Array<{
    index: number;
    text: string;
    finish_reason: string | null;
  }>;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  model_used: string;
  total_cost: number;
  cached: boolean;
  latency_ms_ms?: number;
  failover_from?: string;
  failover_to?: string;
}

export const generationService = {
  async listGenerations(
    projectId: string, 
    filters?: GenerationFilter,
    page = 1,
    limit = 20
  ): Promise<GenerationListResponse> {
    const headers = getAuthHeaders();
    
    // Build query string from filters
    const queryParams = new URLSearchParams();
    if (page) queryParams.append('page', page.toString());
    if (limit) queryParams.append('limit', limit.toString());
    
    if (filters?.status) {
      queryParams.append('status', filters.status);
    }
    if (filters?.dateFrom) {
      queryParams.append('dateFrom', filters.dateFrom);
    }
    if (filters?.dateTo) {
      queryParams.append('dateTo', filters.dateTo);
    }
    if (filters?.modelId) {
      queryParams.append('modelId', filters.modelId);
    }
    if (filters?.provider) {
      queryParams.append('provider', filters.provider);
    }
    if (filters?.searchQuery) {
      queryParams.append('search', filters.searchQuery);
    }
    
    const queryString = queryParams.toString();
    const url = `/api/generations/${projectId}${queryString ? '?' + queryString : ''}`;
    
    const response = await fetch(url, { headers });
    if (!response.ok) throw new Error(`Failed to fetch generations: ${response.statusText}`);
    return response.json();
  },

  async createGeneration(projectId: string, generationData: {
    prompt: string;
    modelId: string;
    provider: string;
    jobId?: string;
  }): Promise<Generation> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/generations/${projectId}`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        ...generationData,
        projectId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to create generation: ${response.statusText}`);
    }

    const data = await response.json();
    return data.result;
  },

  async getGeneration(projectId: string, generationId: string): Promise<Generation> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/generations/${projectId}/${generationId}`, { headers });
    
    if (!response.ok) throw new Error(`Failed to fetch generation: ${response.statusText}`);
    return (await response.json()).result;
  },

  async updateGeneration(projectId: string, generationId: string, generationData: {
    prompt?: string;
    modelId?: string;
    provider?: string;
    status?: 'COMPLETED' | 'FAILED' | 'IN_PROGRESS' | 'HUMAN_REVIEW';
    files?: Array<{
      name: string;
      language: string;
      content: string;
    }>;
    logs?: Array<{
      stage: string;
      status: 'running' | 'success' | 'error' | 'retrying';
      message: string;
      timestamp: string;
    }>;
  }): Promise<Generation> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/generations/${projectId}/${generationId}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify({
        ...generationData,
        projectId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to update generation: ${response.statusText}`);
    }

    const data = await response.json();
    return data.result;
  },

  async deleteGeneration(projectId: string, generationId: string): Promise<void> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/generations/${projectId}/${generationId}`, {
      method: 'DELETE',
      headers,
    });

    if (!response.ok) {
      throw new Error(`Failed to delete generation: ${response.statusText}`);
    }
  },

  async retryGeneration(projectId: string, generationId: string, retryData?: GenerationRetryRequest): Promise<Generation> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/generations/${projectId}/${generationId}/retry`, {
      method: 'POST',
      headers,
      body: JSON.stringify(retryData || {}),
    });

    if (!response.ok) {
      throw new Error(`Failed to retry generation: ${response.statusText}`);
    }

    const data = await response.json();
    return data.result;
  },

  async getGenerationStateHistory(projectId: string, generationId: string): Promise<GenerationStateHistory> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/generations/${projectId}/${generationId}/state-history`, { headers });
    
    if (!response.ok) throw new Error(`Failed to fetch state history: ${response.statusText}`);
    return response.json();
  },

  async getGenerationEstimatedTimeRemaining(projectId: string, generationId: string): Promise<GenerationEstimatedTimeRemaining> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/generations/${projectId}/${generationId}/estimated-time-remaining`, { headers });
    
    if (!response.ok) throw new Error(`Failed to fetch estimated time: ${response.statusText}`);
    return response.json();
  },

  async exportGeneration(projectId: string, generationId: string): Promise<Blob> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/generations/${projectId}/${generationId}/export`, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      throw new Error(`Failed to export generation: ${response.statusText}`);
    }

    return response.blob();
  },

  async bulkDeleteGenerations(projectId: string, generationIds: string[]): Promise<void> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/generations/${projectId}/bulk-delete`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ generationIds }),
    });

    if (!response.ok) {
      throw new Error(`Failed to bulk delete generations: ${response.statusText}`);
    }
  },

  async bulkExportGenerations(projectId: string, generationIds: string[]): Promise<Blob> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/generations/${projectId}/bulk-export`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ generationIds }),
    });

    if (!response.ok) {
      throw new Error(`Failed to bulk export generations: ${response.statusText}`);
    }

    return response.blob();
  },
};

export default generationService;
