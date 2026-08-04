import React, { useState } from 'react';
import Card from '../ui/Card';
import PhaseStatusIndicator from './PhaseStatusIndicator';
import { usePipelineStore } from '.././store/usePipelineStore';
import type { LogLevel } from './types';

interface CurrentPhasePanelProps {
  pipelineId?: string;
}

const levelColors: Record<LogLevel, string> = {
  info: 'text-blue-400',
  warning: 'text-amber-400',
  error: 'text-red-400',
};

const CurrentPhasePanel: React.FC<CurrentPhasePanelProps> = (_props) => {
  const activePipeline = usePipelineStore((s) => s.activePipeline);
  const phaseHistory = usePipelineStore((s) => s.phaseHistory);
  const pipelineLogs = usePipelineStore((s) => s.pipelineLogs);

  const [isCodeExpanded, setIsCodeExpanded] = useState(false);
  const [logFilter, setLogFilter] = useState<LogLevel | 'all'>('all');

  if (!activePipeline) {
    return (
      <Card variant="empty-state" padding="lg">
        <p className="text-sm text-gray-400 dark:text-gray-500">No active pipeline</p>
      </Card>
    );
  }

  const currentPhase = activePipeline.phase;
  const progress = activePipeline.currentPhaseProgress;

  // Get current phase entry from history
  const currentHistoryEntry = phaseHistory[phaseHistory.length - 1];

  // Filter recent logs (last 5)
  const recentLogs = pipelineLogs
    .filter((log) => logFilter === 'all' || log.level === logFilter)
    .slice(-5);

  return (
    <Card padding="lg" className="space-y-4">
      {/* Phase header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <PhaseStatusIndicator
            phase={currentPhase}
            status={activePipeline.status === 'paused' ? 'paused' : 'running'}
            size="md"
            showLabel
          />
        </div>
        <span className="text-sm font-mono text-gray-400 dark:text-gray-500">
          {progress}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-700 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
        <div
          className="h-full bg-brand-primary transition-all duration-300 ease-out rounded-full"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Agent badge */}
      {currentHistoryEntry && (
        <div className="flex items-center gap-2 text-sm text-gray-400 dark:text-gray-500">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-700 dark:bg-slate-600 text-gray-300">
            Agent: {currentHistoryEntry.phase}
          </span>
        </div>
      )}

      {/* HCL code preview (collapsible) */}
      <div>
        <button
          onClick={() => setIsCodeExpanded(!isCodeExpanded)}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-300 transition-colors"
        >
          <svg
            className={`h-4 w-4 transition-transform ${isCodeExpanded ? 'rotate-90' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          HCL Preview
        </button>
        {isCodeExpanded && (
          <div className="mt-2 p-3 bg-gray-950 dark:bg-slate-950 rounded-lg border border-gray-700 dark:border-slate-700 font-mono text-xs text-green-400 overflow-x-auto">
            <pre className="whitespace-pre">{`# ${currentPhase} phase output`}{'\n'}
{`# Code generation in progress...`}</pre>
          </div>
        )}
      </div>

      {/* Mini log console */}
      {recentLogs.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Recent Logs</span>
            <select
              value={logFilter}
              onChange={(e) => setLogFilter(e.target.value as LogLevel | 'all')}
              className="text-xs bg-gray-800 dark:bg-slate-800 border border-gray-700 rounded px-2 py-0.5 text-gray-400"
            >
              <option value="all">All</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
            </select>
          </div>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {recentLogs.map((log, idx) => (
              <div key={idx} className="flex items-start gap-2 text-xs font-mono">
                <span className={levelColors[log.level]}>{log.level.toUpperCase()}</span>
                <span className="text-gray-400 dark:text-gray-500">{log.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
};

export default CurrentPhasePanel;
