import { getAuthHeaders } from "./authHeaders";

export interface BillingInfo {
  id: string;
  userId: string;
  projectId: string;
  plan: string;
  usage: {
    generations: { current: number; limit: number };
    deployments: { current: number; limit: number };
    api_calls: { current: number; limit: number };
  };
  cost: number;
  invoiceHistory: Array<{
    id: string;
    date: string;
    amount: number;
    status: string;
    description: string;
  }>;
  createdAt: string;
  updatedAt: string;
}

export const billingService = {
  async getBillingInfo(projectId: string): Promise<BillingInfo> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/billing/${projectId}`, { headers });
    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('iacgenie_token');
        localStorage.removeItem('iacgenie_user');
        throw new Error('Authentication required. Please sign in again.');
      }
      throw new Error(`Failed to fetch billing info: ${response.statusText}`);
    }
    return await response.json();
  },

  async updateUsage(projectId: string, usageData: {
    type: 'generations' | 'deployments' | 'api_calls';
    count: number;
    cost: number;
  }): Promise<BillingInfo> {
    try {
      const headers = getAuthHeaders();
      const response = await fetch(`/api/billing/${projectId}/usage`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          ...usageData,
          projectId,
        }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          // Clear invalid token
          localStorage.removeItem('iacgenie_token');
          localStorage.removeItem('iacgenie_user');
          throw new Error('Authentication required. Please sign in again.');
        }
        throw new Error(`Failed to update usage: ${response.statusText}`);
      }

      const data = await response.json();
      return data.result;
    } catch (error) {
      console.error('Failed to update usage:', error);
      throw error;
    }
  },

  async createInvoice(projectId: string, invoiceData: {
    amount: number;
    status?: string;
    description?: string;
  }): Promise<BillingInfo> {
    try {
      const headers = getAuthHeaders();
      const response = await fetch(`/api/billing/${projectId}/invoice`, {
        method: 'POST',
        headers,
        body: JSON.stringify(invoiceData),
      });

      if (!response.ok) {
        if (response.status === 401) {
          // Clear invalid token
          localStorage.removeItem('iacgenie_token');
          localStorage.removeItem('iacgenie_user');
          throw new Error('Authentication required. Please sign in again.');
        }
        throw new Error(`Failed to create invoice: ${response.statusText}`);
      }

      const data = await response.json();
      return data.result;
    } catch (error) {
      console.error('Failed to create invoice:', error);
      throw error;
    }
  },
}; 