import React, { useState, useEffect } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import Modal from '../ui/Modal';
import Input from '../ui/Input';
import { apiKeyService, ApiKeyRecord, ApiKeyCreateRequest } from '../../services/apiKeyService';
import { useAppStore } from '.././store/useAppStore';
import toast from 'react-hot-toast';

const DeveloperSettingsPage: React.FC = () => {
    const { currentProject } = useAppStore();
    const [apiKeys, setApiKeys] = useState<ApiKeyRecord[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [newKeyName, setNewKeyName] = useState('');
    const [generatedKey, setGeneratedKey] = useState<string | null>(null);
    const [keyToRevoke, setKeyToRevoke] = useState<ApiKeyRecord | null>(null);
    const [isCreating, setIsCreating] = useState(false);
    const [isRevoking, setIsRevoking] = useState(false);

    useEffect(() => {
        const fetchApiKeys = async () => {
            if (!currentProject?.id) return;
            
            setIsLoading(true);
            setError(null);
            
            try {
                const keys = await apiKeyService.listApiKeys(currentProject.id);
                setApiKeys(keys);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to fetch API keys');
                toast.error('Failed to load API keys');
            } finally {
                setIsLoading(false);
            }
        };

        fetchApiKeys();
    }, [currentProject?.id]);

    const handleCreateKey = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!currentProject?.id) return;
        
        setIsCreating(true);
        try {
            const keyData: ApiKeyCreateRequest = {
                name: newKeyName,
                permissions: ['read', 'write']
            };
            
            const result = await apiKeyService.createApiKey(currentProject.id, keyData);
            setGeneratedKey(result.token);
            
            // Refresh the list
            const updatedKeys = await apiKeyService.listApiKeys(currentProject.id);
            setApiKeys(updatedKeys);
            
            toast.success('API key created successfully');
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to create API key';
            toast.error(errorMessage);
        } finally {
            setIsCreating(false);
        }
    };

    const handleRevokeKey = async () => {
        if (!keyToRevoke || !currentProject?.id) return;
        
        setIsRevoking(true);
        try {
            await apiKeyService.revokeApiKey(currentProject.id, keyToRevoke.id);
            
            // Remove from local state
            setApiKeys(apiKeys.filter(key => key.id !== keyToRevoke.id));
            setKeyToRevoke(null);
            
            toast.success('API key revoked successfully');
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to revoke API key';
            toast.error(errorMessage);
        } finally {
            setIsRevoking(false);
        }
    };

    const closeCreateModal = () => {
        setIsCreateModalOpen(false);
        setNewKeyName('');
        setGeneratedKey(null);
    };

    if (!currentProject) {
        return (
            <div className="text-center py-8">
                <p className="text-slate-500 dark:text-slate-400 mb-4">No project selected</p>
                <p className="text-sm text-slate-400 dark:text-slate-500">Please create or select a project to manage API keys.</p>
                <Button
                    variant="primary"
                    onClick={() => useAppStore.getState().navigate('settings')}
                >
                    Go to Project Settings
                </Button>
            </div>
        );
    }

    if (isLoading) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">Developer Settings</h1>
                    <p className="mt-1 text-slate-600 dark:text-slate-300">Loading API keys...</p>
                </div>
                <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary"></div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">Developer Settings</h1>
                    <p className="mt-1 text-slate-600 dark:text-slate-300">Error loading API keys</p>
                </div>
                <Card className="p-6 border-red-200 bg-red-50">
                    <div className="flex items-center space-x-3">
                        <div className="flex-shrink-0">
                            <div className="w-10 h-10 bg-red-500 rounded-lg flex items-center justify-center text-white">
                                ⚠️
                            </div>
                        </div>
                        <div className="flex-1">
                            <h4 className="font-semibold text-red-800">Error Loading API Keys</h4>
                            <p className="text-sm text-red-700">{error}</p>
                        </div>
                        <Button 
                            variant="secondary" 
                            size="sm"
                            onClick={() => window.location.reload()}
                        >
                            Retry
                        </Button>
                    </div>
                </Card>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {/* Create API Key Modal */}
            <Modal isOpen={isCreateModalOpen} onClose={closeCreateModal} title={generatedKey ? 'API Key Created' : 'Create New API Key'}>
                {generatedKey ? (
                    <div>
                        <p className="text-sm text-slate-500 dark:text-slate-400">
                            Your new API key has been created. Please copy it now. You will not be able to see it again.
                        </p>
                        <div className="mt-4">
                            <Input id="new-key" label="Your new API Key" readOnly value={generatedKey} />
                        </div>
                        <div className="mt-5 sm:mt-6">
                            <Button className="w-full" onClick={closeCreateModal}>Done</Button>
                        </div>
                    </div>
                ) : (
                    <form onSubmit={handleCreateKey}>
                        <p className="text-sm text-slate-500 dark:text-slate-400">
                           Give your key a descriptive name to remember its purpose.
                        </p>
                        <div className="mt-4">
                            <Input
                                id="key-name"
                                label="Key Name"
                                value={newKeyName}
                                onChange={(e) => setNewKeyName(e.target.value)}
                                placeholder="e.g., My Dev Laptop"
                                required
                                disabled={isCreating}
                            />
                        </div>
                        <div className="mt-5 sm:mt-6">
                            <Button type="submit" className="w-full" disabled={isCreating}>
                                {isCreating ? 'Creating...' : 'Generate Key'}
                            </Button>
                        </div>
                    </form>
                )}
            </Modal>
            
            {/* Revoke API Key Modal */}
            <Modal isOpen={!!keyToRevoke} onClose={() => setKeyToRevoke(null)} title="Revoke API Key">
                 <p className="text-sm text-slate-500 dark:text-slate-400">
                    Are you sure you want to revoke the key named <strong>"{keyToRevoke?.name}"</strong>? This action is permanent and cannot be undone. Any applications using this key will immediately lose access.
                </p>
                <div className="mt-6 flex justify-end space-x-3">
                    <Button variant="secondary" onClick={() => setKeyToRevoke(null)} disabled={isRevoking}>Cancel</Button>
                    <Button variant="danger" onClick={handleRevokeKey} disabled={isRevoking}>
                        {isRevoking ? 'Revoking...' : 'Revoke Key'}
                    </Button>
                </div>
            </Modal>

            {/* Page Header */}
            <div>
                <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">Developer Settings</h1>
                <p className="mt-1 text-slate-600 dark:text-slate-300">Manage API keys and webhooks for programmatic access.</p>
            </div>

            {/* API Keys Card */}
            <Card padding="none">
                <div className="flex justify-between items-center p-4 border-b border-slate-200 dark:border-slate-600">
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">API Keys</h2>
                    <Button onClick={() => setIsCreateModalOpen(true)}>Create New Key</Button>
                </div>
                {apiKeys.length === 0 ? (
                    <div className="text-center p-16">
                        <div className="mx-auto h-12 w-12 text-slate-400 dark:text-slate-500">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="16 18 22 12 16 6" />
                                <polyline points="8 6 2 12 8 18" />
                            </svg>
                        </div>
                        <h3 className="mt-4 text-sm font-medium text-slate-900 dark:text-slate-50">No API keys yet</h3>
                        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Create your first API key to get started with programmatic access.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-600">
                            <thead className="bg-slate-50 dark:bg-slate-700/50">
                                <tr>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Name</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Token</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Last Used</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Created</th>
                                    <th scope="col" className="relative px-6 py-3"><span className="sr-only">Actions</span></th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-slate-200 dark:divide-slate-600">
                                {apiKeys.map(key => (
                                    <tr key={key.id}>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900 dark:text-slate-50">{key.name}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400 font-mono">{key.tokenPreview}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">{key.lastUsed || 'Never'}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                                            {new Date(key.createdAt).toLocaleDateString()}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                            <Button variant="danger" size="sm" onClick={() => setKeyToRevoke(key)}>Revoke</Button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </Card>

            {/* Webhooks Card (Future) */}
            <Card>
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">Webhooks</h2>
                <p className="mt-1 text-slate-600 dark:text-slate-300">Configure webhooks to receive notifications about deployment events. (Coming Soon)</p>
            </Card>
        </div>
    );
};

export default DeveloperSettingsPage;