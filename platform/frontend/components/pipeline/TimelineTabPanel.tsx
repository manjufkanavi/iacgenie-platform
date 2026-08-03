import React, { useState } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import Modal from '../ui/Modal';
import { StateMachineVisualizer, SessionState } from '../ui/StateMachineVisualizer';
import { StateTimeline } from '../ui/StateTimeline';

interface StateTransition {
  fromState: SessionState;
  toState: SessionState;
  timestamp: string;
  duration?: number;
  eventDescription: string;
}

interface TimelineTabPanelProps {
  pipelineId?: string;
  stateHistory?: StateTransition[];
}

const DEFAULT_STATE_HISTORY: StateTransition[] = [
  { fromState: 'CREATED', toState: 'CODING', timestamp: new Date('2026-03-08T10:31:00Z').toISOString(), duration: 60, eventDescription: 'Code generation started with gemini-1.5-pro' },
  { fromState: 'CODING', toState: 'VALIDATING', timestamp: new Date('2026-03-08T10:35:00Z').toISOString(), duration: 240, eventDescription: 'Code validation passed, proceeding to planning' },
  { fromState: 'VALIDATING', toState: 'PLANNING', timestamp: new Date('2026-03-08T10:38:00Z').toISOString(), duration: 180, eventDescription: 'OpenTofu plan generated successfully' },
  { fromState: 'PLANNING', toState: 'APPLYING', timestamp: new Date('2026-03-08T10:42:00Z').toISOString(), duration: 252, eventDescription: 'OpenTofu apply started' },
  { fromState: 'APPLYING', toState: 'TESTING', timestamp: new Date('2026-03-08T10:44:00Z').toISOString(), duration: 120, eventDescription: 'Infrastructure applied, running tests' },
  { fromState: 'TESTING', toState: 'COMPLETED', timestamp: new Date('2026-03-08T10:45:00Z').toISOString(), duration: 60, eventDescription: 'All tests passed, generation completed' },
];

const TimelineTabPanel: React.FC<TimelineTabPanelProps> = ({ pipelineId, stateHistory = DEFAULT_STATE_HISTORY }) => {
  const [selectedStateIndex, setSelectedStateIndex] = useState<number | null>(null);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);

  const totalDuration = stateHistory.reduce((sum, transition) => sum + (transition.duration || 0), 0);
  const avgDuration = totalDuration / stateHistory.length;

  const handleStateClick = (index: number) => {
    setSelectedStateIndex(index);
    setIsDetailsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsDetailsModalOpen(false);
    setSelectedStateIndex(null);
  };

  const machineStates = stateHistory.map((transition) => ({
    state: transition.toState as SessionState,
    status: 'completed' as const,
    timestamp: transition.timestamp,
    duration: transition.duration,
    eventDescription: transition.eventDescription,
  }));

  return (
    <div className="space-y-6">
      {/* Pipeline Overview */}
      <Card>
        <div className="space-y-2">
          <p className="text-sm text-slate-200">{pipelineId ? `Pipeline: ${pipelineId}` : 'Pipeline State Timeline'}</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4">
            <div>
              <span className="text-xs text-slate-500">Model</span>
              <p className="text-sm font-medium text-slate-200">gemini-1.5-pro</p>
            </div>
            <div>
              <span className="text-xs text-slate-500">Provider</span>
              <p className="text-sm font-medium text-slate-200">AWS</p>
            </div>
            <div>
              <span className="text-xs text-slate-500">Started</span>
              <p className="text-sm font-medium text-slate-200">
                {new Date(stateHistory[0]?.timestamp || Date.now()).toLocaleString()}
              </p>
            </div>
            <div>
              <span className="text-xs text-slate-500">Completed</span>
              <p className="text-sm font-medium text-slate-200">
                {stateHistory.length > 0
                  ? new Date(stateHistory[stateHistory.length - 1].timestamp).toLocaleString()
                  : 'In Progress'
                }
              </p>
            </div>
          </div>
        </div>
      </Card>

      {/* State Machine Diagram */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-slate-400 dark:text-slate-500">State Machine Diagram</h3>
          <Button variant="secondary" size="sm">Export Timeline</Button>
        </div>
        <StateMachineVisualizer
          states={machineStates}
          showDetails
          onStateClick={handleStateClick}
        />
      </Card>

      {/* State Transition Timeline */}
      <Card>
        <h3 className="text-sm font-semibold text-slate-400 dark:text-slate-500 mb-4">State Transition Timeline</h3>
        <StateTimeline
          transitions={stateHistory}
          showDetails
          onStateClick={(transition) => {
            const index = stateHistory.indexOf(transition);
            if (index >= 0) handleStateClick(index);
          }}
        />
      </Card>

      {/* State Statistics */}
      <Card>
        <h3 className="text-sm font-semibold text-slate-400 dark:text-slate-500 mb-4">State Statistics</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
            <div className="text-2xl font-bold text-slate-900 dark:text-slate-50">{stateHistory.length}</div>
            <div className="text-sm text-slate-500 dark:text-slate-400">Total States</div>
          </div>
          <div className="text-center p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
            <div className="text-2xl font-bold text-slate-900 dark:text-slate-50">{Math.round(avgDuration)}s</div>
            <div className="text-sm text-slate-500 dark:text-slate-400">Avg Duration</div>
          </div>
          <div className="text-center p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
            <div className="text-2xl font-bold text-slate-900 dark:text-slate-50">{Math.round(totalDuration / 60)}m</div>
            <div className="text-sm text-slate-500 dark:text-slate-400">Total Duration</div>
          </div>
          <div className="text-center p-4 bg-emerald-50 dark:bg-emerald-500/10 rounded-lg">
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">100%</div>
            <div className="text-sm text-emerald-600 dark:text-emerald-400">Success Rate</div>
          </div>
        </div>
      </Card>

      {/* State Details Modal */}
      <Modal isOpen={isDetailsModalOpen} onClose={handleCloseModal} title="State Details">
        {selectedStateIndex !== null && stateHistory[selectedStateIndex] && (
          <div className="space-y-6">
            <Card>
              <h3 className="text-sm font-semibold text-slate-400 dark:text-slate-500 mb-4">State Information</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-500">From State</span>
                  <span className="text-sm font-mono font-semibold text-slate-200">
                    {stateHistory[selectedStateIndex].fromState}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-500">To State</span>
                  <span className="text-sm font-mono font-semibold text-slate-200">
                    {stateHistory[selectedStateIndex].toState}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-500">Timestamp</span>
                  <span className="text-sm font-mono text-slate-200">
                    {new Date(stateHistory[selectedStateIndex].timestamp).toLocaleString()}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-500">Duration</span>
                  <span className="text-sm font-semibold text-slate-200">
                    {stateHistory[selectedStateIndex].duration
                      ? `${Math.round(stateHistory[selectedStateIndex].duration)} seconds`
                      : '-'
                    }
                  </span>
                </div>
              </div>
            </Card>
            <Card>
              <h3 className="text-sm font-semibold text-slate-400 dark:text-slate-500 mb-2">Event Description</h3>
              <p className="text-sm text-slate-200">
                {stateHistory[selectedStateIndex].eventDescription}
              </p>
            </Card>
            <div className="flex justify-end">
              <Button variant="primary" onClick={handleCloseModal}>Close</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default TimelineTabPanel;
