import React, { useState } from 'react';
import { CheckCircle2, Loader2, AlertTriangle, XCircle, GitBranch, RefreshCw } from 'lucide-react';

export type SyncState = 'in-progress' | 'completed' | 'failed' | 'out-of-sync';

interface RepoSyncStatusBadgeProps {
    syncState: SyncState;
    lastSyncedAt?: Date | null;
    expectedSyncAt?: Date | null;
    showMetadata?: boolean;
    size?: 'sm' | 'md';
    className?: string;
    driftCount?: number;
    driftResources?: string[];
    onResolve?: () => void;
}

const RepoSyncStatusBadge: React.FC<RepoSyncStatusBadgeProps> = ({
    syncState,
    lastSyncedAt = null,
    expectedSyncAt = null,
    showMetadata = false,
    size = 'md',
    className = '',
    driftCount = 0,
    driftResources = [],
    onResolve
}) => {
    const [showTooltip, setShowTooltip] = useState(false);
    const [isResolving, setIsResolving] = useState(false);

    const handleResolveClick = async (e: React.MouseEvent) => {
        e.stopPropagation();
        if (onResolve) {
            setIsResolving(true);
            try {
                await onResolve();
            } finally {
                setIsResolving(false);
            }
        }
    };

    const getStatusConfig = () => {
        switch (syncState) {
            case 'completed':
                return {
                    label: 'Synced',
                    dotColor: 'var(--color-git-sync-completed)',
                    bgClass: 'bg-[var(--color-git-sync-completed-bg)] text-[var(--color-git-sync-completed)] border-[var(--color-git-sync-completed)]/20',
                    icon: <CheckCircle2 className="w-3.5 h-3.5" />
                };
            case 'in-progress':
                return {
                    label: 'Syncing...',
                    dotColor: 'var(--color-git-sync-dot)',
                    bgClass: 'bg-[var(--color-git-sync-in-progress-bg)] text-[var(--color-git-sync-in-progress)] border-[var(--color-git-sync-in-progress)]/20',
                    icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />
                };
            case 'out-of-sync':
                return {
                    label: 'Out of Sync',
                    dotColor: 'var(--color-git-sync-out-of-sync)',
                    bgClass: 'bg-[var(--color-git-sync-out-of-sync-bg)] text-[var(--color-git-sync-out-of-sync)] border-[var(--color-git-sync-out-of-sync)]/20',
                    icon: <AlertTriangle className="w-3.5 h-3.5" />
                };
            case 'failed':
            default:
                return {
                    label: 'Sync Error',
                    dotColor: 'var(--color-git-sync-failed)',
                    bgClass: 'bg-[var(--color-git-sync-failed-bg)] text-[var(--color-git-sync-failed)] border-[var(--color-git-sync-failed)]/20',
                    icon: <XCircle className="w-3.5 h-3.5" />
                };
        }
    };

    const config = getStatusConfig();
    const formattedLastSync = lastSyncedAt
        ? new Intl.DateTimeFormat('en-US', {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
              month: 'short',
              day: 'numeric'
          }).format(new Date(lastSyncedAt))
        : 'Never';

    return (
        <div 
            className={`relative inline-flex items-center gap-2 ${className}`}
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
        >
            <div
                className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border text-xs font-semibold select-none transition-all duration-300 ${
                    config.bgClass
                } ${size === 'sm' ? 'px-2 py-0' : 'px-2.5 py-0.5'}`}
                role="status"
                aria-label={`Repository sync status: ${config.label}`}
                tabIndex={0}
            >
                {/* Visual indicator dot / spinner */}
                <span className="flex-shrink-0 relative flex items-center justify-center">
                    {syncState === 'in-progress' ? (
                        config.icon
                    ) : (
                        <span 
                            className="w-2 h-2 rounded-full" 
                            style={{ 
                                backgroundColor: config.dotColor,
                                animation: 'none'
                            }} 
                        />
                    )}
                </span>
                <span>{config.label}</span>
            </div>

            {showMetadata && lastSyncedAt && (
                <span className="text-xs text-slate-400 dark:text-slate-500 font-medium">
                    Last synced: {formattedLastSync}
                </span>
            )}

            {/* Rich Premium Interactive Tooltip */}
            {showTooltip && (
                <div 
                    className="absolute z-[var(--z-tooltip)] w-80 bg-slate-900 border border-slate-700/60 rounded-xl shadow-2xl p-4 text-slate-100 left-1/2 -translate-x-1/2 bottom-full mb-2 animate-fadeIn"
                    role="tooltip"
                >
                    {/* Header */}
                    <div className="flex items-center gap-2 border-b border-slate-800 pb-2 mb-2">
                        <span className="flex-shrink-0" style={{ color: config.dotColor }}>
                            {syncState === 'completed' && <CheckCircle2 className="w-4 h-4" />}
                            {syncState === 'in-progress' && <Loader2 className="w-4 h-4 animate-spin" />}
                            {syncState === 'out-of-sync' && <AlertTriangle className="w-4 h-4" />}
                            {syncState === 'failed' && <XCircle className="w-4 h-4" />}
                        </span>
                        <span className="font-bold text-sm tracking-wide text-white">Sync Status Info</span>
                    </div>

                    {/* Metadata Content */}
                    <div className="space-y-1.5 text-xs text-slate-300">
                        <div className="flex justify-between">
                            <span className="text-slate-500 font-medium">State:</span>
                            <span className="font-semibold text-white">{config.label}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-slate-500 font-medium">Last Synced:</span>
                            <span>{formattedLastSync}</span>
                        </div>
                        {expectedSyncAt && (
                            <div className="flex justify-between">
                                <span className="text-slate-500 font-medium">Next Expected:</span>
                                <span>{new Intl.DateTimeFormat('en', { hour: '2-digit', minute: '2-digit' }).format(new Date(expectedSyncAt))}</span>
                            </div>
                        )}
                        <div className="flex justify-between items-center mt-1 pt-1 border-t border-slate-800">
                            <span className="text-slate-500 font-medium flex items-center gap-1">
                                <GitBranch className="w-3 h-3 text-slate-400" /> Target branch:
                            </span>
                            <span className="font-mono text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-300">main</span>
                        </div>
                    </div>

                    {/* Out of Sync Drift Details */}
                    {syncState === 'out-of-sync' && (
                        <div className="mt-3 bg-amber-500/10 border border-amber-500/20 rounded-lg p-2.5">
                            <span className="text-[11px] font-bold text-amber-400 flex items-center gap-1.5">
                                <AlertTriangle className="w-3.5 h-3.5" />
                                {driftCount || driftResources.length || 2} resources out of sync (drift):
                            </span>
                            <ul className="mt-1.5 space-y-1 text-[10px] font-mono text-amber-300/90 list-disc list-inside">
                                {driftResources.length > 0 ? (
                                    driftResources.map((res, idx) => <li key={idx} className="truncate">{res}</li>)
                                ) : (
                                    <>
                                        <li>aws_s3_bucket.main (modified outside code)</li>
                                        <li>aws_iam_role.app (missing in active branch)</li>
                                    </>
                                )}
                            </ul>
                            {onResolve && (
                                <button
                                    onClick={handleResolveClick}
                                    disabled={isResolving}
                                    className="w-full mt-2.5 py-1.5 bg-amber-500 hover:bg-amber-600 active:bg-amber-700 text-slate-950 font-bold uppercase tracking-wider text-[10px] rounded-md transition duration-200 flex items-center justify-center gap-1 disabled:opacity-50"
                                >
                                    {isResolving ? (
                                        <Loader2 className="w-3 h-3 animate-spin" />
                                    ) : (
                                        <RefreshCw className="w-3 h-3" />
                                    )}
                                    Resolve Sync Drift
                                </button>
                            )}
                        </div>
                    )}

                    {/* Arrow Pointer */}
                    <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2.5 h-2.5 bg-slate-900 border-r border-b border-slate-700/60 rotate-45" />
                </div>
            )}
        </div>
    );
};

export default RepoSyncStatusBadge;
