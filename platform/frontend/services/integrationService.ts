import { getAuthHeaders } from "./authHeaders";
import { Integration } from './db/adapters/IDatabaseAdapter';

export const integrationService = {
  async listIntegrations(projectId: string): Promise<Integration[]> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/integrations/${projectId}`, { headers });
    if (!response.ok) throw new Error(`Failed to fetch integrations: ${response.statusText}`);
    const data = await response.json();
    const integrations = data.integrations || [];
    return integrations.map((i: any) => ({
      ...i,
      projectId: i.project_id || i.projectId || projectId,
    }));
  },

  async createIntegration(projectId: string, data: Omit<Integration, 'id' | 'createdAt' | 'updatedAt'>): Promise<Integration> {
    const headers = getAuthHeaders();
    const payload = {
      ...data,
      project_id: projectId,
    };
    const response = await fetch(`/api/integrations/${projectId}`, {
      method: 'POST',
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`Failed to create integration: ${response.statusText}`);
    const result = await response.json();
    return {
      ...result,
      projectId: result.project_id || result.projectId || projectId,
    };
  },

  async getIntegration(projectId: string, integrationId: string): Promise<Integration | null> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/integrations/${projectId}/${integrationId}`, { headers });
    if (response.status === 404) return null;
    if (!response.ok) throw new Error(`Failed to fetch integration: ${response.statusText}`);
    const result = await response.json();
    return {
      ...result,
      projectId: result.project_id || result.projectId || projectId,
    };
  },

  async updateIntegration(projectId: string, integrationId: string, data: Partial<Integration>): Promise<Integration> {
    const headers = getAuthHeaders();
    const payload = {
      ...data,
      project_id: projectId,
    };
    const response = await fetch(`/api/integrations/${projectId}/${integrationId}`, {
      method: 'PUT',
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`Failed to update integration: ${response.statusText}`);
    const result = await response.json();
    return {
      ...result,
      projectId: result.project_id || result.projectId || projectId,
    };
  },

  async deleteIntegration(projectId: string, integrationId: string): Promise<void> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/integrations/${projectId}/${integrationId}`, {
      method: 'DELETE',
      headers,
    });
    if (!response.ok) throw new Error(`Failed to delete integration: ${response.statusText}`);
  },
};