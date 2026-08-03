import React from 'react';
import { PlayCircle, ShieldCheck, X, Loader2, Check } from 'lucide-react';
import Card from '../ui/Card';

interface DeploymentActionBarProps {
  state: 'idle' | 'planning' | 'applying' | 'complete' | 'error' | 'cancelled';
  onPlan?: () => void;
  onDeploy?: () => void;
  onCancel?: () => void;
  hasPermission?: boolean;
  className?: string;
}

export const DeploymentActionBar: React.FC<DeploymentActionBarProps> = ({
  state,
  onPlan,
  onDeploy,
  onCancel,
  hasPermission = true,
  className = '',
}) => {
  const isPlanning = state === 'planning';
  const isApplying = state === 'applying';
  const isRunning = isPlanning || isApplying;

  // Plan Button state
  const isPlanDisabled = isRunning || state === 'complete' || state === 'cancelled';
  // Deploy Button state
  const isDeployDisabled = isRunning || state === 'complete' || state === 'cancelled' || !hasPermission;

  return (
    <Card 
      padding="lg" 
      className={`border border-slate-200 dark:border-slate-800 shadow-md bg-white dark:bg-slate-900 ${className}`}
    >
      <div 
        className="flex flex-col md:flex-row md:items-center justify-between gap-4"
        role="toolbar"
        aria-label="Deployment actions"
      >
        {/* State Information */}
        <div className="select-none">
          <h4 className="text-xs font-black uppercase tracking-widest text-slate-400">
            Deployment Orchestration
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-0.5">
            {isPlanning && 'Currently running a dry-run plan. Evaluating infrastructure differences.'}
            {isApplying && 'Currently applying changes. Deploying to selected cloud provider.'}
            {state === 'idle' && 'Select dry-run plan to verify changes or deploy changes directly.'}
            {state === 'complete' && 'Deployment phase completed successfully.'}
            {state === 'error' && 'Execution failed. Review plan logs for details.'}
            {state === 'cancelled' && 'Subprocess execution aborted by user.'}
          </p>
        </div>

        {/* Buttons Toolbar */}
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          
          {/* Plan Button */}
          <button
            onClick={onPlan}
            disabled={isPlanDisabled}
            className={`flex items-center justify-center gap-2 px-4 py-2 text-xs font-bold border rounded-xl select-none transition-all duration-200 cursor-pointer ${
              isPlanning
                ? 'border-[var(--color-exec-planning)] text-[var(--color-exec-planning)] bg-orange-50/20 dark:bg-orange-950/20 cursor-wait'
                : state === 'complete'
                ? 'border-green-300 bg-green-50 text-green-700 dark:bg-green-950/20 dark:border-green-800 dark:text-green-400 cursor-not-allowed'
                : isPlanDisabled
                ? 'bg-[var(--color-action-disabled-bg)] text-[var(--color-action-disabled-text)] border-slate-200 dark:border-slate-700 cursor-not-allowed'
                : 'border-[var(--color-action-plan-border)] text-[var(--color-action-plan-text)] hover:bg-[var(--color-action-plan-hover)] bg-transparent'
            }`}
            aria-busy={isPlanning ? 'true' : 'false'}
            aria-disabled={isPlanDisabled}
          >
            {isPlanning ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-[var(--color-exec-planning)]" />
                Planning...
              </>
            ) : state === 'complete' ? (
              <>
                <Check className="w-4 h-4 text-green-500" />
                Plan Completed
              </>
            ) : (
              <>
                <PlayCircle className="w-4 h-4" />
                Run Dry-Run Plan
              </>
            )}
          </button>

          {/* Deploy Button */}
          <div className="relative group w-full sm:w-auto">
            <button
              onClick={onDeploy}
              disabled={isDeployDisabled}
              className={`w-full flex items-center justify-center gap-2 px-4 py-2 text-xs font-bold rounded-xl select-none transition-all duration-200 cursor-pointer ${
                isApplying
                  ? 'bg-[var(--color-exec-applying)] text-white cursor-wait opacity-80'
                  : isDeployDisabled
                  ? 'bg-[var(--color-action-disabled-bg)] text-[var(--color-action-disabled-text)] border border-slate-200 dark:border-slate-700 cursor-not-allowed'
                  : 'bg-[var(--color-action-deploy-bg)] text-[var(--color-action-deploy-text)] hover:bg-[var(--color-action-deploy-hover)]'
              }`}
              aria-busy={isApplying ? 'true' : 'false'}
              aria-disabled={isDeployDisabled}
            >
              {isApplying ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Applying...
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  Deploy Infrastructure
                </>
              )}
            </button>
            
            {/* RBAC Tooltip Hover Overlay */}
            {!hasPermission && (
              <div 
                className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 bg-slate-900 border border-slate-800 text-[10px] text-amber-400 font-bold p-2 rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition duration-150 text-center select-none z-[100]"
                role="tooltip"
              >
                Cannot deploy: insufficient permissions
              </div>
            )}
          </div>

          {/* Cancel Button */}
          {isRunning && (
            <button
              onClick={onCancel}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold text-gray-500 hover:text-red-500 dark:text-slate-400 dark:hover:text-red-400 bg-transparent hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition duration-200 cursor-pointer"
              aria-label="Cancel running execution"
            >
              <X className="w-4 h-4" />
              Cancel Execution
            </button>
          )}

        </div>
      </div>
    </Card>
  );
};

export default DeploymentActionBar;
