import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { AlertCircle, CheckCircle2, Loader2, Plus } from 'lucide-react';
import Button from './ui/Button';
import Modal from './ui/Modal';
import { useProjectSettingsStore } from '../store/useProjectSettingsStore';
import { useAppStore } from '../store/useAppStore';
import { useProjectStore } from '../store/useProjectStore';

interface SettingsPanelProps {
    section: 'modelConfigs' | 'gitRepositories' | 'cloudCredentials' | 'teamMembers' | 'integrations';
    title: string;
    subtitle: string;
    icon: React.ReactNode;
    renderForm: (onSubmit: (data: any) => Promise<void>, onCancel: () => void, initialData?: any, isSubmitting?: boolean) => React.ReactNode;
    /** Returns the list item element. Receives (item, onEdit, onDelete, onTest). */
    renderListItem: (item: any, onEdit: () => void, onDelete: () => void, onTest?: () => void, disableActions?: boolean) => React.ReactNode;
    hasTestFunction?: boolean;
    /** Custom delete handler. Returns true if item was deleted. Falls back to window.confirm if not provided. */
    onDeleteItem?: (item: any) => Promise<boolean>;
    /** Called when a verify/test action is triggered from the list (e.g., table Verify button). */
    onVerifyItem?: (item: any) => Promise<any>;
    /** When true, action buttons are disabled. */
    readOnly?: boolean;
}

const SettingsPanel: React.FC<SettingsPanelProps> = ({
    section,
    title,
    subtitle,
    icon,
    renderForm,
    renderListItem,
    hasTestFunction = false,
    onDeleteItem,
    onVerifyItem,
    readOnly = false
}) => {
    const { currentProjectId } = useProjectStore();
    const projectSettingsStore = useProjectSettingsStore();
    
    // Get the appropriate data and functions from the store
    const getSectionData = () => {
        switch (section) {
            case 'modelConfigs':
                return {
                    items: projectSettingsStore.modelConfigs,
                    isLoading: projectSettingsStore.isLoading.modelConfigs,
                    error: projectSettingsStore.errors.modelConfigs,
                    fetchItems: () => projectSettingsStore.fetchModelConfigs(currentProjectId || 'default-project'),
                    deleteItem: (id: string) => projectSettingsStore.deleteModelConfig(currentProjectId || 'default-project', id),
                    testItem: (id: string) => projectSettingsStore.testModelConfig(currentProjectId || 'default-project', id)
                };
            case 'gitRepositories':
                return {
                    items: projectSettingsStore.gitRepositories,
                    isLoading: projectSettingsStore.isLoading.gitRepositories,
                    error: projectSettingsStore.errors.gitRepositories,
                    fetchItems: () => projectSettingsStore.fetchGitRepositories(currentProjectId || 'default-project'),
                    deleteItem: (id: string) => projectSettingsStore.deleteGitRepository(currentProjectId || 'default-project', id),
                    testItem: (id: string) => projectSettingsStore.testGitRepository(currentProjectId || 'default-project', id)
                };
            case 'cloudCredentials':
                return {
                    items: projectSettingsStore.cloudCredentials,
                    isLoading: projectSettingsStore.isLoading.cloudCredentials,
                    error: projectSettingsStore.errors.cloudCredentials,
                    fetchItems: () => projectSettingsStore.fetchCloudCredentials(currentProjectId || 'default-project'),
                    deleteItem: (id: string) => projectSettingsStore.deleteCloudCredentials(currentProjectId || 'default-project', id),
                    testItem: (id: string) => projectSettingsStore.testCloudCredentials(currentProjectId || 'default-project', id)
                };
            case 'teamMembers':
                return {
                    items: projectSettingsStore.teamMembers,
                    isLoading: projectSettingsStore.isLoading.teamMembers,
                    error: projectSettingsStore.errors.teamMembers,
                    fetchItems: () => projectSettingsStore.fetchTeamMembers(currentProjectId || 'default-project'),
                    deleteItem: (id: string) => projectSettingsStore.removeTeamMember(currentProjectId || 'default-project', id)
                };
            case 'integrations':
                return {
                    items: projectSettingsStore.integrations,
                    isLoading: projectSettingsStore.isLoading.integrations,
                    error: projectSettingsStore.errors.integrations,
                    fetchItems: () => projectSettingsStore.fetchIntegrations(currentProjectId || 'default-project'),
                    deleteItem: (id: string) => projectSettingsStore.deleteIntegration(currentProjectId || 'default-project', id),
                    testItem: (id: string) => projectSettingsStore.testIntegration(currentProjectId || 'default-project', id)
                };
            default:
                return {
                    items: [],
                    isLoading: false,
                    error: null,
                    fetchItems: () => {},
                    deleteItem: () => {}
                };
        }
    };

    const sectionData = getSectionData();
    
    // Local state
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingItem, setEditingItem] = useState<any>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isTestModalOpen, setIsTestModalOpen] = useState(false);
    const [currentTestResult, setCurrentTestResult] = useState<any>(null);

    // Load data on mount and when project changes
    useEffect(() => {
        if (currentProjectId) {
            sectionData.fetchItems();
        }
    }, [currentProjectId, section]);

    // Clear errors when component unmounts
    useEffect(() => {
        return () => {
            projectSettingsStore.clearErrors(section);
        };
    }, [section]);

    const handleAddNew = () => {
        setEditingItem(null);
        setIsModalOpen(true);
    };

    const handleEdit = (item: any) => {
        setEditingItem(item);
        setIsModalOpen(true);
    };

    const handleDelete = async (item: any) => {
        let confirmed = true;
        if (onDeleteItem) {
            confirmed = await onDeleteItem(item);
        } else if (!window.confirm(`Are you sure you want to delete "${item.name}"? This action cannot be undone.`)) {
            confirmed = false;
        }
        if (!confirmed) return;
        try {
            if (onDeleteItem) {
                // onDeleteItem is responsible for calling the delete API
                await sectionData.deleteItem(item.id);
            } else {
                await sectionData.deleteItem(item.id);
            }
            toast.success('Item deleted successfully');
        } catch (error) {
            toast.error(`Failed to delete item: ${error}`);
        }
    };

    const handleTest = async (item: any) => {
        if (onVerifyItem) {
            try {
                const result = await onVerifyItem(item);
                if (result) {
                    toast.success('Verification completed');
                }
            } catch (error) {
                toast.error(`Verification failed: ${error}`);
            }
            return;
        }
        if (sectionData.testItem) {
            try {
                await sectionData.testItem(item.id);
                // Get the test result from the store
                const testKey = `${section}-${item.id}`;
                const result = projectSettingsStore.testResults[testKey];
                if (result) {
                    setCurrentTestResult(result);
                    setIsTestModalOpen(true);
                } else {
                    toast('Test completed');
                }
            } catch (error) {
                toast.error(`Test failed: ${error}`);
            }
        }
    };

    const handleSubmit = async (data: any): Promise<void> => {
        setIsSubmitting(true);
        try {
            if (editingItem) {
                // Update existing item
                switch (section) {
                    case 'modelConfigs':
                        await projectSettingsStore.updateModelConfig(currentProjectId || 'default-project', editingItem.id, data);
                        break;
                    case 'gitRepositories':
                        await projectSettingsStore.updateGitRepository(currentProjectId || 'default-project', editingItem.id, data);
                        break;
                    case 'cloudCredentials':
                        await projectSettingsStore.updateCloudCredentials(currentProjectId || 'default-project', editingItem.id, data);
                        break;
                    case 'teamMembers':
                        await projectSettingsStore.updateTeamMember(currentProjectId || 'default-project', editingItem.id, data);
                        break;
                    case 'integrations':
                        await projectSettingsStore.updateIntegration(currentProjectId || 'default-project', editingItem.id, data);
                        break;
                }
            } else {
                // Create new item
                switch (section) {
                    case 'modelConfigs':
                        await projectSettingsStore.createModelConfig(currentProjectId || 'default-project', data);
                        break;
                    case 'gitRepositories':
                        await projectSettingsStore.createGitRepository(currentProjectId || 'default-project', data);
                        break;
                    case 'cloudCredentials':
                        await projectSettingsStore.createCloudCredentials(currentProjectId || 'default-project', data);
                        break;
                    case 'teamMembers':
                        await projectSettingsStore.inviteTeamMember(currentProjectId || 'default-project', data);
                        break;
                    case 'integrations':
                        await projectSettingsStore.createIntegration(currentProjectId || 'default-project', data);
                        break;
                }
            }
            
            setIsModalOpen(false);
            setEditingItem(null);
            toast.success(editingItem ? 'Item updated successfully' : 'Item created successfully');
        } catch (error) {
            toast.error(`Failed to ${editingItem ? 'update' : 'create'} item: ${error}`);
            throw error; // Re-throw to let the form handle the error
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleCancel = () => {
        setIsModalOpen(false);
        setEditingItem(null);
    };

    if (!currentProjectId) {
        return (
            <div className="p-6 border-brand-primary/20 bg-brand-primary/5 rounded-xl text-center">
                <h4 className="font-semibold text-brand-primary mb-2">No Project Selected</h4>
                <p className="text-sm text-brand-primary/80 mb-4">Please create or select a project to manage settings.</p>
                <Button 
                    variant="primary" 
                    size="sm"
                    onClick={() => useAppStore.getState().navigate('settings')}
                >
                    Go to Project Settings
                </Button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                    <div className="flex-shrink-0">
                        {icon}
                    </div>
                    <div>
                        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
                        <p className="text-sm text-gray-500">{subtitle}</p>
                    </div>
                </div>
                <Button onClick={handleAddNew} disabled={sectionData.isLoading}>
                    Add {section === 'modelConfigs' ? 'Model Config' : 
                          section === 'gitRepositories' ? 'Git Repository' :
                          section === 'cloudCredentials' ? 'Cloud Credentials' :
                          section === 'teamMembers' ? 'Team Member' : 'Integration'}
                </Button>
            </div>

            {/* Error Display */}
            {sectionData.error && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                    <div className="flex">
                        <div className="flex-shrink-0">
                            <AlertCircle className="w-5 h-5 text-red-500" />
                        </div>
                        <div className="ml-3">
                            <h3 className="text-sm font-medium text-red-800">Error</h3>
                            <div className="mt-2 text-sm text-red-700">
                                {sectionData.error}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Items List with Loading Overlay */}
            <div className="relative">
                {sectionData.isLoading && (
                    <div className="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center z-10 rounded-xl">
                        <Loader2 className="w-8 h-8 text-brand-primary animate-spin" />
                    </div>
                )}
                {sectionData.items.length === 0 && (
                    <div className="text-center py-10 border-2 border-dashed border-gray-200 rounded-xl">
                        <div className="text-gray-400 mb-3">
                            <svg className="w-10 h-10 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                            </svg>
                        </div>
                        <h3 className="text-sm font-medium text-gray-900 mb-1">No items found</h3>
                        <p className="text-sm text-gray-500 mb-4 max-w-xs mx-auto">
                            Get started by adding your first {section === 'modelConfigs' ? 'model configuration' :
                                                       section === 'gitRepositories' ? 'git repository' :
                                                       section === 'cloudCredentials' ? 'cloud credentials' :
                                                       section === 'teamMembers' ? 'team member' : 'integration'}.
                        </p>
                        <Button onClick={handleAddNew} size="sm">
                            <Plus className="w-4 h-4 mr-1.5" />
                            Add {section === 'modelConfigs' ? 'Model Config' :
                                section === 'gitRepositories' ? 'Git Repository' :
                                section === 'cloudCredentials' ? 'Cloud Credentials' :
                                section === 'teamMembers' ? 'Team Member' : 'Integration'}
                        </Button>
                    </div>
                )}
                {sectionData.items.length > 0 && (
                    <div className="space-y-3">
                        {sectionData.items.map((item: any) => (
                            <div key={item.id} className="bg-white border border-gray-200 rounded-xl p-4">
                                {renderListItem(
                                    item,
                                    () => handleEdit(item),
                                    () => handleDelete(item),
                                    hasTestFunction ? () => handleTest(item) : undefined,
                                    readOnly
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Form Modal */}
            <Modal
                isOpen={isModalOpen}
                onClose={handleCancel}
                title={editingItem ? `Edit ${title}` : `Add ${title}`}
                icon={icon}
            >
                {renderForm(handleSubmit, handleCancel, editingItem, isSubmitting)}
            </Modal>

            {/* Test Results Modal */}
            <Modal
                isOpen={isTestModalOpen}
                onClose={() => setIsTestModalOpen(false)}
                title="Test Results"
                icon={currentTestResult?.success ? <CheckCircle2 className="w-5 h-5 text-green-500" /> : <AlertCircle className="w-5 h-5 text-red-500" />}
            >
                <div className="space-y-4">
                    <div className={`p-4 rounded-md ${currentTestResult?.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                        <div className="flex">
                            <div className="flex-shrink-0">
                                {currentTestResult?.success ? <CheckCircle2 className="w-5 h-5 text-green-500" /> : <AlertCircle className="w-5 h-5 text-red-500" />}
                            </div>
                            <div className="ml-3">
                                <h3 className={`text-sm font-medium ${currentTestResult?.success ? 'text-green-800' : 'text-red-800'}`}>
                                    {currentTestResult?.success ? 'Test Successful' : 'Test Failed'}
                                </h3>
                                <div className={`mt-2 text-sm ${currentTestResult?.success ? 'text-green-700' : 'text-red-700'}`}>
                                    {currentTestResult?.message}
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    {currentTestResult?.details && (
                        <div className="bg-gray-50 rounded-md p-4">
                            <h4 className="text-sm font-medium text-gray-900 mb-2">Details</h4>
                            <pre className="text-xs text-gray-600 whitespace-pre-wrap">
                                {JSON.stringify(currentTestResult.details, null, 2)}
                            </pre>
                        </div>
                    )}
                </div>
            </Modal>
        </div>
    );
};

export default SettingsPanel; 