import { create } from 'zustand';
import { CloudProvider, View, DeploymentMode } from '../types';
import { AVAILABLE_MODELS } from '../constants';
import { LLMCompletionResponse } from '../types';

import { projectService } from '../services/projectService';
import { useProjectStore } from './useProjectStore';
import { localAuthService } from '../services/localAuthService';
import { usePipelineStore } from './usePipelineStore';
import { useAuthStore } from './useAuthStore';
export interface ModelConfig {
    id: string;
    userId: string;
    projectId: string;
    provider: string;
    model_name: string;
    model?: string;
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

export interface TestResult {
    success: boolean;
    message: string;
    provider: string;
    model_name: string;
    request: any;
    response: any;
    status_code: number | null;
}

export interface User {
    name: string;
    email: string;
    avatarUrl: string;
    uid?: string;
    roles?: {
        global: string;
        projects: Record<string, string>;
    };
}

export interface AuthProviderConfig {
    id: string;
    name: string;
    enabled: boolean;
}

export interface AuthConfig {
    providers: AuthProviderConfig[];
    samlEnabled: boolean;
    googleEnabled: boolean;
    githubEnabled: boolean;
    localEnabled: boolean;
}

export interface Project {
    id: string;
    name: string;
    description: string;
}

export interface GenerationMetadata {
    modelUsed: string;
    totalCost: number;
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
    cached: boolean;
    latencyMs?: number;
    failoverFrom?: string;
    failoverTo?: string;
}

interface GeneratorConfig {
    model: string;
    provider: CloudProvider;
}

export interface CostMetrics {
    currentMonthCost: number;
    projectedEndOfMonthCost: number;
    savingsVsLastMonth: number;
}

export interface UsageMetrics {
    totalGenerations: number;
    totalDeployments: number;
    successRate: number;
}

export interface TimeSeriesData {
    date: string;
    count: number;
}

export interface ModelPerformanceData {
    modelName: string;
    provider: string;
    successRate: number;
    usageCount: number;
}

export interface CloudProviderData {
    provider: string;
    percentage: number;
    cost: number;
}

interface AppState {
    // Auth State
    isAuthenticated: boolean;
    user: User | null;

    // Auth Config (discovered providers)
    authConfig: AuthConfig | null;
    isLoadingAuthConfig: boolean;

    // Navigation State
    currentView: View;

    // Project State
    currentProject: Project | null;
    
    // Generator State
    generatorConfig: GeneratorConfig;

    // Generation Metadata (from LiteLLM gateway responses)
    lastGenerationMetadata: GenerationMetadata | null;
    setGenerationMetadata: (metadata: Partial<GenerationMetadata>) => void;
    clearGenerationMetadata: () => void;
    setGenerationMetadataFromResponse: (response: LLMCompletionResponse) => void;

    // Analytics Metrics
    usageMetrics: UsageMetrics | null;
    costMetrics: CostMetrics | null;
    generationsOverTime: TimeSeriesData[];
    deploymentsOverTime: TimeSeriesData[];
    modelPerformance: ModelPerformanceData[];
    cloudProviderDistribution: CloudProviderData[];
    isLoadingMetrics: boolean;
    fetchMetrics: (projectId: string, timeRange?: string) => Promise<void>;

    // Model Configuration State
    modelConfigs: ModelConfig[];
    activeModelConfig: ModelConfig | null;
    isConfiguringModel: boolean;
    modelConfigError: string | null;
    testResults: { [configId: string]: TestResult };
    
    // Project State
    projects: Project[];
    isLoadingProjects: boolean;
    projectError: string | null;
    
    // Actions
    signIn: (user: User) => void;
    signOut: () => void;
    setAuthConfig: (config: AuthConfig) => void;
    navigate: (view: View) => void;
    setCurrentView: (view: View) => void;
    setProject: (project: Project) => void;
    setCurrentProjectId: (projectId: string) => Promise<void>;
    setGeneratorConfig: (config: Partial<GeneratorConfig>) => void;
    
    // Model Configuration Actions
    fetchModelConfigs: () => Promise<void>;
    createModelConfig: (config: Omit<ModelConfig, 'id' | 'userId' | 'createdAt' | 'updatedAt'> & { api_key: string }) => Promise<void>;
    deleteModelConfig: (configId: string) => Promise<void>;
    testModelConfig: (configId: string) => Promise<void>;
    setActiveModelConfig: (config: ModelConfig | null) => void;
    clearModelConfigError: () => void;

    // Project Actions
    listProjects: () => Promise<void>;
    createProject: (data: { name: string; description?: string }) => Promise<void>;
    updateProject: (projectId: string, data: { name: string; description?: string }) => Promise<void>;
    deleteProject: (projectId: string) => Promise<void>;
    setCurrentProject: (project: Project | null) => void;
    clearCurrentProject: () => void;
    
    // 🔧 FIX: Initialize authentication state
    initializeAuth: () => void;
    hasProjectEditAccess: (projectId: string) => boolean;
    isAdmin: () => boolean;

    // Simulation state
    deploymentMode: DeploymentMode;
    setDeploymentMode: (mode: DeploymentMode) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
    // Initial State
    deploymentMode: (localStorage.getItem('iacgenie_deployment_mode') as DeploymentMode) || 'aws',
    isAuthenticated: false,
    user: null,
    authConfig: null,
    isLoadingAuthConfig: false,
    currentView: 'landing',
    currentProject: null,
    generatorConfig: {
        model: AVAILABLE_MODELS[0].id,
        provider: CloudProvider.AWS,
    },

    // Generation Metadata (from LiteLLM gateway responses)
    lastGenerationMetadata: null,

    // Analytics Metrics
    usageMetrics: null,
    costMetrics: null,
    generationsOverTime: [],
    deploymentsOverTime: [],
    modelPerformance: [],
    cloudProviderDistribution: [],
    isLoadingMetrics: false,

    // Model Configuration State
    modelConfigs: [],
    activeModelConfig: null,
    isConfiguringModel: false,
    modelConfigError: null,
    testResults: {},
    
    // Project State
    projects: [],
    isLoadingProjects: false,
    projectError: null,

    // 🔧 FIX: Initialize authentication state from localStorage
    initializeAuth: () => {
        const storedUser = localStorage.getItem('iacgenie_user');
        const storedToken = localStorage.getItem('iacgenie_token');
        // Validate token: must be at least 100 chars and contain 3 segments
        const isValidToken = (token: string | null) => !!token && token.length > 100 && token.split('.').length === 3;
        if (storedUser && isValidToken(storedToken)) {
            try {
                const user = JSON.parse(storedUser);
                set({
                    isAuthenticated: true,
                    user,
                    currentView: 'dashboard',
                });
                // Auth state already validated above via localStorage reads
                
                // Load projects from localStorage on initialization
                const storedProjects = JSON.parse(localStorage.getItem('projects') || '[]');
                if (storedProjects.length > 0) {
                    set({ projects: storedProjects });
                    console.log('Loaded projects from localStorage during auth initialization');
                }
            } catch (error) {
                localStorage.removeItem('iacgenie_user');
                localStorage.removeItem('iacgenie_token');
                set({ isAuthenticated: false, user: null, currentView: 'landing' });
            }
        } else {
            localStorage.removeItem('iacgenie_user');
            localStorage.removeItem('iacgenie_token');
            set({ isAuthenticated: false, user: null, currentView: 'landing' });
        }
    },

    // Actions
    signIn: async (user) => {
        set({ isAuthenticated: true, user, currentView: 'dashboard' });
        
        // 🔧 FIX: Ensure token is stored in localStorage
        const token = localStorage.getItem('iacgenie_token');
        if (!token) {
            console.warn('No token found in localStorage after sign in');
        }
        
        // Load projects after sign in with error handling
        try {
            await get().listProjects();
        } catch (error) {
            console.warn('Failed to load projects after sign in:', error);
            // Set empty projects array to prevent infinite loading
            set({ 
                projects: [], 
                isLoadingProjects: false,
                projectError: 'Failed to load projects. Please try refreshing the page.'
            });
        }
        
        // Restore cached project on login
        const cachedProjectId = localStorage.getItem('currentProjectId');
        if (cachedProjectId) {
            try {
                // Fetch project details from API
                const project = await projectService.getProject(cachedProjectId);
                set({ currentProject: project });
                // Sync with useProjectStore
                useProjectStore.getState().setCurrentProjectId(cachedProjectId);
            } catch (error) {
                console.warn('Failed to restore cached project:', error);
                // Clear invalid cached project
                localStorage.removeItem('currentProjectId');
            }
        }
    },
    
    signOut: async () => {
        try {
            await localAuthService.logout();
        } catch (error) {
            console.error('Logout failed:', error);
        }
        set({ isAuthenticated: false, user: null, currentProject: null });
        // Clear cached project on logout
        localStorage.removeItem('currentProjectId');
        // Clear persisted Zustand auth state
        useAuthStore.getState().logout();
        
        // Navigate to landing page explicitly
        get().navigate('landing');
    },

    setAuthConfig: (config) => {
        // Store in localStorage for persistence across page loads
        try {
            localStorage.setItem('iacgenie_auth_config', JSON.stringify(config));
        } catch (e) {
            console.warn('[AuthConfig] Could not persist auth config to localStorage');
        }
        set({ authConfig: config });
    },

    setCurrentView: (view) => {
        set({ currentView: view });
    },
    
    navigate: (view: View) => {
        // Set the view first
        set({ currentView: view });
        
        // Update browser URL
        const pathMap: Record<View, string> = {
            'landing': '/',
            'signin': '/signin',
            'signup': '/signup',
            'forgot-password': '/forgot-password',
            'reset-password': '/reset-password',
            'dashboard': '/dashboard',
            'generator': '/generator',
            'deployments': '/deployments',
            'settings': '/settings',
            'developer': '/developer',
            'billing': '/billing',
            'audit-log': '/audit-log',
            'docs': '/docs',
            'api-docs': '/api-docs',
            'about': '/about',
            'privacy': '/privacy',
            'terms': '/terms',
            'contact': '/contact',
            'aup': '/aup',
            'human-review': '/human-review',
            'usage-analytics': '/usage-analytics',
            'team-members': '/team-members',
            'pipeline-dashboard': '/pipelines',
            'clarify-agent': '/pipelines/new',
            'generator-agent': '/pipelines/:id/generate',
            'static-analysis': '/pipelines/:id/static-analysis',
            'plan-review': '/pipelines/:id/plan-review',
            'apply-review': '/pipelines/:id/apply-review',
            'escalation-handler': '/pipelines/:id/escalation',
            'session-manager': '/pipelines/:id/sessions',
            'pipeline-detail': '/pipelines/:id',
            'workspace-manager': '/workspace-manager',
            'agent-configuration': '/agent-configuration',
        };
        
        let path = pathMap[view];
        if (path) {
            if (path.includes('/:id')) {
                const activePipeline = usePipelineStore.getState().activePipeline;
                if (activePipeline?.id) {
                    path = path.replace('/:id', `/${activePipeline.id}`);
                } else {
                    path = '/pipelines';
                }
            }
            if (window.location.pathname !== path) {
                window.location.href = path;
            }
        }
    },
    
    setProject: (project) => set({ currentProject: project }),
    
    setCurrentProjectId: async (projectId: string) => {
        try {
            // Fetch project details from API
            const project = await projectService.getProject(projectId);
            
            if (project && project.id) {
                set({ currentProject: project });
                
                // Persist to localStorage
                localStorage.setItem('currentProjectId', projectId);
            } else {
                console.warn('Project not found or invalid:', project, 'projectId:', projectId);
            }
            
            // Sync with useProjectStore
            useProjectStore.getState().setCurrentProjectId(projectId);
        } catch (error) {
            console.error('Failed to set current project:', error);
            throw error;
        }
    },
    
    setGeneratorConfig: (config) => set(state => ({
        generatorConfig: { ...state.generatorConfig, ...config }
    })),

    // Generation Metadata Actions
    setGenerationMetadata: (metadata) => set(state => {
        const existing = state.lastGenerationMetadata;
        return {
            lastGenerationMetadata: existing
                ? { ...existing, ...metadata }
                : {
                      modelUsed: metadata.modelUsed ?? '',
                      totalCost: metadata.totalCost ?? 0,
                      promptTokens: metadata.promptTokens ?? 0,
                      completionTokens: metadata.completionTokens ?? 0,
                      totalTokens: metadata.totalTokens ?? 0,
                      cached: metadata.cached ?? false,
                      failoverFrom: metadata.failoverFrom,
                      failoverTo: metadata.failoverTo,
                  },
        };
    }),
    clearGenerationMetadata: () => set({ lastGenerationMetadata: null }),
    setGenerationMetadataFromResponse: (response) => set({
        lastGenerationMetadata: {
            modelUsed: response.model_used,
            totalCost: response.total_cost,
            promptTokens: response.usage.prompt_tokens,
            completionTokens: response.usage.completion_tokens,
            totalTokens: response.usage.total_tokens,
            cached: response.cached,
            latencyMs: response.latency_ms_ms ?? 0,
            failoverFrom: response.failover_from,
            failoverTo: response.failover_to,
        }
    }),

    // Analytics Actions
    fetchMetrics: async (projectId: string, timeRange: string = 'last-30-days') => {
        set({ isLoadingMetrics: true });
        try {
            const token = localStorage.getItem('iacgenie_token');
            const res = await fetch(`http://localhost:8000/api/metrics/${projectId}?range=${timeRange}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            if (res.ok) {
                const data = await res.json();
                if (data.success && data.result) {
                    set({
                        usageMetrics: data.result.metrics,
                        costMetrics: data.result.cost,
                        generationsOverTime: data.result.generationsOverTime,
                        deploymentsOverTime: data.result.deploymentsOverTime,
                        modelPerformance: data.result.modelPerformance,
                        cloudProviderDistribution: data.result.cloudProviderDistribution
                    });
                }
            }
        } catch (error) {
            console.error("Failed to fetch metrics", error);
        } finally {
            set({ isLoadingMetrics: false });
        }
    },

    // Model Configuration Actions
    fetchModelConfigs: async () => {
        try {
            set({ isConfiguringModel: true, modelConfigError: null });
            
            // 🔧 FIX: Use stored token instead of Firebase SDK
            const token = localAuthService.getAuthToken();
            if (!token) {
                throw new Error('User not authenticated - No token found');
            }
            
            const projectId = get().currentProject?.id;
            if (!projectId) {
                set({ modelConfigError: 'No project selected. Please select or create a project first.', isConfiguringModel: false });
                return;
            }
            const response = await fetch(`/api/model-configs/${projectId}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });
            
            if (!response.ok) {
                throw new Error(`Failed to fetch model configs: ${response.statusText}`);
            }
            
            const data = await response.json();
            const configs = (data.configs || []).map((c: any) => ({
                ...c,
                model_name: c.model_name || c.model
            }));
            set({ modelConfigs: configs, isConfiguringModel: false });
        } catch (error) {
            set({ 
                modelConfigError: error instanceof Error ? error.message : 'Failed to fetch model configs',
                isConfiguringModel: false 
            });
        }
    },
    
    createModelConfig: async (config) => {
        try {
            set({ isConfiguringModel: true, modelConfigError: null });
            
            // 🔧 FIX: Use stored token instead of Firebase SDK
            const token = localAuthService.getAuthToken();
            if (!token) {
                throw new Error('User not authenticated - No token found');
            }
            
            const projectId = get().currentProject?.id || 'default-project';
            const response = await fetch(`/api/model-configs/${projectId}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config),
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `Failed to create model config: ${response.statusText}`);
            }
            
            // Refresh the list
            await get().fetchModelConfigs();
        } catch (error) {
            set({ 
                modelConfigError: error instanceof Error ? error.message : 'Failed to create model config',
                isConfiguringModel: false 
            });
        }
    },
    
    deleteModelConfig: async (configId) => {
        try {
            set({ isConfiguringModel: true, modelConfigError: null });
            
            // 🔧 FIX: Use stored token instead of Firebase SDK
            const token = localAuthService.getAuthToken();
            if (!token) {
                throw new Error('User not authenticated - No token found');
            }
            
            const projectId = get().currentProject?.id || 'default-project';
            const response = await fetch(`/api/model-configs/${projectId}/${configId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `Failed to delete model config: ${response.statusText}`);
            }
            
            // Remove from local state
            set(state => ({
                modelConfigs: state.modelConfigs.filter(config => config.id !== configId),
                isConfiguringModel: false
            }));
        } catch (error) {
            set({ 
                modelConfigError: error instanceof Error ? error.message : 'Failed to delete model config',
                isConfiguringModel: false 
            });
        }
    },
    
    testModelConfig: async (configId) => {
        try {
            // 🔧 FIX: Use stored token instead of Firebase SDK
            const token = localAuthService.getAuthToken();
            if (!token) {
                throw new Error('User not authenticated - No token found');
            }
            
            const projectId = get().currentProject?.id || 'default-project';
            const response = await fetch(`/api/model-configs/${projectId}/${configId}/test`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `Failed to test model config: ${response.statusText}`);
            }
            
            const data = await response.json();
            set(state => ({
                testResults: {
                    ...state.testResults,
                    [configId]: data.result
                }
            }));
        } catch (error) {
            set(state => ({
                testResults: {
                    ...state.testResults,
                    [configId]: {
                        success: false,
                        message: error instanceof Error ? error.message : 'Test failed',
                        provider: 'unknown',
                        model_name: 'unknown',
                        request: {},
                        response: error instanceof Error ? error.message : 'Test failed',
                        status_code: null
                    }
                }
            }));
        }
    },
    
    setActiveModelConfig: (config) => set({ activeModelConfig: config }),
    
    clearModelConfigError: () => set({ modelConfigError: null }),

    // Project Actions
    listProjects: async () => {
        set({ isLoadingProjects: true, projectError: null });
        try {
            const projects = await projectService.listProjects();
            const projectsList = Array.isArray(projects) ? projects : [];

            // Always prefer fresh API data. Only fall back to localStorage when API returns 0
            let finalProjects = projectsList;
            if (projectsList.length === 0) {
                const storedProjects = JSON.parse(localStorage.getItem('projects') || '[]');
                if (storedProjects.length > 0) {
                    console.log('Loading projects from localStorage fallback');
                    finalProjects = storedProjects;
                }
            } else {
                // Keep localStorage in sync with fresh API data
                localStorage.setItem('projects', JSON.stringify(projectsList));
            }

            set({ 
                projects: finalProjects,
                isLoadingProjects: false 
            });
        } catch (error) {
            // Try loading from localStorage as fallback when API fails
            const storedProjects = JSON.parse(localStorage.getItem('projects') || '[]');
            const storedCurrentId = localStorage.getItem('currentProjectId');
            const current = storedProjects.find((p: any) => p.id === storedCurrentId) || (storedProjects.length > 0 ? storedProjects[0] : null);
            
            if (current) {
                useProjectStore.getState().setCurrentProjectId(current.id);
            }
            
            set({
                projects: storedProjects,
                currentProject: current,
                isLoadingProjects: false,
                projectError: error instanceof Error ? error.message : 'Failed to load projects',
            });
        }
    },
    createProject: async (data) => {
        // Prevent duplicate requests
        const state = get();
        if (state.isLoadingProjects) {
            console.log('Projects operation already in progress, skipping duplicate request');
            return;
        }
        
        set({ isLoadingProjects: true, projectError: null });
        
        // Add timeout to prevent infinite loading
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Request timeout')), 10000);
        });
        
        try {
            const projectPromise = projectService.createProject(data);
            const project = await Promise.race([projectPromise, timeoutPromise]) as any;
            
            if (project && project.id) {
                // Store currentProjectId
                localStorage.setItem('currentProjectId', project.id);
                
                // Get current projects from localStorage
                const storedProjects = JSON.parse(localStorage.getItem('projects') || '[]');
                const newProjects = [...storedProjects, project];
                
                // Persist to localStorage FIRST
                localStorage.setItem('projects', JSON.stringify(newProjects));
                
                // Update Zustand state SECOND (so it reads from localStorage)
                set({ 
                    projects: newProjects, 
                    isLoadingProjects: false, 
                    currentProject: project 
                });
            }
        } catch (error) {
            console.error('Failed to create project:', error);
            set({ 
                projectError: error instanceof Error ? error.message : 'Failed to create project', 
                isLoadingProjects: false 
            });
            throw error;
        }
    },
    updateProject: async (projectId, data) => {
        // Prevent duplicate requests
        const state = get();
        if (state.isLoadingProjects) {
            console.log('Projects operation already in progress, skipping duplicate request');
            return;
        }
        
        set({ isLoadingProjects: true, projectError: null });
        
        // Add timeout to prevent infinite loading
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Request timeout')), 10000);
        });
        
        try {
            const updatedPromise = projectService.updateProject(projectId, data);
            const updated = await Promise.race([updatedPromise, timeoutPromise]) as any;
            
            set(state => ({
                projects: state.projects.map(p => p.id === projectId ? updated : p),
                isLoadingProjects: false,
                currentProject: state.currentProject && state.currentProject.id === projectId ? updated : state.currentProject
            }));
        } catch (error) {
            console.error('Failed to update project:', error);
            set({ 
                projectError: error instanceof Error ? error.message : 'Failed to update project', 
                isLoadingProjects: false 
            });
            throw error;
        }
    },
    deleteProject: async (projectId) => {
        // Prevent duplicate requests
        const state = get();
        if (state.isLoadingProjects) {
            console.log('Projects operation already in progress, skipping duplicate request');
            return;
        }
        
        set({ isLoadingProjects: true, projectError: null });
        
        // Add timeout to prevent infinite loading
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Request timeout')), 10000);
        });
        
        try {
            const deletePromise = projectService.deleteProject(projectId);
            await Promise.race([deletePromise, timeoutPromise]);
            
            set(state => {
                const projects = state.projects.filter(p => p.id !== projectId);
                const currentProject = state.currentProject && state.currentProject.id === projectId ? (projects[0] || null) : state.currentProject;
                return { projects, isLoadingProjects: false, currentProject };
            });
        } catch (error) {
            console.error('Failed to delete project:', error);
            set({ 
                projectError: error instanceof Error ? error.message : 'Failed to delete project', 
                isLoadingProjects: false 
            });
            throw error;
        }
    },
    setCurrentProject: (project) => set({ currentProject: project }),
    clearCurrentProject: () => set({ currentProject: null }),
    hasProjectEditAccess: (projectId: string) => {
        const user = get().user;
        if (!user) return false;
        // Global admin check (works for users with roles.global or direct role field)
        const globalRole = user.roles?.global || (user as any).role;
        if (globalRole === 'admin') return true;
        // Project-level owner/admin check
        const projectRole = user.roles?.projects?.[projectId];
        return projectRole === 'owner' || projectRole === 'admin';
    },
    isAdmin: () => {
        const user = get().user;
        if (!user) return false;
        const globalRole = user.roles?.global || (user as any).role;
        return globalRole === 'admin';
    },
    setDeploymentMode: (mode: DeploymentMode) => {
        localStorage.setItem('iacgenie_deployment_mode', mode);
        set({ deploymentMode: mode });
    },
}));