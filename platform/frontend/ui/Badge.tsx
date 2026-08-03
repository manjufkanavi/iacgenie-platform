import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
  className?: string;
}

const Badge: React.FC<BadgeProps> = ({ children, variant = 'info', className = '' }) => {
  const baseStyles = 'inline-flex items-center px-3 py-1 rounded-full text-xs font-medium capitalize';

  const variantStyles = {
    success: 'bg-status-success-bg text-status-success-text border border-status-success-border',
    warning: 'bg-status-escalated-bg text-status-escalated-text border border-status-escalated-border',
    danger: 'bg-status-failed-bg text-status-failed-text border border-status-failed-border',
    info: 'bg-status-info-bg text-status-info-text border border-status-info-border',
    neutral: 'bg-status-pending-bg text-status-pending-text border border-status-pending-border',
  };

  const combinedClassName = `${baseStyles} ${variantStyles[variant]} ${className}`;

  return (
    <span className={combinedClassName}>
      {children}
    </span>
  );
};

export default Badge;
