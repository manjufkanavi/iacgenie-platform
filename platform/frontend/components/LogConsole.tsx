
import React, { useRef, useEffect } from 'react';
import { LogEntry, ValidationStepLog } from '../types';
import { ICONS } from '../constants';
import Button from './ui/Button';

interface LogConsoleProps {
  logs: LogEntry[];
  isOpen: boolean;
  onToggle: () => void;
  onClear: () => void;
  isGenerationComplete?: boolean;
}

const LogConsole: React.FC<LogConsoleProps> = ({ logs, isOpen, onToggle, onClear, isGenerationComplete = false }) => {
  const logContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, isOpen]);

  const getStatusStyle = (status: ValidationStepLog['status']): string => {
      switch (status) {
          case 'success': return 'text-green-400';
          case 'error': return 'text-red-400';
          case 'running': return 'text-yellow-400';
          case 'retrying': return 'text-blue-400';
          default: return 'text-gray-400';
      }
  };

  const getStatusIcon = (status: ValidationStepLog['status']) => {
        switch (status) {
            case 'running': return <div className="w-4 h-4 text-yellow-400">{ICONS.SPINNER}</div>;
            case 'success': return <div className="w-4 h-4 text-green-400">✓</div>;
            case 'error': return <div className="w-4 h-4 text-red-400">✗</div>;
            case 'retrying': return <div className="w-4 h-4 text-blue-400">{ICONS.REDEPLOY}</div>;
            default: return <div className="w-4 h-4 text-gray-400">-</div>;
        }
  }


  return (
    <div className={`fixed bottom-0 left-0 right-0 z-30 transition-all duration-300 ease-in-out`}>
      <div className="max-w-4xl mx-auto w-full">
        <div className={`bg-gray-900 border-t-2 ${isOpen ? 'border-brand-primary' : 'border-gray-700'} rounded-t-xl shadow-2xl transition-all`}>
          <div
            className="w-full flex justify-between items-center p-3 text-left"
          >
            <button
                onClick={onToggle}
                className="flex items-center gap-2 focus:outline-none flex-1"
            >
                <h3 className="text-sm font-semibold text-white font-mono">Terminal Logs</h3>
                {isGenerationComplete && (
                  <span className="text-green-400 text-xs font-medium">✅ Complete</span>
                )}
                <span className={`transform transition-transform text-gray-400 ${isOpen ? 'rotate-180' : ''}`}>
                {ICONS.CHEVRON_DOWN}
                </span>
            </button>
            {logs.length > 0 && (
                <Button variant="ghost" size="sm" onClick={onClear} className="text-gray-400 hover:text-white hover:bg-gray-800">
                    Clear Console
                </Button>
            )}
          </div>
          <div
            className={`transition-all duration-300 ease-in-out overflow-hidden ${
              isOpen ? 'max-h-64' : 'max-h-0'
            }`}
          >
            <div
              ref={logContainerRef}
              className="h-64 p-4 bg-black/50 overflow-y-auto font-mono text-xs"
            >
              {logs.map((log, index) => (
                <div key={index} className="flex items-start gap-3 mb-1">
                  <span className="text-gray-500">{new Date(log.timestamp).toLocaleTimeString()}</span>
                  <div className="flex-shrink-0 pt-px">{getStatusIcon(log.status)}</div>
                  <div className={`${getStatusStyle(log.status)} flex-1`}>
                    <span className="font-bold uppercase">{log.stage}: </span>
                    <span>{log.message}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LogConsole;