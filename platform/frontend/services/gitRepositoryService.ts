import { getAuthHeaders } from "./authHeaders";
import { GitRepository } from './db/adapters/IDatabaseAdapter';

export const gitRepositoryService = {
  async listGitRepositories(projectId: string): Promise<GitRepository[]> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/git-repositories/${projectId}`, { headers });
    if (!response.ok) throw new Error(`Failed to fetch git repositories: ${response.statusText}`);
    const data = await response.json();
    const repositories = data.repositories || [];
    return repositories.map((r: any) => ({
      ...r,
      projectId: r.project_id || r.projectId || projectId,
      repo_url: r.url || r.repo_url || '',
      access_token: r.token_encrypted || r.access_token || '',
    }));
  },

  async createGitRepository(projectId: string, data: Omit<GitRepository, 'id' | 'createdAt' | 'updatedAt'>): Promise<GitRepository> {
    const headers = getAuthHeaders();
    const payload = {
      ...data,
      project_id: projectId,
      url: data.repo_url || (data as any).url || '',
      token: data.access_token || (data as any).token || '',
    };
    const response = await fetch(`/api/git-repositories/${projectId}`, {
      method: 'POST',
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`Failed to create git repository: ${response.statusText}`);
    const result = await response.json();
    return {
      ...result,
      projectId: result.project_id || result.projectId || projectId,
      repo_url: result.url || result.repo_url || '',
      access_token: result.token_encrypted || result.access_token || '',
    };
  },

  async getGitRepository(projectId: string, repoId: string): Promise<GitRepository | null> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/git-repositories/${projectId}/${repoId}`, { headers });
    if (response.status === 404) return null;
    if (!response.ok) throw new Error(`Failed to fetch git repository: ${response.statusText}`);
    const result = await response.json();
    return {
      ...result,
      projectId: result.project_id || result.projectId || projectId,
      repo_url: result.url || result.repo_url || '',
      access_token: result.token_encrypted || result.access_token || '',
    };
  },

  async updateGitRepository(projectId: string, repoId: string, data: Partial<GitRepository>): Promise<GitRepository> {
    const headers = getAuthHeaders();
    const payload = {
      ...data,
      project_id: projectId,
      url: data.repo_url || (data as any).url,
      token: data.access_token || (data as any).token,
    };
    const response = await fetch(`/api/git-repositories/${projectId}/${repoId}`, {
      method: 'PUT',
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`Failed to update git repository: ${response.statusText}`);
    const result = await response.json();
    return {
      ...result,
      projectId: result.project_id || result.projectId || projectId,
      repo_url: result.url || result.repo_url || '',
      access_token: result.token_encrypted || result.access_token || '',
    };
  },

  async deleteGitRepository(projectId: string, repoId: string): Promise<void> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/git-repositories/${projectId}/${repoId}`, {
      method: 'DELETE',
      headers,
    });
    if (!response.ok) throw new Error(`Failed to delete git repository: ${response.statusText}`);
  },
};