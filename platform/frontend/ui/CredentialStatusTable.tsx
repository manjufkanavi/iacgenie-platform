import React, { useMemo, useRef, useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { MoreVertical, Eye, Trash2 } from 'lucide-react';

export type CredentialStatus = 'active' | 'expired' | 'revoked' | 'error' | 'pending';
export type SortColumn = 'keyName' | 'status' | 'lastChecked' | 'expiresAt';
export type SortDirection = 'asc' | 'desc';

export interface CredentialItem {
  id: string;
  provider: string;
  keyName: string;
  status: CredentialStatus;
  lastChecked?: string;
  expiresAt?: string;
  region?: string;
}

interface CredentialStatusTableProps {
  credentials: CredentialItem[];
  onVerify?: (id: string) => void;
  onDelete?: (id: string) => void;
  onSelect?: (id: string, selected: boolean) => void;
  onAllSelected?: (selected: boolean) => void;
  selectedIds?: Set<string>;
  sortColumn?: SortColumn;
  sortDirection?: SortDirection;
  onSortChange?: (column: SortColumn, direction: SortDirection) => void;
  loading?: boolean;
  readOnly?: boolean;
  className?: string;
}

const ActionMenu: React.FC<{
  onVerify?: () => void;
  onDelete?: () => void;
  readOnly?: boolean;
}> = ({ onVerify, onDelete, readOnly }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        aria-label="Actions"
      >
        <MoreVertical className="w-4 h-4 text-slate-400" />
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 w-36 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg z-20 py-1">
          {onVerify && !readOnly && (
            <button
              onClick={() => { onVerify(); setOpen(false); }}
              className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"
            >
              <Eye className="w-3.5 h-3.5" /> Verify
            </button>
          )}
          {onDelete && !readOnly && (
            <button
              onClick={() => { onDelete(); setOpen(false); }}
              className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
            >
              <Trash2 className="w-3.5 h-3.5" /> Delete
            </button>
          )}
        </div>
      )}
    </div>
  );
};

const SkeletonRow: React.FC<{ hasSelect?: boolean }> = ({ hasSelect }) => (
  <tr className="border-b border-slate-100 dark:border-slate-800">
    {hasSelect && <td className="py-4 px-3"><div className="w-4 h-4 rounded bg-slate-200 dark:bg-slate-700 animate-pulse" /></td>}
    <td className="py-4 px-3"><div className="flex items-center gap-2"><div className="w-4 h-4 rounded bg-slate-200 dark:bg-slate-700 animate-pulse" /><div className="w-10 h-4 rounded bg-slate-200 dark:bg-slate-700 animate-pulse" /></div></td>
    <td className="py-4 px-3"><div className="w-32 h-4 rounded bg-slate-200 dark:bg-slate-700 animate-pulse" /></td>
    <td className="py-4 px-3"><div className="w-16 h-5 rounded-full bg-slate-200 dark:bg-slate-700 animate-pulse" /></td>
    <td className="py-4 px-3"><div className="w-24 h-4 rounded bg-slate-200 dark:bg-slate-700 animate-pulse" /></td>
    <td className="py-4 px-3"><div className="w-20 h-4 rounded bg-slate-200 dark:bg-slate-700 animate-pulse" /></td>
    <td className="py-4 px-3 text-right"><div className="w-8 h-8 rounded-lg bg-slate-200 dark:bg-slate-700 animate-pulse ml-auto" /></td>
  </tr>
);

const PROVIDER_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  AWS: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor"><path d="M18.81 7.58c-.06-.34-.4-.53-.71-.41l-2.13.92c-.14.06-.21.21-.19.36l.29 3.25c.01.14-.09.27-.23.31l-.61.13c-.14.03-.23.16-.23.3l.04 2.19c.01.15-.11.28-.26.3l-3.53.41c-.15.02-.27.15-.27.3l.01 1.41c0 .14-.11.26-.25.26H9.85c-.14 0-.25-.12-.25-.26v-1.41c0-.15-.12-.28-.27-.3l-3.53-.41c-.15-.02-.27-.15-.26-.3l.04 2.19c0-.14-.09-.27-.23-.3l-.61-.13c-.14-.04-.24-.17-.23-.31l.29-3.25c.02-.15-.05-.3-.19-.36L4.9 7.17c-.31-.12-.65.07-.71.41l-.96 5.42c-.02.11-.11.2-.22.22L.43 13.5c-.3.04-.3.48 0 .52l3.54.41c.11.02.2.1.23.2l1.08 5.67c.13.68.73 1.18 1.43 1.18h11.48c.7 0 1.3-.5 1.43-1.18l1.08-5.67c.03-.1.12-.18.23-.2l3.54-.41c.3-.04.3-.48 0-.52l-2.65-.68c-.11-.02-.2-.11-.22-.22l-.96-5.42Z" /></svg>
  ),
  Azure: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor"><path d="M14.29 2.33c-.27-.16-.59-.1-.8.12l-.76.86c-.16.19-.4.28-.64.25l-1.54-.25c-.28-.04-.5.14-.53.42L9.3 7.48c-.04.27-.26.47-.53.5l-1.55.14c-.28.03-.45.3-.36.55l1.38 3.62c.1.25.03.54-.18.7l-1.24.89c-.22.16-.28.45-.14.69l2.3 3.76c.15.24.44.34.7.23l1.4-.72c.24-.13.53-.1.74.07l1.13.94c.21.17.5.18.72.02l5.6-4.12c.24-.18.3-.51.14-.76l-4.76-6.59Z" /></svg>
  ),
  GCP: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1Z" /><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23Z" /><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62Z" /><path d="M12 5.38c1.62 0 3.06.56 4.23 1.48l3.16-3.16C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53Z" /></svg>
  ),
  GitHub: ({ className }) => (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24"><path d="M12 1C5.37 1 0 6.37 0 13c0 5.51 3.58 10.16 8.53 11.81.62.12.83-.27.83-.6v-2.1c-3.48.76-4.21-1.67-4.21-1.67-.57-1.44-1.39-1.83-1.39-1.83-1.14-.78.08-.77.08-.77 1.27.09 1.94 1.31 1.94 1.31 1.13 1.94 2.98 1.38 3.71 1.05.11-.82.44-1.38.8-1.7-2.77-.31-5.68-1.38-5.68-6.14 0-1.36.48-2.47 1.27-3.34-.13-.31-.55-1.58.12-3.3 0 0 1.07-.34 3.5 1.31a12.26 12.26 0 0 1 6.5 0c2.42-1.65 3.49-1.31 3.49-1.31.68 1.72.26 2.99.13 3.3.79.87 1.27 1.98 1.27 3.34 0 4.77-2.91 5.82-5.69 6.13.45.38.84 1.12.84 2.26v3.35c0 .33.21.72.83.6C20.42 23.16 24 18.51 24 13c0-6.63-5.37-12-12-12Z" /></svg>
  ),
  GitLab: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor"><path d="M21.31 8.26l-3.77-7.52a.73.73 0 0 0-.65-.36h-6.89c-.27 0-.52.15-.65.39l-3.75 7.49s-.03.06 0 .08a1.09 1.09 0 0 0 .26.9c.12.1.27.15.43.17.05.01.1.01.15.01h.03c.19-.02.36-.11.49-.25l.03-.03 2.83-2.94v9.57a1.1 1.1 0 0 0 .21.66.66.66 0 0 0 .54.28h.07a.68.68 0 0 0 .52-.3l2.95-4.18 2.95 4.18a.68.68 0 0 0 .52.3h.07a.66.66 0 0 0 .54-.28 1.1 1.1 0 0 0 .21-.66V5.9l2.83 2.94.03-.03c.13.14.3.23.49.25h.03c.05 0 .1 0 .15-.01a.74.74 0 0 0 .43-.17 1.09 1.09 0 0 0 .26-.9s0-.06-.03-.08ZM12.02 16.1V5.2l.02-.14.75 1.53v10.07l-.75 1.06-.02-.02Z" /></svg>
  ),
};

const StatusPill: React.FC<{ status: CredentialStatus }> = ({ status }) => (
  <span className={cn(
    'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border',
    `border-[var(--color-credential-${status})] dark:border-[var(--color-credential-${status})]`
  )}>
    <span className={cn('h-1.5 w-1.5 rounded-full', `bg-[var(--color-credential-${status})] dark:bg-[var(--color-credential-${status})]`)} />
    {status.charAt(0).toUpperCase() + status.slice(1)}
  </span>
);

const CredentialStatusTable: React.FC<CredentialStatusTableProps> = ({
  credentials,
  onVerify,
  onDelete,
  onSelect,
  onAllSelected,
  selectedIds = new Set(),
  sortColumn = 'status',
  sortDirection = 'asc',
  onSortChange,
  loading = false,
  readOnly = false,
  className,
}) => {
  const sorted = useMemo(() => {
    if (!onSortChange) return credentials;
    const sortedArr = [...credentials].sort((a, b) => {
      let aVal: string, bVal: string;
      switch (sortColumn) {
        case 'keyName': aVal = a.keyName; bVal = b.keyName; break;
        case 'status': aVal = a.status; bVal = b.status; break;
        case 'lastChecked': aVal = a.lastChecked || ''; bVal = b.lastChecked || ''; break;
        case 'expiresAt': aVal = a.expiresAt || ''; bVal = b.expiresAt || ''; break;
        default: return 0;
      }
      const dir = sortDirection === 'asc' ? 1 : -1;
      return aVal.localeCompare(bVal) * dir;
    });
    return sortedArr;
  }, [credentials, sortColumn, sortDirection]);

  const handleSort = (col: SortColumn) => {
    if (!onSortChange) return;
    if (sortColumn === col) {
      onSortChange(col, sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      onSortChange(col, 'asc');
    }
  };

  const SortIndicator: React.FC<{ col: SortColumn }> = ({ col }) => {
    if (sortColumn !== col) return null;
    return sortDirection === 'asc' ? <span className="ml-1 text-xs">↑</span> : <span className="ml-1 text-xs">↓</span>;
  };

  const hasActions = onVerify || onDelete;
  const hasSelect = !!onSelect;
  const allSelected = credentials.length > 0 && credentials.every(c => selectedIds.has(c.id));

  return (
    <div className={cn('overflow-x-auto', className)}>
      {credentials.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 px-4 text-center max-w-lg mx-auto">
          <div className="flex items-center justify-center h-12 w-12 rounded-xl bg-brand-primary-subtle border border-brand-primary-border/30 text-brand-primary dark:bg-slate-800 dark:border-slate-700 dark:text-brand-primary">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
            </svg>
          </div>
          <h3 className="mt-5 text-xl font-bold text-slate-900 dark:text-slate-50 tracking-tight">No credentials configured</h3>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 max-w-sm">Connect your first cloud provider to get started.</p>
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-700">
              {hasSelect && <th className="w-10 py-2.5 px-3 text-left"><input type="checkbox" checked={allSelected} onChange={(e) => { if (onAllSelected) { onAllSelected(e.target.checked); } else if (onSelect) { onSelect(credentials[0]?.id || '', e.target.checked); } }} className="rounded border-slate-300" aria-label="Select all" /></th>}
              <th className="py-2.5 px-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Provider</th>
              {(onSortChange ? <th
                className="py-2.5 px-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-700 dark:hover:text-slate-200 select-none"
                onClick={() => handleSort('keyName')}
                role="columnheader"
                aria-sort={sortColumn === 'keyName' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
              >
                Key Name<SortIndicator col="keyName" />
              </th> : <th className="py-2.5 px-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Key Name</th>)}
              {(onSortChange ? <th
                className="py-2.5 px-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-700 dark:hover:text-slate-200 select-none"
                onClick={() => handleSort('status')}
                role="columnheader"
                aria-sort={sortColumn === 'status' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
              >
                Status<SortIndicator col="status" />
              </th> : <th className="py-2.5 px-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Status</th>)}
              {(onSortChange ? <th
                className="py-2.5 px-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-700 dark:hover:text-slate-200 select-none"
                onClick={() => handleSort('lastChecked')}
                role="columnheader"
                aria-sort={sortColumn === 'lastChecked' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
              >
                Last Verified<SortIndicator col="lastChecked" />
              </th> : <th className="py-2.5 px-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Last Verified</th>)}
              {(onSortChange ? <th
                className="py-2.5 px-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-700 dark:hover:text-slate-200 select-none"
                onClick={() => handleSort('expiresAt')}
                role="columnheader"
                aria-sort={sortColumn === 'expiresAt' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
              >
                Expires In<SortIndicator col="expiresAt" />
              </th> : <th className="py-2.5 px-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Expires In</th>)}
              {hasActions && <th className="py-2.5 px-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <>
                <SkeletonRow hasSelect={hasSelect} />
                <SkeletonRow hasSelect={hasSelect} />
                <SkeletonRow hasSelect={hasSelect} />
              </>
            ) : (
              sorted.map((cred) => {
                const ProviderIcon = PROVIDER_ICONS[cred.provider] || null;
                return (
                  <tr
                    key={cred.id}
                    className={cn(
                      'border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors',
                      cred.status === 'error' || cred.status === 'expired' ? `border-l-2 border-l-[var(--color-credential-${cred.status})] dark:border-l-[var(--color-credential-${cred.status})]` : '',
                      selectedIds.has(cred.id) ? 'bg-[var(--color-brand-primary-subtle)] dark:bg-[#431407]' : ''
                    )}
                  >
                    {hasSelect && <td className="py-3 px-3"><input type="checkbox" checked={selectedIds.has(cred.id)} onChange={(e) => onSelect(cred.id, e.target.checked)} className="rounded border-slate-300" aria-label={`Select ${cred.keyName}`} /></td>}
                    <td className="py-3 px-3"><div className="flex items-center gap-2"><ProviderIcon className="h-4 w-4 text-slate-400" />{cred.provider}</div></td>
                    <td className="py-3 px-3 font-medium text-slate-900 dark:text-slate-50">{cred.keyName}</td>
                    <td className="py-3 px-3"><StatusPill status={cred.status} /></td>
                    <td className="py-3 px-3 text-slate-500 dark:text-slate-400">{cred.lastChecked || '—'}</td>
                    <td className="py-3 px-3 text-slate-500 dark:text-slate-400">{cred.expiresAt || '—'}</td>
                    {hasActions && (
                      <td className="py-3 px-3 text-right relative">
                        <ActionMenu
                          onVerify={onVerify ? () => onVerify(cred.id) : undefined}
                          onDelete={onDelete ? () => onDelete(cred.id) : undefined}
                          readOnly={readOnly}
                        />
                      </td>
                    )}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      )}

      {credentials.length > 0 && selectedIds.size > 0 && (
        <div className="flex items-center gap-3 mt-3 pt-3 border-t border-slate-200 dark:border-slate-700 text-xs text-slate-500 dark:text-slate-400">
          <span>{selectedIds.size} credential{selectedIds.size > 1 ? 's' : ''} selected</span>
        </div>
      )}
    </div>
  );
};

export default CredentialStatusTable;
