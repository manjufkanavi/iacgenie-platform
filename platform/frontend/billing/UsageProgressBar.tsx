import React from 'react';

interface UsageProgressBarProps {
  label: string;
  current: number;
  limit: number;
  type: string;
}

const UsageProgressBar: React.FC<UsageProgressBarProps> = ({
  label,
  current,
  limit,
  type,
}) => {
  const percentage = limit > 0 ? Math.min((current / limit) * 100, 100) : 0;
  
  // Custom HSL/gradient mapping based on resource load
  const getProgressColor = (pct: number) => {
    if (pct >= 90) return 'from-red-500 to-rose-600';
    if (pct >= 70) return 'from-orange-500 to-amber-600';
    return 'from-orange-500 to-red-500';
  };

  const colorGradient = getProgressColor(percentage);

  return (
    <div className="space-y-2.5" data-testid={`usage-bar-${type}`}>
      <div className="flex justify-between items-center text-sm font-semibold">
        <span className="text-gray-500">{label}</span>
        <span className="text-gray-900 font-bold">
          {current} <span className="text-gray-400 font-normal">/ {limit === -1 || limit > 9999 ? '∞' : limit}</span>
        </span>
      </div>
      <div className="h-2.5 w-full bg-gray-100 rounded-full overflow-hidden shadow-inner">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${colorGradient} transition-all duration-500`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {percentage >= 90 && (
        <p className="text-xs font-semibold text-red-500 animate-pulse">
          ⚠️ Approaching limit! Consider upgrading your plan.
        </p>
      )}
    </div>
  );
};

export default UsageProgressBar;
