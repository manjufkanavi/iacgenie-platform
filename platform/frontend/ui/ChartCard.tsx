import React from 'react';

interface ChartCardProps {
  title: string;
  value?: number | string;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: number; // percentage
  children: React.ReactNode;
}

export const ChartCard: React.FC<ChartCardProps> = ({
  title,
  value,
  subtitle,
  trend,
  trendValue,
  children
}) => {
  const getTrendColor = () => {
    if (trend === 'up') return 'text-green-600';
    if (trend === 'down') return 'text-red-600';
    return 'text-gray-500';
  };

  const getTrendIcon = () => {
    if (trend === 'up') return '▲';
    if (trend === 'down') return '▼';
    return '→';
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
          {value !== undefined && (
            <div className="mt-2">
              <span className="text-3xl font-bold text-gray-900">{value}</span>
              {subtitle && (
                <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
              )}
            </div>
          )}
        </div>
        {trendValue !== undefined && (
          <div className={`flex items-center gap-1 text-sm font-medium ${getTrendColor()}`}>
            <span>{getTrendIcon()}</span>
            <span>{Math.abs(trendValue)}%</span>
          </div>
        )}
      </div>

      {children}
    </div>
  );
};

export default ChartCard;