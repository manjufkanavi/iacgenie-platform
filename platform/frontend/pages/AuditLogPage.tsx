import React, { useState, useEffect } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import Input from '../ui/Input';
import Select from '../ui/Select';
import Modal from '../ui/Modal';
import { auditLogService, AuditLog } from '../services/auditLogService';
import { useAppStore } from '../store/useAppStore';
import { useProjectStore } from '../store/useProjectStore';
import toast from 'react-hot-toast';
import { ICONS } from '../constants';

const AuditLogPage: React.FC = () => {
    const { currentProject } = useAppStore();
    const { currentProjectId } = useProjectStore();
    const projectId = currentProjectId || currentProject?.id;
    
    const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Filtering and search state
    const [searchTerm, setSearchTerm] = useState('');
    const [actionFilter, setActionFilter] = useState('all');
    const [actorFilter, setActorFilter] = useState('all');
    const [dateFilter, setDateFilter] = useState('all');

    // Admin features state
    const [isAdmin] = useState(false); // TODO: Get from user context
    const [selectedLogs, setSelectedLogs] = useState<string[]>([]);
    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);

    useEffect(() => {
        const fetchAuditLogs = async () => {
            if (!projectId) return;
            
            setIsLoading(true);
            setError(null);
            
            try {
                const logs = await auditLogService.listAuditLogs(projectId, 1000); // Get more logs for filtering
                setAuditLogs(logs);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to fetch audit logs');
                toast.error('Failed to load audit logs');
            } finally {
                setIsLoading(false);
            }
        };

        fetchAuditLogs();
    }, [projectId]);

    // Filter logs based on search and filters
    const filteredLogs = auditLogs.filter(log => {
        // Search term filter
        if (searchTerm && !log.action.toLowerCase().includes(searchTerm.toLowerCase()) &&
            !log.resource.toLowerCase().includes(searchTerm.toLowerCase()) &&
            !log.actor.name.toLowerCase().includes(searchTerm.toLowerCase()) &&
            !log.actor.email.toLowerCase().includes(searchTerm.toLowerCase())) {
            return false;
        }

        // Action filter
        if (actionFilter !== 'all' && log.action !== actionFilter) {
            return false;
        }

        // Actor filter
        if (actorFilter !== 'all' && log.actor.email !== actorFilter) {
            return false;
        }

        // Date filter
        if (dateFilter !== 'all') {
            const logDate = new Date(log.timestamp);
            const now = new Date();
            const oneDay = 24 * 60 * 60 * 1000;
            
            switch (dateFilter) {
                case 'today':
                    return logDate.toDateString() === now.toDateString();
                case 'week':
                    return (now.getTime() - logDate.getTime()) <= 7 * oneDay;
                case 'month':
                    return (now.getTime() - logDate.getTime()) <= 30 * oneDay;
                default:
                    return true;
            }
        }

        return true;
    });

    // Get unique actions and actors for filters
    const uniqueActions = [...new Set(auditLogs.map(log => log.action))];
    const uniqueActors = [...new Set(auditLogs.map(log => log.actor.email))];

    const handleSelectLog = (logId: string) => {
        setSelectedLogs(prev => 
            prev.includes(logId) 
                ? prev.filter(id => id !== logId)
                : [...prev, logId]
        );
    };

    const handleSelectAll = () => {
        if (selectedLogs.length === filteredLogs.length) {
            setSelectedLogs([]);
        } else {
            setSelectedLogs(filteredLogs.map(log => log.id));
        }
    };

    const handleDeleteSelected = async () => {
        if (!projectId || selectedLogs.length === 0) return;
        
        setIsDeleting(true);
        try {
            // Delete logs in parallel
            await Promise.all(selectedLogs.map(logId => 
                auditLogService.deleteAuditLog(projectId, logId)
            ));
            
            // Remove from local state
            setAuditLogs(prev => prev.filter(log => !selectedLogs.includes(log.id)));
            setSelectedLogs([]);
            setIsDeleteModalOpen(false);
            toast.success(`Deleted ${selectedLogs.length} audit log(s)`);
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to delete audit logs';
            toast.error(errorMessage);
        } finally {
            setIsDeleting(false);
        }
    };

    const exportLogs = () => {
        const csvContent = [
            ['Timestamp', 'Actor', 'Action', 'Resource', 'IP Address'],
            ...filteredLogs.map(log => [
                new Date(log.timestamp).toLocaleString(),
                log.actor.email,
                log.action,
                log.resource,
                log.ipAddress
            ])
        ].map(row => row.join(',')).join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
    };

    // Handle missing project gracefully
    if (!projectId) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">Audit Log</h1>
                    <p className="mt-1 text-slate-600 dark:text-slate-300">A record of all actions taken within your project.</p>
                </div>
                <Card className="p-8 text-center">
                    <div className="mx-auto h-12 w-12 text-slate-400 dark:text-slate-500 mb-4">
                        {ICONS.AUDIT_LOG}
                    </div>
                    <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-50 mb-2">No Project Selected</h2>
                    <p className="text-slate-500 dark:text-slate-400 mb-6">
                        Please select a project to view its audit logs.
                    </p>
                    <Button 
                        variant="primary"
                        onClick={() => window.location.href = '/settings'}
                    >
                        Go to Project Settings
                    </Button>
                </Card>
            </div>
        );
    }

    if (isLoading) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">Audit Log</h1>
                    <p className="mt-1 text-slate-600 dark:text-slate-300">Loading audit logs...</p>
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
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">Audit Log</h1>
                    <p className="mt-1 text-slate-600 dark:text-slate-300">Error loading audit logs</p>
                </div>
                <Card className="p-6 border-red-200 bg-red-50">
                    <div className="flex items-center space-x-3">
                        <div className="flex-shrink-0">
                            <div className="w-10 h-10 bg-red-500 rounded-lg flex items-center justify-center text-white">
                                ⚠️
                            </div>
                        </div>
                        <div className="flex-1">
                            <h4 className="font-semibold text-red-800">Error Loading Audit Logs</h4>
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

    const renderEmptyState = () => (
        <div className="text-center p-16">
            <div className="mx-auto h-12 w-12 text-slate-400 dark:text-slate-500">
                {ICONS.AUDIT_LOG}
            </div>
            <h2 className="mt-6 text-xl font-semibold text-slate-900 dark:text-slate-50">No Audit Logs Found</h2>
            <p className="mt-2 text-slate-500 dark:text-slate-400">Audit logs will appear here as you perform actions in your project.</p>
        </div>
    );

    return (
        <div className="space-y-8">
            {/* Delete Confirmation Modal */}
            <Modal isOpen={isDeleteModalOpen} onClose={() => setIsDeleteModalOpen(false)} title="Delete Audit Logs">
                <p className="text-sm text-slate-500 dark:text-slate-400">
                    Are you sure you want to delete {selectedLogs.length} audit log(s)? This action cannot be undone.
                </p>
                <div className="mt-6 flex justify-end space-x-3">
                    <Button variant="secondary" onClick={() => setIsDeleteModalOpen(false)} disabled={isDeleting}>
                        Cancel
                    </Button>
                    <Button variant="danger" onClick={handleDeleteSelected} disabled={isDeleting}>
                        {isDeleting ? 'Deleting...' : 'Delete Logs'}
                    </Button>
                </div>
            </Modal>

            {/* Page Header */}
            <div className="flex justify-between items-start">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">Audit Log</h1>
                    <p className="mt-1 text-slate-600 dark:text-slate-300">A record of all actions taken within your project.</p>
                </div>
                <div className="flex space-x-3">
                    <Button variant="secondary" onClick={exportLogs}>
                        Export CSV
                    </Button>
                    {isAdmin && selectedLogs.length > 0 && (
                        <Button variant="danger" onClick={() => setIsDeleteModalOpen(true)}>
                            Delete Selected ({selectedLogs.length})
                        </Button>
                    )}
                </div>
            </div>

            {/* Filters */}
            <Card>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <Input
                        id="search"
                        label="Search"
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                        placeholder="Search actions, resources, or users..."
                    />
                    <Select label="Action" value={actionFilter} onChange={e => setActionFilter(e.target.value)}>
                        <option value="all">All Actions</option>
                        {uniqueActions.map(action => (
                            <option key={action} value={action}>{action}</option>
                        ))}
                    </Select>
                    <Select label="Actor" value={actorFilter} onChange={e => setActorFilter(e.target.value)}>
                        <option value="all">All Users</option>
                        {uniqueActors.map(actor => (
                            <option key={actor} value={actor}>{actor}</option>
                        ))}
                    </Select>
                    <Select label="Date Range" value={dateFilter} onChange={e => setDateFilter(e.target.value)}>
                        <option value="all">All Time</option>
                        <option value="today">Today</option>
                        <option value="week">Last 7 Days</option>
                        <option value="month">Last 30 Days</option>
                    </Select>
                </div>
            </Card>

            <Card padding="none">
                {/* Table Header with Select All */}
                {filteredLogs.length > 0 && (
                    <div className="p-4 border-b border-slate-200 dark:border-slate-600">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-3">
                                {isAdmin && (
                                    <input
                                        type="checkbox"
                                        checked={selectedLogs.length === filteredLogs.length}
                                        onChange={handleSelectAll}
                                        className="rounded border-slate-300 dark:border-slate-500 text-brand-primary focus:ring-brand-primary"
                                    />
                                )}
                                <span className="text-sm text-slate-500 dark:text-slate-400">
                                    {filteredLogs.length} log(s) found
                                </span>
                            </div>
                            <div className="text-sm text-slate-500 dark:text-slate-400">
                                Showing {filteredLogs.length} of {auditLogs.length} total logs
                            </div>
                        </div>
                    </div>
                )}

                {/* Audit Logs Table */}
                {filteredLogs.length === 0 ? (
                    renderEmptyState()
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-600">
                            <thead className="bg-slate-50 dark:bg-slate-700/50">
                                <tr>
                                    {isAdmin && <th scope="col" className="px-6 py-3"><span className="sr-only">Select</span></th>}
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Actor</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Action</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Resource</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">IP Address</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Timestamp</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-slate-200 dark:divide-slate-600">
                                {filteredLogs.map(log => (
                                    <tr key={log.id} className="hover:bg-slate-50 dark:bg-slate-700/50">
                                        {isAdmin && (
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <input
                                                    type="checkbox"
                                                    checked={selectedLogs.includes(log.id)}
                                                    onChange={() => handleSelectLog(log.id)}
                                                    className="rounded border-slate-300 dark:border-slate-500 text-brand-primary focus:ring-brand-primary"
                                                />
                                            </td>
                                        )}
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm font-medium text-slate-900 dark:text-slate-50">{log.actor.name}</div>
                                            <div className="text-sm text-slate-500 dark:text-slate-400">{log.actor.email}</div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-700 dark:text-slate-200">
                                            <span className="font-mono bg-slate-100 dark:bg-slate-700 px-2 py-1 rounded-md">{log.action}</span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">{log.resource}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400 font-mono">{log.ipAddress}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                                            {new Date(log.timestamp).toLocaleString()}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </Card>
        </div>
    );
};

export default AuditLogPage;