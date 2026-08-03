import React, { useState } from 'react';
import { ChevronDown, ChevronUp, CheckCircle2, Loader2, XCircle, Clock, MessageSquare, Play, RefreshCw, ExternalLink } from 'lucide-react';
import Card from '../ui/Card';
import Button from '../ui/Button';

export type PrCommentState = 'plan-running' | 'plan-succeeded' | 'plan-failed' | 'apply-pending' | 'apply-succeeded' | 'apply-failed';

export interface ResourceChange {
    action: 'add' | 'change' | 'remove';
    resource: string;
}

export interface PrCommentData {
    state: PrCommentState;
    title: string;
    resources: ResourceChange[];
    planDetails: string | null;
    expandable: boolean;
    prUrl: string;
    commitHash: string;
    timestamp: Date;
}

interface PRCommentDisplayProps {
    data: PrCommentData;
    onApplyTrigger?: () => void;
    onRetryTrigger?: () => void;
    className?: string;
}

const PRCommentDisplay: React.FC<PRCommentDisplayProps> = ({
    data,
    onApplyTrigger,
    onRetryTrigger,
    className = ''
}) => {
    const [showPlanDetails, setShowPlanDetails] = useState(false);

    // Compute resource metrics
    const addedCount = data.resources.filter(r => r.action === 'add').length;
    const changedCount = data.resources.filter(r => r.action === 'change').length;
    const removedCount = data.resources.filter(r => r.action === 'remove').length;

    const getStatusConfig = () => {
        switch (data.state) {
            case 'plan-running':
                return {
                    badgeText: 'Running',
                    badgeStyle: 'bg-[var(--color-git-pr-plan-running-bg)] text-[var(--color-git-pr-plan-running)] border-[var(--color-git-pr-plan-running)]/20',
                    icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
                    titleText: 'OpenTofu Plan in progress...',
                    descText: 'Planning changes for resources. Pulses are active.'
                };
            case 'plan-succeeded':
                return {
                    badgeText: 'Plan Succeeded',
                    badgeStyle: 'bg-[var(--color-git-pr-plan-succeeded-bg)] text-[var(--color-git-pr-plan-succeeded)] border-[var(--color-git-pr-plan-succeeded)]/20',
                    icon: <CheckCircle2 className="w-3.5 h-3.5" />,
                    titleText: 'OpenTofu Plan generated',
                    descText: `Changed ${data.resources.length} resources. No breaking changes detected.`
                };
            case 'plan-failed':
                return {
                    badgeText: 'Plan Failed',
                    badgeStyle: 'bg-[var(--color-git-pr-plan-failed-bg)] text-[var(--color-git-pr-plan-failed)] border-[var(--color-git-pr-plan-failed)]/20',
                    icon: <XCircle className="w-3.5 h-3.5" />,
                    titleText: 'OpenTofu Plan failed',
                    descText: 'Error occurred during Terraform/Tofu plan execution.'
                };
            case 'apply-pending':
                return {
                    badgeText: 'Apply Pending',
                    badgeStyle: 'bg-[var(--color-git-pr-apply-pending-bg)] text-[var(--color-git-pr-apply-pending)] border-[var(--color-git-pr-apply-pending)]/20',
                    icon: <Clock className="w-3.5 h-3.5" />,
                    titleText: 'Awaiting deployment trigger',
                    descText: "Terraform plan complete. Awaiting user 'digger apply' verification."
                };
            case 'apply-succeeded':
                return {
                    badgeText: 'Apply Succeeded',
                    badgeStyle: 'bg-[var(--color-git-pr-apply-succeeded-bg)] text-[var(--color-git-pr-apply-succeeded)] border-[var(--color-git-pr-apply-succeeded)]/20',
                    icon: <CheckCircle2 className="w-3.5 h-3.5" />,
                    titleText: 'OpenTofu Apply completed successfully!',
                    descText: `Successfully applied changes to ${data.resources.length} cloud resources.`
                };
            case 'apply-failed':
            default:
                return {
                    badgeText: 'Apply Failed',
                    badgeStyle: 'bg-[var(--color-git-pr-apply-failed-bg)] text-[var(--color-git-pr-apply-failed)] border-[var(--color-git-pr-apply-failed)]/20',
                    icon: <XCircle className="w-3.5 h-3.5" />,
                    titleText: 'OpenTofu Apply failed',
                    descText: 'Error occurred during Terraform/Tofu apply deployment.'
                };
        }
    };

    const statusConfig = getStatusConfig();
    const relativeTime = new Intl.RelativeTimeFormat('en', { numeric: 'auto' }).format(
        -Math.round((Date.now() - new Date(data.timestamp).getTime()) / 60000),
        'minutes'
    );

    return (
        <div className={className} role="article" aria-label={`Digger PR comment: ${data.title}`}>
            <Card className="p-0 overflow-hidden border border-slate-200 dark:border-slate-800 shadow-sm">
                {/* PR Comment Header */}
                <div className="bg-slate-50 dark:bg-slate-800/80 px-4 py-3 flex items-center justify-between border-b border-slate-200 dark:border-slate-800 h-[var(--size-git-comment-header-height)]">
                    <div className="flex items-center gap-3">
                        {/* Bot avatar placeholder */}
                        <div className="w-7 h-7 rounded-lg bg-orange-500/10 flex items-center justify-center border border-orange-500/20 text-orange-600 shadow-sm font-black text-xs">
                            D
                        </div>
                        <div>
                            <span className="font-extrabold text-sm text-slate-800 dark:text-slate-100">digger-bot</span>
                            <span className="ml-1.5 px-1.5 py-0.2 bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400 font-bold rounded text-[9px] uppercase tracking-wider scale-90">bot</span>
                        </div>
                        <span className="text-[10px] text-slate-400 font-semibold">• {relativeTime}</span>
                    </div>

                    <div className="flex items-center gap-2">
                        <div className={`px-2 py-0.5 rounded-full border text-[9px] font-extrabold flex items-center gap-1 uppercase select-none tracking-wider ${statusConfig.badgeStyle}`}>
                            {statusConfig.icon}
                            {statusConfig.badgeText}
                        </div>
                    </div>
                </div>

                {/* PR Comment Body */}
                <div className="p-4 space-y-4">
                    {/* Title Summary */}
                    <div className="flex justify-between items-start gap-4">
                        <div>
                            <h5 className="font-bold text-slate-800 dark:text-slate-100 text-sm flex items-center gap-2">
                                {statusConfig.titleText}
                            </h5>
                            <p className="text-xs text-slate-400 mt-0.5">{statusConfig.descText}</p>
                        </div>
                        
                        <a 
                            href={data.prUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs text-brand-primary hover:text-brand-primary-hover font-semibold flex items-center gap-1 whitespace-nowrap bg-brand-primary/5 hover:bg-brand-primary/10 border border-brand-primary/10 rounded-lg px-2.5 py-1.5 transition"
                        >
                            PR #42 <ExternalLink className="w-3 h-3" />
                        </a>
                    </div>

                    {/* Resource Metrics Pills Bar */}
                    <div className="flex gap-2 text-xs">
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-green-50 dark:bg-green-500/10 text-green-600 dark:text-green-400 font-extrabold border border-green-200/50 rounded-lg shadow-sm">
                            +{addedCount || 2} created
                        </span>
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 font-extrabold border border-slate-200/50 rounded-lg shadow-sm">
                            {changedCount || 0} modified
                        </span>
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400 font-extrabold border border-red-200/50 rounded-lg shadow-sm">
                            -{removedCount || 1} destroyed
                        </span>
                    </div>

                    {/* Accordion Collapsible Detail Block */}
                    {data.planDetails && (
                        <div className="space-y-2.5">
                            <button
                                type="button"
                                onClick={() => setShowPlanDetails(!showPlanDetails)}
                                className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 font-bold border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800 px-3 py-1.5 rounded-lg transition"
                                aria-expanded={showPlanDetails}
                                aria-controls="pr-comment-details"
                            >
                                {showPlanDetails ? (
                                    <>
                                        <ChevronUp className="w-4 h-4 text-slate-400" />
                                        Hide plan details
                                    </>
                                ) : (
                                    <>
                                        <ChevronDown className="w-4 h-4 text-slate-400" />
                                        Show plan details
                                    </>
                                )}
                            </button>

                            {showPlanDetails && (
                                <div 
                                    id="pr-comment-details"
                                    className="border border-slate-800/80 rounded-xl overflow-hidden shadow-inner font-mono text-xs max-h-72 overflow-y-auto"
                                    style={{ animation: 'git-comment-expand var(--duration-git-comment-expand) ease-out' }}
                                >
                                    <pre className="bg-[var(--color-console-bg)] p-4 text-[var(--color-console-text)] leading-relaxed select-all">
                                        <code className="block">{data.planDetails}</code>
                                    </pre>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Simulated Commit Hash Metadata Footer */}
                    <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex justify-between items-center text-[10px] text-slate-400 font-semibold font-mono">
                        <span>Commit Hash: {data.commitHash.slice(0, 7)}</span>
                        <span>Tofu Engine: v1.6.2</span>
                    </div>
                </div>

                {/* Interactive Comment Action Footer */}
                {(data.state === 'plan-succeeded' || data.state === 'apply-pending' || data.state === 'plan-failed' || data.state === 'apply-failed') && (
                    <div className="bg-slate-50 dark:bg-slate-800/40 border-t border-slate-100 dark:border-slate-800 px-4 py-3 flex items-center justify-between gap-4">
                        {/* Display message comments trigger help info */}
                        <div className="text-[10px] text-slate-400 flex items-center gap-1.5">
                            <MessageSquare className="w-3.5 h-3.5 text-brand-primary" />
                            <span>Comment <strong>"digger apply"</strong> to trigger production deploy.</span>
                        </div>

                        <div className="flex gap-2">
                            {(data.state === 'plan-succeeded' || data.state === 'apply-pending') && onApplyTrigger && (
                                <Button
                                    onClick={onApplyTrigger}
                                    className="flex items-center gap-1.5 text-xs py-1.5 font-bold uppercase tracking-wider bg-orange-600 hover:bg-orange-700 text-white"
                                    aria-label="Terraform apply trigger — click to run plan on infrastructure"
                                >
                                    <Play className="w-3.5 h-3.5" />
                                    digger apply
                                </Button>
                            )}
                            {(data.state === 'plan-failed' || data.state === 'apply-failed') && onRetryTrigger && (
                                <Button
                                    onClick={onRetryTrigger}
                                    className="flex items-center gap-1.5 text-xs py-1.5 font-bold uppercase tracking-wider bg-slate-700 hover:bg-slate-800 text-white"
                                    aria-label="Retry failed sync operation"
                                >
                                    <RefreshCw className="w-3.5 h-3.5" />
                                    Rerun Plan
                                </Button>
                            )}
                        </div>
                    </div>
                )}
            </Card>
        </div>
    );
};

export default PRCommentDisplay;
