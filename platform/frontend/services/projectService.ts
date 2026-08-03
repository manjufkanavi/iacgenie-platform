import { getAuthHeaders, retryWithFreshToken } from "./authHeaders";
import { Project } from './db/adapters/IDatabaseAdapter';

export const projectService = {
  async listProjects(): Promise<Project[]> {
    const headers = getAuthHeaders();
    const response = await retryWithFreshToken(`/api/projects`, { headers }, () => getAuthHeaders());
    if (!response.ok) throw new Error(`Failed to fetch projects: ${response.statusText}`);
    const data = await response.json();
    return data.projects || [];
  },

  async createProject(data: { name: string; description?: string }): Promise<Project> {
    const headers = getAuthHeaders();
    const response = await retryWithFreshToken(
      `/api/projects`,
      {
        method: 'POST',
        headers: {
          ...headers,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      },
      () => getAuthHeaders()
    );
    if (!response.ok) throw new Error(`Failed to create project: ${response.statusText}`);
    const result = await response.json();
    return result.project;
  },

  async getProject(id: string): Promise<Project> {
    const headers = getAuthHeaders();
    const response = await retryWithFreshToken(`/api/projects/${id}`, { headers }, () => getAuthHeaders());
    if (!response.ok) throw new Error(`Failed to fetch project: ${response.statusText}`);
    const result = await response.json();
    return result.project;
  },

  async updateProject(id: string, data: Partial<Project>): Promise<Project> {
    const headers = getAuthHeaders();
    const response = await retryWithFreshToken(
      `/api/projects/${id}`,
      {
        method: 'PUT',
        headers: {
          ...headers,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      },
      () => getAuthHeaders()
    );
    if (!response.ok) throw new Error(`Failed to update project: ${response.statusText}`);
    const result = await response.json();
    return result.project;
  },

  async deleteProject(id: string): Promise<void> {
    const headers = getAuthHeaders();
    const response = await retryWithFreshToken(`/api/projects/${id}`, { headers }, () => getAuthHeaders());
    if (!response.ok) throw new Error(`Failed to delete project: ${response.statusText}`);
  },
};
