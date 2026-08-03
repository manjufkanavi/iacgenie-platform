import React from 'react';
import { cn } from '@/lib/utils';
import { Lock, CheckCircle2, AlertTriangle } from 'lucide-react';

type BannerVariant = 'info' | 'success' | 'warning';

interface EncryptionTrustBannerProps {
  variant?: BannerVariant;
  message: string;
  secondaryMessage?: string;
  onLearnMore?: () => void;
  onDismiss?: () => void;
  compact?: boolean;
  dismissable?: boolean;
  className?: string;
  children?: React.ReactNode;
}

interface VariantConfig {
  icon: React.ComponentType<{ className?: string }>;
  bg: string;
  text: string;
  border: string;
  iconColor: string;
  role: 'alert' | 'status';
}

const variantConfigs: Record<BannerVariant, VariantConfig> = {
  info: {
    icon: Lock,
    bg: 'bg-[var(--color-encryption-bg)] dark:bg-[var(--color-encryption-bg)]',
    text: 'text-[var(--color-encryption-text)] dark:text-[var(--color-encryption-text)]',
    border: 'border-[var(--color-encryption-border)] dark:border-[var(--color-encryption-border)]',
    iconColor: 'text-[var(--color-encryption-icon)] dark:text-[var(--color-encryption-icon)]',
    role: 'status',
  },
  success: {
    icon: CheckCircle2,
    bg: 'bg-status-success-bg dark:bg-[#052e16]',
    text: 'text-status-success dark:text-[#4ade80]',
    border: 'border-status-success dark:border-[#15803d]',
    iconColor: 'text-status-success dark:text-[#4ade80]',
    role: 'status',
  },
  warning: {
    icon: AlertTriangle,
    bg: 'bg-amber-50 dark:bg-amber-950',
    text: 'text-amber-800 dark:text-[#fbbf24]',
    border: 'border-amber-200 dark:border-amber-800',
    iconColor: 'text-amber-600 dark:text-[#fbbf24]',
    role: 'alert',
  },
};

const EncryptionTrustBanner: React.FC<EncryptionTrustBannerProps> = ({
  variant = 'info',
  message,
  secondaryMessage,
  onLearnMore,
  onDismiss,
  compact = false,
  dismissable,
  className,
  children,
}) => {
  const config = variantConfigs[variant];
  const IconComponent = config.icon;

  if (compact) {
    return (
      <div
        className={cn(
          'flex items-center gap-1 text-xs text-[var(--color-encryption-icon)] dark:text-[var(--color-encryption-icon)]',
          className
        )}
      >
        <IconComponent className="h-3.5 w-3.5 flex-shrink-0" />
        <span>{message}</span>
        {onLearnMore && (
          <button
            type="button"
            onClick={onLearnMore}
            className="underline underline-offset-2 hover:text-[var(--color-encryption-text)] dark:hover:text-[var(--color-encryption-text)] transition-colors"
          >
            Learn more
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        'border rounded-lg px-4 py-3',
        config.bg,
        config.border,
        config.text,
        className
      )}
      role={config.role}
    >
      <div className="flex items-start gap-3">
        <IconComponent className={cn('h-5 w-5 flex-shrink-0 mt-0.5', config.iconColor)} />
        <div className="flex-1 min-w-0">
          <p className="text-sm">{message}</p>
          {secondaryMessage && (
            <p className="text-sm mt-0.5">{secondaryMessage}</p>
          )}
          {children && <div className="mt-2">{children}</div>}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {onLearnMore && (
            <button
              type="button"
              onClick={onLearnMore}
              className="text-sm underline underline-offset-2 hover:text-inherit transition-colors"
            >
              Learn more
            </button>
          )}
          {(dismissable || onDismiss) && (
            <button
              type="button"
              onClick={onDismiss}
              className="p-1 rounded text-current opacity-60 hover:opacity-100 transition-opacity"
              aria-label="Dismiss"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default EncryptionTrustBanner;
