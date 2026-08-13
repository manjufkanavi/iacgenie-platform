import React, { useState } from 'react';
import PhaseStatusBadge from './PhaseStatusBadge';
import type { PipelinePhase, PhaseStatus } from '../types';

interface PhaseNode {
  phase: PipelinePhase;
  status: PhaseStatus;
  label: string;
}

interface PipelinePhaseFlowProps {
  phases: PhaseNode[];
  orientation?: 'horizontal' | 'vertical';
}

const phaseOrder: PipelinePhase[] = [
  'clarify', 'generate', 'format', 'static_analysis',
  'init', 'validate', 'plan_review', 'plan',
  'apply_review', 'apply', 'escalate', 'complete',
];

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

const connectorColor: Record<PhaseStatus, string> = {
  success: 'bg-status-success',
  running: 'bg-status-running animate-pulse-agent',
  pending: 'bg-gray-300 dark:bg-slate-600',
  failed: 'bg-status-failed',
  escalated: 'bg-status-escalated',
};

const PipelinePhaseFlow: React.FC<PipelinePhaseFlowProps> = ({
  phases,
  orientation = 'horizontal',
}) => {
  const [tooltipPhase, setTooltipPhase] = useState<PipelinePhase | null>(null);

  // Build ordered phase nodes
  const orderedPhases = phaseOrder.map((phase) => {
    const found = phases.find((p) => p.phase === phase);
    return found || { phase, status: 'pending' as PhaseStatus, label: phaseLabels[phase] };
  });

  if (orientation === 'vertical') {
    return (
      <div className="flex flex-col gap-2" role="list" aria-label="Pipeline phase flow">
        {orderedPhases.map(({ phase, status, label }, idx) => (
          <div key={phase} className="flex items-center gap-3" role="listitem">
            {idx > 0 && (
              <div className={`w-6 h-0.5 ${connectorColor[status]} transition-all`} />
            )}
            <div
              className="relative flex-1"
              onMouseEnter={() => setTooltipPhase(phase)}
              onMouseLeave={() => setTooltipPhase(null)}
            >
              <PhaseStatusBadge phase={label} status={status} size="sm" />
              {tooltipPhase === phase && (
                <div className="absolute bottom-full left-0 mb-2 px-3 py-1.5 bg-slate-900 dark:bg-slate-700 text-white text-xs rounded-lg shadow-lg whitespace-nowrap z-[600]">
                  {label} — {status}
                  <div className="absolute top-full left-2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-slate-900 dark:border-t-slate-700" />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1 overflow-x-auto" role="list" aria-label="Pipeline phase flow">
      {orderedPhases.map(({ phase, status, label }, idx) => (
        <div key={phase} className="flex items-center" role="listitem">
          {idx > 0 && (
            <div className={`w-4 h-0.5 ${connectorColor[status]} transition-all mx-0.5`} />
          )}
          <div
            className="relative"
            onMouseEnter={() => setTooltipPhase(phase)}
            onMouseLeave={() => setTooltipPhase(null)}
          >
            <PhaseStatusBadge phase={label} status={status} size="sm" />
            {tooltipPhase === phase && (
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-slate-900 dark:bg-slate-700 text-white text-xs rounded-lg shadow-lg whitespace-nowrap z-[600]">
                {label} — {status}
                <div className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-slate-900 dark:border-t-slate-700" />
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default PipelinePhaseFlow;
