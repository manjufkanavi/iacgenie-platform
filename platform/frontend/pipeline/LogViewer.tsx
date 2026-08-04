import React, { useState, useEffect, useRef } from 'react';
import Card from '../ui/Card';
import type { LogLevel, PipelinePhase } from './types';

interface LogEntryData {
  timestamp: string;
  phase: PipelinePhase | string;
  message: string;
  level: LogLevel;
}

interface LogViewerProps {
  logs: LogEntryData[];
  autoScroll?: boolean;
  maxEntries?: number;
}

type FilterLevel = LogLevel | 'debug' | 'all';

const levelColors: Record<LogLevel, string> = {
  info: 'text-blue-400',
  warning: 'text-amber-400',
  error: 'text-red-400',
};

const levelBadge: Record<LogLevel, string> = {
  info: 'bg-blue-500/20 text-blue-400',
  warning: 'bg-amber-500/20 text-amber-400',
  error: 'bg-red-500/20 text-red-400',
};

const LogViewer: React.FC<LogViewerProps> = ({
  logs,
  autoScroll = true,
  maxEntries = 500,
}) => {
  const [filterLevel, setFilterLevel] = useState<FilterLevel>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const filteredLogs = logs.filter((log) => {
    if (filterLevel !== 'all' && log.level !== filterLevel) return false;
    if (searchQuery && !log.message.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  }).slice(-maxEntries);

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [filteredLogs.length, autoScroll]);

  return (
    <Card padding="none" className="overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-700 dark:border-slate-700 bg-gray-950/50">
        {/* Search */}
        <input
          type="text"
          placeholder="Search logs..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1 bg-transparent text-sm text-gray-300 placeholder-gray-500 outline-none border-b border-transparent focus:border-brand-primary transition-colors"
          aria-label="Search logs"
        />

        {/* Level filter */}
        <div className="flex items-center gap-1" role="group" aria-label="Filter by log level">
          {(['all', 'debug', 'info', 'warning', 'error'] as FilterLevel[]).map((level) => (
            <button
              key={level}
              onClick={() => setFilterLevel(level)}
              className={`px-2 py-0.5 text-xs rounded transition-colors ${
                filterLevel === level
                  ? 'bg-brand-primary/20 text-brand-primary'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
              }`}
              aria-pressed={filterLevel === level}
            >
              {level.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Entry count */}
        <span className="text-xs text-gray-500 dark:text-gray-400 tabular-nums">
          {filteredLogs.length} entries
        </span>
      </div>

      {/* Log entries */}
      <div
        ref={containerRef}
        className="h-[350px] overflow-y-auto font-mono text-xs"
        role="log"
        aria-live="polite"
        aria-label="Pipeline logs"
      >
        {filteredLogs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
            No logs to display
          </div>
        ) : (
          filteredLogs.map((log, idx) => (
            <div
              key={idx}
              className="flex items-start gap-3 px-4 py-0.5 hover:bg-gray-800/30 transition-colors"
            >
              <span className="flex-shrink-0 text-gray-500 dark:text-gray-600 tabular-nums">
                {log.timestamp}
              </span>
              <span className={`flex-shrink-0 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                levelBadge[log.level] || 'bg-gray-700 text-gray-400'
              }`}>
                {log.level}
              </span>
              <span className="flex-shrink-0 text-gray-400 dark:text-gray-500">
                [{log.phase}]
              </span>
              <span className={`flex-1 break-all ${levelColors[log.level] || 'text-gray-300 dark:text-gray-400'}`}>
                {log.message}
              </span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </Card>
  );
};

export default LogViewer;
