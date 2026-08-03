import { create } from 'zustand';


// Types for different settings sections
export interface ModelConfig {
    id: string;
    userId: string;
    projectId: string;
    provider: string;
    model_name: string;
    base_url: string;
    max_tokens: number;
    temperature: number;
    timeout: number;
    retry_attempts: number;
    retry_delay: number;
    headers: Record<string, string>;
    metadata: Record<string, any>;
    secure: boolean;
    createdAt: string;
    updatedAt: string;
}

export interface GitRepository {
    id: string;
    userId: string;
    projectId: string;
    name: string;
    url: string;
    branch: string;
    accessToken: string;
    provider: 'github' | 'gitlab' | 'bitbucket';
    createdAt: string;
    updatedAt: string;
}

export type CredentialStatus = 'active' | 'expired' | 'revoked' | 'error' | 'pending';

export interface CloudCredentials {
    id: string;
    userId: string;
    projectId: string;
    provider: 'aws' | 'gcp' | 'azure';
    name: string;
    credentials: Record<string, any>;
    region?: string;
    status?: CredentialStatus;
    lastVerified?: string;
    expiresAt?: string;
    createdAt: string;
    updatedAt: string;
}

export interface TeamMember {
    id: string;
    userId: string;
    projectId: string;
    email: string;
    name: string;
    role: 'owner' | 'admin' | 'editor' | 'viewer';
    avatarUrl?: string;
    status: 'active' | 'pending' | 'invited';
    createdAt: string;
    updatedAt: string;
}

export interface Integration {
    id: string;
    userId: string;
    projectId: string;
    type: 'slack' | 'discord' | 'email' | 'webhook';
    name: string;
    config: Record<string, any>;
    isActive: boolean;
    createdAt: string;
    updatedAt: string;
}

export interface TestResult {
    success: boolean;
    message: string;
    details?: any;
    statusCode?: number;
}

interface ProjectSettingsState {
    // State
    modelConfigs: ModelConfig[];
    gitRepositories: GitRepository[];
    cloudCredentials: CloudCredentials[];
    teamMembers: TeamMember[];
    integrations: Integration[];
    
    // Loading states
    isLoading: {
        modelConfigs: boolean;
        gitRepositories: boolean;
        cloudCredentials: boolean;
        teamMembers: boolean;
        integrations: boolean;
    };
    
    // Error states
    errors: {
        modelConfigs: string | null;
        gitRepositories: string | null;
        cloudCredentials: string | null;
        teamMembers: string | null;
        integrations: string | null;
    };
    
    // Test results
    testResults: Record<string, TestResult>;
    
    // Actions
    // Model Configs
    fetchModelConfigs: (projectId: string) => Promise<void>;
    createModelConfig: (projectId: string, config: Omit<ModelConfig, 'id' | 'userId' | 'createdAt' | 'updatedAt'> & { api_key: string }) => Promise<void>;
    updateModelConfig: (projectId: string, configId: string, config: Partial<ModelConfig> & { api_key?: string }) => Promise<void>;
    deleteModelConfig: (projectId: string, configId: string) => Promise<void>;
    testModelConfig: (projectId: string, configId: string) => Promise<void>;
    
    // Git Repositories
    fetchGitRepositories: (projectId: string) => Promise<void>;
    createGitRepository: (projectId: string, repo: Omit<GitRepository, 'id' | 'userId' | 'createdAt' | 'updatedAt'>) => Promise<void>;
    updateGitRepository: (projectId: string, repoId: string, repo: Partial<GitRepository>) => Promise<void>;
    deleteGitRepository: (projectId: string, repoId: string) => Promise<void>;
    testGitRepository: (projectId: string, repoId: string) => Promise<void>;
    
    // Cloud Credentials
    fetchCloudCredentials: (projectId: string) => Promise<void>;
    createCloudCredentials: (projectId: string, credentials: Omit<CloudCredentials, 'id' | 'userId' | 'createdAt' | 'updatedAt'>) => Promise<void>;
    updateCloudCredentials: (projectId: string, credId: string, credentials: Partial<CloudCredentials>) => Promise<void>;
    deleteCloudCredentials: (projectId: string, credId: string) => Promise<void>;
    testCloudCredentials: (projectId: string, credId: string) => Promise<void>;
    bulkVerifyCredentials: (projectId: string, credentialIds: string[]) => Promise<void>;
    bulkRevokeCredentials: (projectId: string, credentialIds: string[]) => Promise<void>;
    
    // Team Members
    fetchTeamMembers: (projectId: string) => Promise<void>;
    inviteTeamMember: (projectId: string, member: Omit<TeamMember, 'id' | 'userId' | 'createdAt' | 'updatedAt'>) => Promise<void>;
    updateTeamMember: (projectId: string, memberId: string, member: Partial<TeamMember>) => Promise<void>;
    removeTeamMember: (projectId: string, memberId: string) => Promise<void>;
    
    // Integrations
    fetchIntegrations: (projectId: string) => Promise<void>;
    createIntegration: (projectId: string, integration: Omit<Integration, 'id' | 'userId' | 'createdAt' | 'updatedAt'>) => Promise<void>;
    updateIntegration: (projectId: string, integrationId: string, integration: Partial<Integration>) => Promise<void>;
    deleteIntegration: (projectId: string, integrationId: string) => Promise<void>;
    testIntegration: (projectId: string, integrationId: string) => Promise<void>;
    
    // Utility actions
    clearErrors: (section: keyof ProjectSettingsState['errors']) => void;
    clearTestResults: () => void;
}

// 🔧 FIX: Helper function to get auth token from localStorage
const getAuthToken = (): string => {
    const token = localStorage.getItem('iacgenie_token');
    if (!token) {
        throw new Error('User not authenticated - No token found');
    }
    return token;
};

// Check if a credential has expired and return updated credential with correct status
const checkCredentialExpiry = (cred: CloudCredentials): CloudCredentials => {
    if (cred.status === 'revoked' || cred.status === 'error' || cred.status === 'expired') return cred;
    if (!cred.expiresAt) return cred;
    try {
        const expiresAt = new Date(cred.expiresAt);
        if (expiresAt < new Date()) {
            return { ...cred, status: 'expired' as CredentialStatus };
        }
    } catch { /* ignore parse errors */ }
    return cred;
};

const refreshCredentialStatuses = (credentials: CloudCredentials[]): CloudCredentials[] =>
    credentials.map(checkCredentialExpiry);

// 🔧 FIX: Helper function for API calls with stored token
const apiCall = async (endpoint: string, options: RequestInit = {}) => {
    const token = getAuthToken();
    const buildHeaders = () => ({
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers,
    });
    const response = await fetch(endpoint, {
        ...options,
        headers: buildHeaders(),
    });

    // On 401, try to refresh token and retry
    if (response.status === 401) {
        const { localAuthService } = await import('../services/localAuthService');
        const refreshed = await localAuthService.refreshToken();
        if (refreshed) {
            const newToken = localStorage.getItem('iacgenie_token');
            const retryHeaders = {
                Authorization: `Bearer ${newToken}`,
                'Content-Type': 'application/json',
                ...options.headers,
            };
            const retryOptions = { ...options, headers: retryHeaders };
            const retryResponse = await fetch(endpoint, retryOptions);
            if (!retryResponse.ok) {
                const errorData = await retryResponse.json().catch(() => ({}));
                throw new Error(errorData.message || `HTTP ${retryResponse.status}: ${retryResponse.statusText}`);
            }
            return retryResponse.json();
        }
        // Refresh failed — redirect to login
        localAuthService.clearStorage();
        window.location.href = '/signin';
        throw new Error('Session expired. Please log in again.');
    }

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
};

export const useProjectSettingsStore = create<ProjectSettingsState>((set, get) => ({
    // Initial state
    modelConfigs: [],
    gitRepositories: [],
    cloudCredentials: [],
    teamMembers: [],
    integrations: [],
    
    isLoading: {
        modelConfigs: false,
        gitRepositories: false,
        cloudCredentials: false,
        teamMembers: false,
        integrations: false,
    },
    
    errors: {
        modelConfigs: null,
        gitRepositories: null,
        cloudCredentials: null,
        teamMembers: null,
        integrations: null,
    },
    
    testResults: {},
    
    // Model Configs
    fetchModelConfigs: async (projectId: string) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, modelConfigs: true },
                errors: { ...state.errors, modelConfigs: null }
            }));
            
            const data = await apiCall(`/api/model-configs/${projectId}`);
            set({ modelConfigs: data.configs || [] });
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, modelConfigs: error instanceof Error ? error.message : 'Failed to fetch model configs' }
            }));
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, modelConfigs: false }
            }));
        }
    },
    
    createModelConfig: async (projectId: string, config) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, modelConfigs: true },
                errors: { ...state.errors, modelConfigs: null }
            }));
            
            await apiCall(`/api/model-configs/${projectId}`, {
                method: 'POST',
                body: JSON.stringify(config),
            });
            
            // Refresh the list
            await get().fetchModelConfigs(projectId);
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, modelConfigs: error instanceof Error ? error.message : 'Failed to create model config' }
            }));
            throw error;
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, modelConfigs: false }
            }));
        }
    },
    
    updateModelConfig: async (projectId: string, configId: string, config) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, modelConfigs: true },
                errors: { ...state.errors, modelConfigs: null }
            }));
            
            await apiCall(`/api/model-configs/${projectId}/${configId}`, {
                method: 'PUT',
                body: JSON.stringify(config),
            });
            
            // Refresh the list
            await get().fetchModelConfigs(projectId);
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, modelConfigs: error instanceof Error ? error.message : 'Failed to update model config' }
            }));
            throw error;
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, modelConfigs: false }
            }));
        }
    },
    
    deleteModelConfig: async (projectId: string, configId: string) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, modelConfigs: true },
                errors: { ...state.errors, modelConfigs: null }
            }));
            
            await apiCall(`/api/model-configs/${projectId}/${configId}`, {
                method: 'DELETE',
            });
            
            // Remove from local state
            set(state => ({
                modelConfigs: state.modelConfigs.filter(config => config.id !== configId)
            }));
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, modelConfigs: error instanceof Error ? error.message : 'Failed to delete model config' }
            }));
            throw error;
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, modelConfigs: false }
            }));
        }
    },
    
    testModelConfig: async (projectId: string, configId: string) => {
        try {
            const result = await apiCall(`/api/model-configs/${projectId}/${configId}/test`, {
                method: 'POST',
            });
            
            set(state => ({
                testResults: {
                    ...state.testResults,
                    [`model-${configId}`]: result.result
                }
            }));
        } catch (error) {
            set(state => ({
                testResults: {
                    ...state.testResults,
                    [`model-${configId}`]: {
                        success: false,
                        message: error instanceof Error ? error.message : 'Test failed',
                        statusCode: 500
                    }
                }
            }));
        }
    },
    
    // Git Repositories
    fetchGitRepositories: async (projectId: string) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, gitRepositories: true },
                errors: { ...state.errors, gitRepositories: null }
            }));
            
            const data = await apiCall(`/api/git-repositories/${projectId}`);
            set({ gitRepositories: data.repositories || [] });
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, gitRepositories: error instanceof Error ? error.message : 'Failed to fetch git repositories' }
            }));
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, gitRepositories: false }
            }));
        }
    },
    
    createGitRepository: async (projectId: string, repo) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, gitRepositories: true },
                errors: { ...state.errors, gitRepositories: null }
            }));
            
            await apiCall(`/api/git-repositories/${projectId}`, {
                method: 'POST',
                body: JSON.stringify(repo),
            });
            
            await get().fetchGitRepositories(projectId);
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, gitRepositories: error instanceof Error ? error.message : 'Failed to create git repository' }
            }));
            throw error;
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, gitRepositories: false }
            }));
        }
    },
    
    updateGitRepository: async (projectId: string, repoId: string, repo) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, gitRepositories: true },
                errors: { ...state.errors, gitRepositories: null }
            }));
            
            await apiCall(`/api/git-repositories/${projectId}/${repoId}`, {
                method: 'PUT',
                body: JSON.stringify(repo),
            });
            
            await get().fetchGitRepositories(projectId);
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, gitRepositories: error instanceof Error ? error.message : 'Failed to update git repository' }
            }));
            throw error;
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, gitRepositories: false }
            }));
        }
    },
    
    deleteGitRepository: async (projectId: string, repoId: string) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, gitRepositories: true },
                errors: { ...state.errors, gitRepositories: null }
            }));
            
            await apiCall(`/api/git-repositories/${projectId}/${repoId}`, {
                method: 'DELETE',
            });
            
            set(state => ({
                gitRepositories: state.gitRepositories.filter(repo => repo.id !== repoId)
            }));
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, gitRepositories: error instanceof Error ? error.message : 'Failed to delete git repository' }
            }));
            throw error;
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, gitRepositories: false }
            }));
        }
    },
    
    testGitRepository: async (projectId: string, repoId: string) => {
        try {
            const result = await apiCall(`/api/git-repositories/${projectId}/${repoId}/test`, {
                method: 'POST',
            });
            
            set(state => ({
                testResults: {
                    ...state.testResults,
                    [`git-${repoId}`]: result.result
                }
            }));
        } catch (error) {
            set(state => ({
                testResults: {
                    ...state.testResults,
                    [`git-${repoId}`]: {
                        success: false,
                        message: error instanceof Error ? error.message : 'Test failed',
                        statusCode: 500
                    }
                }
            }));
        }
    },
    
    // Cloud Credentials
    fetchCloudCredentials: async (projectId: string) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, cloudCredentials: true },
                errors: { ...state.errors, cloudCredentials: null }
            }));

            const data = await apiCall(`/api/cloud-credentials/${projectId}`);
            const credentials = refreshCredentialStatuses(data.credentials || []);
            set({ cloudCredentials: credentials });
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, cloudCredentials: error instanceof Error ? error.message : 'Failed to fetch cloud credentials' }
            }));
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, cloudCredentials: false }
            }));
        }
    },
    
    createCloudCredentials: async (projectId: string, credentials) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, cloudCredentials: true },
                errors: { ...state.errors, cloudCredentials: null }
            }));
            
            await apiCall(`/api/cloud-credentials/${projectId}`, {
                method: 'POST',
                body: JSON.stringify(credentials),
            });
            
            await get().fetchCloudCredentials(projectId);
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, cloudCredentials: error instanceof Error ? error.message : 'Failed to create cloud credentials' }
            }));
            throw error;
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, cloudCredentials: false }
            }));
        }
    },
    
    updateCloudCredentials: async (projectId: string, credId: string, credentials) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, cloudCredentials: true },
                errors: { ...state.errors, cloudCredentials: null }
            }));
            
            await apiCall(`/api/cloud-credentials/${projectId}/${credId}`, {
                method: 'PUT',
                body: JSON.stringify(credentials),
            });
            
            await get().fetchCloudCredentials(projectId);
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, cloudCredentials: error instanceof Error ? error.message : 'Failed to update cloud credentials' }
            }));
            throw error;
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, cloudCredentials: false }
            }));
        }
    },
    
    deleteCloudCredentials: async (projectId: string, credId: string) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, cloudCredentials: true },
                errors: { ...state.errors, cloudCredentials: null }
            }));
            
            await apiCall(`/api/cloud-credentials/${projectId}/${credId}`, {
                method: 'DELETE',
            });
            
            set(state => ({
                cloudCredentials: state.cloudCredentials.filter(cred => cred.id !== credId)
            }));
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, cloudCredentials: error instanceof Error ? error.message : 'Failed to delete cloud credentials' }
            }));
            throw error;
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, cloudCredentials: false }
            }));
        }
    },
    
    testCloudCredentials: async (projectId: string, credId: string) => {
        try {
            const result = await apiCall(`/api/cloud-credentials/${projectId}/${credId}/test`, {
                method: 'POST',
            });

            set(state => ({
                testResults: {
                    ...state.testResults,
                    [`cloud-${credId}`]: result.result
                },
                cloudCredentials: state.cloudCredentials.map(cred =>
                    cred.id === credId
                        ? { ...cred, status: 'active' as CredentialStatus, lastVerified: new Date().toISOString() }
                        : cred
                )
            }));
        } catch (error) {
            set(state => ({
                testResults: {
                    ...state.testResults,
                    [`cloud-${credId}`]: {
                        success: false,
                        message: error instanceof Error ? error.message : 'Test failed',
                        statusCode: 500
                    }
                },
                cloudCredentials: state.cloudCredentials.map(cred =>
                    cred.id === credId
                        ? { ...cred, status: 'error' as CredentialStatus, lastVerified: new Date().toISOString() }
                        : cred
                )
            }));
        }
    },

    bulkVerifyCredentials: async (projectId: string, credentialIds: string[]) => {
        try {
            set(state => ({
                errors: { ...state.errors, cloudCredentials: null }
            }));

            const result = await apiCall(`/api/cloud-credentials/${projectId}/bulk/verify`, {
                method: 'POST',
                body: JSON.stringify({ credential_ids: credentialIds }),
            });

            const bulkResult = result.result;
            // Update local state based on results
            set(state => {
                let updatedCreds = [...state.cloudCredentials];
                const newTestResults: Record<string, TestResult> = {};
                for (const r of bulkResult.results) {
                    const resultKey = `cloud-${r.cred_id}`;
                    newTestResults[resultKey] = {
                        success: r.success,
                        message: r.message,
                    };
                    updatedCreds = updatedCreds.map(cred =>
                        cred.id === r.cred_id
                            ? { ...cred, status: r.success ? 'active' as CredentialStatus : 'error' as CredentialStatus, lastVerified: new Date().toISOString() }
                            : cred
                    );
                }
                return {
                    cloudCredentials: updatedCreds,
                    testResults: { ...state.testResults, ...newTestResults },
                };
            });
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, cloudCredentials: error instanceof Error ? error.message : 'Bulk verify failed' }
            }));
        }
    },

    bulkRevokeCredentials: async (projectId: string, credentialIds: string[]) => {
        try {
            set(state => ({
                errors: { ...state.errors, cloudCredentials: null }
            }));

            await apiCall(`/api/cloud-credentials/${projectId}/bulk/revoke`, {
                method: 'POST',
                body: JSON.stringify({ credential_ids: credentialIds }),
            });

            // Update local state - set status to 'revoked'
            set(state => ({
                cloudCredentials: state.cloudCredentials.map(cred =>
                    credentialIds.includes(cred.id)
                        ? { ...cred, status: 'revoked' as CredentialStatus, updatedAt: new Date().toISOString() }
                        : cred
                )
            }));
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, cloudCredentials: error instanceof Error ? error.message : 'Bulk revoke failed' }
            }));
            throw error;
        }
    },

    // Team Members
    fetchTeamMembers: async (projectId: string) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, teamMembers: true },
                errors: { ...state.errors, teamMembers: null }
            }));
            
            const data = await apiCall(`/api/team-members/${projectId}`);
            set({ teamMembers: data.members || [] });
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, teamMembers: error instanceof Error ? error.message : 'Failed to fetch team members' }
            }));
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, teamMembers: false }
            }));
        }
    },
    
    inviteTeamMember: async (projectId: string, member) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, teamMembers: true },
                errors: { ...state.errors, teamMembers: null }
            }));
            
            await apiCall(`/api/team-members/${projectId}`, {
                method: 'POST',
                body: JSON.stringify(member),
            });
            
            await get().fetchTeamMembers(projectId);
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, teamMembers: error instanceof Error ? error.message : 'Failed to invite team member' }
            }));
            throw error;
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, teamMembers: false }
            }));
        }
    },
    
    updateTeamMember: async (projectId: string, memberId: string, member) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, teamMembers: true },
                errors: { ...state.errors, teamMembers: null }
            }));
            
            await apiCall(`/api/team-members/${projectId}/${memberId}`, {
                method: 'PUT',
                body: JSON.stringify(member),
            });
            
            await get().fetchTeamMembers(projectId);
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, teamMembers: error instanceof Error ? error.message : 'Failed to update team member' }
            }));
            throw error;
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, teamMembers: false }
            }));
        }
    },
    
    removeTeamMember: async (projectId: string, memberId: string) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, teamMembers: true },
                errors: { ...state.errors, teamMembers: null }
            }));
            
            await apiCall(`/api/team-members/${projectId}/${memberId}`, {
                method: 'DELETE',
            });
            
            set(state => ({
                teamMembers: state.teamMembers.filter(member => member.id !== memberId)
            }));
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, teamMembers: error instanceof Error ? error.message : 'Failed to remove team member' }
            }));
            throw error;
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, teamMembers: false }
            }));
        }
    },
    
    // Integrations
    fetchIntegrations: async (projectId: string) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, integrations: true },
                errors: { ...state.errors, integrations: null }
            }));
            
            const data = await apiCall(`/api/integrations/${projectId}`);
            set({ integrations: data.integrations || [] });
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, integrations: error instanceof Error ? error.message : 'Failed to fetch integrations' }
            }));
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, integrations: false }
            }));
        }
    },
    
    createIntegration: async (projectId: string, integration) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, integrations: true },
                errors: { ...state.errors, integrations: null }
            }));
            
            await apiCall(`/api/integrations/${projectId}`, {
                method: 'POST',
                body: JSON.stringify(integration),
            });
            
            await get().fetchIntegrations(projectId);
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, integrations: error instanceof Error ? error.message : 'Failed to create integration' }
            }));
            throw error;
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, integrations: false }
            }));
        }
    },
    
    updateIntegration: async (projectId: string, integrationId: string, integration) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, integrations: true },
                errors: { ...state.errors, integrations: null }
            }));
            
            await apiCall(`/api/integrations/${projectId}/${integrationId}`, {
                method: 'PUT',
                body: JSON.stringify(integration),
            });
            
            await get().fetchIntegrations(projectId);
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, integrations: error instanceof Error ? error.message : 'Failed to update integration' }
            }));
            throw error;
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, integrations: false }
            }));
        }
    },
    
    deleteIntegration: async (projectId: string, integrationId: string) => {
        try {
            set(state => ({
                isLoading: { ...state.isLoading, integrations: true },
                errors: { ...state.errors, integrations: null }
            }));
            
            await apiCall(`/api/integrations/${projectId}/${integrationId}`, {
                method: 'DELETE',
            });
            
            set(state => ({
                integrations: state.integrations.filter(integration => integration.id !== integrationId)
            }));
        } catch (error) {
            set(state => ({
                errors: { ...state.errors, integrations: error instanceof Error ? error.message : 'Failed to delete integration' }
            }));
            throw error;
        } finally {
            set(state => ({
                isLoading: { ...state.isLoading, integrations: false }
            }));
        }
    },
    
    testIntegration: async (projectId: string, integrationId: string) => {
        try {
            const result = await apiCall(`/api/integrations/${projectId}/${integrationId}/test`, {
                method: 'POST',
            });
            
            set(state => ({
                testResults: {
                    ...state.testResults,
                    [`integration-${integrationId}`]: result.result
                }
            }));
        } catch (error) {
            set(state => ({
                testResults: {
                    ...state.testResults,
                    [`integration-${integrationId}`]: {
                        success: false,
                        message: error instanceof Error ? error.message : 'Test failed',
                        statusCode: 500
                    }
                }
            }));
        }
    },
    
    // Utility actions
    clearErrors: (section) => {
        set(state => ({
            errors: { ...state.errors, [section]: null }
        }));
    },
    
    clearTestResults: () => {
        set({ testResults: {} });
    },
})); 