import React from 'react';
import Card from './Card';
import Button from './Button';
import { cn } from '@/lib/utils';

type CredentialStatus = 'active' | 'expired' | 'revoked' | 'error' | 'pending';

interface CredentialStatusCardProps {
  provider: string;
  keyName: string;
  status: CredentialStatus;
  lastChecked?: string;
  expiresAt?: string;
  onVerify?: () => void;
  onClick?: () => void;
  loading?: boolean;
  className?: string;
}

const STATUS_CONFIG: Record<CredentialStatus, {
  dotColor: string;
  bgColor: string;
  text: string;
  badgeVariant: 'success' | 'danger' | 'neutral' | 'info' | 'warning';
  label: string;
}> = {
  active: {
    dotColor: 'bg-[var(--color-credential-active)] dark:bg-[var(--color-credential-active)]',
    bgColor: 'bg-[var(--color-credential-active-bg)] dark:bg-[var(--color-credential-active-bg)]',
    text: 'text-[var(--color-credential-active-text)] dark:text-[var(--color-credential-active)]',
    badgeVariant: 'success',
    label: 'Active',
  },
  expired: {
    dotColor: 'bg-[var(--color-credential-expired)] dark:bg-[var(--color-credential-expired)]',
    bgColor: 'bg-[var(--color-credential-expired-bg)] dark:bg-[var(--color-credential-expired-bg)]',
    text: 'text-[var(--color-credential-expired-text)] dark:text-[var(--color-credential-expired)]',
    badgeVariant: 'danger',
    label: 'Expired',
  },
  revoked: {
    dotColor: 'bg-[var(--color-credential-revoked)] dark:bg-[var(--color-credential-revoked)]',
    bgColor: 'bg-[var(--color-credential-revoked-bg)] dark:bg-[var(--color-credential-revoked-bg)]',
    text: 'text-[var(--color-credential-revoked-text)] dark:text-[var(--color-credential-revoked)]',
    badgeVariant: 'neutral',
    label: 'Revoked',
  },
  error: {
    dotColor: 'bg-[var(--color-credential-error)] dark:bg-[var(--color-credential-error)]',
    bgColor: 'bg-[var(--color-credential-error-bg)] dark:bg-[var(--color-credential-error-bg)]',
    text: 'text-[var(--color-credential-error-text)] dark:text-[var(--color-credential-error)]',
    badgeVariant: 'danger',
    label: 'Error',
  },
  pending: {
    dotColor: 'bg-[var(--color-credential-pending)] dark:bg-[var(--color-credential-pending)]',
    bgColor: 'bg-[var(--color-credential-pending-bg)] dark:bg-[var(--color-credential-pending-bg)]',
    text: 'text-[var(--color-credential-pending-text)] dark:text-[var(--color-credential-pending)]',
    badgeVariant: 'warning',
    label: 'Pending',
  },
};

const STATUS_PROVIDERS: Record<string, React.ComponentType<{ className?: string }>> = {
  AWS: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
      <path d="M18.81 7.58c-.06-.34-.4-.53-.71-.41l-2.13.92c-.14.06-.21.21-.19.36l.29 3.25c.01.14-.09.27-.23.31l-.61.13c-.14.03-.23.16-.23.3l.04 2.19c.01.15-.11.28-.26.3l-3.53.41c-.15.02-.27.15-.27.3l.01 1.41c0 .14-.11.26-.25.26H9.85c-.14 0-.25-.12-.25-.26v-1.41c0-.15-.12-.28-.27-.3l-3.53-.41c-.15-.02-.27-.15-.26-.3l.04-2.19c0-.14-.09-.27-.23-.3l-.61-.13c-.14-.04-.24-.17-.23-.31l.29-3.25c.02-.15-.05-.3-.19-.36L4.9 7.17c-.31-.12-.65.07-.71.41l-.96 5.42c-.02.11-.11.2-.22.22L.43 13.5c-.3.04-.3.48 0 .52l3.54.41c.11.02.2.1.23.2l1.08 5.67c.13.68.73 1.18 1.43 1.18h11.48c.7 0 1.3-.5 1.43-1.18l1.08-5.67c.03-.1.12-.18.23-.2l3.54-.41c.3-.04.3-.48 0-.52l-2.65-.68c-.11-.02-.2-.11-.22-.22l-.96-5.42Z" />
    </svg>
  ),
  Azure: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
      <path d="M14.29 2.33c-.27-.16-.59-.1-.8.12l-.76.86c-.16.19-.4.28-.64.25l-1.54-.25c-.28-.04-.5.14-.53.42L9.3 7.48c-.04.27-.26.47-.53.5l-1.55.14c-.28.03-.45.3-.36.55l1.38 3.62c.1.25.03.54-.18.7l-1.24.89c-.22.16-.28.45-.14.69l2.3 3.76c.15.24.44.34.7.23l1.4-.72c.24-.13.53-.1.74.07l1.13.94c.21.17.5.18.72.02l5.6-4.12c.24-.18.3-.51.14-.76l-4.76-6.59Z" />
    </svg>
  ),
  GCP: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1Z" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23Z" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62Z" />
      <path d="M12 5.38c1.62 0 3.06.56 4.23 1.48l3.16-3.16C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53Z" />
    </svg>
  ),
  GitHub: ({ className }) => (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 1C5.37 1 0 6.37 0 13c0 5.51 3.58 10.16 8.53 11.81.62.12.83-.27.83-.6v-2.1c-3.48.76-4.21-1.67-4.21-1.67-.57-1.44-1.39-1.83-1.39-1.83-1.14-.78.08-.77.08-.77 1.27.09 1.94 1.31 1.94 1.31 1.13 1.94 2.98 1.38 3.71 1.05.11-.82.44-1.38.8-1.7-2.77-.31-5.68-1.38-5.68-6.14 0-1.36.48-2.47 1.27-3.34-.13-.31-.55-1.58.12-3.3 0 0 1.07-.34 3.5 1.31a12.26 12.26 0 0 1 6.5 0c2.42-1.65 3.49-1.31 3.49-1.31.68 1.72.26 2.99.13 3.3.79.87 1.27 1.98 1.27 3.34 0 4.77-2.91 5.82-5.69 6.13.45.38.84 1.12.84 2.26v3.35c0 .33.21.72.83.6C20.42 23.16 24 18.51 24 13c0-6.63-5.37-12-12-12Z" />
    </svg>
  ),
  GitLab: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
      <path d="M21.31 8.26l-3.77-7.52a.73.73 0 0 0-.65-.36h-6.89c-.27 0-.52.15-.65.39l-3.75 7.49s-.03.06 0 .08a1.09 1.09 0 0 0 .26.9c.12.1.27.15.43.17.05.01.1.01.15.01h.03c.19-.02.36-.11.49-.25l.03-.03 2.83-2.94v9.57a1.1 1.1 0 0 0 .21.66.66.66 0 0 0 .54.28h.07a.68.68 0 0 0 .52-.3l2.95-4.18 2.95 4.18a.68.68 0 0 0 .52.3h.07a.66.66 0 0 0 .54-.28 1.1 1.1 0 0 0 .21-.66V5.9l2.83 2.94.03.03c.13.14.3.23.49.25h.03c.05 0 .1 0 .15-.01a.74.74 0 0 0 .43-.17 1.09 1.09 0 0 0 .26-.9s0-.06-.03-.08ZM12.02 16.1V5.2l.02-.14.75 1.53v10.07l-.75 1.06-.02-.02Z" />
    </svg>
  ),
};

const CredentialStatusCard: React.FC<CredentialStatusCardProps> = ({
  provider,
  keyName,
  status,
  lastChecked,
  expiresAt,
  onVerify,
  onClick,
  loading = false,
  className,
}) => {
  if (loading) {
    return (
      <Card padding="md" variant="interactive" className={cn('animate-pulse', className)}>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <div className="h-5 w-5 rounded bg-slate-200 dark:bg-slate-700 flex-shrink-0" />
            <div className="min-w-0 space-y-2">
              <div className="h-4 w-32 rounded bg-slate-200 dark:bg-slate-700" />
              <div className="h-3 w-16 rounded bg-slate-200 dark:bg-slate-700" />
            </div>
          </div>
          <div className="h-5 w-16 rounded-full bg-slate-200 dark:bg-slate-700" />
        </div>
        <div className="mt-3 flex items-center gap-4">
          <div className="h-3 w-20 rounded bg-slate-200 dark:bg-slate-700" />
          <div className="h-3 w-20 rounded bg-slate-200 dark:bg-slate-700" />
        </div>
        <div className="mt-3 flex justify-end">
          <div className="h-8 w-24 rounded bg-slate-200 dark:bg-slate-700" />
        </div>
      </Card>
    );
  }
  const config = STATUS_CONFIG[status];
  const ProviderIcon = STATUS_PROVIDERS[provider] || null;

  return (
    <Card
      hoverable
      padding="md"
      variant="interactive"
      onClick={onClick}
      className={cn('cursor-pointer', className)}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3 min-w-0">
          {ProviderIcon && (
            <ProviderIcon className="h-5 w-5 text-slate-400 dark:text-slate-500 flex-shrink-0" />
          )}
          <div className="min-w-0">
            <p className="text-sm font-medium text-slate-900 dark:text-slate-50 truncate">{keyName}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">{provider}</p>
          </div>
        </div>
        <span className={cn('inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border', config.bgColor, config.text, config.badgeVariant === 'success' ? 'border-[var(--color-credential-active)] dark:border-[var(--color-credential-active)]' : config.badgeVariant === 'danger' ? 'border-[var(--color-credential-expired)] dark:border-[var(--color-credential-expired)]' : config.badgeVariant === 'neutral' ? 'border-[var(--color-credential-revoked)] dark:border-[var(--color-credential-revoked)]' : config.badgeVariant === 'warning' ? 'border-[var(--color-credential-pending)] dark:border-[var(--color-credential-pending)]' : 'border-blue-200')}>
          <span className={cn('h-1.5 w-1.5 rounded-full', config.dotColor)} />
          {config.label}
        </span>
      </div>
      {(lastChecked || expiresAt) && (
        <div className="mt-3 flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
          {lastChecked && <span>Last: {lastChecked}</span>}
          {expiresAt && <span>Expires: {expiresAt}</span>}
        </div>
      )}
      {onVerify && (
        <div className="mt-3 flex justify-end">
          <Button variant="outline" size="sm" onClick={(e) => { e.stopPropagation(); onVerify(); }}>
            Verify Now
          </Button>
        </div>
      )}
    </Card>
  );
};

export { type CredentialStatus };
export default CredentialStatusCard;
