import { getAuthHeaders } from "./authHeaders";
import { TeamMember } from './db/adapters/IDatabaseAdapter';

export const teamMemberService = {
  async listTeamMembers(projectId: string): Promise<TeamMember[]> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/team-members/${projectId}`, { headers });
    if (!response.ok) throw new Error(`Failed to fetch team members: ${response.statusText}`);
    const data = await response.json();
    const members = data.members || [];
    return members.map((m: any) => ({
      ...m,
      projectId: m.project_id || m.projectId || projectId,
    }));
  },

  async inviteTeamMember(projectId: string, data: { email: string; role: string }): Promise<TeamMember> {
    const headers = getAuthHeaders();
    const payload = {
      ...data,
      project_id: projectId,
    };
    const response = await fetch(`/api/team-members/${projectId}`, {
      method: 'POST',
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`Failed to invite team member: ${response.statusText}`);
    const result = await response.json();
    return {
      ...result,
      projectId: result.project_id || result.projectId || projectId,
    };
  },

  async getTeamMember(projectId: string, memberId: string): Promise<TeamMember | null> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/team-members/${projectId}/${memberId}`, { headers });
    if (response.status === 404) return null;
    if (!response.ok) throw new Error(`Failed to fetch team member: ${response.statusText}`);
    const result = await response.json();
    return {
      ...result,
      projectId: result.project_id || result.projectId || projectId,
    };
  },

  async updateTeamMember(projectId: string, memberId: string, data: Partial<TeamMember>): Promise<TeamMember> {
    const headers = getAuthHeaders();
    const payload = {
      ...data,
      project_id: projectId,
    };
    const response = await fetch(`/api/team-members/${projectId}/${memberId}`, {
      method: 'PUT',
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`Failed to update team member: ${response.statusText}`);
    const result = await response.json();
    return {
      ...result,
      projectId: result.project_id || result.projectId || projectId,
    };
  },

  async removeTeamMember(projectId: string, memberId: string): Promise<void> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/team-members/${projectId}/${memberId}`, {
      method: 'DELETE',
      headers,
    });
    if (!response.ok) throw new Error(`Failed to remove team member: ${response.statusText}`);
  },
};