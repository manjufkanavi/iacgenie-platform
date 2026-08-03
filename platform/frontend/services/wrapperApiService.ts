/**
 * Wrapper API Service
 * Handles all API calls through the wrapper endpoints using /token authentication
 */

import { getAuthHeaders } from "./authHeaders";

export interface WrapperApiResponse<T = any> {
  success: boolean;
  message: string;
  data: T;
  timestamp: string;
}

export interface WrapperApiError {
  success: false;
  error: {
    message: string;
    code: string;
    statusCode: number;
    details?: any;
    timestamp: string;
  };
}

class WrapperApiService {
  private baseUrl = "";

  constructor(baseUrl = "") {
    this.baseUrl = baseUrl;
  }



  private async makeRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = getAuthHeaders();
    const response = await fetch(`${this.baseUrl}/api${endpoint}`, {
      ...options,
      headers: { ...headers, ...options.headers },
    });
    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('iacgenie_token');
        localStorage.removeItem('iacgenie_user');
        throw new Error('Authentication required. Please sign in again.');
      }
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return await response.json();
  }

  // Project Management
  async getProjects(): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>('/projects');
  }

  async getProject(projectId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/projects/${projectId}`);
  }

  async createProject(projectData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>('/projects', {
      method: 'POST',
      body: JSON.stringify(projectData),
    });
  }

  async updateProject(projectId: string, projectData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/projects/${projectId}`, {
      method: 'PUT',
      body: JSON.stringify(projectData),
    });
  }

  async deleteProject(projectId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/projects/${projectId}`, {
      method: 'DELETE',
    });
  }

  // Generation Management
  async getGenerations(projectId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/generations/${projectId}`);
  }

  async createGeneration(generationData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>('/generations', {
      method: 'POST',
      body: JSON.stringify(generationData),
    });
  }

  async getGeneration(generationId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/generations/${generationId}`);
  }

  async updateGeneration(generationId: string, generationData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/generations/${generationId}`, {
      method: 'PUT',
      body: JSON.stringify(generationData),
    });
  }

  async deleteGeneration(generationId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/generations/${generationId}`, {
      method: 'DELETE',
    });
  }

  // Model Configuration Management
  async getModelConfigs(projectId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/model-configs/${projectId}`);
  }

  async createModelConfig(modelConfigData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>('/model-configs', {
      method: 'POST',
      body: JSON.stringify(modelConfigData),
    });
  }

  async updateModelConfig(configId: string, modelConfigData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/model-configs/${configId}`, {
      method: 'PUT',
      body: JSON.stringify(modelConfigData),
    });
  }

  async deleteModelConfig(configId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/model-configs/${configId}`, {
      method: 'DELETE',
    });
  }

  // API Key Management
  async getApiKeys(projectId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/api-keys/${projectId}`);
  }

  async createApiKey(apiKeyData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>('/api-keys', {
      method: 'POST',
      body: JSON.stringify(apiKeyData),
    });
  }

  async revokeApiKey(keyId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/api-keys/${keyId}`, {
      method: 'DELETE',
    });
  }

  // Team Member Management
  async getTeamMembers(projectId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/team-members/${projectId}`);
  }

  async createTeamMember(teamMemberData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>('/team-members', {
      method: 'POST',
      body: JSON.stringify(teamMemberData),
    });
  }

  async updateTeamMember(memberId: string, teamMemberData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/team-members/${memberId}`, {
      method: 'PUT',
      body: JSON.stringify(teamMemberData),
    });
  }

  async removeTeamMember(memberId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/team-members/${memberId}`, {
      method: 'DELETE',
    });
  }

  // Webhook Management
  async getWebhooks(projectId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/webhooks/${projectId}`);
  }

  async createWebhook(webhookData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>('/webhooks', {
      method: 'POST',
      body: JSON.stringify(webhookData),
    });
  }

  async updateWebhook(webhookId: string, webhookData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/webhooks/${webhookId}`, {
      method: 'PUT',
      body: JSON.stringify(webhookData),
    });
  }

  async deleteWebhook(webhookId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/webhooks/${webhookId}`, {
      method: 'DELETE',
    });
  }

  // Integration Management
  async getIntegrations(projectId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/integrations/${projectId}`);
  }

  async createIntegration(integrationData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>('/integrations', {
      method: 'POST',
      body: JSON.stringify(integrationData),
    });
  }

  async updateIntegration(integrationId: string, integrationData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/integrations/${integrationId}`, {
      method: 'PUT',
      body: JSON.stringify(integrationData),
    });
  }

  async deleteIntegration(integrationId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/integrations/${integrationId}`, {
      method: 'DELETE',
    });
  }

  // Cloud Credentials Management
  async getCloudCredentials(projectId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/cloud-credentials/${projectId}`);
  }

  async createCloudCredentials(credentialsData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>('/cloud-credentials', {
      method: 'POST',
      body: JSON.stringify(credentialsData),
    });
  }

  async updateCloudCredentials(credentialId: string, credentialsData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/cloud-credentials/${credentialId}`, {
      method: 'PUT',
      body: JSON.stringify(credentialsData),
    });
  }

  async deleteCloudCredentials(credentialId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/cloud-credentials/${credentialId}`, {
      method: 'DELETE',
    });
  }

  // Git Repository Management
  async getGitRepositories(projectId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/git-repositories/${projectId}`);
  }

  async createGitRepository(repoData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>('/git-repositories', {
      method: 'POST',
      body: JSON.stringify(repoData),
    });
  }

  async updateGitRepository(repoId: string, repoData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/git-repositories/${repoId}`, {
      method: 'PUT',
      body: JSON.stringify(repoData),
    });
  }

  async deleteGitRepository(repoId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/git-repositories/${repoId}`, {
      method: 'DELETE',
    });
  }

  // Deployment Management
  async getDeployments(projectId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/deployments/${projectId}`);
  }

  async createDeployment(deploymentData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>('/deployments', {
      method: 'POST',
      body: JSON.stringify(deploymentData),
    });
  }

  async getDeployment(deploymentId: string): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>(`/deployments/${deploymentId}`);
  }

  // Audit Logs
  async getAuditLogs(projectId: string, filters?: any): Promise<WrapperApiResponse> {
    const queryParams = filters ? `?${new URLSearchParams(filters).toString()}` : '';
    return this.makeRequest<WrapperApiResponse>(`/audit-logs/${projectId}${queryParams}`);
  }

  // Billing Management
  async getBillingInfo(): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>('/billing');
  }

  async getInvoices(): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>('/billing/invoices');
  }

  async updateBillingInfo(billingData: any): Promise<WrapperApiResponse> {
    return this.makeRequest<WrapperApiResponse>('/billing', {
      method: 'PUT',
      body: JSON.stringify(billingData),
    });
  }
}

// Export singleton instance
export const wrapperApiService = new WrapperApiService();

// Export individual methods for convenience
export const {
  getProjects,
  getProject,
  createProject,
  updateProject,
  deleteProject,
  getGenerations,
  createGeneration,
  getGeneration,
  updateGeneration,
  deleteGeneration,
  getModelConfigs,
  createModelConfig,
  updateModelConfig,
  deleteModelConfig,
  getApiKeys,
  createApiKey,
  revokeApiKey,
  getTeamMembers,
  createTeamMember,
  updateTeamMember,
  removeTeamMember,
  getWebhooks,
  createWebhook,
  updateWebhook,
  deleteWebhook,
  getIntegrations,
  createIntegration,
  updateIntegration,
  deleteIntegration,
  getCloudCredentials,
  createCloudCredentials,
  updateCloudCredentials,
  deleteCloudCredentials,
  getGitRepositories,
  createGitRepository,
  updateGitRepository,
  deleteGitRepository,
  getDeployments,
  createDeployment,
  getDeployment,
  getAuditLogs,
  getBillingInfo,
  getInvoices,
  updateBillingInfo,
} = wrapperApiService; 