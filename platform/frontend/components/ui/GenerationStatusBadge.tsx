import React from 'react';
import { CheckCircle2, XCircle, Clock, AlertCircle } from 'lucide-react';

interface GenerationStatusBadgeProps {
  status: string;
  showIcon?: boolean;
}

const getStatusVariant = (status: string) => {
  const normalizedStatus = status.toLowerCase();
  
  if (normalizedStatus === 'completed' || normalizedStatus === 'success') {
    return 'bg-green-100 text-green-800 border-green-200';
  }
  if (normalizedStatus === 'failed' || normalizedStatus === 'error') {
    return 'bg-red-100 text-red-800 border-red-200';
  }
  if (normalizedStatus === 'in_progress' || normalizedStatus === 'running') {
    return 'bg-amber-100 text-amber-800 border-amber-200';
  }
  if (normalizedStatus === 'human_review') {
    return 'bg-violet-100 text-violet-800 border-violet-200';
  }
  if (normalizedStatus === 'pending' || normalizedStatus === 'validating') {
    return 'bg-blue-100 text-blue-800 border-blue-200';
  }
  
  return 'bg-gray-100 text-gray-800 border-gray-200';
};

const getStatusIcon = (status: string) => {
  const normalizedStatus = status.toLowerCase();
  
  if (normalizedStatus === 'completed' || normalizedStatus === 'success') {
    return <CheckCircle2 className="w-4 h-4 mr-1" />;
  }
  if (normalizedStatus === 'failed' || normalizedStatus === 'error') {
    return <XCircle className="w-4 h-4 mr-1" />;
  }
  if (normalizedStatus === 'in_progress' || normalizedStatus === 'running') {
    return <Clock className="w-4 h-4 mr-1" />;
  }
  if (normalizedStatus === 'human_review') {
    return <AlertCircle className="w-4 h-4 mr-1" />;
  }
  
  return <Clock className="w-4 h-4 mr-1" />;
};

const formatStatus = (status: string): string => {
  return status
    .toLowerCase()
    .replace(/_/g, ' ')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

export const GenerationStatusBadge: React.FC<GenerationStatusBadgeProps> = ({ 
  status, 
  showIcon = true 
}) => {
  const variantClass = getStatusVariant(status);
  
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-semibold border ${variantClass}`}
      aria-label={`${formatStatus(status)} status`}
    >
      {showIcon && getStatusIcon(status)}
      {formatStatus(status)}
    </span>
  );
};

export default GenerationStatusBadge;