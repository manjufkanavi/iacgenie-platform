import Button from './Button';
import { cn } from '@/lib/utils';
import type { ComponentType, SVGProps } from 'react';

interface EmptyStateProps {
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  secondaryActionLabel?: string;
  onSecondaryAction?: () => void;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  secondaryActionLabel,
  onSecondaryAction,
  className
}: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-16 px-4 text-center max-w-lg mx-auto', className)}>
      <div className="flex items-center justify-center h-12 w-12 rounded-xl bg-brand-primary-subtle border border-brand-primary-border/30 text-brand-primary dark:bg-slate-800 dark:border-slate-700 dark:text-brand-primary">
        <Icon className="h-6 w-6" strokeWidth={1.5} />
      </div>
      <h3 className="mt-5 text-xl font-bold text-slate-900 dark:text-slate-50 tracking-tight">{title}</h3>
      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 max-w-sm leading-relaxed">{description}</p>
      
      {(actionLabel || secondaryActionLabel) && (
        <div className="mt-6 flex flex-col sm:flex-row items-center gap-3">
          {actionLabel && onAction && (
            <Button variant="primary" onClick={onAction}>
              {actionLabel}
            </Button>
          )}
          {secondaryActionLabel && onSecondaryAction && (
            <button
              onClick={onSecondaryAction}
              className="text-sm font-semibold text-brand-primary hover:text-brand-primary-hover active:text-brand-primary-active transition-colors px-4 py-2"
            >
              {secondaryActionLabel}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
