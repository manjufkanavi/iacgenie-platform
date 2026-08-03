import { getAuthHeaders } from "./authHeaders";

export interface WebhookRecord {
  id: string;
  projectId: string;
  name: string;
  url: string;
  events: string[];
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
  lastTriggered: string | null;
  successCount: number;
  failureCount: number;
}

export interface WebhookCreateRequest {
  name: string;
  url: string;
  events?: string[];
  secret?: string;
  isActive?: boolean;
}

export interface WebhookUpdateRequest {
  name?: string;
  url?: string;
  events?: string[];
  secret?: string;
  isActive?: boolean;
}

export interface WebhookTestRequest {
  eventType: string;
  payload?: Record<string, any>;
}

export interface WebhookTestResponse {
  success: boolean;
  statusCode: number;
  responseBody: string;
  webhookUrl: string;
}

export const webhookService = {
  async listWebhooks(projectId: string): Promise<WebhookRecord[]> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/webhooks/${projectId}`, { headers });
    if (!response.ok) throw new Error(`Failed to fetch webhooks: ${response.statusText}`);
    return (await response.json()).webhooks;
  },

  async createWebhook(projectId: string, webhookData: WebhookCreateRequest): Promise<WebhookRecord> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/webhooks/${projectId}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(webhookData),
    });

    if (!response.ok) {
      throw new Error(`Failed to create webhook: ${response.statusText}`);
    }

    const data = await response.json();
    return data.result;
  },

  async updateWebhook(projectId: string, webhookId: string, webhookData: WebhookUpdateRequest): Promise<WebhookRecord> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/webhooks/${projectId}/${webhookId}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(webhookData),
    });

    if (!response.ok) {
      throw new Error(`Failed to update webhook: ${response.statusText}`);
    }

    const data = await response.json();
    return data.result;
  },

  async deleteWebhook(projectId: string, webhookId: string): Promise<void> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/webhooks/${projectId}/${webhookId}`, {
      method: 'DELETE',
      headers,
    });

    if (!response.ok) {
      throw new Error(`Failed to delete webhook: ${response.statusText}`);
    }
  },

  async testWebhook(projectId: string, webhookId: string, testData: WebhookTestRequest): Promise<WebhookTestResponse> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/webhooks/${projectId}/${webhookId}/test`, {
      method: 'POST',
      headers,
      body: JSON.stringify(testData),
    });

    if (!response.ok) {
      throw new Error(`Failed to test webhook: ${response.statusText}`);
    }

    const data = await response.json();
    return data.result;
  }
}; 