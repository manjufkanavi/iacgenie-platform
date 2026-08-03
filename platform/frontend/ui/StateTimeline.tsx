import React from 'react';
import { CheckCircle2, Clock, XCircle, AlertCircle } from 'lucide-react';

export type SessionState = 
  | 'CREATED' 
  | 'CODING' 
  | 'VALIDATING' 
  | 'PLANNING' 
  | 'APPLYING' 
  | 'TESTING' 
  | 'GIT_PUSH' 
  | 'CI_TRIGGER' 
  | 'CI_MONITOR' 
  | 'COMPLETED' 
  | 'FAILED' 
  | 'HUMAN_REVIEW';

interface StateTransition {
  fromState: SessionState;
  toState: SessionState;
  timestamp: string;
  duration?: number; // in seconds
  eventDescription: string;
}

interface StateTimelineProps {
  transitions: StateTransition[];
  showDetails?: boolean;
  onStateClick?: (transition: StateTransition) => void;
}

const getStatusColor = (toState: SessionState) => {
  if (toState === 'COMPLETED') return 'text-green-600';
  if (toState === 'FAILED' || toState === 'HUMAN_REVIEW') return 'text-red-600';
  if (toState === 'CODING' || toState === 'VALIDATING' || toState === 'PLANNING') return 'text-amber-600';
  return 'text-gray-600';
};

const getStatusIcon = (toState: SessionState) => {
  if (toState === 'COMPLETED') return <CheckCircle2 className="w-5 h-5" />;
  if (toState === 'FAILED') return <XCircle className="w-5 h-5" />;
  if (toState === 'HUMAN_REVIEW') return <AlertCircle className="w-5 h-5" />;
  if (toState === 'CODING' || toState === 'VALIDATING') return <Clock className="w-5 h-5" />;
  return <CheckCircle2 className="w-5 h-5" />;
};

const formatDuration = (seconds?: number): string => {
  if (!seconds) return '-';
  
  if (seconds < 60) {
    return `${seconds}s`;
  }
  
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  
  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds}s`;
  }
  
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
};

const formatTimestamp = (timestamp: string): string => {
  return new Date(timestamp).toLocaleString();
};

export const StateTimeline: React.FC<StateTimelineProps> = ({
  transitions,
  showDetails = true,
  onStateClick
}) => {
  if (transitions.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No state transitions recorded
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {transitions.map((transition, index) => (
        <div key={index} className="relative">
          {/* Timeline line */}
          {index < transitions.length - 1 && (
            <div className="absolute left-5 top-8 bottom-[-16px] w-0.5 bg-gray-200" />
          )}

          {/* Timeline item */}
          <button
            onClick={() => onStateClick?.(transition)}
            className="w-full flex items-start gap-4 p-4 rounded-lg hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-primary"
            aria-label={`State transition from ${transition.fromState} to ${transition.toState}`}
          >
            {/* Status icon */}
            <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center bg-gray-100 ${getStatusColor(transition.toState)}`}>
              {getStatusIcon(transition.toState)}
            </div>

            {/* Content */}
            <div className="flex-1 text-left">
              <div className="flex items-center justify-between mb-1">
                <h4 className="text-sm font-semibold text-gray-900">
                  {transition.fromState} → {transition.toState}
                </h4>
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  <span className="font-mono">{formatTimestamp(transition.timestamp)}</span>
                  <span>Duration: {formatDuration(transition.duration)}</span>
                </div>
              </div>

              {showDetails && (
                <p className="text-sm text-gray-600">
                  {transition.eventDescription}
                </p>
              )}
            </div>
          </button>
        </div>
      ))}
    </div>
  );
};

export default StateTimeline;