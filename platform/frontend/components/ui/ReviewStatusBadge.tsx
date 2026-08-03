import React from 'react';
import { AlertCircle, CheckCircle2, XCircle, User } from 'lucide-react';

interface ReviewStatusBadgeProps {
  status: string;
  priority?: 'high' | 'medium' | 'low';
  showIcon?: boolean;
}

const getStatusVariant = (status: string) => {
  const normalizedStatus = status.toLowerCase();

  if (normalizedStatus === 'pending_review' || normalizedStatus === 'pending-review') {
    return 'bg-amber-100 text-amber-800 border-amber-200';
  }
  if (normalizedStatus === 'needs_revision' || normalizedStatus === 'needs-revision') {
    return 'bg-red-100 text-red-800 border-red-200';
  }
  if (normalizedStatus === 'assigned') {
    return 'bg-blue-100 text-blue-800 border-blue-200';
  }
  if (normalizedStatus === 'approved') {
    return 'bg-green-100 text-green-800 border-green-200';
  }

  return 'bg-gray-100 text-gray-800 border-gray-200';
};

const getPriorityBorder = (priority?: string) => {
  if (!priority) return '';

  switch(priority.toLowerCase()) {
    case 'high':
      return 'border-l-4 border-red-500';
    case 'medium':
      return 'border-l-4 border-yellow-500';
    case 'low':
      return 'border-l-4 border-blue-500';
    default:
      return '';
  }
};

const getStatusIcon = (status: string) => {
  const normalizedStatus = status.toLowerCase();

  if (normalizedStatus === 'pending_review' || normalizedStatus === 'pending-review') {
    return <AlertCircle className="w-4 h-4 mr-1" />;
  }
  if (normalizedStatus === 'needs_revision' || normalizedStatus === 'needs-revision') {
    return <XCircle className="w-4 h-4 mr-1" />;
  }
  if (normalizedStatus === 'assigned') {
    return <User className="w-4 h-4 mr-1" />;
  }
  if (normalizedStatus === 'approved') {
    return <CheckCircle2 className="w-4 h-4 mr-1" />;
  }

  return <AlertCircle className="w-4 h-4 mr-1" />;
};

const formatStatus = (status: string): string => {
  return status
    .toLowerCase()
    .replace(/_/g, ' ')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

export const ReviewStatusBadge: React.FC<ReviewStatusBadgeProps> = ({
  status,
  priority,
  showIcon = true
}) => {
  const variantClass = getStatusVariant(status);
  const priorityBorder = getPriorityBorder(priority);

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-semibold border ${variantClass} ${priorityBorder}`}
      aria-label={`${formatStatus(status)} status${priority ? `, ${priority} priority` : ''}`}
    >
      {showIcon && getStatusIcon(status)}
      {formatStatus(status)}
      {priority && (
        <span className="ml-1 text-xs opacity-75">({priority})</span>
      )}
    </span>
  );
};

export default ReviewStatusBadge;