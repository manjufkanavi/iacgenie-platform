import React from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import { usePipelineStore } from '../../store/usePipelineStore';

interface PipelineMetricsProps {
  pipelineId?: string;
}

const formatDuration = (seconds: number): string => {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${mins}m`;
};

interface MetricCardProps {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  variant?: 'default' | 'success' | 'error' | 'warning';
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value, icon, variant = 'default' }) => {
  const variantClasses: Record<string, string> = {
    default: 'bg-gray-800 dark:bg-slate-800 border-gray-700',
    success: 'bg-green-950/30 border-green-800/30',
    error: 'bg-red-950/30 border-red-800/30',
    warning: 'bg-yellow-950/30 border-yellow-800/30',
  };

  return (
    <div className={`p-4 rounded-lg border ${variantClasses[variant]}`}>
      <div className="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-1">
        {icon}
        <span>{label}</span>
      </div>
      <div className="text-2xl font-bold text-gray-100 dark:text-gray-100">{value}</div>
    </div>
  );
};

const PipelineMetrics: React.FC<PipelineMetricsProps> = (_props) => {
  const activePipeline = usePipelineStore((s) => s.activePipeline);
  const phaseHistory = usePipelineStore((s) => s.phaseHistory);

  if (!activePipeline) {
    return (
      <Card variant="empty-state" padding="lg">
        <p className="text-sm text-gray-400 dark:text-gray-500">No active pipeline metrics</p>
      </Card>
    );
  }

  const completedPhases = phaseHistory.filter((e) => e.status === 'success').length;
  const failedPhases = phaseHistory.filter((e) => e.status === 'failed').length;
  const totalRetries = activePipeline.retryCount;

  // Calculate phase timing breakdown
  const lastPhase = phaseHistory[phaseHistory.length - 2];
  const currentPhaseEntry = phaseHistory[phaseHistory.length - 1];

  return (
    <Card padding="lg" className="space-y-4">
      {/* Metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard
          label="Total Time"
          value={formatDuration(activePipeline.elapsedSeconds)}
        />
        <MetricCard
          label="Retries"
          value={totalRetries}
          variant="warning"
        />
        <MetricCard
          label="Errors"
          value={activePipeline.errorCount}
          variant={activePipeline.errorCount > 0 ? 'error' : 'default'}
        />
        <MetricCard
          label="Completed"
          value={`${completedPhases}/${phaseHistory.length}`}
          variant={failedPhases === 0 ? 'success' : 'default'}
        />
      </div>

      {/* Phase timing breakdown */}
      {phaseHistory.length > 0 && (
        <div className="space-y-2">
          <span className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
            Phase Timing
          </span>
          <div className="space-y-1.5">
            {lastPhase && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-400 dark:text-gray-500">{lastPhase.phase}</span>
                <span className="text-gray-300 font-mono">
                  {lastPhase.duration ? formatDuration(lastPhase.duration) : '—'}
                </span>
              </div>
            )}
            {currentPhaseEntry && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-brand-primary font-medium">{currentPhaseEntry.phase}</span>
                <span className="text-gray-300 font-mono animate-pulse-agent">running...</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Quick action buttons */}
      <div className="flex items-center gap-2 pt-2 border-t border-gray-700 dark:border-slate-700">
        {activePipeline.status === 'running' && (
          <Button size="sm" variant="outline" onClick={() => usePipelineStore.getState().pausePipeline()}>
            Pause
          </Button>
        )}
        {activePipeline.status === 'paused' && (
          <Button size="sm" variant="outline" onClick={() => usePipelineStore.getState().resumePipeline()}>
            Resume
          </Button>
        )}
        {failedPhases > 0 && (
          <Button size="sm" variant="outline" onClick={() => {}}>
            Retry Failed
          </Button>
        )}
        <div className="flex-1" />
        <Button size="sm" variant="danger" onClick={() => usePipelineStore.getState().abortPipeline()}>
          Abort
        </Button>
      </div>
    </Card>
  );
};

export default PipelineMetrics;
