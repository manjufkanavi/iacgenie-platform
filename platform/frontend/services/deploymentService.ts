import { getAuthHeaders } from "./authHeaders";
import { Deployment, DeploymentLog, DeploymentStatus, CloudProvider, OutputType } from './types';

export interface DeploymentRecord {
  id: string;
  userId: string;
  projectId: string;
  generationId: string;
  provider: string;
  region: string;
  credentialsId: string;
  status: string;
  logs: Array<{
    stage: string;
    status: string;
    message: string;
    timestamp: string;
  }>;
  outputs: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

export interface DeploymentListResponse {
  deployments: DeploymentRecord[];
  total: number;
}

// Mock data for backward compatibility
const MOCK_DEPLOYMENTS: Deployment[] = [
  {
    id: 'dep_1',
    projectName: 'Production EKS Cluster',
    provider: CloudProvider.AWS,
    type: OutputType.OPENTOFU,
    status: 'Success',
    timestamp: '2 hours ago',
    createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
  },
  {
    id: 'dep_2',
    projectName: 'Staging VPC',
    provider: CloudProvider.AWS,
    type: OutputType.OPENTOFU,
    status: 'Running',
    timestamp: '5 hours ago',
    createdAt: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString()
  },
  {
    id: 'dep_3',
    projectName: 'Dev Environment',
    provider: CloudProvider.GCP,
    type: OutputType.OPENTOFU,
    status: 'Failed',
    timestamp: '1 day ago',
    createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
  }
];

export const deploymentService = {
  async listDeployments(projectId: string): Promise<DeploymentRecord[]> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/deployments/${projectId}`, { headers });
    if (!response.ok) throw new Error(`Failed to fetch deployments: ${response.statusText}`);
    return (await response.json()).deployments;
  },

  async createDeployment(projectId: string, deploymentData: {
    generationId: string;
    provider: string;
    region: string;
    credentialsId: string;
  }): Promise<DeploymentRecord> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/deployments/${projectId}`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        ...deploymentData,
        projectId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to create deployment: ${response.statusText}`);
    }

    const data = await response.json();
    return data.result;
  },

  async updateDeployment(projectId: string, deploymentId: string, deploymentData: {
    generationId: string;
    provider: string;
    region: string;
    credentialsId: string;
    status?: string;
    logs?: Array<{
      stage: string;
      status: string;
      message: string;
      timestamp: string;
    }>;
    outputs?: Record<string, any>;
  }): Promise<DeploymentRecord> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/deployments/${projectId}/${deploymentId}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify({
        ...deploymentData,
        projectId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to update deployment: ${response.statusText}`);
    }

    const data = await response.json();
    return data.result;
  },

  async deleteDeployment(projectId: string, deploymentId: string): Promise<void> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/deployments/${projectId}/${deploymentId}`, {
      method: 'DELETE',
      headers,
    });

    if (!response.ok) {
      throw new Error(`Failed to delete deployment: ${response.statusText}`);
    }
  },

  // Legacy methods for backward compatibility
  async getDeployments(): Promise<Deployment[]> {
    // For now, return mock data until we migrate all components
    return Promise.resolve(MOCK_DEPLOYMENTS);
  },

  async getDeploymentLogs(_status: DeploymentStatus): Promise<DeploymentLog> {
    // Mock deployment logs
    const mockLogs: DeploymentLog = {
      plan: 'OpenTofu plan output...',
      apply: 'OpenTofu apply output...',
      output: 'OpenTofu output...'
    };

    return Promise.resolve(mockLogs);
  }
};