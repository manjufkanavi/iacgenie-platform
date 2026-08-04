import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../ui/Card';
import Button from '../ui/Button';
import Badge from '../ui/Badge';
import PageHeader from '../layout/PageHeader';
import { ICONS } from '.../constants';
import { CloudProvider, Deployment, Generation, GenerationJob, JobStatus, OutputType, ProjectStatus, DeploymentStatus, Plan } from '../types';
import { useAppStore } from '../store/useAppStore';
import { useProjectStore } from '../store/useProjectStore';
import { generationService } from '../../services/generationService';
import { deploymentService, DeploymentRecord } from '../../services/deploymentService';
import { billingService, BillingInfo } from '../../services/billingService';
import toast from 'react-hot-toast';

// Error boundary for dashboard section
class DashboardErrorBoundary extends React.Component<any, { hasError: boolean, error: any }> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }
  componentDidCatch(_error: any, _errorInfo: any) {
    // Log error if needed
    // console.error('Dashboard error boundary:', error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">Dashboard</h1>
            <p className="mt-1 text-slate-600 dark:text-slate-400">A dashboard error occurred.</p>
          </div>
          <Card className="p-6 border-red-200 bg-red-50">
            <div className="flex items-center space-x-3">
              <div className="flex-shrink-0">
                <div className="w-10 h-10 bg-red-500 rounded-lg flex items-center justify-center text-white">⚠️</div>
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-red-800">Dashboard Error</h4>
                <p className="text-sm text-red-700">{this.state.error?.message || 'Unknown error'}</p>
              </div>
              <Button variant="secondary" size="sm" onClick={() => window.location.reload()}>Reload</Button>
            </div>
          </Card>
        </div>
      );
    }
    return this.props.children;
  }
}

const SummaryCard: React.FC<{ icon: React.ReactNode, title: string, value: string | number }> = ({ icon, title, value }) => (
    <Card data-testid="dashboard-stats-card" className="flex items-center p-4 sm:p-5 transition hover:shadow-md">
        <div className="p-2.5 sm:p-3 rounded-xl bg-orange-50 text-orange-500 flex-shrink-0">
            {icon}
        </div>
        <div className="ml-4 min-w-0 flex-1">
            <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider truncate">{title}</p>
            <p className="text-lg sm:text-xl font-bold text-slate-900 dark:text-slate-50 mt-0.5 truncate">{value}</p>
        </div>
    </Card>
);

const UsageBar: React.FC<{ label: string, current: number, max: number }> = ({ label, current, max }) => (
    <div data-testid={`usage-bar-${label.toLowerCase()}`}>
        <div className="flex justify-between text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1.5">
            <span>{label}</span>
            <span className="text-slate-700 dark:text-slate-200">{current} / {max}</span>
        </div>
        <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-2">
            <div className="bg-orange-500 h-2 rounded-full transition-all duration-500" style={{ width: `${max > 0 ? (current / max) * 100 : 0}%` }}></div>
        </div>
    </div>
);

export const getStatusVariant = (status: JobStatus | DeploymentStatus): 'success' | 'danger' | 'warning' | 'info' => {
    switch (status) {
        case 'Completed':
        case 'Success':
            return 'success';
        case 'Failed':
            return 'danger';
        case 'In Progress':
        case 'Running':
            return 'warning';
        default:
            return 'info';
    }
}

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  // Zustand state hooks (always at top)
  const { currentProject } = useAppStore();
  const { currentProjectId } = useProjectStore();
  const projectId = currentProjectId || currentProject?.id;
  const noProject = !projectId;

  // Local UI state
  const [recentGenerations, setRecentGenerations] = useState<Generation[]>([]);
  const [recentDeployments, setRecentDeployments] = useState<DeploymentRecord[]>([]);
  const [billingInfo, setBillingInfo] = useState<BillingInfo | null>(null);
  const [isLoadingGenerations, setIsLoadingGenerations] = useState(true);
  const [isLoadingDeployments, setIsLoadingDeployments] = useState(true);
  const [isLoadingBilling, setIsLoadingBilling] = useState(true);
  const [errorGenerations, setErrorGenerations] = useState<string | null>(null);
  const [errorDeployments, setErrorDeployments] = useState<string | null>(null);
  const [errorBilling, setErrorBilling] = useState<string | null>(null);

  // Data loading hooks (granular, robust)
  useEffect(() => {
    if (noProject) return;
    setIsLoadingGenerations(true);
    setErrorGenerations(null);
    generationService.listGenerations(projectId)
      .then(generations => setRecentGenerations(generations.generations.slice(0, 5).map(g => ({ ...g, provider: g.provider as CloudProvider })) as Generation[]))
      .catch(err => {
        const msg = err instanceof Error ? err.message : 'Failed to load generations';
        setErrorGenerations(msg);
        toast.error(msg);
      })
      .finally(() => setIsLoadingGenerations(false));
  }, [projectId, noProject]);

  useEffect(() => {
    if (noProject) return;
    setIsLoadingDeployments(true);
    setErrorDeployments(null);
    deploymentService.listDeployments(projectId)
      .then(deployments => setRecentDeployments(deployments.slice(0, 5)))
      .catch(err => {
        const msg = err instanceof Error ? err.message : 'Failed to load deployments';
        setErrorDeployments(msg);
        toast.error(msg);
      })
      .finally(() => setIsLoadingDeployments(false));
  }, [projectId, noProject]);

  useEffect(() => {
    if (noProject) return;
    setIsLoadingBilling(true);
    setErrorBilling(null);
    billingService.getBillingInfo(projectId)
      .then(billing => setBillingInfo(billing))
      .catch(err => {
        const msg = err instanceof Error ? err.message : 'Failed to load billing info';
        setErrorBilling(msg);
        toast.error(msg);
      })
      .finally(() => setIsLoadingBilling(false));
  }, [projectId, noProject]);

  // Dashboard stats (safe defaults)
  const dashboardStats = {
    totalGenerations: recentGenerations?.length ?? 0,
    totalDeployments: recentDeployments?.length ?? 0,
    lastRun: recentGenerations && recentGenerations.length > 0
      ? new Date(recentGenerations[0].createdAt).toLocaleDateString()
      : 'Never',
    status: 'Active' as ProjectStatus
  };

  // Get current plan safely
  const currentPlan = (billingInfo?.plan as Plan) || 'Free';

  // Defensive helpers for usage
  const generationsUsage = {
    current: billingInfo?.usage?.generations?.current ?? 0,
    limit: billingInfo?.usage?.generations?.limit ?? 0
  };
  const deploymentsUsage = {
    current: billingInfo?.usage?.deployments?.current ?? 0,
    limit: billingInfo?.usage?.deployments?.limit ?? 0
  };

  // Data conversion helpers
  const convertGenerationToDisplay = (gen: Generation): GenerationJob => ({
    id: gen.id,
    timestamp: new Date(gen.createdAt).toLocaleDateString(),
    status: gen.status as JobStatus,
    provider: gen.provider as CloudProvider,
    output: OutputType.OPENTOFU,
    prompt: gen.prompt
  });
  const convertDeploymentToDisplay = (dep: DeploymentRecord): Deployment => ({
    id: dep.id,
    projectName: dep.id,
    type: OutputType.OPENTOFU,
    provider: dep.provider as CloudProvider,
    status: dep.status as DeploymentStatus,
    createdAt: dep.createdAt,
    timestamp: new Date(dep.createdAt).toLocaleDateString()
  });

  // Fallback for missing project
  if (noProject) {
    return (
      <div className="space-y-8" data-testid="dashboard-page">
        <PageHeader 
          title="Dashboard" 
          subtitle="No project selected." 
        />
        <Card data-testid="no-project-alert" className="p-6 border-orange-200 bg-orange-50">
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <div className="w-10 h-10 bg-orange-500 rounded-lg flex items-center justify-center text-white font-bold">⚠️</div>
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-orange-850">No Project Selected</h4>
              <p className="text-sm text-orange-700">Please create a new project or select an existing one to view your dashboard.</p>
            </div>
            <Button variant="primary" size="sm" onClick={() => navigate('/settings')}>Go to Project Settings</Button>
          </div>
        </Card>
      </div>
    );
  }

  // Main dashboard UI with error boundaries and skeletons
  return (
    <DashboardErrorBoundary>
      <div className="space-y-8" data-testid="dashboard-page">
        {/* Page Header */}
        <div data-testid="welcome-message">
          <PageHeader 
            title="Dashboard" 
            subtitle={`Welcome back! Here's an overview of your ${currentProject?.name || 'project'}.`} 
          />
        </div>

        {/* Summary Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
          <SummaryCard icon={ICONS.GENERATOR} title="Total Generations" value={dashboardStats.totalGenerations} />
          <SummaryCard icon={ICONS.DEPLOYMENTS} title="Deployments" value={dashboardStats.totalDeployments} />
          <SummaryCard icon={ICONS.CLOCK} title="Last Run" value={dashboardStats.lastRun} />
          <SummaryCard icon={ICONS.STATUS} title="Status" value={dashboardStats.status} />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          {/* Recent Generations Table */}
          <div className="lg:col-span-2">
            <Card padding="none">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50 p-4">Recent Generations</h2>
              {isLoadingGenerations ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-pulse w-full">
                    <div className="h-6 bg-slate-200 dark:bg-slate-600 rounded mb-2 w-1/2 mx-auto" />
                    <div className="h-4 bg-slate-100 dark:bg-slate-600 rounded mb-2 w-3/4 mx-auto" />
                    <div className="h-4 bg-slate-100 dark:bg-slate-600 rounded mb-2 w-2/3 mx-auto" />
                  </div>
                </div>
              ) : errorGenerations ? (
                <div className="p-4 text-center text-red-600">
                  <p>{errorGenerations}</p>
                  <Button variant="secondary" size="sm" onClick={() => window.location.reload()}>Retry</Button>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table data-testid="recent-generations-table" className="min-w-full divide-y divide-slate-200 dark:divide-slate-600">
                    <thead className="bg-slate-50 dark:bg-slate-800/50">
                      <tr>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Request</th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Status</th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Details</th>
                        <th scope="col" className="relative px-6 py-3"><span className="sr-only">Actions</span></th>
                      </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-slate-800 divide-y divide-slate-200 dark:divide-slate-600">
                      {recentGenerations.length === 0 ? (
                        <tr>
                          <td colSpan={4} className="px-6 py-4 text-center text-slate-500 dark:text-slate-400">
                            No generations yet. Start by creating your first infrastructure.
                          </td>
                        </tr>
                      ) : (
                        recentGenerations.map(gen => {
                          const displayGen = convertGenerationToDisplay(gen);
                          return (
                            <tr key={gen.id}>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <div className="text-sm font-medium text-slate-900 dark:text-slate-50 truncate max-w-xs">{displayGen.prompt}</div>
                                <div className="text-sm text-slate-500 dark:text-slate-400">{displayGen.timestamp}</div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <Badge variant={getStatusVariant(displayGen.status)}>{displayGen.status}</Badge>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
                                <div><span className="font-semibold text-slate-500 dark:text-slate-400">Provider:</span> {displayGen.provider.toUpperCase()}</div>
                                <div><span className="font-semibold text-slate-500 dark:text-slate-400">Output:</span> {displayGen.output}</div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                <Button 
                                  variant="secondary" 
                                  size="sm"
                                  data-testid={`view-code-button-${gen.id}`}
                                  onClick={() => navigate('/generator')}
                                >
                                  View Code
                                </Button>
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
 
          {/* Side Column */}
          <div className="lg:col-span-1 space-y-8">
            {/* Current Usage */}
            {currentPlan === 'Free' && !isLoadingBilling && !errorBilling && billingInfo && (
              <Card>
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50 mb-4">Current Usage (Free Plan)</h2>
                <div className="space-y-4">
                  <UsageBar label="Generations" current={generationsUsage.current} max={generationsUsage.limit} />
                  <UsageBar label="Deployments" current={deploymentsUsage.current} max={deploymentsUsage.limit} />
                </div>
              </Card>
            )}
            {isLoadingBilling && (
              <Card>
                <div className="animate-pulse h-16 bg-slate-100 dark:bg-slate-600 rounded mb-2 w-3/4 mx-auto" />
                <div className="animate-pulse h-4 bg-slate-100 dark:bg-slate-600 rounded w-1/2 mx-auto" />
              </Card>
            )}
            {errorBilling && (
              <Card className="p-4 text-center text-red-600">
                <p>{errorBilling}</p>
                <Button variant="secondary" size="sm" onClick={() => window.location.reload()}>Retry</Button>
              </Card>
            )}
 
            {/* Upgrade to Pro */}
            <Card data-testid="upgrade-card" className="bg-gradient-to-br from-orange-100 to-white">
              <div className="flex items-center mb-4">
                <div className="p-2 rounded-full bg-orange-500 text-white">{ICONS.UPGRADE}</div>
                <h2 className="ml-3 text-lg font-semibold text-slate-900 dark:text-slate-50">Unlock More Power</h2>
              </div>
              <p className="text-slate-600 dark:text-slate-400 mb-5">Upgrade to Pro for unlimited generations, advanced models, and priority support.</p>
              <Button variant="primary" size="md" data-testid="upgrade-pro-button" className="w-full" onClick={() => navigate('/billing')}>Upgrade to Pro</Button>
            </Card>

            {/* Recent Deployments */}
            <Card>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50 mb-4">Recent Deployments</h2>
              {isLoadingDeployments ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-pulse w-full">
                    <div className="h-6 bg-slate-200 dark:bg-slate-600 rounded mb-2 w-1/2 mx-auto" />
                    <div className="h-4 bg-slate-100 dark:bg-slate-600 rounded mb-2 w-3/4 mx-auto" />
                  </div>
                </div>
              ) : errorDeployments ? (
                <div className="p-4 text-center text-red-600">
                  <p>{errorDeployments}</p>
                  <Button variant="secondary" size="sm" onClick={() => window.location.reload()}>Retry</Button>
                </div>
              ) : recentDeployments.length === 0 ? (
                <div className="text-center py-4">
                  <p className="text-sm text-slate-500 dark:text-slate-400">No deployments yet</p>
                </div>
              ) : (
                <ul className="space-y-4">
                  {recentDeployments.map(dep => {
                    const displayDep = convertDeploymentToDisplay(dep);
                    return (
                      <li key={dep.id} className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-slate-900 dark:text-slate-50">{displayDep.projectName}</p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">{displayDep.timestamp}</p>
                        </div>
                        <Badge variant={getStatusVariant(displayDep.status)}>{displayDep.status}</Badge>
                      </li>
                    );
                  })}
                </ul>
              )}
            </Card>
          </div>
        </div>
      </div>
    </DashboardErrorBoundary>
  );
};

export default DashboardPage;