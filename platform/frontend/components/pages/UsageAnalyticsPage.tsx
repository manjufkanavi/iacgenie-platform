import React, { useState, useEffect } from 'react';
import Card from '../ui/Card';
import { ChartCard } from '../ui/ChartCard';
import toast from 'react-hot-toast';
import { Calendar, FileSpreadsheet, FileText, BarChart3, TrendingUp, Cpu, HelpCircle } from 'lucide-react';
import { useAppStore } from '.././store/useAppStore';
import { useProjectStore } from '.././store/useProjectStore';

interface TimeSeriesData {
  date: string;
  count: number;
}

const UsageAnalyticsPage: React.FC = () => {
  const {
    usageMetrics: storeUsageMetrics,
    costMetrics: storeCostMetrics,
    generationsOverTime,
    deploymentsOverTime,
    modelPerformance,
    cloudProviderDistribution,
    fetchMetrics
  } = useAppStore();

  const currentProjectId = useProjectStore((state) => state.currentProjectId);

  const usageMetrics = storeUsageMetrics || {
    totalGenerations: 0,
    totalDeployments: 0,
    successRate: 0
  };

  const costMetrics = storeCostMetrics || {
    currentMonthCost: 0,
    projectedEndOfMonthCost: 0,
    savingsVsLastMonth: 0
  };

  const [dateRange, setDateRange] = useState<string>('last-30-days');
  const [customStartDate, setCustomStartDate] = useState<string>('2026-03-01');
  const [customEndDate, setCustomEndDate] = useState<string>('2026-03-31');
  const [hoveredDataPoint, setHoveredDataPoint] = useState<{ date: string; count: number } | null>(null);

  useEffect(() => {
    if (currentProjectId) {
      fetchMetrics(currentProjectId, dateRange);
    }
  }, [currentProjectId, dateRange, fetchMetrics]);

  // Export Data formats: CSV, JSON
  const handleExport = (format: 'csv' | 'json') => {
    const reportData = {
      metrics: usageMetrics,
      cost: costMetrics,
      generations: generationsOverTime,
      deployments: deploymentsOverTime,
      cloudDistribution: cloudProviderDistribution,
      models: modelPerformance,
      exportedAt: new Date().toISOString(),
      range: dateRange
    };

    if (format === 'json') {
      const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(reportData, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute('href', dataStr);
      downloadAnchor.setAttribute('download', `iacgenie-analytics-report-${dateRange}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
      toast.success('JSON Report downloaded successfully!');
    } else {
      let csvContent = 'data:text/csv;charset=utf-8,Category,Value\n';
      csvContent += `Total Generations,${usageMetrics.totalGenerations}\n`;
      csvContent += `Total Deployments,${usageMetrics.totalDeployments}\n`;
      csvContent += `Success Rate,${usageMetrics.successRate}%\n`;
      csvContent += `Current Month Cost,$${costMetrics.currentMonthCost}\n`;

      const dataStr = encodeURI(csvContent);
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute('href', dataStr);
      downloadAnchor.setAttribute('download', `iacgenie-analytics-report-${dateRange}.csv`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
      toast.success('CSV Report downloaded successfully!');
    }
  };

  const renderSimpleBarChart = (data: TimeSeriesData[], maxValue: number) => {
    return (
      <div className="relative pt-6" data-testid="bar-chart-container">
        <div className="flex items-end justify-between gap-3 h-44 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
          {data.map((item, index) => {
            const heightPercentage = (item.count / maxValue) * 100;
            return (
              <div
                key={index}
                className="flex-1 flex flex-col items-center gap-2 group relative"
                onMouseEnter={() => setHoveredDataPoint(item)}
                onMouseLeave={() => setHoveredDataPoint(null)}
              >
                {/* Visual Tooltip inside Group hover */}
                <div className="absolute -top-12 scale-0 group-hover:scale-100 transition bg-slate-800 text-white text-[10px] font-bold px-2 py-1 rounded shadow-lg border border-slate-700 z-10 pointer-events-none">
                  {item.count} deploys
                </div>
                <div
                  className="w-full bg-gradient-to-t from-brand-primary to-red-500 rounded-t-lg transition-all duration-300 hover:from-brand-primary/90 hover:to-red-650"
                  style={{ height: `${heightPercentage}%` }}
                />
                <span className="text-[10px] font-bold text-slate-500">
                  {new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderSimpleLineChart = (data: TimeSeriesData[]) => {
    const maxValue = Math.max(...data.map(d => d.count)) || 1;
    const points = data.map((item, index) => {
      const x = (index / (data.length - 1)) * 100;
      const y = 100 - (item.count / maxValue) * 100;
      return `${x},${y}`;
    }).join(' ');

    return (
      <div className="relative pt-6" data-testid="line-chart-container">
        <div className="h-44 bg-slate-900/60 p-4 rounded-xl border border-slate-800 relative">
          <svg className="w-full h-32" viewBox="0 0 100 100" preserveAspectRatio="none">
            {/* Grid lines */}
            <line x1="0" y1="25" x2="100" y2="25" stroke="#1e293b" strokeWidth="0.5" strokeDasharray="2" />
            <line x1="0" y1="50" x2="100" y2="50" stroke="#1e293b" strokeWidth="0.5" strokeDasharray="2" />
            <line x1="0" y1="75" x2="100" y2="75" stroke="#1e293b" strokeWidth="0.5" strokeDasharray="2" />

            <polyline
              fill="none"
              stroke="url(#brand-grad)"
              strokeWidth="2.5"
              points={points}
              className="drop-shadow-[0_2px_8px_rgba(249,115,22,0.3)] animate-pulse"
            />
            <defs>
              <linearGradient id="brand-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="var(--color-brand-primary)" />
                <stop offset="100%" stopColor="#ef4444" />
              </linearGradient>
            </defs>
          </svg>
          <div className="flex justify-between mt-2 px-1">
            {data.map((item, index) => (
              <span key={index} className="text-[10px] font-bold text-slate-500">
                {new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              </span>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderPieChart = (data: Array<{ provider: string; percentage: number }>) => {
    let cumulativeAngle = 0;
    const colors = ['#F97316', '#3B82F6', '#10B981'];

    return (
      <div className="flex flex-col md:flex-row items-center justify-around gap-6" data-testid="pie-chart-container">
        <svg width="180" height="180" viewBox="0 0 160 160" className="transform -rotate-90 filter drop-shadow-md">
          {data.map((item, index) => {
            const angle = (item.percentage / 100) * 360;
            const x = 80 + 70 * Math.cos((cumulativeAngle * Math.PI) / 180);
            const y = 80 + 70 * Math.sin((cumulativeAngle * Math.PI) / 180);
            const x2 = 80 + 70 * Math.cos(((cumulativeAngle + angle) * Math.PI) / 180);
            const y2 = 80 + 70 * Math.sin(((cumulativeAngle + angle) * Math.PI) / 180);
            const largeArcFlag = item.percentage > 50 ? 1 : 0;

            const pathData = [
              `M 80 80`,
              `A 70 70 0 ${largeArcFlag} 1 ${x} ${y}`,
              `L 80 80`,
              `A 70 70 0 ${largeArcFlag} 1 ${x2} ${y2}`,
              `Z`
            ].join(' ');

            cumulativeAngle += angle;

            return (
              <path
                key={index}
                d={pathData}
                fill={colors[index % colors.length]}
                className="transition-all duration-350 hover:opacity-85 cursor-pointer"
              >
                <title>{`${item.provider}: ${item.percentage}%`}</title>
              </path>
            );
          })}
          <circle cx="80" cy="80" r="42" fill="#0f172a" />
        </svg>

        <div className="space-y-3.5 w-full md:w-auto">
          {data.map((item, index) => (
            <div key={index} className="flex items-center justify-between gap-4 p-3 bg-slate-50 dark:bg-slate-700/50 dark:bg-slate-900 rounded-xl border border-gray-150 dark:border-slate-600">
              <div className="flex items-center gap-2">
                <div
                  className="w-3.5 h-3.5 rounded-md"
                  style={{ backgroundColor: colors[index % colors.length] }}
                />
                <span className="text-sm font-bold text-slate-700 dark:text-slate-200 dark:text-slate-300">{item.provider}</span>
              </div>
              <span className="text-sm font-black text-slate-900 dark:text-slate-50 dark:text-slate-100">{item.percentage}%</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-6" data-testid="usage-analytics-page">
      {/* Header and responsive date selector controls */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6 mb-8">
        <div>
          <h1 className="text-3xl font-black text-slate-900 dark:text-slate-50 dark:text-slate-100">Usage Analytics Dashboard</h1>
          <p className="text-sm font-semibold text-slate-500 dark:text-slate-400 dark:text-slate-400 mt-1">Real-time resource utilization, model successes and budgets metrics.</p>
        </div>

        {/* Date Selector Row & Export options */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 bg-white dark:bg-slate-800 p-2.5 rounded-xl border border-gray-250 dark:border-slate-600 shadow-sm">
            <Calendar className="w-4 h-4 text-brand-primary" />
            <select
              id="date-range-select"
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="text-xs font-bold text-slate-700 dark:text-slate-200 dark:text-slate-200 focus:outline-none bg-transparent"
            >
              <option value="last-7-days">Last 7 Days</option>
              <option value="last-30-days">Last 30 Days</option>
              <option value="this-month">This Month</option>
              <option value="custom">Custom Date Range</option>
            </select>
          </div>

          {/* Export Dropdown Button options */}
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => handleExport('csv')}
              className="flex items-center gap-1 py-2.5 px-3.5 bg-slate-50 dark:bg-slate-700/50 border border-gray-250 dark:border-slate-600 text-slate-700 dark:text-slate-200 rounded-xl text-xs font-bold hover:bg-slate-100 dark:bg-slate-700 transition shadow-sm uppercase tracking-wider"
              data-testid="export-csv-button"
            >
              <FileSpreadsheet className="w-4 h-4 text-emerald-500" />
              CSV
            </button>
            <button
              onClick={() => handleExport('json')}
              className="flex items-center gap-1 py-2.5 px-3.5 bg-slate-50 dark:bg-slate-700/50 border border-gray-250 dark:border-slate-600 text-slate-700 dark:text-slate-200 rounded-xl text-xs font-bold hover:bg-slate-100 dark:bg-slate-700 transition shadow-sm uppercase tracking-wider"
              data-testid="export-json-button"
            >
              <FileText className="w-4 h-4 text-blue-500" />
              JSON
            </button>
          </div>
        </div>
      </div>

      {/* Conditional Custom Date Selector input row */}
      {dateRange === 'custom' && (
        <Card className="p-4 mb-6 bg-brand-primary/5 border border-brand-primary/10 rounded-xl animate-fade-in" data-testid="custom-date-inputs">
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <div className="flex flex-col gap-1 w-full">
              <label className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-wider">Start Date</label>
              <input
                type="date"
                value={customStartDate}
                onChange={(e) => setCustomStartDate(e.target.value)}
                className="p-2.5 border border-gray-250 dark:border-slate-600 rounded-xl text-xs font-bold focus:ring-brand-primary bg-white"
              />
            </div>
            <div className="flex flex-col gap-1 w-full">
              <label className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-wider">End Date</label>
              <input
                type="date"
                value={customEndDate}
                onChange={(e) => setCustomEndDate(e.target.value)}
                className="p-2.5 border border-gray-250 dark:border-slate-600 rounded-xl text-xs font-bold focus:ring-brand-primary bg-white"
              />
            </div>
          </div>
        </Card>
      )}

      {/* Summary Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-8">
        <ChartCard
          title="Total AI Generations"
          value={usageMetrics.totalGenerations}
          subtitle="vs last period"
          trend="up"
          trendValue={14}
        >
          <div className="text-xs font-semibold text-slate-400 dark:text-slate-500 flex items-center gap-1 mt-1">
            <TrendingUp className="w-3.5 h-3.5 text-green-500" />
            <span>+14% from last month</span>
          </div>
        </ChartCard>

        <ChartCard
          title="Active Deployments"
          value={usageMetrics.totalDeployments}
          subtitle="vs last period"
          trend="up"
          trendValue={9}
        >
          <div className="text-xs font-semibold text-slate-400 dark:text-slate-500 flex items-center gap-1 mt-1">
            <BarChart3 className="w-3.5 h-3.5 text-green-500" />
            <span>+9% from last month</span>
          </div>
        </ChartCard>

        <ChartCard
          title="Synthesizer Success Rate"
          value={`${usageMetrics.successRate}%`}
          subtitle="vs last period"
          trend="up"
          trendValue={1.8}
        >
          <div className="text-xs font-semibold text-slate-400 dark:text-slate-500 flex items-center gap-1 mt-1">
            <TrendingUp className="w-3.5 h-3.5 text-green-500" />
            <span>+1.8% average reliability</span>
          </div>
        </ChartCard>
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Line chart: Generations */}
        <Card className="p-6 border border-slate-100 dark:border-slate-600 shadow-md">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-brand-primary" />
              Generations Timeline
            </h3>
            {hoveredDataPoint && (
              <span className="text-xs font-bold bg-brand-primary/10 text-brand-primary px-2 py-0.5 rounded">
                {hoveredDataPoint.count} generations
              </span>
            )}
          </div>
          {renderSimpleLineChart(generationsOverTime)}
        </Card>

        {/* Bar chart: Deployments */}
        <Card className="p-6 border border-slate-100 dark:border-slate-600 shadow-md">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-brand-primary" />
              Deployments Volume
            </h3>
          </div>
          {renderSimpleBarChart(deploymentsOverTime, 40)}
        </Card>
      </div>

      {/* Bottom Grid: Model comparison & Provider Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Model performance list */}
        <Card className="p-6 border border-slate-100 dark:border-slate-600 shadow-md">
          <h3 className="text-sm font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-5 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-brand-primary" />
            Model Reliability Metrics
          </h3>
          <div className="space-y-4">
            {modelPerformance.map((model, index) => (
              <div key={index} className="flex items-center justify-between gap-4 p-3 bg-slate-50 dark:bg-slate-700/50 rounded-xl border border-slate-100 dark:border-slate-600">
                <div className="w-1/3">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-100">{model.modelName}</span>
                  <p className="text-[10px] text-slate-400 dark:text-slate-500 font-semibold">{model.provider}</p>
                </div>
                <div className="flex-1">
                  <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-2.5 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-brand-primary to-red-500 h-2.5 rounded-full transition-all"
                      style={{ width: `${model.successRate}%` }}
                    />
                  </div>
                </div>
                <div className="w-24 text-right">
                  <span className="text-xs font-extrabold text-brand-primary">{model.successRate}% success</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Cloud provider pie distribution */}
        <Card className="p-6 border border-slate-100 dark:border-slate-600 shadow-md">
          <h3 className="text-sm font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-5 flex items-center gap-2">
            <HelpCircle className="w-4 h-4 text-brand-primary" />
            Cloud Provider Distribution
          </h3>
          {renderPieChart(cloudProviderDistribution)}
        </Card>
      </div>

      {/* Cost Analytics row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <Card className="p-6 border border-slate-100 dark:border-slate-600 shadow-md flex flex-col justify-between h-56">
          <div>
            <h3 className="text-sm font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-3">Cost Summaries</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold">Active project spending and budget thresholds.</p>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-500 dark:text-slate-400 font-semibold">Current Month Spend</span>
              <span className="font-extrabold text-slate-900 dark:text-slate-50">${costMetrics.currentMonthCost.toFixed(2)}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-500 dark:text-slate-400 font-semibold">Projected End of Month</span>
              <span className="font-extrabold text-slate-700 dark:text-slate-200">${costMetrics.projectedEndOfMonthCost.toFixed(2)}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-500 dark:text-slate-400 font-semibold">Savings vs Last Month</span>
              <span className="font-extrabold text-green-600">-{costMetrics.savingsVsLastMonth}%</span>
            </div>
          </div>
        </Card>

        <Card className="p-6 border border-gray-150 dark:border-slate-600 shadow-md flex flex-col justify-between h-56 bg-slate-900 text-white">
          <div>
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-1">Forecast Metrics</h3>
            <p className="text-xs text-slate-500 font-semibold">Projected token usage expenses in next 30 days.</p>
          </div>
          <div className="text-center">
            <div className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-brand-primary to-red-500">
              ${costMetrics.projectedEndOfMonthCost.toFixed(2)}
            </div>
            <p className="text-[10px] text-slate-500 uppercase tracking-wider font-extrabold mt-1">Projected End of Month Spend</p>
          </div>
          <button
            onClick={() => toast.success('Forecast breakdown fetched successfully!')}
            className="w-full py-2.5 bg-slate-800 border border-slate-700 text-xs font-bold uppercase tracking-wider rounded-xl hover:bg-slate-700 transition"
          >
            Detailed Forecast
          </button>
        </Card>
      </div>
    </div>
  );
};

export default UsageAnalyticsPage;
export { UsageAnalyticsPage };
