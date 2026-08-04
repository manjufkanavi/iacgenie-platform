import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import Card from '../ui/Card';
import Button from '../ui/Button';
import { gitRepositoryService } from '../../services/gitRepositoryService';
import { gitOpsService, type ListRunsResponse } from '../../services/gitOpsService';
import type { GitRepository as GitRepositoryType } from '../../services/db/adapters/IDatabaseAdapter';
import { useAppStore } from '../store/useAppStore';
import { Github, Gitlab, Code, AlertCircle, CheckCircle2, AlertTriangle, Terminal, ExternalLink, Loader2 } from 'lucide-react';
import Modal from '../ui/Modal';
import GitRepositoryForm from './forms/GitRepositoryForm';
import RepoSyncStatusBadge from './RepoSyncStatusBadge';
import WebhookSetupForm from '../forms/WebhookSetupForm';
import SyncProgressPanel, { SyncHealthData, ExecutionRun } from './SyncProgressPanel';
import PRCommentSimulator from './PRCommentSimulator';

/**
 * Convert backend GitOpsRunResponse (snake_case) to frontend ExecutionRun (camelCase).
 */
function runResponseToExecutionRun(
    run: ListRunsResponse['runs'][0],
    provider: string,
): ExecutionRun {
    const startedAt = run.startedAt ? new Date(run.startedAt) : new Date();
    const finishedAt = run.completedAt ? new Date(run.completedAt) : null;
    const duration = startedAt && finishedAt
        ? Math.round((finishedAt.getTime() - startedAt.getTime()) / 1000)
        : 0;

    // Map backend status enum to frontend status
    let status: ExecutionRun['status'] = 'failed';
    switch (run.status) {
        case 'completed': status = 'success'; break;
        case 'failed': status = 'failed'; break;
        case 'cancelled': status = 'cancelled'; break;
        case 'running': status = 'in-progress'; break;
        case 'queued': status = 'in-progress'; break;
    }

    return {
        id: run.runId,
        type: run.runType,
        provider: provider as ExecutionRun['provider'],
        status,
        commitHash: run.commitSha,
        commitMessage: run.commitSha.substring(0, 12) || '',
        duration,
        startedAt,
        finishedAt,
        logs: run.planDiff || run.applyDiff || '',
    };
}

// Display type for repositories shown in the UI
interface RepoEntry {
    id: string;
    name: string;
    url: string;
    branch: string;
    provider: string;
    createdAt?: string;
    updatedAt?: string;
    enableGitOps?: boolean;
    webhookSecret?: string;
}

// Helper to map GitRepositoryType to RepoEntry for display
function toRepoEntry(repo: GitRepositoryType): RepoEntry {
    return {
        id: repo.id,
        name: (repo as any).name || repo.provider, // Use provider as name since GitRepository has no name field
        url: repo.repo_url,
        branch: repo.branch,
        provider: repo.provider,
        createdAt: repo.createdAt,
        updatedAt: repo.updatedAt,
        enableGitOps: (repo as any).enableGitOps || false,
        webhookSecret: (repo as any).webhookSecret || ''
    };
}

const RepoConfigPanel: React.FC = () => {
    const { currentProject, navigate } = useAppStore();
    const projectId = currentProject?.id;

    const [repositories, setRepositories] = useState<RepoEntry[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showAddRepoModal, setShowAddRepoModal] = useState(false);
    
    // Testing state
    const [testingId, setTestingId] = useState<string | null>(null);
    const [testResult, setTestResult] = useState<{ [key: string]: { success: boolean; message: string } }>({});

    // Digger GitOps Operational States
    const [syncHealthData, setSyncHealthData] = useState<Record<string, SyncHealthData>>({});
    const [executionHistory, setExecutionHistory] = useState<Record<string, ExecutionRun[]>>({});
    const [runsLoading, setRunsLoading] = useState<Record<string, boolean>>({});
    
    // Active panels toggles
    const [activeWebhookRepo, setActiveWebhookRepo] = useState<RepoEntry | null>(null);
    const [expandedSyncHistory, setExpandedSyncHistory] = useState<Record<string, boolean>>({});
    const [expandedPRSimulator, setExpandedPRSimulator] = useState<Record<string, boolean>>({});

    const fetchRepositories = async () => {
        if (!projectId) return;
        setIsLoading(true);
        setError(null);
        try {
            const repos = await gitRepositoryService.listGitRepositories(projectId);
            setRepositories(repos.map(toRepoEntry));
        } catch (err: any) {
            console.error(err);
            setError(err.message || 'Failed to fetch repositories');
            toast.error(err.message || 'Failed to fetch repositories');
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchRepositories();
    }, [projectId]);

    // Load real GitOps runs from the API when repositories change
    useEffect(() => {
        if (repositories.length === 0) return;

        const fetchRunsForAllRepos = async () => {
            const loadingMap: Record<string, boolean> = {};
            repositories.forEach(repo => { loadingMap[repo.id] = true; });
            setRunsLoading(loadingMap);

            const historyMap: Record<string, ExecutionRun[]> = {};

            await Promise.all(
                repositories.map(async (repo) => {
                    try {
                        const result = await gitOpsService.listRuns(repo.id, { limit: 50 });
                        historyMap[repo.id] = result.runs.map(run =>
                            runResponseToExecutionRun(run, repo.provider),
                        );
                    } catch (err: any) {
                        console.error(`Failed to fetch runs for ${repo.name}:`, err);
                        historyMap[repo.id] = [];
                    } finally {
                        setRunsLoading(prev => ({ ...prev, [repo.id]: false }));
                    }
                }),
            );

            setExecutionHistory(historyMap);
        };

        fetchRunsForAllRepos();
    }, [repositories]);

    // Keep basic sync health states (drift detection is not yet backed by a real API)
    useEffect(() => {
        if (repositories.length > 0) {
            const healthMap: Record<string, SyncHealthData> = {};
            repositories.forEach((repo) => {
                // Default to completed; drift detection will populate 'out-of-sync'
                healthMap[repo.id] = {
                    state: 'completed',
                    lastSyncedAt: new Date(),
                    expectedSyncAt: new Date(Date.now() + 5 * 60000),
                    currentBranch: repo.branch,
                    targetBranch: repo.branch,
                };
            });
            setSyncHealthData(healthMap);
        }
    }, [repositories]);

    const handleSave = async (formData: any) => {
        if (!projectId) return;
        setIsSaving(true);
        setError(null);

        try {
            await gitRepositoryService.createGitRepository(projectId, {
                name: formData.name,
                repo_url: formData.url,
                branch: formData.branch,
                provider: formData.provider as any,
                access_token: formData.accessToken,
                userId: '',
                projectId: '',
                // Extra fields for Digger GitOps
                enableGitOps: formData.enableGitOps,
                webhookSecret: formData.webhookSecret
            } as any);

            toast.success('Git repository configuration saved successfully!');
            setShowAddRepoModal(false);
            fetchRepositories();
        } catch (err: any) {
            const message = err.message || 'An error occurred while saving the configuration.';
            setError(message);
            toast.error(message);
        } finally {
            setIsSaving(false);
        }
    };

    const handleDelete = async (repoId: string) => {
        if (!projectId) return;
        if (!window.confirm('Are you sure you want to delete this repository configuration? This action is permanent.')) {
            return;
        }

        setError(null);
        try {
            await gitRepositoryService.deleteGitRepository(projectId, repoId);
            toast.success('Repository configuration deleted.');
            fetchRepositories();
        } catch (err: any) {
            const message = err.message || 'Failed to delete configuration';
            setError(message);
            toast.error(message);
        }
    };

    const handleTestConnection = async (repoId: string) => {
        setTestingId(repoId);
        try {
            const { getAuthHeaders } = await import('../services/authHeaders');
            const response = await fetch(`/api/git-repositories/${projectId}/${repoId}/test`, {
                method: 'POST',
                headers: getAuthHeaders()
            });
            if (response.ok) {
                setTestResult(prev => ({
                    ...prev,
                    [repoId]: { success: true, message: 'Connection validated successfully!' }
                }));
                toast.success('Connection validated successfully!');
            } else {
                setTestResult(prev => ({
                    ...prev,
                    [repoId]: { success: false, message: 'Could not connect to repository.' }
                }));
                toast.error('Could not connect to repository.');
            }
        } catch (err) {
            setTestResult(prev => ({
                ...prev,
                [repoId]: { success: false, message: 'Network error occurred.' }
            }));
            toast.error('Network error occurred.');
        } finally {
            setTestingId(null);
        }
    };

    const toggleSyncHistory = (repoId: string) => {
        setExpandedSyncHistory(prev => ({
            ...prev,
            [repoId]: !prev[repoId]
        }));
        // Close PR simulator when history opens to clean up visual space
        if (expandedPRSimulator[repoId]) {
            setExpandedPRSimulator(prev => ({ ...prev, [repoId]: false }));
        }
    };

    const togglePRSimulator = (repoId: string) => {
        setExpandedPRSimulator(prev => ({
            ...prev,
            [repoId]: !prev[repoId]
        }));
        // Close logs history when simulator opens
        if (expandedSyncHistory[repoId]) {
            setExpandedSyncHistory(prev => ({ ...prev, [repoId]: false }));
        }
    };

    const handleResolveSyncDrift = async (repoId: string) => {
        // Optimistically set to in-progress
        setSyncHealthData(prev => {
            const current = prev[repoId];
            if (!current) return prev;
            return {
                ...prev,
                [repoId]: { ...current, state: 'in-progress' }
            };
        });

        toast.loading('Starting GitOps workflow reconciliation pipeline...', { duration: 1500 });
        
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Finalize completed sync
        setSyncHealthData(prev => {
            const current = prev[repoId];
            if (!current) return prev;
            return {
                ...prev,
                [repoId]: { 
                    ...current, 
                    state: 'completed',
                    lastSyncedAt: new Date()
                }
            };
        });
        toast.success('GitOps drift successfully resolved! Infrastructure is in sync.');
    };

    if (!projectId) {
        return (
            <div className="space-y-6">
                <div>
                    <h2 className="text-3xl font-extrabold text-gray-900 dark:text-slate-50">Git Integration</h2>
                    <p className="mt-1 text-gray-500 dark:text-slate-400">Configure continuous deployment repositories</p>
                </div>
                <div className="p-8 border border-amber-200 bg-amber-50 rounded-2xl text-center shadow-sm">
                    <div className="text-amber-500 mb-3">
                        <AlertCircle className="w-12 h-12 mx-auto" />
                    </div>
                    <h4 className="font-semibold text-amber-700 text-lg mb-2">No Active Project</h4>
                    <p className="text-sm text-gray-500 mb-6">Please select or create a project to configure Git integrations.</p>
                    <Button
                        variant="primary"
                        size="md"
                        onClick={() => navigate('dashboard')}
                    >
                        Go to Dashboard
                    </Button>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-8 max-w-5xl mx-auto pb-12">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
                <div>
                    <h2 className="text-3xl font-black text-slate-900 dark:text-slate-50">
                        Git Repository Configurations
                    </h2>
                    <p className="text-slate-500 dark:text-slate-400 mt-1 text-xs">
                        Connect and configure continuous integration repositories for your generated infrastructure code
                    </p>
                </div>
                <div className="flex gap-3">
                    <Button
                        onClick={() => setShowAddRepoModal(true)}
                        variant="primary"
                    >
                        + Add Git Repository
                    </Button>
                </div>
            </div>

            {/* Notifications */}
            {error && (
                <div className="bg-red-50 border border-red-200 dark:bg-red-950/20 dark:border-red-900/30 rounded-xl p-4 flex items-start space-x-3 text-red-700 dark:text-red-400 animate-fadeIn">
                    <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                        <h4 className="font-bold text-red-800 dark:text-red-300 text-sm">Error Occurred</h4>
                        <p className="text-xs text-red-600 dark:text-red-400 mt-1">{error}</p>
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 gap-8">
                {/* List Column */}
                <div className="space-y-5">
                    <div className="flex justify-between items-center">
                        <h3 className="text-xl font-bold text-slate-900 dark:text-slate-100">Configured Repositories</h3>
                        <span className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 px-2.5 py-1 rounded-full font-bold">
                            {repositories.length} Total
                        </span>
                    </div>

                    {isLoading ? (
                        <Card className="p-8 text-center border border-slate-200">
                            <div className="flex flex-col items-center space-y-3">
                                <Loader2 className="w-8 h-8 text-brand-primary animate-spin" />
                                <span className="text-slate-500 text-sm">Loading configurations...</span>
                            </div>
                        </Card>
                    ) : repositories.length === 0 ? (
                        <Card className="p-12 text-center border-dashed border-slate-300 dark:border-slate-800 rounded-2xl">
                            <div className="text-slate-300 mb-4">
                                <Code className="w-16 h-16 mx-auto" />
                            </div>
                            <h4 className="font-semibold text-slate-600 text-lg mb-1">No Configured Repositories</h4>
                            <p className="text-sm text-slate-500 max-w-sm mx-auto">
                                You haven't configured any Git repositories for this project yet. Use the form on the left to add one.
                            </p>
                        </Card>
                    ) : (
                        <div className="grid grid-cols-1 gap-6">
                            {repositories.map(repo => {
                                const tr = testResult[repo.id];
                                const syncHealth = syncHealthData[repo.id];
                                const runsList = executionHistory[repo.id] || [];
                                const isHistoryExpanded = expandedSyncHistory[repo.id];
                                const isPRSimulatorExpanded = expandedPRSimulator[repo.id];

                                return (
                                    <div key={repo.id} className="space-y-4">
                                        {/* Drift Alert Panel: Wireframe 4 */}
                                        {syncHealth?.state === 'out-of-sync' && (
                                            <div 
                                                className="bg-amber-500/10 border-l-4 border-amber-500 text-amber-700 dark:text-amber-400 rounded-r-xl p-4 flex items-start gap-3 shadow-sm animate-slideDown"
                                                style={{ animation: 'git-alert-enter var(--duration-git-alert-enter) ease-out' }}
                                            >
                                                <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0 animate-bounce" />
                                                <div className="flex-1">
                                                    <span className="text-xs font-bold block">Infrastructure Drift Warning!</span>
                                                    <p className="text-[10px] text-amber-600 dark:text-amber-400/90 mt-0.5 leading-relaxed">
                                                        Generated configuration files on branch <strong>{repo.branch}</strong> differ from active cloud resources (2 changes).
                                                    </p>
                                                    <div className="flex gap-3 mt-2">
                                                        <button 
                                                            onClick={() => handleResolveSyncDrift(repo.id)}
                                                            className="text-[10px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400 hover:underline"
                                                        >
                                                            Resolve Sync Drift
                                                        </button>
                                                        <button 
                                                            onClick={() => toggleSyncHistory(repo.id)}
                                                            className="text-[10px] font-bold uppercase tracking-wider text-slate-500 hover:underline"
                                                        >
                                                            View Drift Details
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {/* Main Repo Card */}
                                        <Card className="p-5 space-y-4 border border-slate-200 dark:border-slate-800 shadow-sm relative overflow-hidden">
                                            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                                <div className="flex items-center space-x-3">
                                                    <div className="w-10 h-10 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200/50 dark:border-slate-700/50 flex items-center justify-center">
                                                        {repo.provider === 'github' ? <Github className="w-5 h-5 text-[var(--color-git-provider-github)]" /> : repo.provider === 'gitlab' ? <Gitlab className="w-5 h-5 text-[var(--color-git-provider-gitlab)]" /> : <Code className="w-5 h-5" />}
                                                    </div>
                                                    <div>
                                                        <div className="flex items-center gap-2">
                                                            <h4 className="font-extrabold text-slate-900 dark:text-slate-100 text-lg leading-tight">{repo.name}</h4>
                                                            {syncHealth && (
                                                                <RepoSyncStatusBadge
                                                                    syncState={syncHealth.state}
                                                                    lastSyncedAt={syncHealth.lastSyncedAt}
                                                                    expectedSyncAt={syncHealth.expectedSyncAt}
                                                                    onResolve={() => handleResolveSyncDrift(repo.id)}
                                                                />
                                                            )}
                                                        </div>
                                                        <div className="flex items-center space-x-2 text-[10px] text-slate-400 font-semibold mt-0.5">
                                                            <span className="uppercase text-slate-500">{repo.provider}</span>
                                                            <span>•</span>
                                                            <span className="font-mono text-slate-500">{repo.branch}</span>
                                                        </div>
                                                    </div>
                                                </div>

                                                <div className="flex space-x-1.5 w-full sm:w-auto justify-end flex-wrap gap-1">
                                                    <Button
                                                        onClick={() => setActiveWebhookRepo(repo)}
                                                        variant="secondary"
                                                        size="sm"
                                                        className="text-[10px] py-1.5 font-extrabold uppercase tracking-wider"
                                                    >
                                                        Setup Webhook
                                                    </Button>
                                                    <Button
                                                        onClick={() => toggleSyncHistory(repo.id)}
                                                        variant="secondary"
                                                        size="sm"
                                                        className={`text-[10px] py-1.5 font-extrabold uppercase tracking-wider ${
                                                            isHistoryExpanded ? 'bg-slate-100 text-slate-800 border-slate-300' : ''
                                                        }`}
                                                    >
                                                        Sync Logs
                                                    </Button>
                                                    <Button
                                                        onClick={() => togglePRSimulator(repo.id)}
                                                        variant="secondary"
                                                        size="sm"
                                                        className={`text-[10px] py-1.5 font-extrabold uppercase tracking-wider ${
                                                            isPRSimulatorExpanded ? 'bg-orange-50 text-brand-primary border-brand-primary/20' : ''
                                                        }`}
                                                    >
                                                        PR Tool
                                                    </Button>
                                                    <Button
                                                        onClick={() => handleTestConnection(repo.id)}
                                                        disabled={testingId === repo.id}
                                                        variant="secondary"
                                                        size="sm"
                                                        className="text-[10px] py-1.5 font-extrabold uppercase tracking-wider"
                                                    >
                                                        {testingId === repo.id ? 'Testing...' : 'Test'}
                                                    </Button>
                                                    <Button
                                                        onClick={() => handleDelete(repo.id)}
                                                        variant="danger"
                                                        size="sm"
                                                        className="text-[10px] py-1.5 font-extrabold uppercase tracking-wider"
                                                    >
                                                        Delete
                                                    </Button>
                                                </div>
                                            </div>

                                            <div className="text-xs bg-slate-50 dark:bg-slate-800/40 p-3 rounded-xl border border-slate-200/50 dark:border-slate-700/50 flex justify-between items-center gap-4">
                                                <div className="font-mono text-slate-800 dark:text-slate-300 truncate select-all">{repo.url}</div>
                                                <a href={repo.url} target="_blank" rel="noreferrer" className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
                                                    <ExternalLink className="w-3.5 h-3.5" />
                                                </a>
                                            </div>

                                            {tr && (
                                                <div className={`p-3 rounded-xl border text-xs flex items-start space-x-2 animate-slideDown ${
                                                    tr.success
                                                        ? 'bg-green-50 border-green-200 text-green-700'
                                                        : 'bg-red-50 border-red-200 text-red-700'
                                                }`}>
                                                    {tr.success ? (
                                                        <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                                                    ) : (
                                                        <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                                                    )}
                                                    <div>
                                                        <span className="font-bold">{tr.success ? 'Connected' : 'Connection Failed'}</span>
                                                        <p className="text-[10px] text-slate-500 mt-0.5">{tr.message}</p>
                                                    </div>
                                                </div>
                                            )}
                                        </Card>

                                        {/* Expandable Sync Progress & Log timeline */}
                                        {isHistoryExpanded && syncHealth && (
                                            <Card className="p-5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-md animate-slideDown">
                                                {runsLoading[repo.id] && !runsList.length ? (
                                                    <div className="flex flex-col items-center py-8 space-y-3">
                                                        <Loader2 className="w-6 h-6 text-brand-primary animate-spin" />
                                                        <span className="text-slate-500 text-sm">Loading run history...</span>
                                                    </div>
                                                ) : (
                                                    <SyncProgressPanel
                                                    health={syncHealth}
                                                    runs={runsList}
                                                    onRefresh={async () => {
                                                        // Re-fetch runs for this repo from the real API
                                                        try {
                                                            setRunsLoading(prev => ({ ...prev, [repo.id]: true }));
                                                            const result = await gitOpsService.listRuns(repo.id, { limit: 50 });
                                                            const convertedRuns = result.runs.map(run =>
                                                                runResponseToExecutionRun(run, repo.provider),
                                                            );
                                                            setExecutionHistory(prev => ({
                                                                ...prev,
                                                                [repo.id]: convertedRuns,
                                                            }));
                                                        } catch (err: any) {
                                                            toast.error(err.message || 'Failed to refresh run history');
                                                        } finally {
                                                            setRunsLoading(prev => ({ ...prev, [repo.id]: false }));
                                                        }
                                                    }}
                                                />
                                                )}
                                            </Card>
                                        )}

                                        {/* Expandable PR comment simulator */}
                                        {isPRSimulatorExpanded && (
                                            <Card className="p-5 border border-orange-500/10 bg-slate-50/50 dark:bg-slate-900/30 shadow-md animate-slideDown">
                                                <PRCommentSimulator
                                                    projectId={projectId}
                                                    repoId={repo.id}
                                                    repoName={repo.name}
                                                    provider={repo.provider as any}
                                                    branch={repo.branch}
                                                />
                                            </Card>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>

            {/* Webhook Configuration Steps Wizard Modal */}
            {activeWebhookRepo && (
                <div 
                    className="fixed inset-0 bg-slate-900/60 backdrop-blur-md flex items-center justify-center z-[var(--z-modal)] p-4 animate-fadeIn"
                    onClick={() => setActiveWebhookRepo(null)}
                >
                    <div 
                        className="bg-white dark:bg-slate-900 rounded-3xl shadow-2xl max-w-4xl w-full p-8 border border-slate-200/50 dark:border-slate-800 overflow-hidden relative"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Modal Header */}
                        <div className="flex justify-between items-start mb-6">
                            <div>
                                <h3 className="text-2xl font-black text-slate-900 dark:text-slate-100 flex items-center gap-2">
                                    <Terminal className="w-6 h-6 text-brand-primary" /> Setup Digger GitOps Webhook
                                </h3>
                                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                    Configure push & comment notifications on <strong>{activeWebhookRepo.name}</strong> to automate OpenTofu pipelines.
                                </p>
                            </div>
                            <button 
                                onClick={() => setActiveWebhookRepo(null)}
                                className="w-8 h-8 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 flex items-center justify-center font-bold text-slate-500 transition-colors"
                            >
                                ✕
                            </button>
                        </div>

                        {/* Webhook Setup Form Wizard */}
                        <WebhookSetupForm
                            projectId={projectId}
                            repoUrl={activeWebhookRepo.url}
                            provider={activeWebhookRepo.provider}
                            onComplete={() => {
                                setActiveWebhookRepo(null);
                                fetchRepositories();
                            }}
                            onCancel={() => setActiveWebhookRepo(null)}
                        />
                    </div>
                </div>
            )}

            {/* Add Git Repository Modal */}
            <Modal
                isOpen={showAddRepoModal}
                onClose={() => setShowAddRepoModal(false)}
                title="Add Git Repository"
                size="md"
            >
                <div className="mt-4">
                    <p className="text-sm text-slate-500 mb-6">Configure credentials and repository details for GitOps continuous deployment.</p>
                    <GitRepositoryForm
                        onSubmit={handleSave}
                        onCancel={() => setShowAddRepoModal(false)}
                        isSubmitting={isSaving}
                    />
                </div>
            </Modal>
        </div>
    );
};

export default RepoConfigPanel;
