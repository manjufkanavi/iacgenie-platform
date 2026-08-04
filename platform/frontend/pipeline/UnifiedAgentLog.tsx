import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ValidationStepLog } from '../types';
import { ChevronDown, ChevronUp, Terminal, Filter } from 'lucide-react';

export interface UnifiedAgentLogProps {
  logs: ValidationStepLog[];
  isExpanded?: boolean;
  onToggleExpand?: (expanded: boolean) => void;
}

const severityColors: Record<string, string> = {
  success: 'text-emerald-400',
  error: 'text-red-400',
  running: 'text-blue-400',
  retrying: 'text-amber-400',
  info: 'text-gray-300'
};

const UnifiedAgentLog: React.FC<UnifiedAgentLogProps> = ({
  logs,
  isExpanded = true,
  onToggleExpand,
}) => {
  const [internalExpanded, setInternalExpanded] = useState(isExpanded);
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [agentFilter, setAgentFilter] = useState<string>('all');
  const scrollRef = useRef<HTMLDivElement>(null);

  const expanded = onToggleExpand ? isExpanded : internalExpanded;

  useEffect(() => {
    if (!onToggleExpand) {
      setInternalExpanded(isExpanded);
    }
  }, [isExpanded, onToggleExpand]);

  const handleToggle = () => {
    if (onToggleExpand) {
      onToggleExpand(!expanded);
    } else {
      setInternalExpanded(!expanded);
    }
  };

  useEffect(() => {
    if (expanded && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, expanded]);

  const uniqueAgents = Array.from(new Set(logs.map(l => l.stage))).filter(Boolean);

  const filteredLogs = logs.filter(log => {
    if (severityFilter !== 'all' && log.status !== severityFilter && !(severityFilter === 'info' && !['success', 'error', 'running', 'retrying'].includes(log.status))) {
      return false;
    }
    if (agentFilter !== 'all' && log.stage !== agentFilter) {
      return false;
    }
    return true;
  });

  return (
    <div className="w-full bg-slate-900 border border-slate-700/50 rounded-xl overflow-hidden shadow-lg flex flex-col font-mono text-[12px] leading-relaxed">
      {/* Header Toolbar */}
      <div 
        className="h-10 px-4 bg-slate-800/80 border-b border-slate-700/50 flex items-center justify-between cursor-pointer select-none"
        onClick={handleToggle}
      >
        <div className="flex items-center space-x-3">
          <Terminal size={14} className="text-slate-400" />
          <span className="font-semibold text-slate-200 tracking-wide">Agent Reasoning Stream</span>
          {!expanded && (
            <span className="text-slate-500 ml-2">
              ({logs.length} events)
            </span>
          )}
        </div>
        
        <div className="flex items-center space-x-4" onClick={(e) => e.stopPropagation()}>
          {expanded && (
            <>
              <div className="flex items-center space-x-2">
                <Filter size={12} className="text-slate-400" />
                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="bg-slate-900 border border-slate-700 text-slate-300 text-[11px] rounded px-2 py-0.5 outline-none focus:border-blue-500 transition-colors"
                >
                  <option value="all">All Severities</option>
                  <option value="success">Success</option>
                  <option value="error">Error</option>
                  <option value="running">Running</option>
                  <option value="info">Info</option>
                </select>
              </div>
              <div className="flex items-center space-x-2">
                <select
                  value={agentFilter}
                  onChange={(e) => setAgentFilter(e.target.value)}
                  className="bg-slate-900 border border-slate-700 text-slate-300 text-[11px] rounded px-2 py-0.5 outline-none focus:border-blue-500 transition-colors"
                >
                  <option value="all">All Agents</option>
                  {uniqueAgents.map(agent => (
                    <option key={agent} value={agent}>{agent}</option>
                  ))}
                </select>
              </div>
            </>
          )}
          <button 
            className="text-slate-400 hover:text-slate-200 transition-colors focus:outline-none"
            aria-label={expanded ? 'Collapse Logs' : 'Expand Logs'}
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {/* Log Body */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 300 }}
            exit={{ height: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="w-full bg-slate-900"
          >
            <div 
              ref={scrollRef}
              className="p-4 h-full overflow-y-auto space-y-2"
            >
              {filteredLogs.length === 0 ? (
                <div className="text-slate-500 italic text-center mt-4">No logs found matching filters.</div>
              ) : (
                filteredLogs.map((log, i) => (
                  <div key={i} className="flex items-start space-x-3 font-mono">
                    <span className="text-slate-500 shrink-0 select-none">
                      [{new Date(log.timestamp).toLocaleTimeString([], { hour12: false })}]
                    </span>
                    {log.stage && (
                      <span className="text-purple-400 shrink-0 font-semibold select-none">
                        [{log.stage}]
                      </span>
                    )}
                    <span className={`${severityColors[log.status] || severityColors.info} whitespace-pre-wrap break-words`}>
                      {log.message}
                    </span>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default UnifiedAgentLog;
