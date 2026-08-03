import React, { useState, useMemo } from 'react';
import { PlusCircle, Pencil, Trash2, ChevronDown, ChevronRight } from 'lucide-react';

// ============================================================
// Types (aligned with types.ts DiffResource)
// ============================================================

export interface DiffResource {
  address: string; // e.g., 'aws_security_group.web'
  type: string;    // e.g., 'aws_security_group'
  name: string;    // e.g., 'web'
  action: 'create' | 'update' | 'destroy';
  provider: string; // e.g., 'aws'
  changes?: Record<string, { old?: unknown; new?: unknown }>;
  costDelta?: number; // monthly cost change in USD
}

export type DiffViewMode = 'summary' | 'side-by-side' | 'inline';

export interface DiffPanelProps {
  resources: DiffResource[];
  effectiveViewMode?: DiffViewMode; // default 'summary'
  selectedResource?: string;
  onResourceSelect?: (path: string) => void;
  showCostImpact?: boolean; // default false
  className?: string;
}

// ============================================================
// Helpers
// ============================================================

function getActionIcon(action: DiffResource['action']): React.ReactNode {
  switch (action) {
    case 'create': return <PlusCircle className="w-3.5 h-3.5 text-green-500" />;
    case 'update': return <Pencil className="w-3.5 h-3.5 text-blue-500" />;
    case 'destroy': return <Trash2 className="w-3.5 h-3.5 text-red-500" />;
  }
}

function formatCost(delta: number): string {
  const sign = delta >= 0 ? '+' : '';
  return `${sign}$${delta.toFixed(0)}/mo`;
}

// ============================================================
// Summary View Component
// ============================================================

interface SummaryViewProps {
  resources: DiffResource[];
  selectedResource?: string;
  onResourceSelect?: (path: string) => void;
  showCostImpact?: boolean;
}

function SummaryView({ resources, selectedResource, onResourceSelect, showCostImpact }: SummaryViewProps): React.ReactElement {
  const createResources = resources.filter(r => r.action === 'create');
  const updateResources = resources.filter(r => r.action === 'update');
  const destroyResources = resources.filter(r => r.action === 'destroy');
  
  const totalCostDelta = useMemo(() => {
    return resources.reduce((sum, r) => sum + (r.costDelta || 0), 0);
  }, [resources]);

  return (
    <div>
      {/* Summary Header */}
      <div className="flex flex-wrap items-center gap-3 px-4 py-3 bg-gray-50 dark:bg-slate-800/50 border-b border-gray-200 dark:border-slate-700">
        <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
          <span className="text-green-500 font-bold">{createResources.length}</span> to create
          <span className="mx-2 text-gray-300 dark:text-slate-600">·</span>
          <span className="text-blue-500 font-bold">{updateResources.length}</span> to update
          <span className="mx-2 text-gray-300 dark:text-slate-600">·</span>
          <span className="text-red-500 font-bold">{destroyResources.length}</span> to destroy
        </span>
        
        {showCostImpact && (
          <>
            <span className="mx-2 text-gray-300 dark:text-slate-600">·</span>
            <span className={`text-sm font-medium ${totalCostDelta >= 0 ? 'text-amber-600 dark:text-amber-400' : 'text-green-600 dark:text-green-400'}`}>
              {totalCostDelta >= 0 ? '↑' : '↓'} {formatCost(Math.abs(totalCostDelta))}
            </span>
          </>
        )}
      </div>

      {/* Summary Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4">
        {/* Create Column */}
        <div className="border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden">
          <div className="bg-green-50 dark:bg-green-950/30 px-4 py-2.5 border-b border-green-200 dark:border-green-900">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100 flex items-center gap-2">
              <PlusCircle className="w-4 h-4 text-green-500" />
              To Create ({createResources.length})
            </h3>
          </div>
          <div className="p-3 space-y-1.5 max-h-48 overflow-y-auto">
            {createResources.length === 0 ? (
              <p className="text-xs text-gray-400 dark:text-slate-500 text-center py-4">None</p>
            ) : (
              createResources.map((resource) => (
                <button
                  key={resource.address}
                  onClick={() => onResourceSelect?.(resource.address)}
                  className={`w-full flex items-start gap-2 text-sm p-2 rounded transition-colors text-left ${
                    selectedResource === resource.address
                      ? 'bg-green-50 dark:bg-green-950/30 ring-1 ring-green-200 dark:ring-green-800'
                      : 'hover:bg-gray-50 dark:hover:bg-slate-700/50'
                  }`}
                >
                  <PlusCircle className="w-3.5 h-3.5 text-green-500 mt-0.5 flex-shrink-0" />
                  <div>
                    <strong className="text-gray-900 dark:text-slate-100">{resource.type}</strong>
                    <span className="text-gray-500 dark:text-slate-400">"{resource.name}"</span>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Update Column */}
        <div className="border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden">
          <div className="bg-blue-50 dark:bg-blue-950/30 px-4 py-2.5 border-b border-blue-200 dark:border-blue-900">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100 flex items-center gap-2">
              <Pencil className="w-4 h-4 text-blue-500" />
              To Update ({updateResources.length})
            </h3>
          </div>
          <div className="p-3 space-y-1.5 max-h-48 overflow-y-auto">
            {updateResources.length === 0 ? (
              <p className="text-xs text-gray-400 dark:text-slate-500 text-center py-4">None</p>
            ) : (
              updateResources.map((resource) => (
                <button
                  key={resource.address}
                  onClick={() => onResourceSelect?.(resource.address)}
                  className={`w-full flex items-start gap-2 text-sm p-2 rounded transition-colors text-left ${
                    selectedResource === resource.address
                      ? 'bg-blue-50 dark:bg-blue-950/30 ring-1 ring-blue-200 dark:ring-blue-800'
                      : 'hover:bg-gray-50 dark:hover:bg-slate-700/50'
                  }`}
                >
                  <Pencil className="w-3.5 h-3.5 text-blue-500 mt-0.5 flex-shrink-0" />
                  <div>
                    <strong className="text-gray-900 dark:text-slate-100">{resource.type}</strong>
                    <span className="text-gray-500 dark:text-slate-400">"{resource.name}"</span>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Destroy Column */}
        <div className="border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden">
          <div className="bg-red-50 dark:bg-red-950/30 px-4 py-2.5 border-b border-red-200 dark:border-red-900">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100 flex items-center gap-2">
              <Trash2 className="w-4 h-4 text-red-500" />
              To Destroy ({destroyResources.length})
            </h3>
          </div>
          <div className="p-3 space-y-1.5 max-h-48 overflow-y-auto">
            {destroyResources.length === 0 ? (
              <p className="text-xs text-gray-400 dark:text-slate-500 text-center py-4">None</p>
            ) : (
              destroyResources.map((resource) => (
                <button
                  key={resource.address}
                  onClick={() => onResourceSelect?.(resource.address)}
                  className={`w-full flex items-start gap-2 text-sm p-2 rounded transition-colors text-left ${
                    selectedResource === resource.address
                      ? 'bg-red-50 dark:bg-red-950/30 ring-1 ring-red-200 dark:ring-red-800'
                      : 'hover:bg-gray-50 dark:hover:bg-slate-700/50'
                  }`}
                >
                  <Trash2 className="w-3.5 h-3.5 text-red-500 mt-0.5 flex-shrink-0" />
                  <div>
                    <strong className="text-gray-900 dark:text-slate-100">{resource.type}</strong>
                    <span className="text-gray-500 dark:text-slate-400">"{resource.name}"</span>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Cost Impact Summary */}
      {showCostImpact && totalCostDelta !== 0 && (
        <div className="mx-4 mb-4 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
          <p className="text-xs font-medium text-amber-700 dark:text-amber-400 mb-2">
            <span className="inline-block w-3 h-3 mr-1">💰</span>
            Cost Impact
          </p>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-500 dark:text-slate-400 text-xs">Current:</span>
              <p className="font-medium text-gray-900 dark:text-slate-100">$180/mo</p>
            </div>
            <div>
              <span className="text-gray-500 dark:text-slate-400 text-xs">New:</span>
              <p className="font-medium text-gray-900 dark:text-slate-100">${Math.max(0, 180 + totalCostDelta)}/mo</p>
            </div>
            <div>
              <span className="text-gray-500 dark:text-slate-400 text-xs">Δ:</span>
              <p className={`font-medium ${totalCostDelta >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                {totalCostDelta >= 0 ? '↑' : '↓'} {formatCost(Math.abs(totalCostDelta))}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// Side-by-Side Diff View Component
// ============================================================

interface SideBySideViewProps {
  resource: DiffResource;
}

function SideBySideView({ resource }: SideBySideViewProps): React.ReactElement {
  const changes = resource.changes || {};
  const changeKeys = Object.keys(changes);

  if (changeKeys.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-500 dark:text-slate-400">
        No detailed changes available for this resource.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono" role="table" aria-label={`Changes for ${resource.address}`}>
        <thead>
          <tr className="border-b border-gray-200 dark:border-slate-700">
            <th className="px-4 py-2 text-left text-gray-500 dark:text-slate-400 font-medium w-[50%]">
              <span className="text-red-400">−</span> Expected
            </th>
            <th className="px-4 py-2 text-left text-gray-500 dark:text-slate-400 font-medium w-[50%]">
              <span className="text-green-400">+</span> New
            </th>
          </tr>
        </thead>
        <tbody>
          {changeKeys.map((key) => {
            const change = changes[key];
            const hasOld = change.old !== undefined;
            const hasNew = change.new !== undefined;

            return (
              <tr key={key} className="border-b border-gray-100 dark:border-slate-700/50">
                <td className={`px-4 py-1.5 ${hasOld ? '' : 'text-gray-300 dark:text-slate-600'}`}>
                  {hasOld ? (
                    <>
                      <span className="text-red-400">  -</span> <span className="text-red-400">{JSON.stringify(change.old)}</span>
                    </>
                  ) : (
                    <span className="text-gray-300 dark:text-slate-600">  ·</span>
                  )}
                </td>
                <td className={`px-4 py-1.5 ${hasNew ? '' : 'text-gray-300 dark:text-slate-600'}`}>
                  {hasNew ? (
                    <>
                      <span className="text-green-400">  +</span> <span className="text-green-400">{JSON.stringify(change.new)}</span>
                    </>
                  ) : (
                    <span className="text-gray-300 dark:text-slate-600">  ·</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ============================================================
// Inline Diff View Component
// ============================================================

function InlineDiffView({ resource }: SideBySideViewProps): React.ReactElement {
  const changes = resource.changes || {};
  const changeKeys = Object.keys(changes);

  if (changeKeys.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-500 dark:text-slate-400">
        No detailed changes available for this resource.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono" role="table" aria-label={`Inline diff for ${resource.address}`}>
        <thead>
          <tr className="border-b border-gray-200 dark:border-slate-700">
            <th className="px-4 py-2 text-left text-gray-500 dark:text-slate-400 font-medium">
              Change
            </th>
          </tr>
        </thead>
        <tbody>
          {changeKeys.map((key) => {
            const change = changes[key];
            const hasOld = change.old !== undefined;
            const hasNew = change.new !== undefined;

            return (
              <tr key={key} className="border-b border-gray-100 dark:border-slate-700/50">
                <td className="px-4 py-1.5">
                  {hasOld && hasNew ? (
                    <div>
                      <span className="text-red-400">  -{key}: {JSON.stringify(change.old)}</span>
                      <br />
                      <span className="text-green-400">  +{key}: {JSON.stringify(change.new)}</span>
                    </div>
                  ) : hasOld ? (
                    <span className="text-red-400">  -{key}: {JSON.stringify(change.old)}</span>
                  ) : (
                    <span className="text-green-400">  +{key}: {JSON.stringify(change.new)}</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ============================================================
// Main DiffPanel Component
// ============================================================

const DiffPanel: React.FC<DiffPanelProps> = ({
  resources,
  effectiveViewMode: _effectiveViewMode,
  selectedResource,
  onResourceSelect,
  showCostImpact = false,
  className = '',
}) => {
  const effectiveViewMode = _effectiveViewMode ?? 'summary';
  const [expandedResources, setExpandedResources] = useState<Set<string>>(new Set());

  const toggleExpand = (address: string) => {
    setExpandedResources(prev => {
      const next = new Set(prev);
      if (next.has(address)) next.delete(address);
      else next.add(address);
      return next;
    });
  };

  const selectedResourceData = useMemo(() => {
    if (!selectedResource) return null;
    return resources.find(r => r.address === selectedResource);
  }, [resources, selectedResource]);

  return (
    <div className={`border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden ${className}`} role="table" aria-label="Infrastructure plan diff">
      {/* Summary View */}
      <SummaryView
        resources={resources}
        selectedResource={selectedResource}
        onResourceSelect={onResourceSelect}
        showCostImpact={showCostImpact}
      />

      {/* Expanded Detail View */}
      {selectedResourceData && (
        <div className="border-t border-gray-200 dark:border-slate-700">
          {/* Resource Header */}
          <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 dark:bg-slate-800/50 border-b border-gray-200 dark:border-slate-700">
            <div className="flex items-center gap-2 text-sm">
              {getActionIcon(selectedResourceData.action)}
              <span className="font-medium text-gray-900 dark:text-slate-100">
                {selectedResourceData.type}.{selectedResourceData.name}
              </span>
              <span className="text-xs text-gray-500 dark:text-slate-400">
                ({selectedResourceData.provider})
              </span>
            </div>
            <button
              onClick={() => toggleExpand(selectedResourceData.address)}
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 rounded"
              aria-label="Collapse detail view"
            >
              <ChevronDown className="w-4 h-4" />
            </button>
          </div>

          {/* Diff Content */}
          {effectiveViewMode === 'side-by-side' ? (
            <SideBySideView resource={selectedResourceData} />
          ) : effectiveViewMode === 'inline' ? (
            <InlineDiffView resource={selectedResourceData} />
          ) : (
            <SideBySideView resource={selectedResourceData} />
          )}
        </div>
      )}

      {/* Expandable resource rows (optional detail below summary) */}
      {resources.length > 0 && effectiveViewMode === 'summary' && (
        <div className="border-t border-gray-200 dark:border-slate-700">
          {resources.map((resource) => {
            const isExpanded = expandedResources.has(resource.address);
            
            return (
              <div key={resource.address}>
                <button
                  onClick={() => {
                    onResourceSelect?.(resource.address);
                    toggleExpand(resource.address);
                  }}
                  className={`w-full flex items-center justify-between px-4 py-2 text-sm hover:bg-gray-50 dark:hover:bg-slate-700/30 transition-colors text-left ${
                    isExpanded ? 'bg-gray-50 dark:bg-slate-800/30' : ''
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {getActionIcon(resource.action)}
                    <span className="font-medium text-gray-900 dark:text-slate-100">
                      {resource.type}.{resource.name}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {resource.costDelta !== undefined && (
                      <span className={`text-xs ${resource.costDelta >= 0 ? 'text-amber-600 dark:text-amber-400' : 'text-green-600 dark:text-green-400'}`}>
                        {formatCost(resource.costDelta)}
                      </span>
                    )}
                    {isExpanded ? (
                      <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
                    )}
                  </div>
                </button>

                {isExpanded && resource.changes && Object.keys(resource.changes).length > 0 && (
                  <div className="px-4 pb-3">
                    <div className="bg-gray-50 dark:bg-slate-800/30 rounded-lg border border-gray-200 dark:border-slate-700 overflow-hidden">
                      {effectiveViewMode === ('inline' as DiffViewMode) ? (
                        <InlineDiffView resource={resource} />
                      ) : (
                        <SideBySideView resource={resource} />
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export { DiffPanel };