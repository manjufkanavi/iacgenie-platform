import React, { useState } from 'react';
import { CheckCircle2, Loader2, AlertTriangle, XCircle, RefreshCw, Github, Gitlab, Calendar, Clock, Terminal, ChevronDown, ChevronUp, FileCode, Play, BarChart2 } from 'lucide-react';
import Button from '../ui/Button';
import Card from '../ui/Card';

export interface SyncHealthData {
    state: 'in-progress' | 'completed' | 'failed' | 'out-of-sync';
    lastSyncedAt: Date | null;
    expectedSyncAt?: Date | null;
    currentBranch: string;
    targetBranch: string;
}

export interface ExecutionRun {
    id: string;
    type: 'plan' | 'apply';
    provider: 'github' | 'gitlab';
    status: 'success' | 'failed' | 'in-progress' | 'cancelled';
    commitHash: string;
    commitMessage: string;
    duration: number; // in seconds
    startedAt: Date;
    finishedAt: Date | null;
    logs?: string;
}

interface SyncProgressPanelProps {
    health: SyncHealthData;
    runs: ExecutionRun[];
    onRefresh?: () => Promise<void>;
    className?: string;
}

const SyncProgressPanel: React.FC<SyncProgressPanelProps> = ({
    health,
    runs: initialRuns,
    onRefresh,
    className = ''
}) => {
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [expandedRuns, setExpandedRuns] = useState<Record<string, boolean>>({});
    const [runs, _setRuns] = useState<ExecutionRun[]>(initialRuns);
    const [filter, setFilter] = useState<'all' | 'plan' | 'apply'>('all');

    const handleRefresh = async () => {
        if (isRefreshing) return;
        setIsRefreshing(true);
        try {
            if (onRefresh) {
                await onRefresh();
            } else {
                // Mock refresh timing
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
        } finally {
            setIsRefreshing(false);
        }
    };

    const toggleExpand = (runId: string) => {
        setExpandedRuns(prev => ({
            ...prev,
            [runId]: !prev[runId]
        }));
    };

    // Filter runs
    const filteredRuns = runs.filter(run => {
        if (filter === 'all') return true;
        return run.type === filter;
    });

    const getHealthConfig = () => {
        switch (health.state) {
            case 'completed':
                return {
                    label: 'Synced & Healthy',
                    color: 'text-green-500',
                    dotColor: 'bg-green-500',
                    bgClass: 'bg-green-500/10 border-green-500/20 text-green-700 dark:text-green-400',
                    icon: <CheckCircle2 className="w-5 h-5 text-green-500" />
                };
            case 'in-progress':
                return {
                    label: 'Sync In Progress',
                    color: 'text-blue-500',
                    dotColor: 'bg-blue-500',
                    bgClass: 'bg-blue-500/10 border-blue-500/20 text-blue-700 dark:text-blue-400',
                    icon: <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                };
            case 'out-of-sync':
                return {
                    label: 'Out of Sync (Drift)',
                    color: 'text-amber-500',
                    dotColor: 'bg-amber-500',
                    bgClass: 'bg-amber-500/10 border-amber-500/20 text-amber-700 dark:text-amber-400',
                    icon: <AlertTriangle className="w-5 h-5 text-amber-500" />
                };
            case 'failed':
            default:
                return {
                    label: 'Sync Error',
                    color: 'text-red-500',
                    dotColor: 'bg-red-500',
                    bgClass: 'bg-red-500/10 border-red-500/20 text-red-700 dark:text-red-400',
                    icon: <XCircle className="w-5 h-5 text-red-500" />
                };
        }
    };

    const healthConfig = getHealthConfig();

    // Compute mock statistics
    const totalRuns = runs.length;
    const successfulRuns = runs.filter(r => r.status === 'success').length;
    const successRate = totalRuns > 0 ? Math.round((successfulRuns / totalRuns) * 100) : 100;
    const avgDuration = totalRuns > 0 
        ? Math.round(runs.reduce((acc, r) => acc + r.duration, 0) / totalRuns) 
        : 0;

    return (
        <div className={`space-y-6 ${className}`}>
            {/* Health and Statistics Overview Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Health Overview Card */}
                <Card className={`p-5 flex flex-col justify-between border relative overflow-hidden ${healthConfig.bgClass}`}>
                    <div className="flex justify-between items-start">
                        <div>
                            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 dark:text-slate-400 block mb-1">Sync Status</span>
                            <h4 className="text-lg font-black tracking-wide flex items-center gap-2">
                                <span className={`w-2.5 h-2.5 rounded-full ${healthConfig.dotColor} ${health.state === 'in-progress' ? 'animate-ping' : ''}`} />
                                {healthConfig.label}
                            </h4>
                        </div>
                        <div className="p-2.5 bg-white/60 dark:bg-slate-800/60 rounded-xl shadow-sm border border-slate-200/20">
                            {healthConfig.icon}
                        </div>
                    </div>

                    <div className="mt-6 pt-4 border-t border-slate-200/10 space-y-1.5 text-xs text-slate-600 dark:text-slate-400">
                        <div className="flex justify-between">
                            <span>Branch Mapping:</span>
                            <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">{health.currentBranch} → {health.targetBranch}</span>
                        </div>
                        <div className="flex justify-between">
                            <span>Last sync complete:</span>
                            <span className="font-semibold text-slate-800 dark:text-slate-200">
                                {health.lastSyncedAt ? `${new Intl.DateTimeFormat('en', { hour: '2-digit', minute: '2-digit' }).format(new Date(health.lastSyncedAt))} (${Math.round((Date.now() - new Date(health.lastSyncedAt).getTime()) / 60000)}m ago)` : 'Never'}
                            </span>
                        </div>
                    </div>
                </Card>

                {/* Operations Statistics */}
                <Card className="col-span-1 md:col-span-2 p-5 flex flex-col justify-between border border-slate-200 dark:border-slate-700/50">
                    <div className="flex justify-between items-center mb-4">
                        <div>
                            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 dark:text-slate-400 block">Observability Metrics</span>
                            <h4 className="text-lg font-bold text-slate-800 dark:text-slate-100 flex items-center gap-1.5">
                                <BarChart2 className="w-4 h-4 text-brand-primary" /> Webhook Actions History
                            </h4>
                        </div>
                        <Button
                            onClick={handleRefresh}
                            disabled={isRefreshing}
                            variant="secondary"
                            size="sm"
                            className="flex items-center gap-1 text-xs py-1.5"
                        >
                            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
                            Refresh logs
                        </Button>
                    </div>

                    <div className="grid grid-cols-3 gap-4 text-center mt-2">
                        <div className="bg-slate-50 dark:bg-slate-800/40 p-3 rounded-xl border border-slate-200/50 dark:border-slate-700/50">
                            <span className="text-[10px] text-slate-400 uppercase font-semibold">Total Runs</span>
                            <p className="text-xl font-black text-slate-800 dark:text-slate-100 mt-1">{totalRuns}</p>
                        </div>
                        <div className="bg-slate-50 dark:bg-slate-800/40 p-3 rounded-xl border border-slate-200/50 dark:border-slate-700/50">
                            <span className="text-[10px] text-slate-400 uppercase font-semibold">Success Rate</span>
                            <p className="text-xl font-black text-green-500 mt-1">{successRate}%</p>
                        </div>
                        <div className="bg-slate-50 dark:bg-slate-800/40 p-3 rounded-xl border border-slate-200/50 dark:border-slate-700/50">
                            <span className="text-[10px] text-slate-400 uppercase font-semibold">Avg Duration</span>
                            <p className="text-xl font-black text-indigo-500 mt-1">{avgDuration}s</p>
                        </div>
                    </div>
                </Card>
            </div>

            {/* Timelines of execution logs */}
            <div className="space-y-4">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-3">
                    <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Digger Pipeline Execution Run History</h3>
                    <div className="flex gap-2">
                        {['all', 'plan', 'apply'].map((t) => (
                            <button
                                key={t}
                                onClick={() => setFilter(t as any)}
                                className={`px-3 py-1 rounded-lg text-xs font-semibold uppercase tracking-wider transition ${
                                    filter === t
                                        ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
                                        : 'bg-slate-100 dark:bg-slate-800 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                                }`}
                            >
                                {t}
                            </button>
                        ))}
                    </div>
                </div>

                {filteredRuns.length === 0 ? (
                    <Card className="p-8 text-center border-dashed">
                        <Terminal className="w-10 h-10 text-slate-400 mx-auto mb-2" />
                        <h4 className="font-bold text-slate-600">No Execution History</h4>
                        <p className="text-xs text-slate-400">There are no matching Digger plan/apply execution runs for this repository.</p>
                    </Card>
                ) : (
                    <div className="relative border-l border-slate-200 dark:border-slate-700/50 pl-5 ml-3.5 space-y-6">
                        {filteredRuns.map((run) => {
                            const isExpanded = expandedRuns[run.id];
                            
                            // Setup badges
                            const statusConfig = {
                                success: { label: 'Succeeded', icon: <CheckCircle2 className="w-4 h-4 text-green-500" />, bg: 'bg-green-50 text-green-600 dark:bg-green-500/10 dark:text-green-400 border-green-200' },
                                failed: { label: 'Failed', icon: <XCircle className="w-4 h-4 text-red-500" />, bg: 'bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400 border-red-200' },
                                'in-progress': { label: 'Syncing', icon: <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />, bg: 'bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400 border-blue-200' },
                                cancelled: { label: 'Cancelled', icon: <XCircle className="w-4 h-4 text-slate-400" />, bg: 'bg-slate-50 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border-slate-200' }
                            }[run.status];

                            return (
                                <div key={run.id} className="relative group">
                                    {/* Timeline icon indicator */}
                                    <div 
                                        className={`absolute -left-[30px] top-1.5 w-5 h-5 rounded-full flex items-center justify-center border-2 border-white dark:border-slate-900 text-white shadow-sm transition-all duration-300 ${
                                            run.status === 'success'
                                                ? 'bg-green-500'
                                                : run.status === 'failed'
                                                ? 'bg-red-500'
                                                : run.status === 'in-progress'
                                                ? 'bg-blue-500 animate-pulse'
                                                : 'bg-slate-400'
                                        }`}
                                    >
                                        {run.type === 'plan' ? <FileCode className="w-2.5 h-2.5" /> : <Play className="w-2.5 h-2.5" />}
                                    </div>

                                    {/* Run Detail Row */}
                                    <Card className="p-4 hover:shadow-md transition-shadow duration-300 border border-slate-200 dark:border-slate-700/50">
                                        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                            <div className="flex flex-wrap items-center gap-2">
                                                <span className="font-extrabold text-slate-800 dark:text-slate-100 text-sm uppercase">
                                                    digger {run.type}
                                                </span>
                                                <div className={`px-2 py-0.5 rounded-full border text-[10px] font-bold inline-flex items-center gap-1.5 ${statusConfig.bg}`}>
                                                    {statusConfig.icon}
                                                    {statusConfig.label}
                                                </div>
                                                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-500">
                                                    {run.provider === 'github' ? <Github className="w-3 h-3 text-[var(--color-git-provider-github)]" /> : <Gitlab className="w-3 h-3 text-[var(--color-git-provider-gitlab)]" />}
                                                    {run.provider.toUpperCase()}
                                                </span>
                                            </div>

                                            <div className="flex items-center gap-3 text-slate-400 text-xs font-medium ml-auto">
                                                <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" /> {run.duration}s</span>
                                                <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> {new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(run.startedAt)}</span>
                                                <button
                                                    onClick={() => toggleExpand(run.id)}
                                                    className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 border border-slate-200 dark:border-slate-700/50 transition-colors"
                                                >
                                                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                                </button>
                                            </div>
                                        </div>

                                        <div className="mt-2.5 flex items-center gap-2.5 text-xs">
                                            <span className="font-mono bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-slate-500 font-semibold">{run.commitHash.slice(0, 7)}</span>
                                            <span className="text-slate-600 dark:text-slate-300 font-semibold truncate max-w-sm sm:max-w-xl">{run.commitMessage}</span>
                                        </div>

                                        {/* Expanded Logs Console Area */}
                                        {isExpanded && (
                                            <div 
                                                className="mt-4 border border-slate-800/80 rounded-xl overflow-hidden shadow-inner animate-slideDown"
                                                style={{ animation: 'git-comment-expand var(--duration-git-comment-expand) var(--ease-default)' }}
                                            >
                                                {/* Header console tab */}
                                                <div className="bg-slate-900 border-b border-slate-800 px-4 py-2 flex items-center justify-between text-slate-400 font-mono text-[10px]">
                                                    <span className="flex items-center gap-1.5"><Terminal className="w-3.5 h-3.5 text-brand-primary" /> execution_run_logs.sh</span>
                                                    <span className="text-slate-500">PAGER=cat</span>
                                                </div>
                                                
                                                {/* Log stream console */}
                                                <pre className="bg-[var(--color-console-bg)] p-4 text-[var(--color-console-text)] font-mono text-xs overflow-x-auto whitespace-pre leading-relaxed select-all">
                                                    <code>{run.logs || `$ tofu ${run.type} -out=tfplan\nInitializing the backend...\nSuccess! The backend initialized successfully.\n\nRunning plan...\nPlan: 2 to add, 0 to change, 1 to destroy.\nFinished successfully at ${run.finishedAt?.toLocaleTimeString()}`}</code>
                                                </pre>
                                            </div>
                                        )}
                                    </Card>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
};

export default SyncProgressPanel;
