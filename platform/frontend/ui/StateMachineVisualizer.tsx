import React, { useState } from 'react';
import { CheckCircle2, Clock, XCircle, ChevronRight } from 'lucide-react';

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

interface StateInfo {
  state: SessionState;
  status: 'completed' | 'current' | 'pending' | 'error';
  timestamp?: string;
  duration?: number; // in seconds
  eventDescription?: string;
}

interface StateMachineVisualizerProps {
  states: StateInfo[];
  showDetails?: boolean;
  onStateClick?: (stateIndex: number) => void;
}

const getStateColor = (status: string) => {
  switch (status) {
    case 'completed':
      return 'bg-green-500';
    case 'current':
      return 'bg-amber-500';
    case 'error':
      return 'bg-red-500';
    default:
      return 'bg-gray-300';
  }
};

const getStateIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="w-5 h-5 text-green-600" />;
    case 'current':
      return <Clock className="w-5 h-5 text-amber-600" />;
    case 'error':
      return <XCircle className="w-5 h-5 text-red-600" />;
    default:
      return <div className="w-5 h-5 rounded-full border-2 border-gray-300" />;
  }
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

export const StateMachineVisualizer: React.FC<StateMachineVisualizerProps> = ({
  states,
  showDetails = false,
  onStateClick
}) => {
  const [expandedStates, setExpandedStates] = useState<Set<number>>(new Set());

  const toggleStateDetails = (index: number) => {
    if (!onStateClick && !showDetails) return;
    
    const newExpanded = new Set(expandedStates);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedStates(newExpanded);
    
    onStateClick?.(index);
  };

  const renderStateMachine = () => {
    if (states.length === 0) {
      return (
        <div className="text-center py-8 text-gray-500">
          No state history available
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {/* Horizontal timeline for main states */}
        <div className="flex flex-wrap items-center justify-center gap-2">
          {states.map((stateInfo, index) => (
            <React.Fragment key={index}>
              {/* State node */}
              <button
                onClick={() => toggleStateDetails(index)}
                className="flex flex-col items-center gap-2 group focus:outline-none focus:ring-2 focus:ring-brand-primary rounded-lg"
                aria-label={`${stateInfo.state} state - ${stateInfo.status}`}
              >
                <div className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${getStateColor(stateInfo.status)}`}>
                  {getStateIcon(stateInfo.status)}
                </div>
                <span className="text-xs font-semibold text-gray-700 group-hover:text-brand-primary transition-colors">
                  {stateInfo.state}
                </span>
              </button>

              {/* Arrow between states (except for last) */}
              {index < states.length - 1 && (
                <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Expanded state details */}
        {showDetails && (
          <div className="space-y-2">
            {states.map((stateInfo, index) => (
              <div
                key={index}
                className={`p-3 rounded-lg border transition-colors ${
                  expandedStates.has(index)
                    ? 'bg-brand-primary/5 border-brand-primary/20'
                    : 'bg-gray-50 border-gray-200 hover:border-brand-primary/20'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {getStateIcon(stateInfo.status)}
                    <div>
                      <span className="text-sm font-semibold text-gray-900">
                        {stateInfo.state}
                      </span>
                      <div className="text-xs text-gray-500">
                        {stateInfo.eventDescription || 'No description'}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-gray-500">
                      Duration: {formatDuration(stateInfo.duration)}
                    </div>
                    {stateInfo.timestamp && (
                      <div className="text-xs text-gray-400 font-mono">
                        {new Date(stateInfo.timestamp).toLocaleTimeString()}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">
        State Machine Progress
      </h3>
      {renderStateMachine()}
    </div>
  );
};

export default StateMachineVisualizer;