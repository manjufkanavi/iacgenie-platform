import { getAuthHeaders } from "./authHeaders";

export interface AuditLog {
  id: string;
  userId: string;
  projectId: string;
  actor: {
    name: string;
    email: string;
  };
  action: string;
  resource: string;
  details: Record<string, any>;
  ipAddress: string;
  timestamp: string;
}

export interface AuditLogListResponse {
  logs: AuditLog[];
  total: number;
}

export const auditLogService = {
  async listAuditLogs(projectId: string, limit: number = 100): Promise<AuditLog[]> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/audit-logs/${projectId}?limit=${limit}`, { headers });
    if (!response.ok) throw new Error(`Failed to fetch audit logs: ${response.statusText}`);
    return (await response.json()).logs;
  },

  async createAuditLog(projectId: string, logData: {
    action: string;
    resource: string;
    details?: Record<string, any>;
  }): Promise<AuditLog> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/audit-logs/${projectId}`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        ...logData,
        projectId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to create audit log: ${response.statusText}`);
    }

    const data = await response.json();
    return data.result;
  },

  async deleteAuditLog(projectId: string, logId: string): Promise<void> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/audit-logs/${projectId}/${logId}`, {
      method: 'DELETE',
      headers,
    });

    if (!response.ok) {
      throw new Error(`Failed to delete audit log: ${response.statusText}`);
    }
  },
}; 