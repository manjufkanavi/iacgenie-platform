import React, { useState, useEffect, useMemo } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import Badge from '../ui/Badge';
import Select from '../ui/Select';
import Modal from '../ui/Modal';
import Input from '../ui/Input';
import DeploymentPreviewModal from './components/ui/DeploymentPreviewModal';
import LogViewer from './LogViewer';
import { ICONS } from '.../constants';
import { deploymentService, DeploymentRecord } from '../../services/deploymentService';
import { generationService } from '../../services/generationService';
import { Generation } from '..../types';
import { DeploymentStatus, CloudProvider, OutputType } from './types';
import { getStatusVariant } from './DashboardPage'; // Re-using this handy function
import { useAppStore } from '../store/useAppStore';
import { useProjectStore } from '../store/useProjectStore';
import { toast } from 'react-hot-toast';
import { DeploymentLog } from './types';

const ProviderLogo: React.FC<{ provider: CloudProvider }> = ({ provider }) => {
    const logos: Record<CloudProvider, React.ReactNode> = {
        [CloudProvider.AWS]: ICONS.AWS_LOGO,
        [CloudProvider.GCP]: ICONS.GCP_LOGO,
        [CloudProvider.AZURE]: ICONS.AZURE_LOGO,
    };
    return <div className="w-6 h-6">{logos[provider]}</div>;
}

const DeploymentsPage: React.FC = () => {
  const { currentProjectId } = useProjectStore();
  const [deployments, setDeployments] = useState<DeploymentRecord[]>([]);
  const [generations, setGenerations] = useState<Generation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [providerFilter, setProviderFilter] = useState<string>('all');

  // Log Viewer State
  const [isLogViewerOpen, setIsLogViewerOpen] = useState(false);
  const [selectedDeployment, setSelectedDeployment] = useState<DeploymentRecord | null>(null);
  const [deploymentLogs, setDeploymentLogs] = useState<DeploymentLog | null>(null);
  const [isLogsLoading, setIsLogsLoading] = useState(false);

  // Create Deployment Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newDeployment, setNewDeployment] = useState({
    generationId: '',
    provider: 'aws',
    region: 'us-west-2',
    credentialsId: ''
  });

  // Deployment Preview Modal State
  const [isPreviewModalOpen, setIsPreviewModalOpen] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      if (!currentProjectId) return;
      
      setIsLoading(true);
      setError(null);
      
      try {
        // Load deployments and generations in parallel
        const [deploymentsData, generationsData] = await Promise.all([
          deploymentService.listDeployments(currentProjectId),
          generationService.listGenerations(currentProjectId)
        ]);
        
        setDeployments(deploymentsData);
        setGenerations(generationsData.generations.map(g => ({
          ...g,
          provider: g.provider as CloudProvider,
        })) as Generation[]);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to fetch deployments';
        setError(errorMessage);
        toast.error(errorMessage);
        console.error('Failed to fetch deployments:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [currentProjectId]);

  const handleDeleteDeployment = async (deploymentId: string) => {
    if (!currentProjectId) return;
    
    if (window.confirm('Are you sure you want to delete this deployment? This action cannot be undone.')) {
      try {
        await deploymentService.deleteDeployment(currentProjectId, deploymentId);
        setDeployments(prev => prev.filter(d => d.id !== deploymentId));
        toast.success('Deployment deleted successfully');
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to delete deployment';
        toast.error(errorMessage);
      }
    }
  };

  const handleViewLogs = async (deployment: DeploymentRecord) => {
    setSelectedDeployment(deployment);
    setIsLogViewerOpen(true);
    setIsLogsLoading(true);
    try {
      // For now, use the deployment logs from the record
      const logs: DeploymentLog = {
        plan: deployment.logs.find(log => log.stage === 'plan')?.message || 'No plan logs available',
        apply: deployment.logs.find(log => log.stage === 'apply')?.message || 'No apply logs available',
        output: deployment.outputs ? JSON.stringify(deployment.outputs, null, 2) : 'No outputs available'
      };
      setDeploymentLogs(logs);
    } catch (error) {
      console.error('Failed to fetch deployment logs:', error);
      toast.error('Failed to load deployment logs');
    } finally {
      setIsLogsLoading(false);
    }
  };
  
  const handleCloseLogs = () => {
    setIsLogViewerOpen(false);
    setSelectedDeployment(null);
    setDeploymentLogs(null);
  }

  const filteredDeployments = useMemo(() => {
    return deployments
      .filter(d => statusFilter === 'all' || d.status.toLowerCase() === statusFilter)
      .filter(d => providerFilter === 'all' || d.provider === providerFilter);
  }, [deployments, statusFilter, providerFilter]);

  // Get available generations for deployment creation
  const availableGenerations = generations.filter(g => g.status === 'COMPLETED');

  const renderEmptyState = () => (
    <div className="text-center p-16">
        {ICONS.EMPTY_BOX}
        <h2 className="mt-6 text-xl font-semibold text-slate-900 dark:text-slate-50">No Deployments Found</h2>
        <p className="mt-2 text-slate-500 dark:text-slate-400">Get started by generating and deploying your first piece of infrastructure.</p>
        <div className="mt-6 space-x-4">
            <Button variant="primary" onClick={() => useAppStore.getState().navigate('generator')}>Generate Infrastructure</Button>
            <Button variant="secondary" onClick={() => setIsCreateModalOpen(true)} disabled={availableGenerations.length === 0}>
              Deploy Existing Generation
            </Button>
        </div>
    </div>
  );

  // Handle missing project gracefully
  if (!currentProjectId) {
    return (
      <div className="text-center py-8">
        <p className="text-slate-500 dark:text-slate-400 mb-4">No project selected</p>
        <p className="text-sm text-slate-400 dark:text-slate-500">Please create or select a project to view deployments.</p>
        <Button
          variant="primary"
          onClick={() => useAppStore.getState().navigate('settings')}
        >
          Go to Project Settings
        </Button>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">Deployments</h1>
          <p className="mt-1 text-slate-600 dark:text-slate-300">Error loading deployments</p>
        </div>
        <Card className="p-6 border-red-200 bg-red-50">
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <div className="w-10 h-10 bg-red-500 rounded-lg flex items-center justify-center text-white">
                ⚠️
              </div>
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-red-800">Error Loading Deployments</h4>
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
        <LogViewer
            isOpen={isLogViewerOpen}
            onClose={handleCloseLogs}
            deployment={selectedDeployment ? {
              id: selectedDeployment.id,
              projectName: selectedDeployment.id, // Using ID as name for now
              provider: selectedDeployment.provider as CloudProvider,
              type: OutputType.OPENTOFU, // Default to OpenTofu
              status: selectedDeployment.status as DeploymentStatus,
              timestamp: new Date(selectedDeployment.createdAt).toLocaleDateString(),
              createdAt: selectedDeployment.createdAt
            } : null}
            logs={deploymentLogs}
            isLoading={isLogsLoading}
        />

        {/* Create Deployment Modal */}
        <Modal isOpen={isCreateModalOpen} onClose={() => setIsCreateModalOpen(false)} title="Review Deployment">
          <div className="space-y-4">
            {/* Provider Selection */}
            <div>
              <Select
                label="Cloud Provider"
                value={newDeployment.provider}
                onChange={e => setNewDeployment(prev => ({ ...prev, provider: e.target.value }))}
                required
              >
                <option value="aws">AWS</option>
                <option value="gcp">Google Cloud Platform</option>
                <option value="azure">Microsoft Azure</option>
              </Select>
            </div>

            <div>
              <Input
                id="region"
                label="Region"
                value={newDeployment.region}
                onChange={e => setNewDeployment(prev => ({ ...prev, region: e.target.value }))}
                placeholder="e.g., us-west-2"
                required
              />
            </div>

            <div>
              <Select
                label="Generation" 
                value={newDeployment.generationId} 
                onChange={e => setNewDeployment(prev => ({ ...prev, generationId: e.target.value }))}
                required
              >
                <option value="">Select a generation...</option>
                {availableGenerations.map(gen => (
                  <option key={gen.id} value={gen.id}>
                    {gen.prompt.substring(0, 50)}... ({gen.provider})
                  </option>
                ))}
              </Select>
            </div>

            <div className="pt-4 border-t">
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-3">Preview of resources to be created:</p>
              <div className="bg-blue-50 p-4 rounded-lg text-sm">
                <p className="text-blue-800 font-medium">Cloud: {newDeployment.provider.toUpperCase()}</p>
                <p className="text-blue-700">Region: {newDeployment.region}</p>
                <p className="text-blue-600 mt-1">This deployment will create infrastructure based on the selected generation.</p>
              </div>
            </div>

            <div className="pt-4 border-t">
              <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-50 mb-2">Important:</h4>
              <ul className="text-xs text-slate-600 dark:text-slate-300 space-y-1">
                <li>• This will create actual cloud resources</li>
                <li>• You will be charged for the created infrastructure</li>
                <li>• Review your cloud provider pricing before confirming</li>
              </ul>
            </div>

            <div className="flex justify-end space-x-3 pt-4">
              <Button variant="secondary" onClick={() => {
                setIsCreateModalOpen(false);
                setNewDeployment({ generationId: '', provider: 'aws', region: 'us-west-2', credentialsId: '' });
              }} disabled={false}>
                Cancel
              </Button>
              <Button type="button" onClick={(e) => {
                e.preventDefault();
                if (newDeployment.generationId && newDeployment.provider && newDeployment.region) {
                  setIsCreateModalOpen(false);
                  setIsPreviewModalOpen(true);
                } else {
                  toast.error('Please fill in all fields');
                }
              }} disabled={false}>
                Preview
              </Button>
            </div>
          </div>
        </Modal>

        {/* Deployment Preview Modal */}
        <DeploymentPreviewModal 
          isOpen={isPreviewModalOpen}
          onClose={() => setIsPreviewModalOpen(false)}
          generationId={newDeployment.generationId}
          provider={newDeployment.provider}
          region={newDeployment.region}
        />

        {/* Page Header */}
        <div className="flex justify-between items-start">
            <div>
                <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">Deployments</h1>
                <p className="mt-1 text-slate-600 dark:text-slate-300">Monitor, manage, and debug your infrastructure deployments.</p>
            </div>
            <Button onClick={() => setIsCreateModalOpen(true)} disabled={availableGenerations.length === 0}>
                Create Deployment
            </Button>
        </div>

        {/* Filters and Table Card */}
        <Card padding="none">
            {/* Filter Controls */}
            <div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-4 border-b border-slate-200 dark:border-slate-600">
                <Select label="Filter by Status" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
                    <option value="all">All Statuses</option>
                    <option value="success">Success</option>
                    <option value="running">Running</option>
                    <option value="failed">Failed</option>
                    <option value="pending">Pending</option>
                </Select>
                 <Select label="Filter by Provider" value={providerFilter} onChange={e => setProviderFilter(e.target.value)}>
                    <option value="all">All Providers</option>
                    <option value="aws">AWS</option>
                    <option value="gcp">GCP</option>
                    <option value="azure">Azure</option>
                </Select>
                {/* Date filter could be added here */}
            </div>

            {/* Deployments Table */}
            {isLoading ? (
                 <div className="text-center p-16 text-slate-500 dark:text-slate-400">Loading deployments...</div>
            ) : filteredDeployments.length === 0 ? (
                renderEmptyState()
            ) : (
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-600">
                        <thead className="bg-slate-50 dark:bg-slate-700/50">
                            <tr>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Deployment ID</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Provider</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Region</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Status</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Created</th>
                                <th scope="col" className="relative px-6 py-3"><span className="sr-only">Actions</span></th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-slate-200 dark:divide-slate-600">
                            {filteredDeployments.map(dep => (
                                <tr key={dep.id}>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="text-sm font-medium text-slate-900 dark:text-slate-50">{dep.id}</div>
                                        <div className="text-sm text-slate-500 dark:text-slate-400">Generation: {dep.generationId}</div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center">
                                            <ProviderLogo provider={dep.provider as CloudProvider} />
                                            <span className="ml-2 text-sm text-slate-900 dark:text-slate-50">{dep.provider.toUpperCase()}</span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900 dark:text-slate-50">{dep.region}</td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <Badge variant={getStatusVariant(dep.status as DeploymentStatus)}>{dep.status}</Badge>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                                        {new Date(dep.createdAt).toLocaleDateString()}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                                        <Button variant="secondary" size="sm" onClick={() => handleViewLogs(dep)}>
                                            View Logs
                                        </Button>
                                        <Button variant="danger" size="sm" onClick={() => handleDeleteDeployment(dep.id)}>
                                            Delete
                                        </Button>
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

export default DeploymentsPage;