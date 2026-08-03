import React, { useState } from 'react';
import Card from '../ui/Card';
import MetricCard from '../ui/MetricCard';
import {
  Activity,
  Clock,
  Server,
  Zap,
  Search,
} from 'lucide-react';

interface LogEntry {
  pipeline: string;
  phase: string;
  severity: 'info' | 'warn' | 'error' | 'debug';
  message: string;
  timestamp: string;
}

interface PhaseMetric {
  phase: string;
  avgDuration: number;
  successRate: number;
  failureCount: number;
  totalRuns: number;
}

interface ObservabilityTabPanelProps {
  runId?: string;
}

const MOCK_LOGS: LogEntry[] = [
  { pipeline: 'pipe-abc123', phase: 'clarify', severity: 'info', message: 'Clarification session initiated', timestamp: '2026-03-08T10:30:00Z' },
  { pipeline: 'pipe-abc123', phase: 'generate', severity: 'info', message: 'Code generation started', timestamp: '2026-03-08T10:31:00Z' },
  { pipeline: 'pipe-abc123', phase: 'generate', severity: 'warn', message: 'High token usage detected', timestamp: '2026-03-08T10:33:00Z' },
  { pipeline: 'pipe-abc123', phase: 'validate', severity: 'info', message: 'Validation check passed', timestamp: '2026-03-08T10:35:00Z' },
  { pipeline: 'pipe-abc123', phase: 'plan', severity: 'info', message: 'OpenTofu plan generated', timestamp: '2026-03-08T10:38:00Z' },
  { pipeline: 'pipe-abc123', phase: 'apply', severity: 'error', message: 'Apply failed: resource conflict', timestamp: '2026-03-08T10:42:00Z' },
  { pipeline: 'pipe-abc123', phase: 'apply', severity: 'info', message: 'Retrying apply...', timestamp: '2026-03-08T10:43:00Z' },
  { pipeline: 'pipe-abc123', phase: 'complete', severity: 'info', message: 'Pipeline completed successfully', timestamp: '2026-03-08T10:45:00Z' },
];

const MOCK_PHASE_METRICS: PhaseMetric[] = [
  { phase: 'Clarify', avgDuration: 45, successRate: 98, failureCount: 2, totalRuns: 125 },
  { phase: 'Generate', avgDuration: 320, successRate: 94, failureCount: 8, totalRuns: 125 },
  { phase: 'Validate', avgDuration: 180, successRate: 99, failureCount: 1, totalRuns: 125 },
  { phase: 'Plan', avgDuration: 250, successRate: 97, failureCount: 4, totalRuns: 125 },
  { phase: 'Apply', avgDuration: 400, successRate: 91, failureCount: 11, totalRuns: 125 },
  { phase: 'Complete', avgDuration: 30, successRate: 100, failureCount: 0, totalRuns: 125 },
];

const ObservabilityTabPanel: React.FC<ObservabilityTabPanelProps> = ({ runId: _runId }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [phaseFilter, setPhaseFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');

  const filteredLogs = MOCK_LOGS.filter(log => {
    if (phaseFilter !== 'all' && log.phase !== phaseFilter) return false;
    if (severityFilter !== 'all' && log.severity !== severityFilter) return false;
    if (searchQuery && !log.message.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const totalRuns = 125;
  const overallSuccessRate = 96;
  const avgLatency = 8.2;
  const totalCost = 234.50;

  return (
    <div className="space-y-6">
      {/* Summary Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Runs"
          value={totalRuns}
          subtitle="Last 30 days"
          icon={<Activity className="w-5 h-5" />}
          trend="+12%"
          trendType="success"
          borderAccent="border-emerald-500"
        />
        <MetricCard
          title="Success Rate"
          value={`${overallSuccessRate}%`}
          subtitle="Overall"
          icon={<Zap className="w-5 h-5" />}
          trend="+2.3%"
          trendType="success"
          borderAccent="border-blue-500"
        />
        <MetricCard
          title="Avg Latency"
          value={`${avgLatency}s`}
          subtitle="Per phase"
          icon={<Clock className="w-5 h-5" />}
          trend="-0.5s"
          trendType="success"
          borderAccent="border-amber-500"
        />
        <MetricCard
          title="Total Cost"
          value={`$${totalCost.toFixed(2)}`}
          subtitle="LLM usage"
          icon={<Server className="w-5 h-5" />}
          trend="+$12.30"
          trendType="warning"
          borderAccent="border-rose-500"
        />
      </div>

      {/* Phase Performance Metrics */}
      <Card>
        <h3 className="text-sm font-semibold text-slate-400 dark:text-slate-500 mb-4">Phase Performance Metrics</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700">
                <th className="text-left py-2 px-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Phase</th>
                <th className="text-right py-2 px-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Avg Duration</th>
                <th className="text-right py-2 px-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Success Rate</th>
                <th className="text-right py-2 px-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Failures</th>
                <th className="text-right py-2 px-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Total Runs</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_PHASE_METRICS.map((m) => (
                <tr key={m.phase} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                  <td className="py-2.5 px-3 text-slate-200 font-medium">{m.phase}</td>
                  <td className="py-2.5 px-3 text-right text-slate-200 font-mono">{m.avgDuration}s</td>
                  <td className="py-2.5 px-3 text-right">
                    <span className={`font-bold ${m.successRate >= 95 ? 'text-emerald-400' : m.successRate >= 90 ? 'text-amber-400' : 'text-rose-400'}`}>
                      {m.successRate}%
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right text-slate-200 font-mono">{m.failureCount}</td>
                  <td className="py-2.5 px-3 text-right text-slate-200 font-mono">{m.totalRuns}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Logs Viewer with Filters */}
      <Card>
        <h3 className="text-sm font-semibold text-slate-400 dark:text-slate-500 mb-4">Execution Logs</h3>

        {/* Filter Bar */}
        <div className="flex flex-wrap gap-3 mb-4">
          <div className="flex-1 min-w-[200px] relative">
            <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
              <Search className="w-4 h-4 text-slate-500" />
            </div>
            <input
              type="text"
              placeholder="Search logs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg py-2 px-3 pl-10 text-sm text-slate-900 dark:text-slate-50 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition"
            />
          </div>
          <div>
            <select
              value={phaseFilter}
              onChange={(e) => setPhaseFilter(e.target.value)}
              className="bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg py-2 px-3 text-sm text-slate-900 dark:text-slate-50 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition"
            >
              <option value="all">All Phases</option>
              <option value="clarify">Clarify</option>
              <option value="generate">Generate</option>
              <option value="validate">Validate</option>
              <option value="plan">Plan</option>
              <option value="apply">Apply</option>
              <option value="complete">Complete</option>
            </select>
          </div>
          <div>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg py-2 px-3 text-sm text-slate-900 dark:text-slate-50 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition"
            >
              <option value="all">All Severities</option>
              <option value="info">Info</option>
              <option value="warn">Warn</option>
              <option value="error">Error</option>
              <option value="debug">Debug</option>
            </select>
          </div>
        </div>

        {/* Logs List */}
        <div className="bg-black/50 rounded-lg p-4 max-h-80 overflow-y-auto">
          {filteredLogs.length === 0 ? (
            <p className="text-xs text-slate-500 text-center py-8">No logs match your filters.</p>
          ) : (
            <div className="space-y-1">
              {filteredLogs.map((log, index) => (
                <div key={index} className="text-xs font-mono">
                  <span className="text-slate-500">{new Date(log.timestamp).toLocaleTimeString()}</span>
                  <span className={`ml-2 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                    log.severity === 'info' ? 'text-blue-400 bg-blue-500/10' :
                    log.severity === 'warn' ? 'text-amber-400 bg-amber-500/10' :
                    log.severity === 'error' ? 'text-red-400 bg-red-500/10' :
                    'text-slate-400 bg-slate-500/10'
                  }`}>
                    {log.phase}
                  </span>
                  <span className="ml-2 text-slate-300">{log.message}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      {/* Distributed Traces Explorer */}
      <Card>
        <h3 className="text-sm font-semibold text-slate-400 dark:text-slate-500 mb-4">Distributed Traces</h3>
        <div className="space-y-3">
          {[
            { traceId: 'trace-001', duration: '2.3s', spans: 12, status: 'completed' },
            { traceId: 'trace-002', duration: '5.1s', spans: 18, status: 'failed' },
            { traceId: 'trace-003', duration: '1.8s', spans: 8, status: 'completed' },
          ].map((trace) => (
            <div key={trace.traceId} className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono text-slate-500">{trace.traceId}</span>
                <span className="text-xs text-slate-400">{trace.duration}</span>
                <span className="text-xs text-slate-400">{trace.spans} spans</span>
              </div>
              <span className={`text-xs font-bold uppercase ${
                trace.status === 'completed' ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                {trace.status}
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

export default ObservabilityTabPanel;
