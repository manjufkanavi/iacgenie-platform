import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
  variant?: 'rect' | 'circle' | 'text';
}

export function Skeleton({ className, variant = 'rect' }: SkeletonProps) {
  const base = 'animate-shimmer rounded-md bg-gradient-to-r from-slate-200 via-slate-100 to-slate-200 dark:from-slate-800 dark:via-slate-700 dark:to-slate-800 bg-[length:200%_100%]';
  const shapes = { rect: '', circle: 'rounded-full', text: 'h-4 w-full' };
  return <div className={cn(base, shapes[variant], className)} />;
}
