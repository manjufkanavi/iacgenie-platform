import React from 'react';
import {
  CheckCircle2,
  Clock,
  XCircle,
  AlertTriangle,
  Loader2,
} from 'lucide-react';

type PhaseStatus = 'success' | 'running' | 'pending' | 'failed' | 'escalated';

interface PhaseStatusBadgeProps {
  phase: string;
  status: PhaseStatus;
  size?: 'sm' | 'md' | 'lg';
}

const statusConfig: Record<PhaseStatus, { icon: React.ElementType; color: string; bgClass: string }> = {
  success: { icon: CheckCircle2, color: 'text-status-success', bgClass: '' },
  running: { icon: Loader2, color: 'text-status-running', bgClass: '' },
  pending: { icon: Clock, color: 'text-status-pending', bgClass: '' },
  failed: { icon: XCircle, color: 'text-status-failed', bgClass: '' },
  escalated: { icon: AlertTriangle, color: 'text-status-escalated', bgClass: '' },
};

const sizeStyles: Record<NonNullable<PhaseStatusBadgeProps['size']>, string> = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-3 py-1 text-sm',
  lg: 'px-4 py-1.5 text-base',
};

const iconSizes: Record<NonNullable<PhaseStatusBadgeProps['size']>, number> = {
  sm: 12,
  md: 14,
  lg: 16,
};

const PhaseStatusBadge: React.FC<PhaseStatusBadgeProps> = ({
  phase,
  status,
  size = 'md',
}) => {
  const config = statusConfig[status];
  const Icon = config.icon;
  const iconSize = iconSizes[size];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${sizeStyles[size]} ${config.color} ${
        status === 'running' ? 'animate-pulse-agent' : ''
      }`}
      role="status"
      aria-label={`${phase}: ${status}`}
    >
      <Icon size={iconSize} className={status === 'running' ? 'animate-spin' : ''} />
      <span>{phase}</span>
    </span>
  );
};

export default PhaseStatusBadge;
