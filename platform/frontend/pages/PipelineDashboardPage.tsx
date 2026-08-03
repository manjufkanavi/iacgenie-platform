import React, { useState, useEffect } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { workflowService as workflowService } from '../../services/workflowService';
import type { PipelineListItem, PipelineStatus, PipelinePhase, PipelineFilters } from '../../types';

interface Pagination {
  page: number;
  totalPages: number;
  totalItems: number;
  itemsPerPage: number;
}

const statusColors: Record<PipelineStatus, string> = {
  running: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  paused: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  completed: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  escalated: 'bg-brand-primary/10 text-brand-primary dark:bg-brand-primary/20 dark:text-brand-primary',
};

const formatRelativeTime = (isoString: string): string => {
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
  return isoString.slice(0, 10);
};

const PipelineDashboardPage: React.FC = () => {
  const [pipelines, setPipelines] = useState<PipelineListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState<Pagination>({
    page: 1, totalPages: 1, totalItems: 0, itemsPerPage: 20,
  });
  const [filters, setFilters] = useState<PipelineFilters>({});
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadPipelines();
  }, [pagination.page, filters]);

  const loadPipelines = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await workflowService.getPipelines({
        ...filters,
        searchQuery,
        limit: pagination.itemsPerPage,
        offset: (pagination.page - 1) * pagination.itemsPerPage,
      });
      setPipelines(
        (response.data?.sessions || []).map((s: any) => ({
          id: s.id,
          name: s.build_id || s.id,
          status: (s.status as PipelineStatus) || 'running',
          current_phase: 'workflow' as PipelinePhase,
          created_at: s.created_at,
          updated_at: s.updated_at,
        })) as PipelineListItem[],
      );
      setPagination((prev) => ({
        ...prev,
        totalItems: response.data?.total || 0,
        totalPages: Math.ceil((response.data?.total || 0) / prev.itemsPerPage),
      }));
    } catch (err: any) {
      setError(err.message || 'Failed to load pipelines');
    } finally {
      setLoading(false);
    }
  };

  const handleNavigate = (pipelineId: string) => {
    window.location.href = `/pipelines/${pipelineId}`;
  };

  const totalPages = pagination.totalPages || 1;
  const pageNumbers: number[] = [];
  for (let i = 1; i <= Math.min(totalPages, 5); i++) {
    pageNumbers.push(i);
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">Pipeline Dashboard</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Monitor and manage your Iacgenie pipeline sessions
          </p>
        </div>
        <Button onClick={() => { window.location.href = '/pipelines/new'; }}>
          New Pipeline
        </Button>
      </div>

      {/* Filters */}
      <Card padding="lg">
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            placeholder="Search pipelines..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 px-3 py-2 text-sm border border-slate-300 dark:border-slate-500 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-50 focus:outline-none focus:ring-2 focus:ring-brand-primary"
          />
          <select
            value={filters.status || ''}
            onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value as PipelineStatus || undefined }))}
            className="px-3 py-2 text-sm border border-slate-300 dark:border-slate-500 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-50 focus:outline-none focus:ring-2 focus:ring-brand-primary"
          >
            <option value="">All Statuses</option>
            <option value="running">Running</option>
            <option value="paused">Paused</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="escalated">Escalated</option>
          </select>
        </div>
      </Card>

      {/* Error state */}
      {error && (
        <Card className="p-4 border-red-200 bg-red-50 dark:bg-red-950/30 dark:border-red-800">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </Card>
      )}

      {/* Loading state */}
      {loading ? (
        <Card padding="lg">
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary" />
          </div>
        </Card>
      ) : pipelines.length === 0 ? (
        <Card variant="empty-state" padding="lg">
          <p className="text-slate-500 dark:text-slate-400">No pipelines found</p>
        </Card>
      ) : (
        /* Pipeline table */
        <Card padding="none" className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 dark:bg-slate-700/50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-600 dark:border-slate-700">
                <tr>
                  <th className="px-6 py-3 text-left font-semibold text-slate-600 dark:text-slate-400">Name</th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-600 dark:text-slate-400">Status</th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-600 dark:text-slate-400">Phase</th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-600 dark:text-slate-400">Created</th>
                  <th className="px-6 py-3 text-right font-semibold text-slate-600 dark:text-slate-400">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-600 dark:divide-slate-700">
                {pipelines.map((pipeline) => (
                  <tr key={pipeline.id} className="hover:bg-slate-50 dark:bg-slate-700/50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer" onClick={() => handleNavigate(pipeline.id)}>
                    <td className="px-6 py-4 font-medium text-slate-900 dark:text-slate-50">{pipeline.name}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[pipeline.status]}`}>
                        {pipeline.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-500 dark:text-slate-400">{pipeline.current_phase}</td>
                    <td className="px-6 py-4 text-slate-500 dark:text-slate-400">{formatRelativeTime(pipeline.created_at)}</td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleNavigate(pipeline.id); }}
                        className="text-brand-primary hover:text-brand-primary/80 dark:text-brand-primary text-sm font-medium"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-6 py-3 border-t border-slate-200 dark:border-slate-600 dark:border-slate-700">
              <span className="text-sm text-slate-500 dark:text-slate-400">
                Page {pagination.page} of {totalPages} ({pagination.totalItems} total)
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPagination((p) => ({ ...p, page: Math.max(1, p.page - 1) }))}
                  disabled={pagination.page <= 1}
                  className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-40"
                >
                  <ChevronLeft className="h-4 w-4 text-slate-600 dark:text-slate-400" />
                </button>
                {pageNumbers.map((pageNum) => (
                  <button
                    key={pageNum}
                    onClick={() => setPagination((p) => ({ ...p, page: pageNum }))}
                    className={`w-8 h-8 rounded text-sm font-medium ${
                      pagination.page === pageNum
                        ? 'bg-brand-primary text-white'
                        : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
                  >
                    {pageNum}
                  </button>
                ))}
                <button
                  onClick={() => setPagination((p) => ({ ...p, page: Math.min(totalPages, p.page + 1) }))}
                  disabled={pagination.page >= totalPages}
                  className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-40"
                >
                  <ChevronRight className="h-4 w-4 text-slate-600 dark:text-slate-400" />
                </button>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
};

export default PipelineDashboardPage;
