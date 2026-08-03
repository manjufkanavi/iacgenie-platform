import { getAuthHeaders } from "./authHeaders";

export interface ApiKeyRecord {
  id: string;
  userId: string;
  projectId: string;
  name: string;
  tokenPreview: string;
  createdAt: string;
  lastUsed: string | null;
  isActive: boolean;
}

export interface ApiKeyCreateRequest {
  name: string;
  permissions?: string[];
}

export interface ApiKeyCreateResponse {
  id: string;
  name: string;
  token: string;
  tokenPreview: string;
  createdAt: string;
}

export const apiKeyService = {
  async listApiKeys(projectId: string): Promise<ApiKeyRecord[]> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/api-keys/${projectId}`, { headers });
    if (!response.ok) throw new Error(`Failed to fetch API keys: ${response.statusText}`);
    return (await response.json()).keys;
  },

  async createApiKey(projectId: string, keyData: ApiKeyCreateRequest): Promise<ApiKeyCreateResponse> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/api-keys/${projectId}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(keyData),
    });

    if (!response.ok) {
      throw new Error(`Failed to create API key: ${response.statusText}`);
    }

    const data = await response.json();
    return data.result;
  },

  async revokeApiKey(projectId: string, keyId: string): Promise<void> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/api-keys/${projectId}/${keyId}`, {
      method: 'DELETE',
      headers,
    });

    if (!response.ok) {
      throw new Error(`Failed to revoke API key: ${response.statusText}`);
    }
  },

  async updateApiKey(projectId: string, keyId: string, keyData: Partial<ApiKeyCreateRequest>): Promise<ApiKeyRecord> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/api-keys/${projectId}/${keyId}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(keyData),
    });

    if (!response.ok) {
      throw new Error(`Failed to update API key: ${response.statusText}`);
    }

    const data = await response.json();
    return data.result;
  }
}; 