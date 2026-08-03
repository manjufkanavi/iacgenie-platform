/**
 * @deprecated Admin service deprecated. AdminDashboardPage removed per business decision.
 * This file is kept for reference and can be deleted after confirming no rollback needed.
 */

import { getAuthHeaders } from "./authHeaders";

export interface UserRecord {
  uid: string;
  email: string;
  name: string;
  role: string;
  isActive: boolean;
  status?: string; // 'invited', 'active', 'inactive'
  invited_at?: string;
  activated_at?: string;
  createdAt: string;
  lastLogin: string | null;
  projects: string[];
  assignedAt?: string; // Optional field for project members
}

export interface ProjectAdminRecord {
  id: string;
  name: string;
  description: string;
  ownerId: string;
  ownerEmail: string;
  memberCount: number;
  createdAt: string;
  updatedAt: string;
  status: string;
}

export interface SystemStats {
  totalUsers: number;
  totalProjects: number;
  totalGenerations: number;
  totalDeployments: number;
  activeUsersToday: number;
  activeProjectsToday: number;
}

export interface UserCreateRequest {
  email: string;
  name: string;
  role?: string;
  projectId?: string;
}

export interface UserUpdateRequest {
  name?: string;
  role?: string;
  isActive?: boolean;
}

export const adminService = {
  async listUsers(): Promise<UserRecord[]> {
    const headers = getAuthHeaders();
    console.log('[DEBUG] listUsers headers:', headers);
    const response = await fetch('/api/admin/users', { headers });
    console.log('[DEBUG] listUsers response status:', response.status);
    if (!response.ok) throw new Error(`Failed to fetch users: ${response.statusText}`);
    const data = await response.json();
    // Transform the response to match UserRecord interface
    return (data.users || []).map((user: any) => ({
      uid: user.id || user.uid,
      email: user.email,
      name: user.name,
      role: user.role,
      isActive: user.is_active || user.isActive,
      status: user.status || (user.is_active || user.isActive ? 'active' : 'inactive'),
      invited_at: user.invited_at || user.invitedAt,
      activated_at: user.activated_at || user.activatedAt,
      createdAt: user.createdAt || user.created_at,
      lastLogin: user.lastLogin || user.last_login,
      projects: user.projects || []
    }));
  },

  async createUser(userData: UserCreateRequest): Promise<UserRecord> {
    const headers = getAuthHeaders();
    const response = await fetch('/api/admin/users', {
      method: 'POST',
      headers,
      body: JSON.stringify(userData),
    });

    if (!response.ok) {
      throw new Error(`Failed to create user: ${response.statusText}`);
    }

    const data = await response.json();
    // Transform the response to match UserRecord interface
    return {
      uid: data.id || data.uid,
      email: data.email,
      name: data.name,
      role: data.role,
      isActive: data.is_active || data.isActive,
      createdAt: data.createdAt || data.created_at,
      lastLogin: data.lastLogin || data.last_login,
      projects: data.projects || []
    };
  },

  async updateUser(userUid: string, userData: UserUpdateRequest): Promise<UserRecord> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/admin/users/${userUid}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(userData),
    });

    if (!response.ok) {
      throw new Error(`Failed to update user: ${response.statusText}`);
    }

    const data = await response.json();
    // Transform the response to match UserRecord interface
    return {
      uid: data.id || data.uid,
      email: data.email,
      name: data.name,
      role: data.role,
      isActive: data.is_active || data.isActive,
      createdAt: data.createdAt || data.created_at,
      lastLogin: data.lastLogin || data.last_login,
      projects: data.projects || []
    };
  },

  async deleteUser(userUid: string): Promise<void> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/admin/users/${userUid}`, {
      method: 'DELETE',
      headers,
    });

    if (!response.ok) {
      throw new Error(`Failed to delete user: ${response.statusText}`);
    }
  },

  async listProjectsAdmin(): Promise<ProjectAdminRecord[]> {
    const headers = getAuthHeaders();
    const response = await fetch('/api/admin/projects', {
      headers,
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch projects: ${response.statusText}`);
    }

    const data = await response.json();
    // Transform the response to match ProjectAdminRecord interface
    return (data.projects || []).map((project: any) => ({
      id: project.id,
      name: project.name,
      description: project.description,
      ownerId: project.ownerId || project.owner_id,
      ownerEmail: project.ownerEmail || project.owner_email,
      memberCount: project.memberCount || project.member_count || 0,
      createdAt: project.createdAt || project.created_at,
      updatedAt: project.updatedAt || project.updated_at,
      status: project.status
    }));
  },

  async createProject(projectData: any): Promise<ProjectAdminRecord> {
    const headers = getAuthHeaders();
    const response = await fetch('/api/admin/projects', {
      method: 'POST',
      headers,
      body: JSON.stringify(projectData),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to create project: ${response.statusText}`);
    }
    const data = await response.json();
    // Transform the response to match ProjectAdminRecord interface
    return {
      id: data.id,
      name: data.name,
      description: data.description,
      ownerId: data.ownerId || data.owner_id,
      ownerEmail: data.ownerEmail || data.owner_email,
      memberCount: data.memberCount || data.member_count || 0,
      createdAt: data.createdAt || data.created_at,
      updatedAt: data.updatedAt || data.updated_at,
      status: data.status
    };
  },

  async updateProject(projectId: string, projectData: any): Promise<ProjectAdminRecord> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/admin/projects/${projectId}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(projectData),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to update project: ${response.statusText}`);
    }
    const data = await response.json();
    // Transform the response to match ProjectAdminRecord interface
    return {
      id: data.id,
      name: data.name,
      description: data.description,
      ownerId: data.ownerId || data.owner_id,
      ownerEmail: data.ownerEmail || data.owner_email,
      memberCount: data.memberCount || data.member_count || 0,
      createdAt: data.createdAt || data.created_at,
      updatedAt: data.updatedAt || data.updated_at,
      status: data.status
    };
  },

  async deleteProject(projectId: string): Promise<void> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/admin/projects/${projectId}`, {
      method: 'DELETE',
      headers,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to delete project: ${response.statusText}`);
    }
  },

  async assignUserToProject(projectId: string, userId: string): Promise<void> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/admin/projects/${projectId}/assign-user`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ user_id: userId }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to assign user: ${response.statusText}`);
    }
  },

  async unassignUserFromProject(projectId: string, userId: string): Promise<void> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/admin/projects/${projectId}/unassign-user`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ user_id: userId }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to unassign user: ${response.statusText}`);
    }
  },

  async getProjectMembers(projectId: string): Promise<UserRecord[]> {
    const headers = getAuthHeaders();
    const response = await fetch(`/api/admin/projects/${projectId}/members`, { headers });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to fetch project members: ${response.statusText}`);
    }
    const data = await response.json();
    // Transform the response to match UserRecord interface
    return (data.members || []).map((member: any) => ({
      uid: member.id || member.uid,
      email: member.email,
      name: member.name,
      role: member.role,
      isActive: member.is_active || member.isActive,
      createdAt: member.createdAt || member.created_at,
      lastLogin: member.lastLogin || member.last_login,
      projects: member.projects || [],
      assignedAt: member.assignedAt || member.assigned_at
    }));
  },

  async getSystemStats(): Promise<SystemStats> {
    const headers = getAuthHeaders();
    const response = await fetch('/api/admin/stats', {
      headers,
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch system stats: ${response.statusText}`);
    }

    const data = await response.json();
    // Transform the response to match SystemStats interface
    return {
      totalUsers: data.total_users || 0,
      totalProjects: data.total_projects || 0,
      totalGenerations: data.total_generations || 0,
      totalDeployments: data.total_deployments || 0,
      activeUsersToday: data.active_users_today || 0,
      activeProjectsToday: data.active_projects_today || 0
    };
  },

  async isAdmin(): Promise<boolean> {
    const headers = getAuthHeaders();
    console.log('[DEBUG] isAdmin headers:', headers);
    const response = await fetch('/api/admin/stats', { headers });
    console.log('[DEBUG] isAdmin response status:', response.status);
    return response.ok;
  },

  async inviteUser(userData: { email: string; name?: string; role?: string }): Promise<any> {
    try {
      console.log('[AdminService] Inviting user:', userData);
      
      const authHeaders = getAuthHeaders();
      const response = await fetch('/api/admin/invite-user', {
        method: 'POST',
        headers: {
          ...authHeaders,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: userData.email,
          name: userData.name || '',
          role: userData.role || 'user'
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('[AdminService] Invite user failed:', response.status, errorData);
        throw new Error(errorData.detail || `Failed to invite user: ${response.statusText}`);
      }

      const result = await response.json();
      console.log('[AdminService] User invitation successful:', result);
      
      return {
        success: true,
        message: result.message,
        user: result.user,
        invitationLink: result.invitation_link,
        emailSent: result.email_sent
      };
    } catch (error) {
      console.error('[AdminService] Error inviting user:', error);
      throw error;
    }
  }
}; 