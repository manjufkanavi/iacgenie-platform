import React from 'react';

export type StatusVariant = 'success' | 'failed' | 'in-progress' | 'pending' | 'neutral';

export type GenerationStatus = 'COMPLETED' | 'FAILED' | 'IN_PROGRESS' | 'HUMAN_REVIEW';
export type DeploymentStatus = 'success' | 'failed' | 'in-progress' | 'pending-approval';

export interface StatusBadgeProps {
  status: string;
  variant?: StatusVariant;
  showIcon?: boolean;
  className?: string;
  ariaLabel?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  variant,
  showIcon = false,
  className = '',
  ariaLabel
}) => {
  // Auto-detect variant if not provided
  const effectiveVariant = variant || getAutoDetectedVariant(status);

  // Get status text
  const getStatusText = (s: string) => {
    return s.charAt(0).toUpperCase() + s.slice(1).replace('-', ' ');
  };

  // Get dot color for 8px indicator
  const getDotColor = () => {
    switch (effectiveVariant) {
      case 'success': return 'bg-green-500';
      case 'failed': return 'bg-red-500';
      case 'in-progress': return 'bg-amber-500';
      case 'pending': return 'bg-blue-500';
      default: return 'bg-slate-500';
    }
  };

  // Get icon based on status
  const getStatusIcon = () => {
    switch (effectiveVariant) {
      case 'success':
        return <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>;
      case 'failed':
        return <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>;
      case 'in-progress':
        return <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>;
      case 'pending':
        return <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>;
      default:
        return <span className="w-4 h-4">-</span>;
    }
  };

  // Get variant styles using design tokens
  const getVariantStyles = () => {
    switch (effectiveVariant) {
      case 'success':
        return 'bg-green-100 text-green-800 border border-green-200';
      case 'failed':
        return 'bg-red-100 text-red-800 border border-red-200';
      case 'in-progress':
        return 'bg-amber-100 text-amber-800 border border-amber-200';
      case 'pending':
        return 'bg-blue-100 text-blue-800 border border-blue-200';
      default:
        return 'bg-slate-100 text-slate-800 border border-slate-200';
    }
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-sm font-medium ${getVariantStyles()} ${className}`}
      aria-label={ariaLabel || `${getStatusText(status)} status`}
    >
      <span className={`w-2 h-2 rounded-full ${getDotColor()}`} />
      {showIcon && getStatusIcon()}
      <span>{getStatusText(status)}</span>
    </span>
  );
};

// Helper function to auto-detect variant from status string
const getAutoDetectedVariant = (status: string): StatusVariant => {
  const statusLower = status.toLowerCase();

  if (statusLower === 'completed' || statusLower.includes('success') || statusLower === 'succeeded') {
    return 'success';
  } else if (statusLower === 'failed' || statusLower.includes('error') || statusLower === 'errored') {
    return 'failed';
  } else if (statusLower === 'in-progress' || statusLower.includes('running') || statusLower === 'processing') {
    return 'in-progress';
  } else if (statusLower === 'pending' || statusLower.includes('waiting') || statusLower === 'queued') {
    return 'pending';
  } else {
    return 'neutral';
  }
};

// Specialized component for Generation status (includes HUMAN_REVIEW)
export interface GenerationStatusBadgeProps {
  status: GenerationStatus;
  showIcon?: boolean;
  className?: string;
}

export const GenerationStatusBadge: React.FC<GenerationStatusBadgeProps> = ({
  status,
  showIcon = false,
  className = ''
}) => {
  // Get variant based on generation status
  const getVariant = (s: GenerationStatus) => {
    switch (s) {
      case 'COMPLETED':
        return 'success';
      case 'FAILED':
        return 'failed';
      case 'IN_PROGRESS':
        return 'in-progress';
      case 'HUMAN_REVIEW':
        return 'pending'; // Using pending variant for human review (blue)
      default:
        return 'neutral';
    }
  };

  const variant = getVariant(status);

  return (
    <StatusBadge
      status={status}
      variant={variant as StatusVariant}
      showIcon={showIcon}
      className={className}
      ariaLabel={`${status} generation status`}
    />
  );
};

// Specialized component for Deployment status
export interface DeploymentStatusBadgeProps {
  status: DeploymentStatus;
  showIcon?: boolean;
  className?: string;
}

export const DeploymentStatusBadge: React.FC<DeploymentStatusBadgeProps> = ({
  status,
  showIcon = false,
  className = ''
}) => {
  // Get variant based on deployment status
  const getVariant = (s: DeploymentStatus) => {
    switch (s) {
      case 'success':
        return 'success';
      case 'failed':
        return 'failed';
      case 'in-progress':
        return 'in-progress';
      case 'pending-approval':
        return 'pending'; // Using pending variant for approval (blue)
      default:
        return 'neutral';
    }
  };

  const variant = getVariant(status);

  return (
    <StatusBadge
      status={status}
      variant={variant as StatusVariant}
      showIcon={showIcon}
      className={className}
      ariaLabel={`${status} deployment status`}
    />
  );
};

export default StatusBadge;
