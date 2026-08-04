import React from 'react';
import type { StreamConnectionState } from '../store/usePipelineStore';
import { Wifi, WifiOff, RefreshCw, AlertCircle } from 'lucide-react';

interface SessionStreamIndicatorProps {
  state: StreamConnectionState;
  endpoint?: string;
  latency?: number | null;
  eventsReceived?: number | null;
  reconnects?: number | null;
  errorMessage?: string | null;
  onReconnect?: () => void;
  size?: 'sm' | 'md';
}

export const SessionStreamIndicator: React.FC<SessionStreamIndicatorProps> = ({
  state,
  endpoint = 'WebSocket Stream',
  latency = null,
  eventsReceived = 0,
  reconnects = 0,
  errorMessage = null,
  onReconnect,
  size = 'md',
}) => {
  // Map state to dot colors, text, and icons
  const stateConfig = {
    connecting: {
      dotClass: 'bg-amber-500 animate-pulse',
      text: 'Connecting...',
      colorClass: 'text-amber-500 dark:text-amber-400',
      icon: <RefreshCw className="w-3.5 h-3.5 animate-spin" />,
    },
    connected: {
      dotClass: 'bg-green-500',
      text: 'Connected',
      colorClass: 'text-green-500 dark:text-green-400',
      icon: <Wifi className="w-3.5 h-3.5" />,
    },
    reconnecting: {
      dotClass: 'bg-amber-500 animate-pulse',
      text: 'Reconnecting...',
      colorClass: 'text-amber-500 dark:text-amber-400',
      icon: <RefreshCw className="w-3.5 h-3.5 animate-spin" />,
    },
    disconnected: {
      dotClass: 'bg-slate-400 dark:bg-slate-500',
      text: 'Disconnected',
      colorClass: 'text-slate-500 dark:text-slate-400',
      icon: <WifiOff className="w-3.5 h-3.5" />,
    },
    error: {
      dotClass: 'bg-red-500',
      text: 'Connection Error',
      colorClass: 'text-red-500 dark:text-red-400',
      icon: <AlertCircle className="w-3.5 h-3.5" />,
    },
  };

  const currentConfig = stateConfig[state] || stateConfig.disconnected;
  const isSm = size === 'sm';

  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm relative group`}
      role="status"
      aria-live="polite"
      aria-label={`Connection status: ${currentConfig.text}`}
    >
      {/* Pulse / Dot */}
      <span className="relative flex h-2 w-2">
        {(state === 'connecting' || state === 'reconnecting') && (
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
        )}
        {state === 'connected' && (
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-40"></span>
        )}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${currentConfig.dotClass}`}></span>
      </span>

      {/* Label Text */}
      <span className={`text-xs font-bold font-sans tracking-wide ${currentConfig.colorClass}`}>
        {currentConfig.text}
        {state === 'connected' && latency !== null && (
          <span className="text-slate-400 dark:text-slate-500 font-mono font-semibold ml-1.5">
            ({latency}ms)
          </span>
        )}
      </span>

      {/* Manual Reconnect Action for failure states */}
      {(state === 'disconnected' || state === 'error') && onReconnect && (
        <button
          onClick={onReconnect}
          className="p-0.5 ml-0.5 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-brand-primary transition"
          aria-label="Reconnect to event stream"
        >
          <RefreshCw className="w-3 h-3" />
        </button>
      )}

      {/* Premium Rich Tooltip */}
      {!isSm && (
        <div
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 bg-slate-950/95 dark:bg-black/95 text-slate-200 p-4 rounded-xl border border-slate-800 shadow-2xl opacity-0 scale-95 pointer-events-none group-hover:opacity-100 group-hover:scale-100 transition-all duration-200 z-dropdown"
          role="tooltip"
        >
          <h4 className="text-xs font-black uppercase tracking-wider text-slate-400 mb-2.5 pb-1 border-b border-slate-800 flex items-center gap-1.5">
            {currentConfig.icon}
            Connection Diagnostics
          </h4>
          <div className="space-y-1.5 font-mono text-[10px] tracking-wide text-slate-300">
            <div className="flex justify-between">
              <span className="text-slate-500">Source:</span>
              <span className="truncate max-w-[150px] font-semibold text-right" title={endpoint}>{endpoint}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Events Recv:</span>
              <span className="text-slate-100 font-bold">{eventsReceived}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Reconnects:</span>
              <span className="text-slate-100 font-bold">{reconnects}</span>
            </div>
            {latency !== null && (
              <div className="flex justify-between">
                <span className="text-slate-500">Avg Latency:</span>
                <span className="text-green-400 font-bold">{latency}ms</span>
              </div>
            )}
            {errorMessage && (
              <div className="mt-2.5 pt-2 border-t border-slate-800/80 text-red-400 flex items-start gap-1 font-sans text-[10px] leading-tight">
                <AlertCircle className="w-3 h-3 mt-0.5 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}
          </div>
          {/* Triangular arrow pointing down */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-slate-950 dark:border-t-black"></div>
        </div>
      )}
    </div>
  );
};

export default SessionStreamIndicator;
