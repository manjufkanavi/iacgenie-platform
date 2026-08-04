import React, { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import type { PipelineTab } from './types';
import Card from '../ui/Card';
import PageHeader from '../layout/PageHeader';
import CurrentPhasePanel from '../pipeline/CurrentPhasePanel';
import PipelineMetrics from '../pipeline/PipelineMetrics';
import SessionStreamIndicator from '../pipeline/SessionStreamIndicator';
import PipelineRail, { RailPhaseState } from '../pipeline/PipelineRail';
import UnifiedAgentLog from './pipeline/UnifiedAgentLog';
import InlineReviewPanel from '../pipeline/InlineReviewPanel';
import { usePipelineStore } from '.././store/usePipelineStore';
import { usePipelineWebSocket } from '.././hooks/usePipelineWebSocket';
import { workflowService as workflowService } from './workflowService';
import { useAppStore } from '.././store/useAppStore';
import type { PipelinePhase, PhaseStatus } from './types';
import toast from 'react-hot-toast';
import { SkipForward, AlertTriangle, RefreshCw, Eye } from 'lucide-react';

// Import New OpenTofu Module 4 Components
import TofuPlanOutput from '../pipeline/TofuPlanOutput';
import ResourceImpactSummary from '../pipeline/ResourceImpactSummary';
import DeploymentActionBar from '../pipeline/DeploymentActionBar';
import ExecutionStateIndicator from '../pipeline/ExecutionStateIndicator';
import OpenTofuTabPanel from '../pipeline/OpenTofuTabPanel';
import CostEstimationPanel from '../pipeline/CostEstimationPanel';
import type { DiffResource } from '../pipeline/DiffPanel';
import DiffTabPanel from '../pipeline/DiffTabPanel';
import TimelineTabPanel from '../pipeline/TimelineTabPanel';
import ObservabilityTabPanel from '../pipeline/ObservabilityTabPanel';

const phaseLabels: Record<PipelinePhase, string> = {
  clarify: 'Clarify',
  generate: 'Generate',
  format: 'Format',
  static_analysis: 'Static Analysis',
  init: 'Init',
  validate: 'Validate',
  plan_review: 'Plan Review',
  plan: 'Plan',
  apply_review: 'Apply Review',
  apply: 'Apply',
  escalate: 'Escalate',
  complete: 'Complete',
};

const MOCK_PLAN_RESOURCES: DiffResource[] = [
  {
    address: 'aws_vpc.main',
    type: 'aws_vpc',
    name: 'main',
    action: 'create',
    provider: 'aws',
    costDelta: 36.00,
    changes: {
      cidr_block: { old: undefined, new: '10.0.0.0/16' },
      enable_dns_support: { old: undefined, new: true }
    }
  },
  {
    address: 'aws_security_group.ingress',
    type: 'aws_security_group',
    name: 'ingress',
    action: 'create',
    provider: 'aws',
    costDelta: 0.00,
    changes: {
      name: { old: undefined, new: 'allow-ssh' },
      description: { old: undefined, new: 'Allow SSH inbound traffic' }
    }
  },
  {
    address: 'aws_s3_bucket.state_store',
    type: 'aws_s3_bucket',
    name: 'state_store',
    action: 'create',
    provider: 'aws',
    costDelta: 11.00,
    changes: {
      bucket: { old: undefined, new: 'iacgenie-state-store' },
      versioning: { old: undefined, new: true }
    }
  }
];

const MOCK_FILES = [
  {
    name: 'main.tf',
    content: `# Main Infrastructure Configuration
provider "aws" {
  region = "us-east-1"
}

resource "aws_vpc" "main" {
  cidr_block       = "10.0.0.0/16"
  instance_tenancy = "default"

  tags = {
    Name        = "main-vpc"
    environment = "prod"
  }
}

resource "aws_security_group" "ingress" {
  name        = "allow-ssh"
  description = "Allow SSH inbound traffic"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH from VPC"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
}`
  },
  {
    name: 'variables.tf',
    content: `# Variables Definition
variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "Target deployment region"
}`
  },
  {
    name: 'outputs.tf',
    content: `# Outputs
output "vpc_id" {
  value       = aws_vpc.main.id
  description = "The ID of the main VPC"
}`
  }
];

const PLAN_LOG_OUTPUT = `
Terraform will perform the following actions:

  # aws_vpc.main will be created
  + resource "aws_vpc" "main" {
      + cidr_block       = "10.0.0.0/16"
      + instance_tenancy = "default"
      + enable_dns_support = true

      + tags = {
          + Name        = "main-vpc"
          + environment = "prod"
        }
    }

  # aws_security_group.ingress will be created
  + resource "aws_security_group" "ingress" {
      + name        = "allow-ssh"
      + description = "Allow SSH inbound traffic"
      + vpc_id      = (known after apply)

      + ingress {
          + description = "SSH from VPC"
          + from_port   = 22
          + to_port     = 22
          + protocol    = "tcp"
          + cidr_blocks = [
              + "10.0.0.0/16",
            ]
        }
    }

  # aws_s3_bucket.state_store will be created
  + resource "aws_s3_bucket" "state_store" {
      + bucket = "iacgenie-state-store"
      + force_destroy = false
      + versioning = true
    }

Plan: 3 to add, 0 to change, 0 to destroy.
`;

const APPLY_LOG_OUTPUT = `
aws_vpc.main: Creating...
aws_s3_bucket.state_store: Creating...
aws_vpc.main: Creation complete after 3s [id=vpc-12345]
aws_security_group.ingress: Creating...
aws_s3_bucket.state_store: Creation complete after 5s [id=iacgenie-state-store]
aws_security_group.ingress: Creation complete after 2s [id=sg-56789]

Apply complete! Resources: 3 added, 0 changed, 0 destroyed.
`;

const PipelineDetailView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const activePipeline = usePipelineStore((s) => s.activePipeline);
  const phaseHistory = usePipelineStore((s) => s.phaseHistory);
  const pipelineLogs = usePipelineStore((s) => s.pipelineLogs);
  const transitionPhase = usePipelineStore((s) => s.transitionPhase);
  const errorMessage = usePipelineStore((s) => s.errorMessage);
  
  // App store roles
  const currentProject = useAppStore((s) => s.currentProject);
  const hasPermission = currentProject ? useAppStore((s) => s.hasProjectEditAccess(currentProject.id)) : true;
  const deploymentMode = useAppStore((s) => s.deploymentMode);

  // Real-time connection states from Zustand store
  const connectionState = usePipelineStore((s) => s.connectionState);
  const latency = usePipelineStore((s) => s.latency);
  const eventsReceived = usePipelineStore((s) => s.eventsReceived);
  const reconnects = usePipelineStore((s) => s.reconnects);

  const [pipelineId] = useState(id || 'abc123-def456');
  const [interruptModalOpen, setInterruptModalOpen] = useState(false);
  const [loadingApproval, setLoadingApproval] = useState(false);
  
  // New OpenTofu Workspaces layout state
  const [activeTab, setActiveTab] = useState('plan');
  const [selectedFileIdx, setSelectedFileIdx] = useState(0);

  // Top-level tab navigation (synced with URL ?tab= query param)
  const [searchParams, setSearchParams] = useSearchParams();
  const topLevelTab = (searchParams.get('tab') as PipelineTab) || 'overview';
  const setTopLevelTab = (tab: PipelineTab) => setSearchParams({ tab });
  
  // LocalStack simulation state
  const [estimatedCostData, setEstimatedCostData] = useState<any>(null);
  const [isTearingDown, setIsTearingDown] = useState(false);

  useEffect(() => {
    if (deploymentMode === 'localstack' && pipelineId) {
      workflowService.estimateCost(pipelineId)
        .then((res: any) => setEstimatedCostData(res.data))
        .catch((err: any) => console.error("Failed to fetch cost estimation:", err));
    }
  }, [deploymentMode, pipelineId]);

  const handleTeardownSimulation = async () => {
    setIsTearingDown(true);
    try {
      await workflowService.teardownSimulation(pipelineId);
      toast.success('LocalStack simulation infrastructure destroyed successfully.');
    } catch (err: any) {
      toast.error('Teardown failed: ' + (err.response?.data?.detail?.error || err.message || 'Server error'));
    } finally {
      setIsTearingDown(false);
    }
  };

  // Connect WebSocket for real-time updates
  usePipelineWebSocket(pipelineId);

  // Auto-trigger human review modal if active state enters clarify escalate or validate interrupt state
  useEffect(() => {
    if (activePipeline?.phase === 'escalate' || activePipeline?.status === 'escalated') {
      setInterruptModalOpen(true);
    }
  }, [activePipeline?.phase, activePipeline?.status]);

  // Build phase nodes from history + active pipeline
  const phases = (() => {
    const phaseSet = new Map<PipelinePhase, PhaseStatus>();
    for (const entry of phaseHistory) {
      phaseSet.set(entry.phase, entry.status);
    }
    for (const phase of Object.keys(phaseLabels) as PipelinePhase[]) {
      if (!phaseSet.has(phase)) {
        phaseSet.set(phase, 'pending');
      }
    }
    return Array.from(phaseSet.entries()).map(([phase, status]) => ({ phase, status }));
  })();

  // Set active pipeline placeholder if not set to prevent breaks
  useEffect(() => {
    if (pipelineId && !activePipeline) {
      usePipelineStore.getState().setActivePipeline({
        id: pipelineId,
        name: `Infrastructure Pipeline ${pipelineId.slice(0, 6)}`,
        phase: 'validate',
        status: 'running',
        currentPhaseProgress: 45,
        startTime: new Date().toISOString(),
        elapsedSeconds: 120,
        retryCount: 0,
        errorCount: 0
      });
    }
  }, [pipelineId, activePipeline]);

  // Action: Manual Retry
  const handleRetryPhase = () => {
    if (!activePipeline) return;
    toast.promise(
      new Promise((resolve) => setTimeout(resolve, 1500)),
      {
        loading: 'Retrying current pipeline phase...',
        success: <b>Successfully restarted active phase validation!</b>,
        error: <b>Retry failed.</b>,
      }
    );
  };

  // Action: Skip Phase
  const handleSkipPhase = () => {
    if (!activePipeline) return;
    const currentPhase = activePipeline.phase;
    toast.success(`Skipped current phase: ${phaseLabels[currentPhase] || currentPhase}`);
    const nextPhaseMap: Record<PipelinePhase, PipelinePhase> = {
      clarify: 'generate',
      generate: 'format',
      format: 'static_analysis',
      static_analysis: 'init',
      init: 'validate',
      validate: 'plan_review',
      plan_review: 'plan',
      plan: 'apply_review',
      apply_review: 'apply',
      apply: 'complete',
      escalate: 'clarify',
      complete: 'complete',
    };
    const nextPhase = nextPhaseMap[currentPhase] || 'complete';
    transitionPhase(nextPhase, 'running');
  };

  // Action: Escalate Phase
  const handleEscalatePhase = () => {
    if (!activePipeline) return;
    toast.error('Escalating pipeline session to Human-in-the-Loop review queue...');
    transitionPhase('escalate', 'escalated');
  };

  // Action: Approval Resumption
  const handleApproveResumption = async (_notes?: string) => {
    setLoadingApproval(true);
    try {
      await workflowService.approvePhase(pipelineId);
      toast.success('Validation review approved. State resumed!');
      setInterruptModalOpen(false);
      transitionPhase('plan_review', 'running');
    } catch (err: any) {
      toast.error('Approval failed: ' + (err.message || 'Server error'));
    } finally {
      setLoadingApproval(false);
    }
  };

  // Action: Abort Pipeline
  const handleAbortResumption = async () => {
    try {
      await workflowService.abortPipeline(pipelineId);
      toast.success('Pipeline execution aborted successfully.');
      setInterruptModalOpen(false);
      usePipelineStore.getState().abortPipeline();
    } catch (err: any) {
      toast.error('Abort failed: ' + (err.message || 'Server error'));
    }
  };

  // State mapping for DeploymentActionBar
  const getExecutionState = (): 'idle' | 'planning' | 'applying' | 'complete' | 'error' | 'cancelled' => {
    if (!activePipeline) return 'idle';
    if (activePipeline.status === 'failed') {
      if (errorMessage?.toLowerCase().includes('cancel') || errorMessage?.toLowerCase().includes('abort')) return 'cancelled';
      return 'error';
    }
    if (activePipeline.status === 'completed') return 'complete';
    if (activePipeline.phase === 'plan' && activePipeline.status === 'running') return 'planning';
    if (activePipeline.phase === 'apply' && activePipeline.status === 'running') return 'applying';
    return 'idle';
  };

  const handlePlan = () => {
    toast.promise(
      new Promise((resolve) => setTimeout(resolve, 2000)),
      {
        loading: 'Initializing OpenTofu dry-run plan...',
        success: 'Dry-run plan finished successfully!',
        error: 'Plan dry-run failed.',
      }
    );
    transitionPhase('plan', 'running');
    usePipelineStore.getState().addLogEntry({
      phase: 'plan',
      level: 'info',
      message: 'Running OpenTofu dry-run plan generation...'
    });
    // Autoselect plan tab
    setActiveTab('plan');
    
    // Simulate successful run complete
    setTimeout(() => {
      usePipelineStore.getState().addLogEntry({
        phase: 'plan',
        level: 'info',
        message: 'Plan complete: 3 resources to create.'
      });
      transitionPhase('plan_review', 'running');
    }, 2000);
  };

  const handleDeploy = () => {
    if (!hasPermission) {
      toast.error('Cannot deploy: insufficient project permissions.');
      return;
    }
    toast.promise(
      new Promise((resolve) => setTimeout(resolve, 2500)),
      {
        loading: 'Initializing OpenTofu apply deployment...',
        success: 'Infrastructure successfully applied!',
        error: 'Apply deployment failed.',
      }
    );
    transitionPhase('apply', 'running');
    usePipelineStore.getState().addLogEntry({
      phase: 'apply',
      level: 'info',
      message: 'Applying plan alterations in workspace...'
    });
    setActiveTab('apply');

    setTimeout(() => {
      usePipelineStore.getState().addLogEntry({
        phase: 'apply',
        level: 'info',
        message: 'Deployment finished successfully! Infrastructure active.'
      });
      transitionPhase('complete', 'success');
    }, 2500);
  };

  const handleCancel = async () => {
    try {
      await workflowService.abortPipeline(pipelineId);
      toast.success('Pipeline execution aborted.');
      usePipelineStore.getState().abortPipeline();
      usePipelineStore.getState().setError('Execution was cancelled by user');
    } catch (e) {
      // Offline fallback
      usePipelineStore.getState().abortPipeline();
      usePipelineStore.getState().setError('Execution was cancelled by user');
      toast.success('Pipeline execution aborted locally.');
    }
  };



  const isTofuPhase = activePipeline && ['init', 'validate', 'plan_review', 'plan', 'apply_review', 'apply', 'complete'].includes(activePipeline.phase);
  const execState = getExecutionState();

  return (
    <div className="space-y-8" data-testid="pipeline-detail-view">
      {/* Page Header with Stream Indicator */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 select-none">
        <PageHeader
          title={`Pipeline ${activePipeline ? ` — ${activePipeline.name}` : ''}`}
          subtitle={`Session ID: ${pipelineId}`}
        />
        <SessionStreamIndicator
          state={connectionState}
          latency={latency}
          eventsReceived={eventsReceived}
          reconnects={reconnects}
          errorMessage={errorMessage}
          onReconnect={() => usePipelineWebSocket(pipelineId)}
          size="md"
        />
      </div>

      {/* Interactive controls row (Retry, Skip, Escalate) */}
      <Card className="p-6 border border-slate-100 dark:border-slate-800 shadow-md">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h3 className="text-sm font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Pipeline Orchestration Options</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold">Manually alter the current execution state or escalate issues.</p>
          </div>
          <div className="flex flex-wrap gap-2 w-full sm:w-auto justify-end">
            <button
              onClick={handleRetryPhase}
              className="flex items-center gap-1.5 px-4 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 rounded-xl text-xs font-bold hover:bg-slate-100 dark:hover:bg-slate-750 transition shadow-sm uppercase tracking-wider"
              data-testid="pipeline-retry-button"
            >
              <RefreshCw className="w-3.5 h-3.5 text-brand-primary" />
              Retry Phase
            </button>
            <button
              onClick={handleSkipPhase}
              className="flex items-center gap-1.5 px-4 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 rounded-xl text-xs font-bold hover:bg-slate-100 dark:hover:bg-slate-750 transition shadow-sm uppercase tracking-wider"
              data-testid="pipeline-skip-button"
            >
              <SkipForward className="w-3.5 h-3.5 text-brand-primary" />
              Skip Step
            </button>
            <button
              onClick={handleEscalatePhase}
              className="flex items-center gap-1.5 px-4 py-2.5 bg-red-50 border border-red-200 text-red-700 rounded-xl text-xs font-bold hover:bg-red-100 transition shadow-sm uppercase tracking-wider"
              data-testid="pipeline-escalate-button"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Escalate Phase
            </button>
          </div>
        </div>
      </Card>

      {/* Linear Pipeline Rail */}
      <PipelineRail
        phases={[
          'clarify', 'generate', 'format', 'static_analysis', 'init', 'validate',
          'plan_review', 'plan', 'apply_review', 'apply', 'escalate', 'complete'
        ]}
        currentPhase={activePipeline?.phase || null}
        phaseStates={
          phases.reduce((acc, p) => {
            const isActive = activePipeline?.phase === p.phase;
            const statusVal = isActive
              ? (activePipeline?.status === 'failed' ? 'failed' : activePipeline?.status === 'escalated' ? 'needs_input' : 'active')
              : (p.status === 'success' ? 'completed' : p.status === 'failed' ? 'failed' : p.status === 'escalated' ? 'needs_input' : 'pending');
            acc[p.phase] = statusVal as RailPhaseState;
            return acc;
          }, {} as Record<string, RailPhaseState>)
        }
      />

      {/* Top-level Tab Navigation */}
      <div className="border-b border-slate-200 dark:border-slate-700">
        <nav className="flex gap-1 -mb-px" role="tablist">
          {([
            { key: 'overview' as PipelineTab, label: 'Overview' },
            { key: 'infrastructure' as PipelineTab, label: 'Infrastructure' },
            { key: 'diff' as PipelineTab, label: 'Diff' },
            { key: 'timeline' as PipelineTab, label: 'Timeline' },
            { key: 'observability' as PipelineTab, label: 'Observability' },
          ]).map((tab) => (
            <button
              key={tab.key}
              onClick={() => setTopLevelTab(tab.key)}
              role="tab"
              aria-selected={topLevelTab === tab.key}
              aria-controls={`${tab.key}-panel`}
              className={`px-4 py-2.5 text-xs font-bold uppercase tracking-wider border-b-2 transition-colors ${
                topLevelTab === tab.key
                  ? 'border-brand-primary text-brand-primary'
                  : 'border-transparent text-slate-500 hover:text-slate-300 hover:border-slate-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Panels */}
      {topLevelTab === 'overview' && (
        <>
          {/* NEW OpenTofu Module 4 Dashboard / Layout */}
      {isTofuPhase ? (
        <div className="space-y-6">
          
          {/* Actions Bar */}
          <DeploymentActionBar
            state={execState}
            onPlan={handlePlan}
            onDeploy={handleDeploy}
            onCancel={handleCancel}
            hasPermission={hasPermission}
          />

          {/* Core Panel Grid: Left Summary, Right Output Panel */}
          <div className="grid grid-cols-1 lg:grid-cols-10 gap-6">
            
            {/* Impact summary (col-span-3) */}
            <div className="lg:col-span-3 space-y-4">
              <ResourceImpactSummary
                resources={MOCK_PLAN_RESOURCES}
                showCostImpact
                onResourceSelect={(addr) => {
                  setActiveTab('plan');
                  toast.success(`Showing plan diff line for: ${addr}`);
                }}
                hasPermission={hasPermission}
              />

              <div className="flex items-center justify-between p-3.5 bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-xl">
                <span className="text-xs font-bold text-slate-500 dark:text-slate-400">Current Session State</span>
                <ExecutionStateIndicator state={execState} size="sm" showLabel />
              </div>
            </div>

            {/* Right Multi-Tabs details view (col-span-7) */}
            <div className="lg:col-span-7 flex flex-col space-y-2">
              <OpenTofuTabPanel
                tabs={[
                  { key: 'plan', label: 'Plan Output', count: execState === 'planning' ? 0 : undefined },
                  { key: 'apply', label: 'Apply Output', count: execState === 'applying' ? 0 : undefined },
                  { key: 'state', label: 'State Summary' },
                  { key: 'files', label: 'Generated Files' },
                ]}
                activeTab={activeTab}
                onTabChange={setActiveTab}
              />

              <div className="flex-1 bg-white dark:bg-slate-900 rounded-xl overflow-hidden min-h-[350px] animate-[console-log-enter_150ms_ease-out]">
                {activeTab === 'plan' && (
                  <TofuPlanOutput
                    output={PLAN_LOG_OUTPUT}
                    mode="plan"
                    isLive={execState === 'planning'}
                    onResourceClick={(addr) => toast.success(`Selected resource: ${addr}`)}
                  />
                )}

                {activeTab === 'apply' && (
                  <TofuPlanOutput
                    output={execState === 'idle' && !phaseHistory.some(h => h.phase === 'apply') ? 'No apply output yet. Trigger deployment apply to stream logs.' : APPLY_LOG_OUTPUT}
                    mode="apply"
                    isLive={execState === 'applying'}
                  />
                )}

                {activeTab === 'state' && (
                  <Card padding="lg" className="border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/20 h-full flex flex-col justify-between">
                    <div>
                      <h4 className="text-sm font-bold text-gray-800 dark:text-slate-200">Active State Information</h4>
                      <p className="text-xs text-slate-500 mt-1">OpenTofu state registry containing active tracked records.</p>
                      
                      <div className="grid grid-cols-2 gap-4 mt-6">
                        <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 p-4 rounded-xl shadow-sm">
                          <span className="text-xs text-slate-500 font-bold uppercase block">Tracked Resources</span>
                          <strong className="text-2xl text-slate-900 dark:text-slate-100 font-black mt-1 block">3</strong>
                        </div>
                        <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 p-4 rounded-xl shadow-sm">
                          <span className="text-xs text-slate-500 font-bold uppercase block">Monthly Total Cost</span>
                          <strong className="text-2xl text-green-600 dark:text-green-400 font-black mt-1 block">$47.00</strong>
                        </div>
                      </div>
                    </div>

                    <div className="border-t border-slate-200 dark:border-slate-800 pt-4 mt-8 flex justify-end">
                      <span className="text-xs font-mono text-slate-400 font-semibold select-none flex items-center gap-1">
                        state_version: v4 • serial: 1
                      </span>
                    </div>
                  </Card>
                )}

                {activeTab === 'files' && (
                  <div className="grid grid-cols-1 md:grid-cols-10 h-full min-h-[350px] border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-slate-950">
                    
                    {/* Left list (span 3) */}
                    <div className="md:col-span-3 border-r border-slate-800 bg-slate-900/60 p-3.5 space-y-2 select-none">
                      <h4 className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2">HCL Configuration Files</h4>
                      <div className="space-y-1">
                        {MOCK_FILES.map((file, idx) => (
                          <button
                            key={file.name}
                            onClick={() => setSelectedFileIdx(idx)}
                            className={`w-full flex items-center justify-between px-3 py-2 text-xs font-bold font-sans rounded-xl border text-left cursor-pointer transition ${
                              selectedFileIdx === idx
                                ? 'bg-slate-950 border-slate-800 text-white'
                                : 'bg-transparent border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
                            }`}
                          >
                            <span>{file.name}</span>
                            <Eye className="w-3.5 h-3.5 opacity-60" />
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Right File Preview editor (span 7) */}
                    <div className="md:col-span-7 flex flex-col p-4 overflow-y-auto">
                      <div className="text-[10px] font-black text-slate-500 font-mono mb-2 uppercase select-none flex justify-between">
                        <span>PREVIEW AREA: {MOCK_FILES[selectedFileIdx].name}</span>
                        <span className="text-green-500 font-bold">READY</span>
                      </div>
                      <pre className="text-xs font-mono text-green-400 leading-relaxed whitespace-pre-wrap select-text max-h-[300px] overflow-y-auto pr-2">
                        <code>{MOCK_FILES[selectedFileIdx].content}</code>
                      </pre>
                    </div>

                  </div>
                )}
              </div>
            </div>

          </div>

        </div>
      ) : (
        /* Legacy current status panel layout */
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <CurrentPhasePanel pipelineId={pipelineId} />
          </div>
          <PipelineMetrics pipelineId={pipelineId} />
        </div>
      )}
        </>
      )}

      {/* Infrastructure Tab */}
      {topLevelTab === 'infrastructure' && (
        <div id="infrastructure-panel" role="tabpanel">
          <OpenTofuTabPanel
            tabs={[
              { key: 'plan', label: 'Plan Output', count: execState === 'planning' ? 0 : undefined },
              { key: 'apply', label: 'Apply Output', count: execState === 'applying' ? 0 : undefined },
              { key: 'state', label: 'State Summary' },
              { key: 'files', label: 'Generated Files' },
            ]}
            activeTab={activeTab}
            onTabChange={setActiveTab}
          />
          <div className="flex-1 bg-white dark:bg-slate-900 rounded-xl overflow-hidden min-h-[350px] animate-[console-log-enter_150ms_ease-out] mt-2">
            {activeTab === 'plan' && (
              <TofuPlanOutput
                output={PLAN_LOG_OUTPUT}
                mode="plan"
                isLive={execState === 'planning'}
                onResourceClick={(addr) => toast.success(`Selected resource: ${addr}`)}
              />
            )}
            {activeTab === 'apply' && (
              <TofuPlanOutput
                output={execState === 'idle' && !phaseHistory.some(h => h.phase === 'apply') ? 'No apply output yet. Trigger deployment apply to stream logs.' : APPLY_LOG_OUTPUT}
                mode="apply"
                isLive={execState === 'applying'}
              />
            )}
            {activeTab === 'state' && (
              <Card padding="lg" className="border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/20 h-full flex flex-col justify-between">
                <div>
                  <h4 className="text-sm font-bold text-gray-800 dark:text-slate-200">Active State Information</h4>
                  <p className="text-xs text-slate-500 mt-1">OpenTofu state registry containing active tracked records.</p>
                  <div className="grid grid-cols-2 gap-4 mt-6">
                    <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 p-4 rounded-xl shadow-sm">
                      <span className="text-xs text-slate-500 font-bold uppercase block">Tracked Resources</span>
                      <strong className="text-2xl text-slate-900 dark:text-slate-100 font-black mt-1 block">3</strong>
                    </div>
                    <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 p-4 rounded-xl shadow-sm">
                      <span className="text-xs text-slate-500 font-bold uppercase block">Monthly Total Cost</span>
                      <strong className="text-2xl text-green-600 dark:text-green-400 font-black mt-1 block">$47.00</strong>
                    </div>
                  </div>
                </div>
                <div className="border-t border-slate-200 dark:border-slate-800 pt-4 mt-8 flex justify-end">
                  <span className="text-xs font-mono text-slate-400 font-semibold select-none flex items-center gap-1">
                    state_version: v4 • serial: 1
                  </span>
                </div>
              </Card>
            )}
            {activeTab === 'files' && (
              <div className="grid grid-cols-1 md:grid-cols-10 h-full min-h-[350px] border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-slate-950">
                <div className="md:col-span-3 border-r border-slate-800 bg-slate-900/60 p-3.5 space-y-2 select-none">
                  <h4 className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2">HCL Configuration Files</h4>
                  <div className="space-y-1">
                    {MOCK_FILES.map((file, idx) => (
                      <button
                        key={file.name}
                        onClick={() => setSelectedFileIdx(idx)}
                        className={`w-full flex items-center justify-between px-3 py-2 text-xs font-bold font-sans rounded-xl border text-left cursor-pointer transition ${
                          selectedFileIdx === idx
                            ? 'bg-slate-950 border-slate-800 text-white'
                            : 'bg-transparent border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
                        }`}
                      >
                        <span>{file.name}</span>
                        <Eye className="w-3.5 h-3.5 opacity-60" />
                      </button>
                    ))}
                  </div>
                </div>
                <div className="md:col-span-7 flex flex-col p-4 overflow-y-auto">
                  <div className="text-[10px] font-black text-slate-500 font-mono mb-2 uppercase select-none flex justify-between">
                    <span>PREVIEW AREA: {MOCK_FILES[selectedFileIdx].name}</span>
                    <span className="text-green-500 font-bold">READY</span>
                  </div>
                  <pre className="text-xs font-mono text-green-400 leading-relaxed whitespace-pre-wrap select-text max-h-[300px] overflow-y-auto pr-2">
                    <code>{MOCK_FILES[selectedFileIdx].content}</code>
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Diff Tab */}
      {topLevelTab === 'diff' && (
        <div id="diff-panel" role="tabpanel">
          <DiffTabPanel />
        </div>
      )}

      {/* Timeline Tab */}
      {topLevelTab === 'timeline' && (
        <div id="timeline-panel" role="tabpanel">
          <TimelineTabPanel />
        </div>
      )}

      {/* Observability Tab */}
      {topLevelTab === 'observability' && (
        <div id="observability-panel" role="tabpanel">
          <ObservabilityTabPanel runId={pipelineId} />
        </div>
      )}

      {/* Shared content shown below tabs (always visible) */}
      <UnifiedAgentLog
        logs={pipelineLogs.map((log) => ({
          timestamp: log.timestamp,
          stage: log.phase,
          status: log.level === 'error' ? 'error' : log.level === 'warning' ? 'retrying' : activePipeline?.status === 'running' ? 'running' : 'success',
          message: log.message,
        }))}
        isExpanded={activePipeline?.status === 'running'}
      />

      {/* LocalStack Simulation Cost Estimation Dashboard Panel */}
      {deploymentMode === 'localstack' && (
        <div className="mt-8 space-y-6">
          <CostEstimationPanel metrics={estimatedCostData} resources={MOCK_PLAN_RESOURCES} compact={false} className="shadow-lg" />

          {/* Sandbox Environment Card */}
          <Card padding="lg" className="shadow-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">Sandbox Environment Active</h3>
              <p className="text-xs text-slate-500 mt-1">Resources are simulated locally. You can browse them in the LocalStack Web Console.</p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <a href="https://app.localstack.cloud/inst/default/resources" target="_blank" rel="noreferrer" className="text-xs font-bold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-4 py-2 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition">
                Open LocalStack UI
              </a>
              <button
                onClick={handleTeardownSimulation}
                disabled={isTearingDown}
                className="text-xs font-bold bg-red-50 text-red-600 px-4 py-2 rounded-lg hover:bg-red-100 transition disabled:opacity-50"
              >
                {isTearingDown ? 'Tearing down...' : 'Teardown Simulation'}
              </button>
            </div>
          </Card>
        </div>
      )}

      {/* Completed Phase History panel */}
      {phaseHistory.length > 0 && (
        <Card padding="lg" className="shadow-lg border-0 bg-slate-900">
          <h3 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-4">Completed Phase History</h3>
          <div className="space-y-3.5">
            {phaseHistory.map((entry, idx) => (
              <div key={idx} className="flex items-center justify-between text-sm border-b border-slate-800 pb-3 last:border-0 last:pb-0">
                <span className="text-slate-300 dark:text-slate-200 font-semibold">{phaseLabels[entry.phase] || entry.phase}</span>
                <div className="flex items-center gap-4">
                  {entry.duration && (
                    <span className="text-slate-500 dark:text-slate-400 font-mono text-xs">
                      {entry.duration}s elapsed
                    </span>
                  )}
                  <span className={`text-xs font-bold uppercase tracking-wider ${
                    entry.status === 'success' ? 'text-green-400' :
                    entry.status === 'failed' ? 'text-red-400' :
                    entry.status === 'escalated' ? 'text-brand-primary' :
                    entry.status === 'running' ? 'text-blue-400' :
                    'text-slate-500 dark:text-slate-400'
                  }`}>
                    {entry.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* HUMAN_REVIEW inline review panel */}
      {interruptModalOpen && (
        <InlineReviewPanel
          onApprove={() => handleApproveResumption()}
          onAbort={handleAbortResumption}
          isLoading={loadingApproval}
        />
      )}
    </div>
  );
};

export default PipelineDetailView;
export { PipelineDetailView };
