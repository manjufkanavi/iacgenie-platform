import React from 'react';
import { Loader2, Check, X, Minus } from 'lucide-react';

export type ExecutionState = 'idle' | 'planning' | 'applying' | 'complete' | 'error' | 'cancelled';

interface ExecutionStateIndicatorProps {
  state: ExecutionState;
  size?: 'sm' | 'md';
  showLabel?: boolean;
  className?: string;
}

export const ExecutionStateIndicator: React.FC<ExecutionStateIndicatorProps> = ({
  state,
  size = 'sm',
  showLabel = true,
  className = '',
}) => {
  const getBadgeDetails = (): {
    colorClass: string;
    icon: React.ReactNode | null;
    label: string;
  } => {
    switch (state) {
      case 'planning':
        return {
          colorClass: 'text-[var(--color-exec-planning)] bg-orange-50/50 dark:bg-orange-950/20 border-orange-200 dark:border-orange-900/40',
          icon: <Loader2 className="animate-spin shrink-0" style={{ width: size === 'sm' ? 12 : 14, height: size === 'sm' ? 12 : 14 }} />,
          label: 'Planning',
        };
      case 'applying':
        return {
          colorClass: 'text-[var(--color-exec-applying)] bg-blue-50/50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900/40',
          icon: <Loader2 className="animate-spin shrink-0" style={{ width: size === 'sm' ? 12 : 14, height: size === 'sm' ? 12 : 14 }} />,
          label: 'Applying',
        };
      case 'complete':
        return {
          colorClass: 'text-[var(--color-exec-complete)] bg-green-50/50 dark:bg-green-950/20 border-green-200 dark:border-green-900/40',
          icon: <Check className="shrink-0" style={{ width: size === 'sm' ? 12 : 14, height: size === 'sm' ? 12 : 14 }} />,
          label: 'Complete',
        };
      case 'error':
        return {
          colorClass: 'text-[var(--color-exec-error)] bg-red-50/50 dark:bg-red-950/20 border-red-200 dark:border-red-900/40',
          icon: <X className="shrink-0" style={{ width: size === 'sm' ? 12 : 14, height: size === 'sm' ? 12 : 14 }} />,
          label: 'Error',
        };
      case 'cancelled':
        return {
          colorClass: 'text-[var(--color-exec-cancelled)] bg-slate-50/50 dark:bg-slate-800/20 border-slate-200 dark:border-slate-700/60',
          icon: <Minus className="shrink-0" style={{ width: size === 'sm' ? 12 : 14, height: size === 'sm' ? 12 : 14 }} />,
          label: 'Cancelled',
        };
      case 'idle':
      default:
        return {
          colorClass: 'text-[var(--color-exec-idle)] bg-slate-50/50 dark:bg-slate-800/20 border-slate-200 dark:border-slate-700/60',
          icon: null,
          label: 'Idle',
        };
    }
  };

  const details = getBadgeDetails();

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 border rounded-full text-xs font-bold uppercase tracking-wider select-none ${details.colorClass} ${className}`}
      role="status"
      aria-live="polite"
      aria-label={`Status: ${details.label}`}
    >
      {details.icon}
      {showLabel && <span>{details.label}</span>}
    </div>
  );
};

export default ExecutionStateIndicator;
