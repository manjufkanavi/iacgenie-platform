import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon: React.ReactNode;
  trend: string;
  trendType: 'success' | 'warning' | 'info' | 'error';
  borderAccent: string;
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  trendType,
  borderAccent
}) => {
  const trendColors: Record<string, string> = {
    success: 'text-emerald-500 bg-emerald-500/10 dark:bg-emerald-500/20',
    warning: 'text-amber-500 bg-amber-500/10 dark:bg-amber-500/20',
    error: 'text-rose-500 bg-rose-500/10 dark:bg-rose-500/20',
    info: 'text-blue-500 bg-blue-500/10 dark:bg-blue-500/20',
  };

  return (
    <div className={`bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl p-5 shadow-sm hover:shadow-md transition-all duration-300 border-t-4 ${borderAccent} flex flex-col justify-between`}>
      <div className="flex items-start justify-between">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">{title}</span>
          <div className="text-3xl font-black text-slate-850 dark:text-white mt-1.5 font-sans tracking-tight">{value}</div>
        </div>
        <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800 text-slate-500 dark:text-slate-450 border border-slate-100 dark:border-slate-750">
          {icon}
        </div>
      </div>
      <div className="flex items-center gap-2 mt-4 text-xs font-medium">
        <span className={`px-2 py-0.5 rounded-full font-bold ${trendColors[trendType]}`}>
          {trend}
        </span>
        <span className="text-slate-400 dark:text-slate-500">{subtitle}</span>
      </div>
    </div>
  );
};

export default MetricCard;
