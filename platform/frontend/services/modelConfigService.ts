import { getAuthHeaders } from "./authHeaders";
import { ModelConfig } from './db/adapters/IDatabaseAdapter';

export const modelConfigService = {
  async listModelConfigs(projectId: string): Promise<ModelConfig[]> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/model-configs/${projectId}`, { headers });
    if (!response.ok) throw new Error(`Failed to fetch model configs: ${response.statusText}`);
    const data = await response.json();
    const configs = data.configs || [];
    return configs.map((c: any) => ({
      ...c,
      projectId: c.project_id || c.projectId || projectId,
      model_name: c.model_name || c.model || '',
    }));
  },

  async createModelConfig(projectId: string, data: Omit<ModelConfig, 'id' | 'createdAt' | 'updatedAt'>): Promise<ModelConfig> {
    const headers = getAuthHeaders();
    const payload = {
      ...data,
      project_id: projectId,
      model_name: data.model_name || (data as any).model || '',
    };
    const response = await fetch(`/api/model-configs/${projectId}`, {
      method: 'POST',
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`Failed to create model config: ${response.statusText}`);
    const result = await response.json();
    return {
      ...result,
      projectId: result.project_id || result.projectId || projectId,
      model_name: result.model_name || result.model || '',
    };
  },

  async getModelConfig(projectId: string, configId: string): Promise<ModelConfig | null> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/model-configs/${projectId}/${configId}`, { headers });
    if (response.status === 404) return null;
    if (!response.ok) throw new Error(`Failed to fetch model config: ${response.statusText}`);
    const result = await response.json();
    return {
      ...result,
      projectId: result.project_id || result.projectId || projectId,
      model_name: result.model_name || result.model || '',
    };
  },

  async updateModelConfig(projectId: string, configId: string, data: Partial<ModelConfig>): Promise<ModelConfig> {
    const headers = getAuthHeaders();
    const payload = {
      ...data,
      project_id: projectId,
      model_name: data.model_name || (data as any).model,
    };
    const response = await fetch(`/api/model-configs/${projectId}/${configId}`, {
      method: 'PUT',
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`Failed to update model config: ${response.statusText}`);
    const result = await response.json();
    return {
      ...result,
      projectId: result.project_id || result.projectId || projectId,
      model_name: result.model_name || result.model || '',
    };
  },

  async deleteModelConfig(projectId: string, configId: string): Promise<void> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/model-configs/${projectId}/${configId}`, {
      method: 'DELETE',
      headers,
    });
    if (!response.ok) throw new Error(`Failed to delete model config: ${response.statusText}`);
  },
};