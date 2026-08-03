import React, { useState } from 'react';
import PhaseStatusIndicator from './PhaseStatusIndicator';
import type { PipelinePhase, PhaseStatus } from '../../types';

interface PipelineFlowDiagramProps {
  phases: Array<{ phase: PipelinePhase; status: PhaseStatus; label?: string }>;
  orientation?: 'horizontal' | 'vertical';
  onPhaseClick?: (phase: PipelinePhase) => void;
  className?: string;
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

const PipelineFlowDiagram: React.FC<PipelineFlowDiagramProps> = ({
  phases,
  orientation,
  onPhaseClick,
  className = '',
}) => {
  const [tooltipPhase, setTooltipPhase] = useState<PipelinePhase | null>(null);
  const [expandedPhase, setExpandedPhase] = useState<PipelinePhase | null>(null);

  const effectiveOrientation: 'horizontal' | 'vertical' =
    orientation || (typeof window !== 'undefined' ? (window.innerWidth > 768 ? 'horizontal' : 'vertical') : 'horizontal');

  // Build ordered phase nodes
  const orderedPhases = phaseOrder.map((phase) => {
    const found = phases.find((p) => p.phase === phase);
    return found || { phase, status: 'pending' as PhaseStatus, label: phaseLabels[phase] };
  });

  const handlePhaseClick = (phase: PipelinePhase) => {
    setExpandedPhase(expandedPhase === phase ? null : phase);
    onPhaseClick?.(phase);
  };

  const expandedNode = expandedPhase ? orderedPhases.find((p) => p.phase === expandedPhase) : null;

  return (
    <div className={className}>
      {effectiveOrientation === 'vertical' ? (
        <div className="flex flex-col gap-2" role="list" aria-label="Pipeline phase flow">
          {orderedPhases.map(({ phase, status, label }, idx) => (
            <div key={phase} className="flex items-center gap-3" role="listitem">
              {idx > 0 && (
                <div className={`w-6 h-0.5 ${connectorColor[status]} transition-all`} />
              )}
              <div
                className="relative flex-1 cursor-pointer"
                onMouseEnter={() => setTooltipPhase(phase)}
                onMouseLeave={() => setTooltipPhase(null)}
                onClick={() => handlePhaseClick(phase)}
              >
                <PhaseStatusIndicator phase={phase} status={status} size="md" showLabel />
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
      ) : (
        <div className="flex items-center gap-1 overflow-x-auto" role="list" aria-label="Pipeline phase flow">
          {orderedPhases.map(({ phase, status, label }, idx) => (
            <div key={phase} className="flex items-center" role="listitem">
              {idx > 0 && (
                <div className={`w-4 h-0.5 ${connectorColor[status]} transition-all mx-0.5`} />
              )}
              <div
                className="relative cursor-pointer"
                onMouseEnter={() => setTooltipPhase(phase)}
                onMouseLeave={() => setTooltipPhase(null)}
                onClick={() => handlePhaseClick(phase)}
              >
                <PhaseStatusIndicator phase={phase} status={status} size="sm" />
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
      )}

      {/* Expanded phase detail panel */}
      {expandedNode && (
        <div className="mt-3 p-3 bg-slate-50 dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">{expandedNode.label}</span>
            <button
              onClick={() => setExpandedPhase(null)}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              aria-label="Close detail panel"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
            expandedNode.status === 'success' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
            expandedNode.status === 'running' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
            expandedNode.status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
            expandedNode.status === 'escalated' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
            'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
          }`}>
            {expandedNode.status}
          </span>
        </div>
      )}
    </div>
  );
};

export default PipelineFlowDiagram;
