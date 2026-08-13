import React from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import { Generation } from '../types';
import { GenerationStatusBadge } from '../ui/StatusBadge';

interface GenerationDetailPanelProps {
  generation: Generation | undefined;
  isOpen: boolean;
  onClose: () => void;
}

const GenerationDetailPanel: React.FC<GenerationDetailPanelProps> = ({ generation, isOpen, onClose }) => {
  if (!isOpen || !generation) return null;

  return (
    <div
      className="fixed inset-0 bg-black/60 z-40 transition-opacity"
      onClick={onClose}
    >
      <div
        className="fixed inset-y-0 right-0 w-full max-w-4xl bg-slate-900 z-50 shadow-2xl transform transition-transform ease-in-out duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700 flex-shrink-0">
          <div>
            <h2 className="text-xl font-bold text-slate-50">Generation Details</h2>
            <p className="text-sm text-slate-400 font-mono">{generation.id}</p>
          </div>
          <button onClick={onClose} className="p-2 rounded-full text-slate-400 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-primary">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 p-6 overflow-y-auto space-y-6">
          {/* Prompt */}
          <Card>
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Prompt</h3>
            <p className="text-slate-200">{generation.prompt}</p>
          </Card>

          {/* Metadata */}
          <Card>
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Metadata</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-slate-500">Provider:</span>{' '}
                <span className="text-slate-200">{generation.provider}</span>
              </div>
              <div>
                <span className="text-slate-500">Model:</span>{' '}
                <span className="text-slate-200">{generation.modelId}</span>
              </div>
              <div>
                <span className="text-slate-500">Status:</span>{' '}
                <GenerationStatusBadge status={generation.status} showIcon />
              </div>
              <div>
                <span className="text-slate-500">Created:</span>{' '}
                <span className="text-slate-200">{new Date(generation.createdAt).toLocaleString()}</span>
              </div>
            </div>
          </Card>

          {/* State History Timeline */}
          {generation.stateHistory && generation.stateHistory.length > 0 && (
            <Card>
              <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">State History</h3>
              <div className="space-y-3">
                {generation.stateHistory.map((transition, index) => (
                  <div key={index} className="flex items-start gap-3 text-sm">
                    <span className="text-slate-500 font-mono whitespace-nowrap">
                      {new Date(transition.timestamp).toLocaleTimeString()}
                    </span>
                    <div className="flex-1">
                      <span className="text-slate-200">{transition.fromState}</span>
                      <span className="text-slate-500"> → </span>
                      <span className="text-slate-200">{transition.toState}</span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Generated Files */}
          <Card>
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Generated Files ({generation.files.length})
            </h3>
            <div className="space-y-2">
              {generation.files.map((file) => (
                <div key={file.name} className="flex items-center justify-between text-sm">
                  <span className="text-slate-200">{file.name}</span>
                  <span className="text-slate-500 text-xs uppercase">{file.language}</span>
                </div>
              ))}
            </div>
          </Card>

          {/* Logs */}
          {generation.logs && generation.logs.length > 0 && (
            <Card>
              <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Logs</h3>
              <div className="bg-black/50 rounded p-4 max-h-64 overflow-y-auto">
                {generation.logs.map((log, index) => (
                  <div key={index} className="text-xs font-mono text-slate-300">
                    <span className="text-slate-500">{new Date(log.timestamp).toLocaleTimeString()}</span>
                    <span className={`ml-2 ${log.status === 'success' ? 'text-green-400' : log.status === 'error' ? 'text-red-400' : 'text-yellow-400'}`}>
                      [{log.stage}] {log.message}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <Button variant="secondary" onClick={onClose}>Close</Button>
            {generation.status === 'FAILED' && (
              <Button variant="primary">Retry Generation</Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default GenerationDetailPanel;
