import React, { useState } from 'react';
import Card from '../ui/Card';
import PhaseStatusBadge from './PhaseStatusBadge';
import type { AgentStatus } from './types';

interface AgentHeaderCardProps {
  agentName: string;
  description: string;
  status: AgentStatus;
  phaseLabel?: string;
  progress?: number; // 0-100
  modelLabel?: string;
  reasoningTimeline?: Array<{ step: string; timestamp: string }>;
}

const agentIconMap: Record<AgentStatus, React.ReactNode> = {
  idle: (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
  ),
  thinking: (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3a5 5 0 0 1 5 5c0 .8-.2 1.6-.5 2.3l-1.8 2.4c-.4.5-.6 1.2-.6 1.8v1"/><path d="M9 10h.01"/><path d="M15 10h.01"/><path d="M9.5 17c.3.2.7.3 1.2.3h3c.5 0 .9-.1 1.3-.3"/></svg>
  ),
  executing: (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
  ),
  'waiting-approval': (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/><path d="m9 12 2 2 4-4"/></svg>
  ),
  done: (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
  ),
  error: (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" x2="9" y1="9" y2="15"/><line x1="9" x2="15" y1="9" y2="15"/></svg>
  ),
};

const agentStatusToPhaseStatus: Record<AgentStatus, 'success' | 'running' | 'pending' | 'failed' | 'escalated'> = {
  idle: 'pending',
  thinking: 'running',
  executing: 'running',
  'waiting-approval': 'pending',
  done: 'success',
  error: 'failed',
};

const AgentHeaderCard: React.FC<AgentHeaderCardProps> = ({
  agentName,
  description,
  status,
  phaseLabel,
  progress = 0,
  modelLabel,
  reasoningTimeline,
}) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card variant="default" padding="md" className="border-l-4" accentColor={
      status === 'error' ? '#ef4444' :
      status === 'done' ? '#22c55e' :
      status === 'thinking' || status === 'executing' ? '#8b5cf6' :
      '#3b82f6'
    }>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div className={`mt-0.5 ${
            status === 'error' ? 'text-status-failed' :
            status === 'done' ? 'text-status-success' :
            status === 'thinking' || status === 'executing' ? 'text-agent-thinking' :
            'text-status-running'
          }`}>
            {agentIconMap[status]}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 truncate">{agentName}</h4>
              {phaseLabel && (
                <PhaseStatusBadge
                  phase={phaseLabel}
                  status={agentStatusToPhaseStatus[status]}
                  size="sm"
                />
              )}
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{description}</p>
            {modelLabel && (
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1 font-mono">{modelLabel}</p>
            )}
          </div>
        </div>

        {progress > 0 && (
          <div className="flex items-center gap-2 min-w-[120px]">
            <div className="flex-1 h-1.5 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-primary rounded-full transition-all duration-300"
                style={{ width: `${Math.min(progress, 100)}%` }}
              />
            </div>
            <span className="text-xs text-gray-500 dark:text-gray-400 tabular-nums">{Math.round(progress)}%</span>
          </div>
        )}
      </div>

      {/* Expandable reasoning timeline */}
      {reasoningTimeline && reasoningTimeline.length > 0 && (
        <div className="mt-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            aria-expanded={expanded}
          >
            {expanded ? 'Hide' : 'Show'} reasoning ({reasoningTimeline.length} steps)
          </button>
          {expanded && (
            <div className="mt-2 space-y-1.5 border-l-2 border-gray-200 dark:border-slate-700 pl-3">
              {reasoningTimeline.map((step, idx) => (
                <div key={idx} className="text-xs">
                  <span className="text-gray-600 dark:text-gray-300">{step.step}</span>
                  <span className="text-gray-400 dark:text-gray-500 ml-2 tabular-nums">{step.timestamp}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  );
};

export default AgentHeaderCard;
