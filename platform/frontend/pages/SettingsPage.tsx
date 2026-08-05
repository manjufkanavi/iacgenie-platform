import React, { useState, useEffect } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import Input from '../ui/Input';
import { useAppStore } from '../store/useAppStore';
import { useProjectStore } from '../store/useProjectStore';
import SettingsPanel from './SettingsPanel';
import EditableProjectInfo from './EditableProjectInfo'
import TeamMemberForm from '../forms/TeamMemberForm';
import { projectService } from '../services/projectService';
import { toast } from 'react-hot-toast';
import { ShieldAlert, Sliders, Cloud, Puzzle, Settings, Brain, GitCommit, Users, X, FolderPlus } from 'lucide-react';
import RepoConfigPanel from '../settings/RepoConfigPanel';
import PageHeader from '../layout/PageHeader';
import ModelConfigPanel from './ModelConfigPanel';
import TeamMemberItem from '../list-items/TeamMemberItem';
import CloudCredentialsSettings from '../settings/CloudCredentialsSettings';
import IntegrationForm from '../forms/IntegrationForm';
import IntegrationItem from '../list-items/IntegrationItem';

const SettingsPage: React.FC = () => {
    const { currentProject, setProject } = useAppStore();
    const { currentProjectId } = useProjectStore();
    const projectId = currentProjectId || currentProject?.id || '';

    const [activeSection, setActiveSection] = useState<string>(() => {
        const hash = window.location.hash.slice(1);
        if (hash && ['project', 'model-config', 'git', 'team', 'tuning', 'cloud-credentials', 'integrations'].includes(hash)) {
            return hash;
        }
        const params = new URLSearchParams(window.location.search);
        const section = params.get('section');
        if (section && ['project', 'model-config', 'git', 'team', 'tuning', 'cloud-credentials', 'integrations'].includes(section)) {
            return section;
        }
        return 'project';
    });

    useEffect(() => {
        const handleHashChange = () => {
            const hash = window.location.hash.slice(1);
            if (hash && ['project', 'model-config', 'git', 'team', 'tuning', 'cloud-credentials', 'integrations'].includes(hash)) {
                setActiveSection(hash);
            }
        };
        window.addEventListener('hashchange', handleHashChange);
        return () => window.removeEventListener('hashchange', handleHashChange);
    }, []);

    // Fine-Tuning State
    const [maxRetries, setMaxRetries] = useState(3);
    const [temperature, setTemperature] = useState(0.2);
    const [llmSelection, setLlmSelection] = useState('gemini-1.5-pro');

    // Create Project Modal State
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [newProjectName, setNewProjectName] = useState('');
    const [newProjectDescription, setNewProjectDescription] = useState('');
    const [isCreatingProject, setIsCreatingProject] = useState(false);

    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const [isArchiveModalOpen, setIsArchiveModalOpen] = useState(false);
    const [isArchiving, setIsArchiving] = useState(false);
    const [deleteConfirmation, setDeleteConfirmation] = useState('');
    const [archiveConfirmation, setArchiveConfirmation] = useState('');

    const { hasProjectEditAccess } = useAppStore();

    const handleDeleteProject = async () => {
        const targetName = currentProject?.name || 'Untitled Project';
        if (deleteConfirmation !== targetName) {
            toast.error('Project name does not match. Please verify capitalization.');
            return;
        }
        setIsDeleting(true);
        try {
            await projectService.deleteProject(projectId);
            toast.success(`Project "${targetName}" deleted successfully!`);
            setIsDeleteModalOpen(false);
            setDeleteConfirmation('');
            useAppStore.setState({ currentProject: null });
            useProjectStore.getState().setCurrentProjectId('');
            localStorage.removeItem('currentProjectId');
        } catch (error: any) {
            toast.error(error.message || 'Failed to delete project');
        } finally {
            setIsDeleting(false);
        }
    };

    const handleArchiveProject = async () => {
        const targetName = currentProject?.name || 'Untitled Project';
        if (archiveConfirmation !== targetName) {
            toast.error('Project name does not match. Please verify capitalization.');
            return;
        }
        setIsArchiving(true);
        try {
            await projectService.updateProject(projectId, { archived: true } as any);
            toast.success(`Project "${targetName}" archived successfully!`);
            setIsArchiveModalOpen(false);
            setArchiveConfirmation('');
            useAppStore.setState({ currentProject: null });
            useProjectStore.getState().setCurrentProjectId('');
            localStorage.removeItem('currentProjectId');
        } catch (error: any) {
            toast.error(error.message || 'Failed to archive project');
        } finally {
            setIsArchiving(false);
        }
    };

    const openCreateModal = () => {
        setNewProjectName('');
        setNewProjectDescription('');
        setIsCreateModalOpen(true);
    };

    const handleCreateProject = async () => {
        if (isCreatingProject) return;
        const trimmedName = newProjectName.trim();
        if (!trimmedName) {
            toast.error('Please enter a project name.');
            return;
        }
        setIsCreatingProject(true);
        try {
            const newProject = await projectService.createProject({
                name: trimmedName,
                description: newProjectDescription.trim() || undefined,
            });
            if (!newProject || !newProject.id) {
                throw new Error('Project was created but no valid project ID was returned from the server.');
            }
            // Update store: set as current project and add to projects list
            setProject(newProject);
            localStorage.setItem('currentProjectId', newProject.id);
            // Sync with useProjectStore
            useProjectStore.getState().setCurrentProjectId(newProject.id);
            // Update the projects array in the app store
            const storeState = useAppStore.getState();
            const updatedProjects = [...(storeState.projects || []).filter(p => p.id !== newProject.id), newProject];
            useAppStore.setState({ projects: updatedProjects });
            // Persist to localStorage
            localStorage.setItem('projects', JSON.stringify(updatedProjects));
            setIsCreateModalOpen(false);
            toast.success(`Project "${newProject.name}" created successfully!`);
        } catch (error: any) {
            toast.error(error.message || 'Failed to create project');
        } finally {
            setIsCreatingProject(false);
        }
    };

    // Inline nav items for sub-sections (no internal sidebar)

    const settingsNavItems = [
        { id: 'project', label: 'Project Info', icon: <Settings className="w-5 h-5" /> },
        { id: 'model-config', label: 'AI Models', icon: <Brain className="w-5 h-5" /> },
        { id: 'git', label: 'Git Repositories', icon: <GitCommit className="w-5 h-5" /> },
        { id: 'team', label: 'Team Members', icon: <Users className="w-5 h-5" /> },
        { id: 'tuning', label: 'Agent Tuning', icon: <Sliders className="w-5 h-5" /> },
        { id: 'cloud-credentials', label: 'Cloud Credentials', icon: <Cloud className="w-5 h-5" /> },
        { id: 'integrations', label: 'Integrations', icon: <Puzzle className="w-5 h-5" /> },
    ];

    const renderSection = () => {
        switch (activeSection) {
            case 'project':
                return (
                    <div className="space-y-6">
                        {currentProject ? (
                            hasProjectEditAccess(currentProject.id) ? <EditableProjectInfo /> : (
                                <div className="text-center py-8">
                                    <p className="text-red-500 font-semibold">You do not have permission to edit this project. Only owners and admins can modify project info.</p>
                                    <EditableProjectInfo readOnly={true} onChange={() => {}} />
                                </div>
                            )
                        ) : (
                            <div className="flex flex-col items-center justify-center py-12">
                                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-primary/10 to-red-500/10 flex items-center justify-center mb-4">
                                    <FolderPlus className="w-8 h-8 text-brand-primary" />
                                </div>
                                <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">No Project Yet</h3>
                                <p className="text-slate-500 dark:text-slate-400 mb-6 text-center max-w-sm">Create your first project to start generating and managing infrastructure as code.</p>
                                <Button
                                    onClick={openCreateModal}
                                    className="flex items-center gap-2"
                                >
                                    <FolderPlus className="w-4 h-4" />
                                    Create Project
                                </Button>
                            </div>
                        )}
                    </div>
                );

            case 'model-config':
                return <ModelConfigPanel />;

            case 'git':
                return <RepoConfigPanel />;

            case 'team':
                return (
                    <SettingsPanel
                        section="teamMembers"
                        title="Team Members"
                        subtitle="Manage team member access and permissions for this project."
                        icon={<Users className="w-5 h-5" />}
                        renderForm={(onSubmit, onCancel, initialData, isSubmitting) => (
                            <TeamMemberForm
                                onSubmit={onSubmit}
                                onCancel={onCancel}
                                initialData={initialData}
                                isSubmitting={isSubmitting}
                            />
                        )}
                        renderListItem={(item, onEdit, onDelete) => (
                            <TeamMemberItem
                                item={item}
                                onEdit={onEdit}
                                onDelete={onDelete}
                            />
                        )}
                    />
                );

            case 'tuning':
                return (
                    <div className="space-y-6" data-testid="settings-tuning-panel">
                        <div className="flex items-center gap-2 mb-4">
                            <Sliders className="w-5 h-5 text-brand-primary" />
                            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-50">Generator Agent Tuning</h2>
                        </div>
                        <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                            Fine-tune the generative parameters and threshold policies of the Iacgenie Orchestrator Agent.
                        </p>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
                            {/* LLM Selection */}
                            <div className="flex flex-col gap-2">
                                <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Primary Generator LLM</label>
                                <select
                                    value={llmSelection}
                                    onChange={(e) => setLlmSelection(e.target.value)}
                                    className="p-3 border border-slate-200 dark:border-slate-600 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-brand-primary font-semibold"
                                >
                                    <option value="gemini-1.5-pro">Gemini 1.5 Pro (Recommended)</option>
                                    <option value="gemini-1.5-flash">Gemini 1.5 Flash (Ultra Fast)</option>
                                    <option value="claude-3.5-sonnet">Claude 3.5 Sonnet</option>
                                    <option value="gpt-4o">GPT-4o</option>
                                </select>
                            </div>

                            {/* Max Retries */}
                            <div className="flex flex-col gap-2">
                                <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Retry Policy Threshold</label>
                                <input
                                    type="number"
                                    min={1}
                                    max={10}
                                    value={maxRetries}
                                    onChange={(e) => setMaxRetries(Number(e.target.value))}
                                    className="p-3 border border-slate-200 dark:border-slate-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-primary font-semibold"
                                />
                            </div>
                        </div>

                        {/* Sliders for Temperature */}
                        <div className="flex flex-col gap-2 mt-4">
                            <div className="flex justify-between items-center">
                                <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Agent Core Temperature</label>
                                <span className="text-sm font-extrabold text-brand-primary">{temperature}</span>
                            </div>
                            <input
                                type="range"
                                min={0.0}
                                max={1.0}
                                step={0.05}
                                value={temperature}
                                onChange={(e) => setTemperature(Number(e.target.value))}
                                className="w-full h-2 bg-slate-100 dark:bg-slate-700/50 rounded-lg appearance-none cursor-pointer accent-brand-primary"
                            />
                            <div className="flex justify-between text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase mt-1">
                                <span>Precise & Strict</span>
                                <span>Creative & Broad</span>
                            </div>
                        </div>

                        <div className="pt-4 border-t border-slate-100 dark:border-slate-600 flex justify-end">
                            <button
                                onClick={async () => {
                                    if (!projectId) { toast.error('No project selected'); return; }
                                    try {
                                        await projectService.updateProject(projectId, {
                                            tuningConfig: { maxRetries, temperature, llmSelection }
                                        } as any);
                                        toast.success('Agent fine-tuning preferences saved successfully!');
                                    } catch (error: any) {
                                        toast.error(error.message || 'Failed to save tuning configuration');
                                    }
                                }}
                                className="px-5 py-2.5 bg-gradient-to-r from-brand-primary to-red-500 text-white rounded-xl text-xs font-extrabold uppercase tracking-wider hover:from-brand-primary/90 hover:to-red-600 transition shadow-md"
                            >
                                Save Tuning Configurations
                            </button>
                        </div>
                    </div>
                );

            case 'cloud-credentials':
                return <CloudCredentialsSettings />;

            case 'integrations':
                return (
                    <SettingsPanel
                        section="integrations"
                        title="Integrations"
                        subtitle="Connect external services and tools to your project."
                        icon={<Puzzle className="w-5 h-5" />}
                        renderForm={(onSubmit, onCancel, initialData, isSubmitting) => (
                            <IntegrationForm
                                onSubmit={onSubmit}
                                onCancel={onCancel}
                                initialData={initialData}
                                isSubmitting={isSubmitting}
                            />
                        )}
                        renderListItem={(item, onEdit, onDelete) => (
                            <IntegrationItem
                                item={item}
                                onEdit={onEdit}
                                onDelete={onDelete}
                            />
                        )}
                    />
                );

            default:
                return null;
        }
    };

    const sectionTitleMap: Record<string, string> = {
        'project': 'Project Information',
        'model-config': 'Model Configuration',
        'git': 'Git Repository',
        'team': 'Team Access',
        'tuning': 'Agent Tuning parameters',
        'cloud-credentials': 'Cloud Credentials',
        'integrations': 'Integrations'
    };

    const sectionSubtitleMap: Record<string, string> = {
        'project': 'Manage project name and description.',
        'model-config': currentProject ? 'Configure AI models for code generation.' : 'Create a project first to configure models.',
        'git': currentProject ? 'Connect to your source control.' : 'Create a project first to connect Git repositories.',
        'team': currentProject ? 'Manage who can access this project.' : 'Create a project first to manage team access.',
        'tuning': 'Tune retry policy rates, LLM preferences, and model settings.',
        'cloud-credentials': currentProject ? 'Manage cloud provider credentials.' : 'Create a project first to manage cloud credentials.',
        'integrations': currentProject ? 'Connect external services and tools.' : 'Create a project first to manage integrations.'
    };

    return (
        <div className="space-y-6" data-testid="settings-page">
            {/* Harmonized Page Header with Breadcrumbs */}
            <PageHeader 
                title={sectionTitleMap[activeSection] || 'Project Settings'} 
                subtitle={sectionSubtitleMap[activeSection] || 'Manage your project configuration.'} 
            />

            {/* Premium Glassmorphic Navigation Tabs */}
            <div className="bg-white/60 backdrop-blur-md border border-slate-200/50 dark:border-slate-600/50 rounded-2xl p-1.5 shadow-sm">
                <nav className="flex gap-1.5 overflow-x-auto scrollbar-none" data-testid="settings-nav-tabs" role="tablist" aria-label="Settings sections">
                    {settingsNavItems.map((item) => {
                        const isActive = activeSection === item.id;
                        return (
                            <button
                                key={item.id}
                                role="tab"
                                aria-selected={isActive}
                                aria-controls="settings-tab-panel"
                                onClick={() => setActiveSection(item.id)}
                                onKeyDown={(e) => {
                                    const indices = settingsNavItems.map(i => i.id);
                                    const currentIndex = indices.indexOf(item.id);
                                    if (e.key === 'ArrowRight') {
                                        e.preventDefault();
                                        setActiveSection(settingsNavItems[(currentIndex + 1) % indices.length].id);
                                    } else if (e.key === 'ArrowLeft') {
                                        e.preventDefault();
                                        setActiveSection(settingsNavItems[(currentIndex - 1 + indices.length) % indices.length].id);
                                    }
                                }}
                                className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-xl transition-all duration-300 whitespace-nowrap ${
                                    isActive
                                        ? 'bg-gradient-to-r from-brand-primary/10 to-red-500/10 text-brand-primary border border-brand-primary/20 shadow-sm'
                                        : 'border border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-50/50 dark:hover:bg-slate-700/50'
                                }`}
                                data-testid={`settings-nav-${item.id}`}
                            >
                                <span className={`w-5 h-5 flex items-center justify-center transition-transform duration-300 ${isActive ? 'scale-110' : ''}`}>{item.icon}</span>
                                {item.label}
                            </button>
                        );
                    })}
                </nav>
            </div>

            {/* Section Content */}
            <div id="settings-tab-panel" role="tabpanel" aria-label={`${sectionTitleMap[activeSection]} settings`} data-testid="settings-tab-panel">
            {renderSection()}
            </div>

            {/* Danger Zone */}
            {currentProject && (
                <Card className="border-red-500/50">
                    <h2 className="text-lg font-semibold text-red-600">Danger Zone</h2>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">These actions are destructive and cannot be undone.</p>
                    <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between border-t border-slate-200 dark:border-slate-600 pt-4">
                        <div>
                            <h3 className="font-semibold text-slate-900 dark:text-slate-50">Archive this project</h3>
                            <p className="text-sm text-slate-500 dark:text-slate-400">Mark this project as read-only and hide it from lists.</p>
                        </div>
                        <Button variant="secondary" className="mt-2 sm:mt-0" onClick={() => setIsArchiveModalOpen(true)}>Archive Project</Button>
                    </div>
                    <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between border-t border-slate-200 dark:border-slate-600 pt-4">
                        <div>
                            <h3 className="font-semibold text-slate-900 dark:text-slate-50">Delete this project</h3>
                            <p className="text-sm text-slate-500 dark:text-slate-400">Permanently remove the project and all its data.</p>
                        </div>
                        <Button variant="danger" className="mt-2 sm:mt-0" onClick={() => setIsDeleteModalOpen(true)}>Delete Project</Button>
                    </div>
                </Card>
            )}

            {/* Archive Confirmation Modal */}
            {isArchiveModalOpen && (
                <div
                    className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
                    onClick={() => setIsArchiveModalOpen(false)}
                >
                    <div
                        className="bg-white rounded-xl shadow-xl max-w-md w-full p-6"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="flex items-center gap-3">
                            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-amber-100">
                                <ShieldAlert className="w-6 h-6 text-amber-600" />
                            </div>
                            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-50">Archive Project</h3>
                        </div>
                        <p className="text-sm text-slate-500 dark:text-slate-400 mt-3">
                            Archiving <strong>{currentProject?.name || 'Untitled Project'}</strong> will mark it as read-only and hide it from project lists. This action can be reversed later.
                        </p>
                        <div className="mt-4">
                            <label htmlFor="archive-confirm" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
                                To confirm, type "{currentProject?.name || 'Untitled Project'}"
                            </label>
                            <Input
                                label=""
                                id="archive-confirm"
                                value={archiveConfirmation}
                                onChange={e => setArchiveConfirmation(e.target.value)}
                                className="w-full mt-2"
                            />
                        </div>
                        <div className="mt-5 flex gap-3 justify-end">
                            <Button variant="secondary" onClick={() => setIsArchiveModalOpen(false)}>Cancel</Button>
                            <Button variant="danger" onClick={handleArchiveProject} disabled={archiveConfirmation !== (currentProject?.name || 'Untitled Project') || isArchiving}>
                                {isArchiving ? 'Archiving...' : 'Archive Project'}
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            {/* Delete Confirmation Modal */}
            {isDeleteModalOpen && (
                <div
                    className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
                    onClick={() => setIsDeleteModalOpen(false)}
                >
                    <div
                        className="bg-white rounded-xl shadow-xl max-w-md w-full p-6"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="flex items-center gap-3">
                            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
                                <ShieldAlert className="w-6 h-6 text-red-600" />
                            </div>
                            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-50">Delete Project</h3>
                        </div>
                        <p className="text-sm text-slate-500 dark:text-slate-400 mt-3">
                            This action cannot be undone. This will permanently delete the <strong>{currentProject?.name || 'Untitled Project'}</strong> project, including all associated generations and deployments.
                        </p>
                        <div className="mt-4">
                            <label htmlFor="delete-confirm" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
                                To confirm, type "{currentProject?.name || 'Untitled Project'}"
                            </label>
                            <Input
                                label=""
                                id="delete-confirm"
                                value={deleteConfirmation}
                                onChange={e => setDeleteConfirmation(e.target.value)}
                                className="w-full mt-2"
                            />
                        </div>
                        <div className="mt-5 flex gap-3 justify-end">
                            <Button variant="secondary" onClick={() => setIsDeleteModalOpen(false)}>Cancel</Button>
                            <Button variant="danger" onClick={handleDeleteProject} disabled={deleteConfirmation !== (currentProject?.name || 'Untitled Project') || isDeleting}>
                                {isDeleting ? 'Deleting...' : 'Delete Project'}
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            {/* Create Project Modal */}
            {isCreateModalOpen && (
                <div
                    className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
                    onClick={() => !isCreatingProject && setIsCreateModalOpen(false)}
                >
                    <div
                        className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl max-w-lg w-full p-8 border border-slate-200/50 dark:border-slate-700/50"
                        onClick={e => e.stopPropagation()}
                    >
                        {/* Modal Header */}
                        <div className="flex items-center justify-between mb-6">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-primary to-red-500 flex items-center justify-center shadow-md">
                                    <FolderPlus className="w-5 h-5 text-white" />
                                </div>
                                <div>
                                    <h3 className="text-lg font-bold text-slate-900 dark:text-slate-50">Create New Project</h3>
                                    <p className="text-xs text-slate-500 dark:text-slate-400">Set up your infrastructure project</p>
                                </div>
                            </div>
                            <button
                                onClick={() => !isCreatingProject && setIsCreateModalOpen(false)}
                                className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                                aria-label="Close"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>

                        {/* Form */}
                        <div className="space-y-5">
                            <div>
                                <label htmlFor="new-project-name" className="block text-sm font-semibold text-slate-700 dark:text-slate-200 mb-1.5">
                                    Project Name <span className="text-red-500">*</span>
                                </label>
                                <input
                                    id="new-project-name"
                                    type="text"
                                    value={newProjectName}
                                    onChange={e => setNewProjectName(e.target.value)}
                                    onKeyDown={e => e.key === 'Enter' && !isCreatingProject && handleCreateProject()}
                                    placeholder="e.g. Production AWS Infrastructure"
                                    autoFocus
                                    disabled={isCreatingProject}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700/50 text-slate-900 dark:text-slate-50 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-primary/40 focus:border-brand-primary transition text-sm"
                                />
                            </div>
                            <div>
                                <label htmlFor="new-project-description" className="block text-sm font-semibold text-slate-700 dark:text-slate-200 mb-1.5">
                                    Purpose / Description
                                    <span className="ml-2 text-xs font-normal text-slate-400">(optional)</span>
                                </label>
                                <textarea
                                    id="new-project-description"
                                    value={newProjectDescription}
                                    onChange={e => setNewProjectDescription(e.target.value)}
                                    placeholder="What is this project for? e.g. Manages all Terraform configurations for our production VPC..."
                                    rows={3}
                                    disabled={isCreatingProject}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700/50 text-slate-900 dark:text-slate-50 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-primary/40 focus:border-brand-primary transition text-sm resize-none"
                                />
                            </div>
                        </div>

                        {/* Actions */}
                        <div className="mt-7 flex gap-3 justify-end">
                            <Button
                                variant="secondary"
                                onClick={() => setIsCreateModalOpen(false)}
                                disabled={isCreatingProject}
                            >
                                Cancel
                            </Button>
                            <button
                                onClick={handleCreateProject}
                                disabled={isCreatingProject || !newProjectName.trim()}
                                className="px-6 py-2.5 bg-gradient-to-r from-brand-primary to-red-500 text-white rounded-xl text-sm font-bold hover:from-brand-primary/90 hover:to-red-600 transition shadow-md disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {isCreatingProject ? (
                                    <>
                                        <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                                        </svg>
                                        Creating...
                                    </>
                                ) : (
                                    <>
                                        <FolderPlus className="w-4 h-4" />
                                        Create Project
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default SettingsPage;
