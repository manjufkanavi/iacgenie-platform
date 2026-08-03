import React, { useState, useMemo } from 'react';
import { PlusCircle, Pencil, Trash2, ChevronDown, ChevronRight, AlertTriangle } from 'lucide-react';
import Card from '../ui/Card';
import type { DiffResource } from './DiffPanel';

interface ResourceImpactSummaryProps {
  resources: DiffResource[];
  showCostImpact?: boolean;
  onResourceSelect?: (address: string) => void;
  totalCount?: number;
  hasPermission?: boolean;
  className?: string;
}

export const ResourceImpactSummary: React.FC<ResourceImpactSummaryProps> = ({
  resources,
  showCostImpact = true,
  onResourceSelect,
  totalCount,
  hasPermission = true,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [showCostBreakdown, setShowCostBreakdown] = useState(false);
  const [activeColumn, setActiveColumn] = useState<'create' | 'update' | 'destroy' | null>(null);

  const createResources = useMemo(() => resources.filter(r => r.action === 'create'), [resources]);
  const updateResources = useMemo(() => resources.filter(r => r.action === 'update'), [resources]);
  const destroyResources = useMemo(() => resources.filter(r => r.action === 'destroy'), [resources]);

  const totalCostDelta = useMemo(() => {
    return resources.reduce((sum, r) => sum + (r.costDelta || 0), 0);
  }, [resources]);

  const formatCostText = (delta: number) => {
    const sign = delta >= 0 ? '+' : '';
    return `${sign}$${delta.toFixed(2)}/mo`;
  };

  const getCostColorClass = (delta: number) => {
    if (delta > 0) return 'text-[var(--color-impact-cost-positive)]';
    if (delta < 0) return 'text-[var(--color-impact-cost-negative)]';
    return 'text-[var(--color-impact-cost-neutral)]';
  };

  const columnCount = totalCount !== undefined ? totalCount : resources.length;

  return (
    <Card padding="none" className={`overflow-hidden border border-slate-200 dark:border-slate-800 shadow-md ${className}`}>
      {/* Header section */}
      <div 
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between px-5 py-4 bg-gray-50 dark:bg-slate-800/30 border-b border-gray-150 dark:border-slate-800 select-none cursor-pointer"
      >
        <div>
          <h3 className="text-sm font-bold text-gray-800 dark:text-slate-200">
            Deployment Impact
          </h3>
          <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
            Planned infrastructure state modifications ({columnCount} changes)
          </p>
        </div>
        <button
          aria-label={isExpanded ? 'Collapse section' : 'Expand section'}
          className="p-1 hover:bg-gray-200 dark:hover:bg-slate-700/50 rounded-lg transition"
        >
          <ChevronDown className={`w-4 h-4 text-gray-500 dark:text-slate-400 transition-transform duration-200 ${isExpanded ? '' : '-rotate-90'}`} />
        </button>
      </div>

      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* Summary Grid Columns */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            
            {/* Create Column */}
            <div 
              className="border border-green-100 dark:border-green-950/40 rounded-xl overflow-hidden bg-[var(--color-impact-create-bg)] transition-all duration-200 hover:shadow-md hover:-translate-y-0.5"
            >
              <div className="px-4 py-3 border-b border-green-150 dark:border-green-900/40 flex items-center justify-between">
                <h4 className="text-xs font-bold text-[var(--color-impact-create-text)] uppercase tracking-wider flex items-center gap-1.5">
                  <PlusCircle className="w-4 h-4 text-[var(--color-impact-create-text)]" />
                  Create ({createResources.length})
                </h4>
                {createResources.length > 0 && (
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveColumn(activeColumn === 'create' ? null : 'create');
                    }}
                    className="text-[10px] font-extrabold text-[var(--color-impact-create-text)] hover:underline"
                  >
                    {activeColumn === 'create' ? 'Hide' : 'View'}
                  </button>
                )}
              </div>
              <div className="p-3 space-y-2 max-h-36 overflow-y-auto">
                {createResources.length === 0 ? (
                  <div className="text-[11px] text-[var(--color-text-muted)] italic py-2 text-center select-none">
                    No resources to create
                  </div>
                ) : (
                  createResources.slice(0, activeColumn === 'create' ? undefined : 3).map((res) => (
                    <button
                      key={res.address}
                      onClick={() => onResourceSelect?.(res.address)}
                      className="w-full flex flex-col items-start text-left p-2 rounded-lg bg-white dark:bg-slate-900/60 border border-green-50 dark:border-green-950 hover:border-green-300 dark:hover:border-green-800 transition"
                      aria-label={`View details for ${res.address}`}
                    >
                      <span className="text-[11px] font-bold text-gray-800 dark:text-slate-200 truncate w-full">{res.type}</span>
                      <span className="text-[10px] text-gray-500 dark:text-slate-400 font-mono truncate w-full">"{res.name}"</span>
                    </button>
                  ))
                )}
              </div>
            </div>

            {/* Update Column */}
            <div 
              className="border border-blue-100 dark:border-blue-950/40 rounded-xl overflow-hidden bg-[var(--color-impact-update-bg)] transition-all duration-200 hover:shadow-md hover:-translate-y-0.5"
            >
              <div className="px-4 py-3 border-b border-blue-150 dark:border-blue-900/40 flex items-center justify-between">
                <h4 className="text-xs font-bold text-[var(--color-impact-update-text)] uppercase tracking-wider flex items-center gap-1.5">
                  <Pencil className="w-4 h-4 text-[var(--color-impact-update-text)]" />
                  Update ({updateResources.length})
                </h4>
                {updateResources.length > 0 && (
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveColumn(activeColumn === 'update' ? null : 'update');
                    }}
                    className="text-[10px] font-extrabold text-[var(--color-impact-update-text)] hover:underline"
                  >
                    {activeColumn === 'update' ? 'Hide' : 'View'}
                  </button>
                )}
              </div>
              <div className="p-3 space-y-2 max-h-36 overflow-y-auto">
                {updateResources.length === 0 ? (
                  <div className="text-[11px] text-[var(--color-text-muted)] italic py-2 text-center select-none">
                    No resources to update
                  </div>
                ) : (
                  updateResources.slice(0, activeColumn === 'update' ? undefined : 3).map((res) => (
                    <button
                      key={res.address}
                      onClick={() => onResourceSelect?.(res.address)}
                      className="w-full flex flex-col items-start text-left p-2 rounded-lg bg-white dark:bg-slate-900/60 border border-blue-50 dark:border-blue-950 hover:border-blue-300 dark:hover:border-blue-800 transition"
                      aria-label={`View details for ${res.address}`}
                    >
                      <span className="text-[11px] font-bold text-gray-800 dark:text-slate-200 truncate w-full">{res.type}</span>
                      <span className="text-[10px] text-gray-500 dark:text-slate-400 font-mono truncate w-full">"{res.name}"</span>
                    </button>
                  ))
                )}
              </div>
            </div>

            {/* Destroy Column */}
            <div 
              className="border border-red-100 dark:border-red-950/40 rounded-xl overflow-hidden bg-[var(--color-impact-destroy-bg)] transition-all duration-200 hover:shadow-md hover:-translate-y-0.5"
            >
              <div className="px-4 py-3 border-b border-red-150 dark:border-red-900/40 flex items-center justify-between">
                <h4 className="text-xs font-bold text-[var(--color-impact-destroy-text)] uppercase tracking-wider flex items-center gap-1.5">
                  <Trash2 className="w-4 h-4 text-[var(--color-impact-destroy-text)]" />
                  Destroy ({destroyResources.length})
                </h4>
                {destroyResources.length > 0 && (
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveColumn(activeColumn === 'destroy' ? null : 'destroy');
                    }}
                    className="text-[10px] font-extrabold text-[var(--color-impact-destroy-text)] hover:underline"
                  >
                    {activeColumn === 'destroy' ? 'Hide' : 'View'}
                  </button>
                )}
              </div>
              <div className="p-3 space-y-2 max-h-36 overflow-y-auto">
                {destroyResources.length === 0 ? (
                  <div className="text-[11px] text-[var(--color-text-muted)] italic py-2 text-center select-none">
                    No resources to destroy
                  </div>
                ) : (
                  destroyResources.slice(0, activeColumn === 'destroy' ? undefined : 3).map((res) => (
                    <button
                      key={res.address}
                      onClick={() => onResourceSelect?.(res.address)}
                      className="w-full flex flex-col items-start text-left p-2 rounded-lg bg-white dark:bg-slate-900/60 border border-red-50 dark:border-red-950 hover:border-red-300 dark:hover:border-red-800 transition"
                      aria-label={`View details for ${res.address}`}
                    >
                      <span className="text-[11px] font-bold text-gray-800 dark:text-slate-200 truncate w-full">{res.type}</span>
                      <span className="text-[10px] text-gray-500 dark:text-slate-400 font-mono truncate w-full">"{res.name}"</span>
                    </button>
                  ))
                )}
              </div>
            </div>

          </div>

          {/* Monthly Cost Impact Summary Row */}
          {showCostImpact && resources.length > 0 && (
            <div className="border-t border-gray-100 dark:border-slate-800 pt-4 flex flex-col gap-3">
              <div className="flex items-center justify-between bg-slate-50 dark:bg-slate-900/40 border border-slate-100 dark:border-slate-800 rounded-xl p-3.5">
                <span className="text-xs font-semibold text-gray-600 dark:text-slate-300 flex items-center gap-1.5">
                  <span className="text-base select-none">💰</span>
                  Monthly Cost Impact:
                  <strong className={`text-sm ${getCostColorClass(totalCostDelta)}`}>
                    {formatCostText(totalCostDelta)}
                  </strong>
                </span>

                <button
                  onClick={() => setShowCostBreakdown(!showCostBreakdown)}
                  className="text-xs font-bold text-[var(--color-brand-primary)] hover:underline flex items-center gap-0.5"
                >
                  {showCostBreakdown ? 'Hide Details' : 'Details'}
                  <ChevronRight className={`w-3.5 h-3.5 transition-transform ${showCostBreakdown ? 'rotate-90' : ''}`} />
                </button>
              </div>

              {/* Cost breakdown breakdown */}
              {showCostBreakdown && (
                <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden animate-[console-log-enter_150ms_ease-out]">
                  <table className="w-full text-left text-xs font-mono select-text" role="table" aria-label="Monthly Cost Breakdown Details">
                    <thead>
                      <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 text-[10px] font-bold uppercase tracking-widest">
                        <th className="px-4 py-2">Resource Address</th>
                        <th className="px-4 py-2">Details</th>
                        <th className="px-4 py-2 text-right">Cost Delta</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-900 text-slate-300">
                      {resources.map((res) => {
                        const cost = res.costDelta || 0;
                        const isDestroyed = res.action === 'destroy';
                        return (
                          <tr key={res.address} className="hover:bg-slate-900/40 transition">
                            <td className="px-4 py-2 text-slate-400 font-semibold">{res.address}</td>
                            <td className="px-4 py-2 text-[10px]">
                              {isDestroyed ? (
                                <span className="text-[var(--color-impact-destroy-text)] font-semibold uppercase tracking-wider">Destroyed</span>
                              ) : (
                                <span className="text-slate-500">{res.type} ({res.action})</span>
                              )}
                            </td>
                            <td className={`px-4 py-2 text-right font-bold ${getCostColorClass(cost)}`}>
                              {cost === 0 ? '$0.00/mo' : formatCostText(cost)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* RBAC Insufficient Permissions Warning Banner */}
          {!hasPermission && (
            <div 
              className="bg-[var(--color-permission-banner-bg)] border border-[var(--color-severity-warning)] rounded-xl p-3 flex items-center gap-3 animate-[console-log-enter_150ms_ease-out]"
              role="alert"
            >
              <AlertTriangle className="w-5 h-5 text-[var(--color-permission-banner-text)] shrink-0" />
              <div className="text-xs font-semibold text-[var(--color-permission-banner-text)]">
                Cannot deploy: insufficient permissions. Only owners or administrators can execute apply steps on this workspace.
              </div>
            </div>
          )}

        </div>
      )}
    </Card>
  );
};

export default ResourceImpactSummary;
