import { getAuthHeaders } from "./authHeaders";
import { CloudCredential } from './db/adapters/IDatabaseAdapter';

export const cloudCredentialService = {
  async listCloudCredentials(projectId: string): Promise<CloudCredential[]> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/cloud-credentials/${projectId}`, { headers });
    if (!response.ok) throw new Error(`Failed to fetch cloud credentials: ${response.statusText}`);
    const data = await response.json();
    const credentials = data.credentials || [];
    return credentials.map((c: any) => ({
      ...c,
      projectId: c.project_id || c.projectId || projectId,
    }));
  },

  async createCloudCredential(projectId: string, data: Omit<CloudCredential, 'id' | 'createdAt' | 'updatedAt'>): Promise<CloudCredential> {
    const headers = getAuthHeaders();
    const payload = {
      ...data,
      project_id: projectId,
    };
    const response = await fetch(`/api/cloud-credentials/${projectId}`, {
      method: 'POST',
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`Failed to create cloud credentials: ${response.statusText}`);
    const result = await response.json();
    return {
      ...result,
      projectId: result.project_id || result.projectId || projectId,
    };
  },

  async getCloudCredential(projectId: string, credId: string): Promise<CloudCredential | null> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/cloud-credentials/${projectId}/${credId}`, { headers });
    if (response.status === 404) return null;
    if (!response.ok) throw new Error(`Failed to fetch cloud credential: ${response.statusText}`);
    const result = await response.json();
    return {
      ...result,
      projectId: result.project_id || result.projectId || projectId,
    };
  },

  async updateCloudCredential(projectId: string, credId: string, data: Partial<CloudCredential>): Promise<CloudCredential> {
    const headers = getAuthHeaders();
    const payload = {
      ...data,
      project_id: projectId,
    };
    const response = await fetch(`/api/cloud-credentials/${projectId}/${credId}`, {
      method: 'PUT',
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`Failed to update cloud credential: ${response.statusText}`);
    const result = await response.json();
    return {
      ...result,
      projectId: result.project_id || result.projectId || projectId,
    };
  },

  async deleteCloudCredential(projectId: string, credId: string): Promise<void> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/cloud-credentials/${projectId}/${credId}`, {
      method: 'DELETE',
      headers,
    });
    if (!response.ok) throw new Error(`Failed to delete cloud credential: ${response.statusText}`);
  },

  async testCredential(projectId: string, credId: string): Promise<{ success: boolean; message: string }> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/cloud-credentials/${projectId}/${credId}/test`, {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (!response.ok) throw new Error(`Credential test failed: ${response.statusText}`);
    return response.json();
  },
};