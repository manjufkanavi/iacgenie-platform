import React, { useState, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';
import { Cloud, LayoutList, LayoutGrid, Trash2, RotateCw, X } from 'lucide-react';
import { useProjectSettingsStore, CloudCredentials, CredentialStatus } from '@/store/useProjectSettingsStore';
import { useProjectStore } from '@/store/useProjectStore';
import { useAppStore } from '@/store/useAppStore';
import Button from '@/components/ui/Button';
import Modal from '@/components/ui/Modal';
import CloudCredentialsForm from '@/components/forms/CloudCredentialsForm';
import CredentialStatusTable, { type CredentialItem } from '@/components/ui/CredentialStatusTable';
import CredentialStatusCard from '@/components/ui/CredentialStatusCard';
import DeleteConfirmModal from '@/components/ui/DeleteConfirmModal';

const CloudCredentialsSettings: React.FC = () => {
    const { currentProjectId } = useProjectStore();
    const projectSettingsStore = useProjectSettingsStore();
    const isAdmin = useAppStore(state => state.isAdmin());

    // View state
    const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');
    const [isFormModalOpen, setIsFormModalOpen] = useState(false);
    const [editingCred, setEditingCred] = useState<CloudCredentials | null>(null);
    const [isFormSubmitting, setIsFormSubmitting] = useState(false);

    // Delete modal state
    const [deleteCred, setDeleteCred] = useState<CloudCredentials | null>(null);

    // Bulk selection state
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [isBulkRevokeConfirmOpen, setIsBulkRevokeConfirmOpen] = useState(false);
    const [isBulkActionLoading, setIsBulkActionLoading] = useState(false);

    // Store data
    const credentials = projectSettingsStore.cloudCredentials;
    const isLoading = projectSettingsStore.isLoading.cloudCredentials;
    const error = projectSettingsStore.errors.cloudCredentials;

    // Test result modal state
    const [testResult, setTestResult] = useState<{ success: boolean; message: string; details?: any } | null>(null);
    const [isTestModalOpen, setIsTestModalOpen] = useState(false);
    const [lastCheckedCreds, setLastCheckedCreds] = useState<Set<string>>(new Set());

    // Read test results from store after verify actions
    useEffect(() => {
        if (!currentProjectId) return;
        for (const cred of credentials) {
            if (lastCheckedCreds.has(cred.id)) continue;
            const key = `cloudCredentials-${cred.id}`;
            const result = projectSettingsStore.testResults[key];
            if (result) {
                setTestResult({
                    success: result.success,
                    message: result.message,
                    details: result.details,
                });
                setIsTestModalOpen(true);
                const next = new Set(lastCheckedCreds);
                next.add(cred.id);
                setLastCheckedCreds(next);
                projectSettingsStore.clearTestResults();
                break;
            }
        }
    }, [credentials, currentProjectId, lastCheckedCreds]);

    // Sort state
    const [sortColumn, setSortColumn] = useState<'status' | 'keyName' | 'lastChecked' | 'expiresAt'>('status');
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

    // Load credentials on mount
    useEffect(() => {
        if (currentProjectId) {
            projectSettingsStore.fetchCloudCredentials(currentProjectId);
        }
    }, [currentProjectId]);

    // Convert CloudCredentials to CredentialItem[]
    const toCredentialItems = (creds: CloudCredentials[]): CredentialItem[] =>
        creds.map(cred => ({
            id: cred.id,
            provider: cred.provider.toUpperCase(),
            keyName: cred.name,
            status: (cred.status as CredentialStatus) || 'active',
            lastChecked: cred.lastVerified ? new Date(cred.lastVerified).toLocaleDateString() : undefined,
            expiresAt: cred.expiresAt ? new Date(cred.expiresAt).toLocaleDateString() : undefined,
            region: cred.region,
        }));

    // Convert CredentialItem to CloudCredentials (for form)
    const toCloudCred = (item: CredentialItem): CloudCredentials => ({
        id: item.id,
        provider: item.provider.toLowerCase() as 'aws' | 'gcp' | 'azure',
        name: item.keyName,
        userId: '',
        projectId: currentProjectId || '',
        credentials: {},
        region: item.region,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
    });

    const handleAdd = () => {
        setEditingCred(null);
        setIsFormModalOpen(true);
    };

    const handleEdit = (item: CredentialItem) => {
        const cred = toCloudCred(item);
        setEditingCred(cred);
        setIsFormModalOpen(true);
    };

    const handleDeleteClick = (item: CredentialItem) => {
        setDeleteCred(toCloudCred(item));
    };

    const handleDeleteConfirm = async () => {
        if (!deleteCred || !currentProjectId) return;
        try {
            await projectSettingsStore.deleteCloudCredentials(currentProjectId, deleteCred.id);
            toast.success('Credential deleted successfully');
        } catch (err) {
            toast.error(`Failed to delete credential: ${err}`);
        }
        setDeleteCred(null);
    };

    const handleFormSubmit = async (data: any): Promise<void> => {
        if (!currentProjectId) return;
        setIsFormSubmitting(true);
        try {
            if (editingCred) {
                await projectSettingsStore.updateCloudCredentials(currentProjectId, editingCred.id, data);
                toast.success('Credential updated successfully');
            } else {
                await projectSettingsStore.createCloudCredentials(currentProjectId, data);
                toast.success('Credential created successfully');
            }
            setIsFormModalOpen(false);
            setEditingCred(null);
        } catch (err) {
            toast.error(`Failed to ${editingCred ? 'update' : 'create'} credential: ${err}`);
            throw err;
        } finally {
            setIsFormSubmitting(false);
        }
    };

    const handleVerify = async (itemId: string) => {
        if (!currentProjectId) return;
        try {
            await projectSettingsStore.testCloudCredentials(currentProjectId, itemId);
            // Result is updated in store by testCloudCredentials action
        } catch (err) {
            toast.error(`Verification failed: ${err}`);
        }
    };

    const handleSelectAll = useCallback((selected: boolean) => {
        if (selected) {
            setSelectedIds(new Set(credentials.map(c => c.id)));
        } else {
            setSelectedIds(new Set());
        }
    }, [credentials]);

    const handleSelectOne = useCallback((id: string, selected: boolean) => {
        setSelectedIds(prev => {
            const next = new Set(prev);
            if (selected) next.add(id); else next.delete(id);
            return next;
        });
    }, []);

    const handleBulkVerify = async () => {
        if (!currentProjectId || selectedIds.size === 0) return;
        setIsBulkActionLoading(true);
        try {
            await projectSettingsStore.bulkVerifyCredentials(currentProjectId, [...selectedIds]);
            toast.success(`Verified ${selectedIds.size} credential(s)`);
            setSelectedIds(new Set());
        } catch (err) {
            toast.error(`Bulk verify failed: ${err}`);
        } finally {
            setIsBulkActionLoading(false);
        }
    };

    const handleBulkRevokeClick = () => {
        setIsBulkRevokeConfirmOpen(true);
    };

    const handleBulkRevokeConfirm = async () => {
        if (!currentProjectId || selectedIds.size === 0) return;
        setIsBulkActionLoading(true);
        try {
            await projectSettingsStore.bulkRevokeCredentials(currentProjectId, [...selectedIds]);
            toast.success(`Revoked ${selectedIds.size} credential(s)`);
            setSelectedIds(new Set());
        } catch (err) {
            toast.error(`Bulk revoke failed: ${err}`);
        } finally {
            setIsBulkActionLoading(false);
        }
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
                        <Cloud className="w-5 h-5" />
                    </div>
                    <div>
                        <h3 className="text-lg font-semibold text-gray-900">Cloud Credentials</h3>
                        <p className="text-sm text-gray-500">Manage cloud provider credentials for infrastructure deployments.</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    {/* View toggle */}
                    <div className="flex items-center border border-gray-200 rounded-lg overflow-hidden">
                        <button
                            onClick={() => setViewMode('table')}
                            className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                                viewMode === 'table'
                                    ? 'bg-brand-primary text-white'
                                    : 'bg-white text-gray-600 hover:bg-gray-50'
                            }`}
                            aria-label="Table view"
                        >
                            <LayoutList className="w-4 h-4" />
                        </button>
                        <button
                            onClick={() => setViewMode('grid')}
                            className={`px-3 py-1.5 text-xs font-medium transition-colors border-l border-gray-200 ${
                                viewMode === 'grid'
                                    ? 'bg-brand-primary text-white'
                                    : 'bg-white text-gray-600 hover:bg-gray-50'
                            }`}
                            aria-label="Grid view"
                        >
                            <LayoutGrid className="w-4 h-4" />
                        </button>
                    </div>
                    <Button onClick={handleAdd} disabled={isLoading}>
                        Add Cloud Credentials
                    </Button>
                </div>
            </div>

            {/* Error */}
            {error && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                    <div className="flex">
                        <div className="flex-shrink-0">
                            <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <div className="ml-3">
                            <h3 className="text-sm font-medium text-red-800">Error</h3>
                            <div className="mt-2 text-sm text-red-700">{error}</div>
                        </div>
                    </div>
                </div>
            )}

            {/* List */}
            <div>
                {isLoading ? (
                    <div className="relative">
                        <div className="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center z-10 rounded-xl">
                            <svg className="w-8 h-8 text-brand-primary animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                            </svg>
                        </div>
                        {viewMode === 'table' ? (
                            <div className="border rounded-xl bg-white p-8">
                                <div className="space-y-3">
                                    {Array.from({ length: 3 }).map((_, i) => (
                                        <div key={i} className="animate-pulse flex items-center gap-4">
                                            <div className="h-4 w-20 bg-gray-200 rounded" />
                                            <div className="h-4 w-32 bg-gray-200 rounded" />
                                            <div className="h-4 w-16 bg-gray-200 rounded" />
                                            <div className="h-4 w-24 bg-gray-200 rounded" />
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {Array.from({ length: 3 }).map((_, i) => (
                                    <div key={i} className="animate-pulse border rounded-xl bg-white p-4">
                                        <div className="h-4 w-24 bg-gray-200 rounded mb-2" />
                                        <div className="h-3 w-16 bg-gray-200 rounded mb-3" />
                                        <div className="h-3 w-32 bg-gray-200 rounded" />
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                ) : credentials.length === 0 ? (
                    <div className="text-center py-10 border-2 border-dashed border-gray-200 rounded-xl">
                        <div className="text-gray-400 mb-3">
                            <svg className="w-10 h-10 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                            </svg>
                        </div>
                        <h3 className="text-sm font-medium text-gray-900 mb-1">No credentials configured</h3>
                        <p className="text-sm text-gray-500 mb-4 max-w-xs mx-auto">
                            Get started by adding your first cloud credential.
                        </p>
                        <Button onClick={handleAdd} size="sm">
                            Add Cloud Credentials
                        </Button>
                    </div>
                ) : viewMode === 'table' ? (
                    <CredentialStatusTable
                        credentials={toCredentialItems(credentials)}
                        onVerify={isAdmin ? (id) => handleVerify(id) : undefined}
                        onDelete={isAdmin ? (id) => {
                            const cred = credentials.find(c => c.id === id);
                            if (cred) handleDeleteClick(toCredentialItems(credentials).find(i => i.id === id)!);
                        } : undefined}
                        onSelect={isAdmin ? handleSelectOne : undefined}
                        onAllSelected={isAdmin ? handleSelectAll : undefined}
                        selectedIds={isAdmin ? selectedIds : undefined}
                        onSortChange={(col, dir) => { setSortColumn(col); setSortDirection(dir); }}
                        sortColumn={sortColumn}
                        sortDirection={sortDirection}
                        readOnly={!isAdmin}
                        loading={false}
                    />
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {toCredentialItems(credentials).map(item => (
                            <CredentialStatusCard
                                key={item.id}
                                provider={item.provider}
                                keyName={item.keyName}
                                status={item.status}
                                lastChecked={item.lastChecked}
                                expiresAt={item.expiresAt}
                                onVerify={isAdmin ? () => handleVerify(item.id) : undefined}
                                onClick={() => isAdmin && handleEdit(item)}
                            />
                        ))}
                    </div>
                )}
            </div>

            {/* Bulk Action Bar */}
            {selectedIds.size > 0 && isAdmin && (
                <div className="flex items-center gap-3 p-3 bg-brand-primary/5 border border-brand-primary/20 rounded-xl">
                    <span className="text-sm font-medium text-brand-primary">
                        {selectedIds.size} credential{selectedIds.size > 1 ? 's' : ''} selected
                    </span>
                    <div className="flex-1" />
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleBulkVerify}
                        disabled={isBulkActionLoading}
                    >
                        <RotateCw className="w-4 h-4 mr-1" />
                        Verify All
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleBulkRevokeClick}
                        disabled={isBulkActionLoading}
                    >
                        <Trash2 className="w-4 h-4 mr-1" />
                        Revoke All
                    </Button>
                    <button
                        onClick={() => setSelectedIds(new Set())}
                        className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
                        aria-label="Clear selection"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
            )}

            {/* Form Modal */}
            <Modal
                isOpen={isFormModalOpen}
                onClose={() => { setIsFormModalOpen(false); setEditingCred(null); }}
                title={editingCred ? 'Edit Cloud Credential' : 'Add Cloud Credential'}
                icon={<Cloud className="w-5 h-5" />}
            >
                <CloudCredentialsForm
                    onSubmit={handleFormSubmit}
                    onCancel={() => { setIsFormModalOpen(false); setEditingCred(null); }}
                    initialData={editingCred}
                    isSubmitting={isFormSubmitting}
                />
            </Modal>

            {/* Delete Confirm Modal */}
            {deleteCred && (
                <DeleteConfirmModal
                    open={!!deleteCred}
                    onClose={() => setDeleteCred(null)}
                    provider={deleteCred.provider.toUpperCase()}
                    keyName={deleteCred.name}
                    onConfirm={handleDeleteConfirm}
                    showInvalidateSessions
                />
            )}

            {/* Bulk Revoke Confirm Modal */}
            {isBulkRevokeConfirmOpen && (
                <Modal
                    isOpen={isBulkRevokeConfirmOpen}
                    onClose={() => setIsBulkRevokeConfirmOpen(false)}
                    title="Revoke Credentials"
                    icon={<Trash2 className="w-5 h-5 text-amber-500" />}
                >
                    <div className="space-y-4">
                        <div className="bg-amber-50 border border-amber-200 rounded-md p-4">
                            <p className="text-sm text-amber-800 font-medium">Confirm Bulk Revocation</p>
                            <p className="text-sm text-amber-700 mt-1">
                                Are you sure you want to revoke {selectedIds.size} credential{selectedIds.size > 1 ? 's' : ''}?
                                This will mark them as revoked but will not delete them from the secret store.
                            </p>
                        </div>
                        <div className="flex justify-end gap-3">
                            <Button variant="outline" onClick={() => setIsBulkRevokeConfirmOpen(false)}>
                                Cancel
                            </Button>
                            <Button variant="danger" onClick={handleBulkRevokeConfirm} disabled={isBulkActionLoading}>
                                {isBulkActionLoading ? 'Revoking...' : 'Revoke'}
                            </Button>
                        </div>
                    </div>
                </Modal>
            )}

            {/* Test Results Modal */}
            <Modal
                isOpen={isTestModalOpen}
                onClose={() => setIsTestModalOpen(false)}
                title="Test Results"
                icon={testResult?.success ? (
                    <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                ) : (
                    <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                )}
            >
                {testResult && (
                    <div className="space-y-4">
                        <div className={`p-4 rounded-md ${testResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                            <p className={`text-sm font-medium ${testResult.success ? 'text-green-800' : 'text-red-800'}`}>
                                {testResult.success ? 'Test Successful' : 'Test Failed'}
                            </p>
                            <p className={`text-sm mt-1 ${testResult.success ? 'text-green-700' : 'text-red-700'}`}>
                                {testResult.message}
                            </p>
                        </div>
                        {testResult.details && (
                            <div className="bg-gray-50 rounded-md p-4">
                                <h4 className="text-sm font-medium text-gray-900 mb-2">Details</h4>
                                <pre className="text-xs text-gray-600 whitespace-pre-wrap">
                                    {JSON.stringify(testResult.details, null, 2)}
                                </pre>
                            </div>
                        )}
                    </div>
                )}
            </Modal>
        </div>
    );
};

export default CloudCredentialsSettings;
