import React from 'react';
import {
  CheckCircle2,
  Clock,
  PauseCircle,
  XCircle,
  AlertTriangle,
  Loader2,
} from 'lucide-react';

type PhaseStatus = 'success' | 'running' | 'paused' | 'failed' | 'escalated' | 'pending';

interface PhaseStatusIndicatorProps {
  phase: string;
  status: PhaseStatus;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

const statusConfig: Record<PhaseStatus, { icon: React.ElementType; color: string }> = {
  success: { icon: CheckCircle2, color: 'text-status-success' },
  running: { icon: Loader2, color: 'text-status-running' },
  paused: { icon: PauseCircle, color: 'text-status-pending' },
  pending: { icon: Clock, color: 'text-status-pending' },
  failed: { icon: XCircle, color: 'text-status-failed' },
  escalated: { icon: AlertTriangle, color: 'text-status-escalated' },
};

const sizeStyles: Record<NonNullable<PhaseStatusIndicatorProps['size']>, string> = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-3 py-1 text-sm',
  lg: 'px-4 py-1.5 text-base',
};

const iconSizes: Record<NonNullable<PhaseStatusIndicatorProps['size']>, number> = {
  sm: 12,
  md: 14,
  lg: 16,
};

const PhaseStatusIndicator: React.FC<PhaseStatusIndicatorProps> = ({
  phase,
  status,
  size = 'md',
  showLabel = false,
}) => {
  const config = statusConfig[status];
  const Icon = config.icon;
  const iconSize = iconSizes[size];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${sizeStyles[size]} ${config.color} ${
        status === 'running' ? 'animate-pulse-agent' : ''
      }`}
    >
      <Icon className={status === 'running' ? 'animate-spin' : ''} size={iconSize} />
      {showLabel && <span>{phase}</span>}
    </span>
  );
};

export default PhaseStatusIndicator;
