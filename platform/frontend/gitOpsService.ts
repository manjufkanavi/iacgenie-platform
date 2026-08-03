import { getAuthHeaders } from "./authHeaders";

export interface WebhookTestResult {
  success: boolean;
  status_code?: number;
  response_time?: number;
  message: string;
  error?: string | null;
}

export interface GitOpsRunResponse {
  runId: string;
  repoConfigId: string;
  runType: 'plan' | 'apply';
  status: string;
  commitSha: string;
  branch: string;
  planDiff: string;
  applyDiff: string;
  triggeredBy: string;
  triggerMethod: string;
  errorMessage: string | null;
  startedAt: string | null;
  completedAt: string | null;
  createdAt: string;
}

export interface GitOpsRunQuery {
  repoConfigId: string;
  runType?: 'plan' | 'apply';
  limit?: number;
  offset?: number;
}

export interface ListRunsResponse {
  runs: GitOpsRunResponse[];
  total: number;
}

export const gitOpsService = {
  /**
   * List GitOps runs for a repository, with optional run_type filter.
   */
  async listRuns(
    repoConfigId: string,
    options?: { runType?: 'plan' | 'apply'; limit?: number; offset?: number },
  ): Promise<ListRunsResponse> {
    const headers = getAuthHeaders();
    const params = new URLSearchParams();
    if (options?.runType) params.set("run_type", options.runType);
    if (options?.limit) params.set("limit", String(options.limit));
    if (options?.offset) params.set("offset", String(options.offset));
    const queryString = params.toString();
    const url = queryString
      ? `/api/git/gitops/${repoConfigId}/runs?${queryString}`
      : `/api/git/gitops/${repoConfigId}/runs`;
    const response = await fetch(url, { headers });
    if (!response.ok) throw new Error(`Failed to fetch runs: ${response.statusText}`);
    const data = await response.json();
    return {
      runs: data.runs || [],
      total: data.total || 0,
    };
  },

  /**
   * Get a single GitOps run by ID.
   */
  async getRun(runId: string): Promise<GitOpsRunResponse | null> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/git/gitops/runs/${runId}`, { headers });
    if (response.status === 404) return null;
    if (!response.ok) throw new Error(`Failed to fetch run: ${response.statusText}`);
    const data = await response.json();
    return data;
  },

  /**
   * Trigger a Digger plan for a repository.
   */
  async triggerPlan(
    repoConfigId: string,
    options?: { commitSha?: string; branch?: string },
  ): Promise<GitOpsRunResponse> {
    const headers = getAuthHeaders();
    const payload: Record<string, string> = {
      session_id: `manual-${Date.now()}`,
      trigger_method: "manual",
    };
    if (options?.commitSha) payload.commit_sha = options.commitSha;
    if (options?.branch) payload.branch = options.branch;
    const response = await fetch(`/api/git/gitops/${repoConfigId}/plan`, {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`Failed to trigger plan: ${response.statusText}`);
    const data = await response.json();
    return data;
  },

  /**
   * Trigger a Digger apply for a repository.
   */
  async triggerApply(
    repoConfigId: string,
    options?: { commitSha?: string; branch?: string },
  ): Promise<GitOpsRunResponse> {
    const headers = getAuthHeaders();
    const payload: Record<string, string> = {
      session_id: `manual-${Date.now()}`,
      trigger_method: "manual",
    };
    if (options?.commitSha) payload.commit_sha = options.commitSha;
    if (options?.branch) payload.branch = options.branch;
    const response = await fetch(`/api/git/gitops/${repoConfigId}/apply`, {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`Failed to trigger apply: ${response.statusText}`);
    const data = await response.json();
    return data;
  },

  /**
   * Cancel a running GitOps run.
   */
  async cancelRun(runId: string): Promise<GitOpsRunResponse> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/git/gitops/runs/${runId}`, {
      method: "DELETE",
      headers,
    });
    if (!response.ok) throw new Error(`Failed to cancel run: ${response.statusText}`);
    const data = await response.json();
    return data;
  },

  /**
   * Test a webhook URL by firing a test payload.
   */
  async testWebhookUrl(url: string, secret: string): Promise<WebhookTestResult> {
    const headers = getAuthHeaders();
    const response = await fetch("/api/git/gitops/webhooks/test-url", {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url, secret }),
    });
    if (!response.ok) throw new Error(`Failed to test webhook URL: ${response.statusText}`);
    const data = await response.json();
    return {
      success: data.success,
      status_code: data.status_code,
      response_time: data.response_time,
      message: data.message,
      error: data.error || null,
    };
  },
};
