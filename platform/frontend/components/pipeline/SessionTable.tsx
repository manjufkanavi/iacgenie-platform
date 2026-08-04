import React, { useState, useMemo } from 'react';
import { ChevronUp, ChevronDown, ChevronLeft, ChevronRight, MoreHorizontal } from 'lucide-react';
import PhaseStatusBadge from './PhaseStatusBadge';
import type { PhaseStatus } from './types';

// ============================================================
// Types (aligned with types.ts PipelineSession)
// ============================================================

export type SessionStatus = 'active' | 'completed' | 'failed' | 'escalated' | 'aborted';

export interface Session {
  id: string;
  name: string;
  status: SessionStatus;
  currentPhase: string;
  duration?: number; // seconds
  createdAt: string; // ISO timestamp
}

export interface Pagination {
  page: number;
  totalPages: number;
  totalItems: number;
  itemsPerPage?: number; // default 20
}

export type SortField = 'name' | 'status' | 'createdAt' | 'duration';
export type SortDirection = 'asc' | 'desc';

export interface SessionTableProps {
  sessions: Session[];
  selectedIds?: string[];
  onSelect?: (id: string, multi?: boolean) => void;
  onSelectAll?: (selected: boolean) => void;
  sortField?: SortField;
  sortDirection?: SortDirection;
  onSort?: (field: SortField) => void;
  pagination?: Pagination;
  onPageChange?: (page: number) => void;
  loading?: boolean;
  emptyMessage?: string;
  onSessionClick?: (session: Session) => void;
  className?: string;
}

// ============================================================
// Helpers
// ============================================================

function formatDuration(seconds: number): string {
  if (!seconds || seconds < 0) return '--';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function formatRelativeTime(isoString: string): string {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffMs = now - then;
  if (diffMs < 0) return isoString.slice(0, 10);
  
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 7) return `${diffDay}d ago`;
  
  // > 7 days: show ISO date
  return isoString.slice(0, 10);
}

function getStatusLabel(status: SessionStatus): PhaseStatus {
  switch (status) {
    case 'active': return 'running';
    case 'completed': return 'success';
    case 'failed': return 'failed';
    case 'escalated': return 'escalated';
    case 'aborted': return 'pending';
    default: return 'pending';
  }
}

function getRowBorderClass(status: SessionStatus): string {
  switch (status) {
    case 'active': return 'border-l-3 border-blue-500 bg-blue-50/50 dark:bg-slate-700';
    case 'failed': return 'border-l-3 border-red-500';
    case 'escalated': return 'border-l-3 border-amber-500';
    default: return '';
  }
}

// ============================================================
// Skeleton Loader
// ============================================================

function SkeletonRow(): React.ReactElement {
  return (
    <tr className="animate-pulse">
      <td className="px-4 py-3 w-10"><div className="w-4 h-4 bg-gray-200 dark:bg-slate-600 rounded" /></td>
      <td className="px-4 py-3"><div className="h-4 bg-gray-200 dark:bg-slate-600 rounded w-3/4" /></td>
      <td className="px-4 py-3"><div className="h-5 bg-gray-200 dark:bg-slate-600 rounded w-16" /></td>
      <td className="px-4 py-3"><div className="h-4 bg-gray-200 dark:bg-slate-600 rounded w-12" /></td>
      <td className="px-4 py-3"><div className="h-4 bg-gray-200 dark:bg-slate-600 rounded w-10" /></td>
      <td className="px-4 py-3"><div className="h-4 bg-gray-200 dark:bg-slate-600 rounded w-16" /></td>
    </tr>
  );
}

// ============================================================
// Empty State Card
// ============================================================

interface EmptyStateProps {
  message?: string;
  onAction?: () => void;
}

function EmptyState({ message, onAction }: EmptyStateProps): React.ReactElement {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="w-12 h-12 mb-4 text-gray-300 dark:text-slate-500">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-full h-full">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <line x1="9" y1="9" x2="15" y2="15" />
          <line x1="15" y1="9" x2="9" y2="15" />
        </svg>
      </div>
      <p className="text-sm font-medium text-gray-600 dark:text-slate-400 mb-1">No pipelines found</p>
      <p className="text-xs text-gray-400 dark:text-slate-500 mb-4 text-center max-w-xs">
        {message || 'Try adjusting your filters or create a new pipeline to get started.'}
      </p>
      {onAction && (
        <button
          onClick={onAction}
          className="px-4 py-2 bg-brand-primary text-white rounded-lg text-xs font-medium hover:bg-brand-primary/90 transition-colors"
        >
          + New Pipeline
        </button>
      )}
    </div>
  );
}

// ============================================================
// Smart Pagination Component
// ============================================================

interface SmartPaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

function SmartPagination({ page, totalPages, onPageChange }: SmartPaginationProps): React.ReactElement | null {
  if (totalPages <= 1) return null;

  const pages: (number | 'ellipsis')[] = [];
  
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (page > 3) pages.push('ellipsis');
    
    const start = Math.max(2, page - 1);
    const end = Math.min(totalPages - 1, page + 1);
    for (let i = start; i <= end; i++) pages.push(i);
    
    if (page < totalPages - 2) pages.push('ellipsis');
    pages.push(totalPages);
  }

  return (
    <div className="flex items-center gap-1" role="navigation" aria-label="Pagination">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        className="p-1.5 rounded text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
        aria-label="Previous page"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>
      
      {pages.map((p, idx) =>
        p === 'ellipsis' ? (
          <span key={`e-${idx}`} className="px-2 text-xs text-gray-400">...</span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(p)}
            className={`w-8 h-8 rounded text-xs font-medium transition-colors ${
              p === page
                ? 'bg-brand-primary text-white'
                : 'text-gray-600 hover:bg-gray-100 dark:text-slate-300 dark:hover:bg-slate-700'
            }`}
            aria-current={p === page ? 'page' : undefined}
          >
            {p}
          </button>
        )
      )}
      
      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        className="p-1.5 rounded text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
        aria-label="Next page"
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  );
}

// ============================================================
// Main SessionTable Component
// ============================================================

const SessionTable: React.FC<SessionTableProps> = ({
  sessions,
  selectedIds = [],
  onSelect,
  onSelectAll,
  sortField = 'createdAt',
  sortDirection = 'desc',
  onSort,
  pagination,
  onPageChange,
  loading = false,
  emptyMessage,
  onSessionClick,
  className = '',
}) => {
  const [sortFieldState, setSortFieldState] = useState<SortField>(sortField);
  const [sortDirState, setSortDirState] = useState<SortDirection>(sortDirection);

  const handleSort = (field: SortField) => {
    if (onSort) {
      onSort(field);
    } else {
      const newDir = sortFieldState === field && sortDirState === 'asc' ? 'desc' : 'asc';
      setSortFieldState(field);
      setSortDirState(newDir);
    }
  };

  const sortedSessions = useMemo(() => {
    if (!onSort) return sessions;
    // Server-side sorting: just return as-is
    return sessions;
  }, [sessions, onSort]);

  const allSelected = sortedSessions.length > 0 && sortedSessions.every(s => selectedIds.includes(s.id));
  const someSelected = selectedIds.length > 0 && !allSelected;

  const SortIcon: React.FC<{ field: SortField }> = ({ field }) => {
    if (sortFieldState !== field) return <MoreHorizontal className="w-3 h-3 text-gray-300" />;
    return sortDirState === 'asc' 
      ? <ChevronUp className="w-3 h-3 text-gray-600 dark:text-slate-300" />
      : <ChevronDown className="w-3 h-3 text-gray-600 dark:text-slate-300" />;
  };

  if (loading) {
    return (
      <div className="overflow-x-auto" role="table" aria-label="Pipeline sessions">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-slate-700">
              <th className="px-4 py-3 w-10" />
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase">Name</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase">Phase</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase">Duration</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase">Created</th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)}
          </tbody>
        </table>
      </div>
    );
  }

  if (sessions.length === 0) {
    return <EmptyState message={emptyMessage} />;
  }

  return (
    <div className={`overflow-x-auto ${className}`} role="table" aria-label="Pipeline sessions">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 dark:border-slate-700 bg-gray-50/50 dark:bg-slate-800/50">
            <th className="px-4 py-3 w-10">
              <input
                type="checkbox"
                checked={allSelected}
                ref={(el) => { el && (el.indeterminate = someSelected); }}
                onChange={(e) => onSelectAll?.(e.target.checked)}
                className="rounded border-gray-300 text-brand-primary focus:ring-brand-primary"
                aria-label="Select all sessions"
              />
            </th>
            
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              <button
                onClick={() => handleSort('name')}
                className="flex items-center gap-1 hover:text-gray-700 dark:hover:text-slate-200 transition-colors"
                aria-sort={sortFieldState === 'name' ? (sortDirState === 'asc' ? 'ascending' : 'descending') : 'none'}
              >
                Name <SortIcon field="name" />
              </button>
            </th>
            
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              <button
                onClick={() => handleSort('status')}
                className="flex items-center gap-1 hover:text-gray-700 dark:hover:text-slate-200 transition-colors"
                aria-sort={sortFieldState === 'status' ? (sortDirState === 'asc' ? 'ascending' : 'descending') : 'none'}
              >
                Status <SortIcon field="status" />
              </button>
            </th>
            
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              Phase
            </th>
            
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              <button
                onClick={() => handleSort('duration')}
                className="flex items-center gap-1 hover:text-gray-700 dark:hover:text-slate-200 transition-colors"
                aria-sort={sortFieldState === 'duration' ? (sortDirState === 'asc' ? 'ascending' : 'descending') : 'none'}
              >
                Duration <SortIcon field="duration" />
              </button>
            </th>
            
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              <button
                onClick={() => handleSort('createdAt')}
                className="flex items-center gap-1 hover:text-gray-700 dark:hover:text-slate-200 transition-colors"
                aria-sort={sortFieldState === 'createdAt' ? (sortDirState === 'asc' ? 'ascending' : 'descending') : 'none'}
              >
                Created <SortIcon field="createdAt" />
              </button>
            </th>
          </tr>
        </thead>
        
        <tbody>
          {sortedSessions.map((session) => {
            const isSelected = selectedIds.includes(session.id);
            const rowBorderClass = getRowBorderClass(session.status);
            
            return (
              <tr
                key={session.id}
                className={`
                  border-b border-gray-100 dark:border-slate-700/50
                  hover:bg-gray-50 dark:hover:bg-slate-700/50
                  cursor-pointer transition-colors
                  ${isSelected ? 'bg-brand-primary/10 dark:bg-slate-600 border-l-3 border-l-brand-primary' : rowBorderClass}
                `}
                onClick={() => onSessionClick?.(session)}
                role="row"
                aria-selected={isSelected}
              >
                <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={(e) => {
                        const target = e.target as HTMLInputElement;
                        onSelect?.(session.id, target.checked);
                    }}
                    className="rounded border-gray-300 text-brand-primary focus:ring-brand-primary"
                    aria-label={`Select ${session.name}`}
                  />
                </td>
                
                <td className="px-4 py-3 font-medium text-gray-900 dark:text-slate-100 max-w-[250px] truncate">
                  {session.name}
                </td>
                
                <td className="px-4 py-3">
                  <PhaseStatusBadge
                    phase={session.status}
                    status={getStatusLabel(session.status)}
                    size="sm"
                  />
                </td>
                
                <td className="px-4 py-3">
                  <span className="px-2 py-0.5 bg-slate-100 dark:bg-slate-700 text-gray-600 dark:text-slate-300 rounded text-xs font-medium">
                    {session.currentPhase}
                  </span>
                </td>
                
                <td className="px-4 py-3 text-gray-600 dark:text-slate-400">
                  {formatDuration(session.duration || 0)}
                </td>
                
                <td className="px-4 py-3 text-gray-500 dark:text-slate-500">
                  {formatRelativeTime(session.createdAt)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      
      {pagination && onPageChange && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-slate-700">
          <span className="text-sm text-gray-500 dark:text-slate-400">
            Showing {((pagination.page - 1) * (pagination.itemsPerPage || 20)) + 1} to {Math.min(pagination.page * (pagination.itemsPerPage || 20), pagination.totalItems)} of {pagination.totalItems} sessions
          </span>
          <SmartPagination
            page={pagination.page}
            totalPages={pagination.totalPages}
            onPageChange={onPageChange}
          />
        </div>
      )}
    </div>
  );
};

export { SessionTable };