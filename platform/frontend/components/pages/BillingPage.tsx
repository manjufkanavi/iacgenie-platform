import React, { useState, useEffect } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import PageHeader from '../layout/PageHeader';
import PlanCard from '../billing/PlanCard';
import UsageProgressBar from '../billing/UsageProgressBar';
import PaymentMethodsContainer from '../billing/PaymentMethodsContainer';
import InvoiceHistoryTable from '../billing/InvoiceHistoryTable';
import { billingService, BillingInfo } from '../../services/billingService';
import { useProjectStore } from '../store/useProjectStore';
import toast from 'react-hot-toast';
import { Plan } from './types';

// Error boundary for billing page
class BillingErrorBoundary extends React.Component<any, { hasError: boolean, error: any }> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }
  componentDidCatch(_error: any, _errorInfo: any) {
    // Optionally log error
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Billing & Plan</h1>
            <p className="mt-1 text-gray-600">A billing error occurred.</p>
          </div>
          <Card className="p-6 border-red-200 bg-red-50">
            <div className="flex items-center space-x-3">
              <div className="flex-shrink-0">
                <div className="w-10 h-10 bg-red-500 rounded-lg flex items-center justify-center text-white">⚠️</div>
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-red-800">Billing Error</h4>
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

// Helper to safely extract usage values
function getUsageValue(billingInfo: BillingInfo | null, type: 'generations' | 'deployments', key: 'limit' | 'current', fallback: number) {
  return billingInfo?.usage?.[type]?.[key] ?? fallback;
}

const BillingPage: React.FC = () => {
    const { currentProjectId } = useProjectStore();
    const [billingInfo, setBillingInfo] = useState<BillingInfo | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [usageError, setUsageError] = useState<string | null>(null);
    const [isLoadingUsage, setIsLoadingUsage] = useState(true);

    // Fetch billing info
    useEffect(() => {
        if (!currentProjectId) return;
        setIsLoading(true);
        setError(null);
        setUsageError(null);
        setIsLoadingUsage(true);
        billingService.getBillingInfo(currentProjectId)
            .then(info => {
                setBillingInfo(info);
                setIsLoadingUsage(false);
            })
            .catch(err => {
                const msg = err instanceof Error ? err.message : 'Failed to fetch billing info';
                setError(msg);
                setUsageError(msg);
                setIsLoadingUsage(false);
                toast.error('Failed to load billing information');
            })
            .finally(() => setIsLoading(false));
    }, [currentProjectId]);

    const handleDownloadInvoice = (invoiceId: string) => {
        toast.success(`Starting download for invoice ${invoiceId}...`);
    };

    const handleUpgradePlan = (plan: Plan) => {
        toast.promise(
            new Promise((resolve) => setTimeout(resolve, 1500)),
            {
                loading: `Upgrading your project to ${plan}...`,
                success: <b>Successfully upgraded to ${plan}! Welcome aboard.</b>,
                error: <b>Could not upgrade at this time.</b>,
            }
        );
    };

    if (!currentProjectId) {
        return (
            <div className="text-center py-12 max-w-md mx-auto">
                <div className="w-16 h-16 bg-brand-primary/5 text-brand-primary rounded-full flex items-center justify-center mx-auto mb-6 border border-brand-primary/10">
                    <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                </div>
                <p className="text-gray-900 font-bold text-lg mb-2">No active project selected</p>
                <p className="text-sm text-gray-500 mb-6 font-semibold">Please select or create a workspace project to access and manage its plan details.</p>
                <Button
                    variant="primary"
                    className="bg-gradient-to-r from-brand-primary to-red-500 border-0 font-bold shadow-lg"
                    onClick={() => window.location.href = '/settings'}
                >
                    Go to Project Settings
                </Button>
            </div>
        );
    }

    if (isLoading) {
        return (
            <div className="space-y-8">
                <PageHeader title="Billing & Plan" subtitle="Loading workspace plan information..." />
                <div className="flex items-center justify-center py-24">
                    <div className="relative">
                        <div className="animate-spin rounded-full h-12 w-12 border-4 border-brand-primary/10 border-t-brand-primary"></div>
                    </div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="space-y-8">
                <PageHeader title="Billing & Plan" subtitle="Error retrieving plan info" />
                <Card className="p-6 border-red-200 bg-red-50/50 backdrop-blur-sm shadow-xl">
                    <div className="flex items-center space-x-4">
                        <div className="flex-shrink-0">
                            <div className="w-12 h-12 bg-red-500 rounded-xl flex items-center justify-center text-white text-xl shadow-md">⚠️</div>
                        </div>
                        <div className="flex-1">
                            <h4 className="font-bold text-red-800">Failed to Load Billing Info</h4>
                            <p className="text-sm text-red-700 font-medium">{error}</p>
                        </div>
                        <Button 
                            variant="secondary" 
                            size="sm"
                            className="font-bold shadow"
                            onClick={() => window.location.reload()}
                        >
                            Retry Loading
                        </Button>
                    </div>
                </Card>
            </div>
        );
    }

    const currentPlan = (billingInfo?.plan as Plan) || 'Free';
    const invoices = billingInfo?.invoiceHistory || [];

    // Render premium usage progress trackers
    const renderUsageSection = () => {
        if (isLoadingUsage) {
            return (
                <Card className="animate-pulse space-y-4">
                    <div className="h-6 bg-gray-150 rounded w-1/3" />
                    <div className="h-4 bg-gray-150 rounded w-full" />
                    <div className="h-4 bg-gray-150 rounded w-full" />
                </Card>
            );
        }
        if (usageError) {
            return (
                <Card className="p-6 text-center text-red-600 bg-red-50 border-red-250">
                    <p className="font-semibold">{usageError}</p>
                    <Button variant="secondary" size="sm" className="mt-3" onClick={() => window.location.reload()}>Retry</Button>
                </Card>
            );
        }
        return (
            <Card className="shadow-lg border border-gray-150">
                <h2 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
                    <svg className="w-5 h-5 text-brand-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                    Current Plan Resource Usage ({currentPlan})
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <UsageProgressBar
                        label="Generations"
                        current={getUsageValue(billingInfo, 'generations', 'current', 0)}
                        limit={getUsageValue(billingInfo, 'generations', 'limit', 20)}
                        type="generations"
                    />
                    <UsageProgressBar
                        label="Deployments"
                        current={getUsageValue(billingInfo, 'deployments', 'current', 0)}
                        limit={getUsageValue(billingInfo, 'deployments', 'limit', 10)}
                        type="deployments"
                    />
                </div>
            </Card>
        );
    };

    return (
        <BillingErrorBoundary>
            <div className="space-y-8" data-testid="billing-page">
                {/* Unified Page Header */}
                <PageHeader 
                    title="Billing & Plan" 
                    subtitle="Manage your subscription, change plans, add cards, and review receipt records."
                />

                {/* Plans Selection Matrix */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <PlanCard
                        plan="Free"
                        description="For small side-projects and developers getting started"
                        price="Free"
                        features={[
                            `${getUsageValue(billingInfo, 'generations', 'limit', 20)} AI code generations/month`,
                            `${getUsageValue(billingInfo, 'deployments', 'limit', 10)} live workspace deployments/month`,
                            'Standard community discord support',
                            'Basic Gemini infrastructure fine-tuning tools'
                        ]}
                        cta="Active Free Tier"
                        currentPlan={currentPlan}
                        onUpgrade={() => handleUpgradePlan('Free')}
                    />
                    <PlanCard
                        plan="Pro"
                        description="For production scale workloads and enterprise architects"
                        price="$49"
                        features={[
                            'Unlimited AI code generations',
                            'Unlimited live workspace deployments',
                            'Access to Ultra premium model models',
                            'Priority 24/7 slack/email engineer support',
                            'Enhanced pipeline concurrency pipelines'
                        ]}
                        cta="Upgrade to Pro"
                        currentPlan={currentPlan}
                        onUpgrade={() => handleUpgradePlan('Pro')}
                    />
                </div>

                {/* Real-time Usage Progress indicators */}
                {renderUsageSection()}

                {/* Reusable Payment Methods container (Adds, deletes cards) */}
                <PaymentMethodsContainer />

                {/* Reusable Invoice History (Includes full search & filter dropdown controls) */}
                <InvoiceHistoryTable 
                    invoices={invoices} 
                    onDownload={handleDownloadInvoice}
                />
            </div>
        </BillingErrorBoundary>
    );
};

export default BillingPage;