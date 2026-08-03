export interface Project {
  id: string;
  name: string;
  description: string;
  created_at?: string;
  updated_at?: string;
}

export interface ModelConfig {
  id: string;
  projectId: string;
  provider: string;
  model_name: string;
  base_url: string;
  api_key: string;
  max_tokens: number;
  temperature: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface GitRepository {
  id: string;
  projectId: string;
  provider: string;
  repo_url: string;
  branch: string;
  access_token: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface CloudCredential {
  id: string;
  projectId: string;
  provider: string;
  credentials: Record<string, any>;
  createdAt?: string;
  updatedAt?: string;
}

export interface TeamMember {
  id: string;
  projectId: string;
  email: string;
  role: string;
  invitedAt?: string;
  joinedAt?: string;
}

export interface Integration {
  id: string;
  projectId: string;
  type: string;
  config: Record<string, any>;
  createdAt?: string;
  updatedAt?: string;
}

export interface IDatabaseAdapter {
  // Project CRUD
  listProjects(userId: string): Promise<Project[]>;
  createProject(userId: string, data: { name: string; description?: string }): Promise<Project>;
  getProject(userId: string, projectId: string): Promise<Project | null>;
  updateProject(userId: string, projectId: string, data: { name: string; description?: string }): Promise<Project>;
  deleteProject(userId: string, projectId: string): Promise<void>;

  // Model Configs CRUD
  listModelConfigs(projectId: string): Promise<ModelConfig[]>;
  createModelConfig(projectId: string, data: Omit<ModelConfig, 'id' | 'createdAt' | 'updatedAt'>): Promise<ModelConfig>;
  getModelConfig(projectId: string, configId: string): Promise<ModelConfig | null>;
  updateModelConfig(projectId: string, configId: string, data: Partial<ModelConfig>): Promise<ModelConfig>;
  deleteModelConfig(projectId: string, configId: string): Promise<void>;

  // Git Repositories CRUD
  listGitRepositories(projectId: string): Promise<GitRepository[]>;
  createGitRepository(projectId: string, data: Omit<GitRepository, 'id' | 'createdAt' | 'updatedAt'>): Promise<GitRepository>;
  getGitRepository(projectId: string, repoId: string): Promise<GitRepository | null>;
  updateGitRepository(projectId: string, repoId: string, data: Partial<GitRepository>): Promise<GitRepository>;
  deleteGitRepository(projectId: string, repoId: string): Promise<void>;

  // Cloud Credentials CRUD
  listCloudCredentials(projectId: string): Promise<CloudCredential[]>;
  createCloudCredential(projectId: string, data: Omit<CloudCredential, 'id' | 'createdAt' | 'updatedAt'>): Promise<CloudCredential>;
  getCloudCredential(projectId: string, credId: string): Promise<CloudCredential | null>;
  updateCloudCredential(projectId: string, credId: string, data: Partial<CloudCredential>): Promise<CloudCredential>;
  deleteCloudCredential(projectId: string, credId: string): Promise<void>;

  // Team Members CRUD
  listTeamMembers(projectId: string): Promise<TeamMember[]>;
  inviteTeamMember(projectId: string, data: Omit<TeamMember, 'id' | 'invitedAt' | 'joinedAt'>): Promise<TeamMember>;
  getTeamMember(projectId: string, memberId: string): Promise<TeamMember | null>;
  updateTeamMember(projectId: string, memberId: string, data: Partial<TeamMember>): Promise<TeamMember>;
  removeTeamMember(projectId: string, memberId: string): Promise<void>;

  // Integrations CRUD
  listIntegrations(projectId: string): Promise<Integration[]>;
  createIntegration(projectId: string, data: Omit<Integration, 'id' | 'createdAt' | 'updatedAt'>): Promise<Integration>;
  getIntegration(projectId: string, integrationId: string): Promise<Integration | null>;
  updateIntegration(projectId: string, integrationId: string, data: Partial<Integration>): Promise<Integration>;
  deleteIntegration(projectId: string, integrationId: string): Promise<void>;
} 