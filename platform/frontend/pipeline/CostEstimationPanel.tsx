import React, { useState, useEffect } from 'react';
import { Cpu, HardDrive, Database, Key, RefreshCw, ChevronDown, ChevronUp, Tag } from 'lucide-react';
import { CostEstimationData, CostMetric } from '../types';
import type { DiffResource } from './DiffPanel';

interface CostEstimationPanelProps {
  metrics?: CostEstimationData;
  resources?: DiffResource[];
  currency?: 'USD' | 'EUR' | 'GBP';
  compact?: boolean;
  className?: string;
}

// Generate static heuristic costs based on resources
const generateHeuristicCosts = (resources: DiffResource[] = []): CostEstimationData => {
  let computeCost = 0;
  let storageCost = 0;
  let databaseCost = 0;
  let apiCost = 0;
  
  let lambdaCount = 0;
  let s3Count = 0;
  let rdsCount = 0;
  let apiCount = 0;

  resources.forEach(r => {
    if (r.type === 'aws_lambda_function') {
      lambdaCount++;
      computeCost += 2.50; // $2.50 base per lambda
    } else if (r.type === 'aws_s3_bucket') {
      s3Count++;
      storageCost += 0.05; // $0.05 per bucket
    } else if (r.type.startsWith('aws_db') || r.type.startsWith('aws_rds')) {
      rdsCount++;
      databaseCost += 18.47; // $18.47 per DB
    } else if (r.type === 'aws_api_gateway_rest_api' || r.type === 'aws_apigatewayv2_api') {
      apiCount++;
      apiCost += 4.50; // $4.50 per API Gateway
    } else if (r.type === 'aws_vpc') {
      computeCost += 0.00; // Free
    } else if (r.type === 'aws_security_group') {
      computeCost += 0.00; // Free
    } else if (r.costDelta) {
      // Fallback to provided costDelta if unknown type
      computeCost += r.costDelta;
    }
  });

  const totalRealCost = computeCost + storageCost + databaseCost + apiCost;
  // LocalStack simulated cost (only very specific services like certain mocked endpoints might charge, typically 0 or minimal)
  const totalSimulatedCost = 0.002;
  const savings = totalRealCost - totalSimulatedCost > 0 ? totalRealCost - totalSimulatedCost : 0;
  const savingsPercent = totalRealCost > 0 ? Math.round((savings / totalRealCost) * 100) : 0;

  return {
    metrics: {
      compute: {
        label: 'Compute',
        icon: 'cpu',
        estimatedCost: computeCost.toFixed(2),
        items: [
          { label: 'Compute Resources', value: lambdaCount, simulated: true },
          { label: 'Monthly Compute Cost', value: `$${computeCost.toFixed(2)}`, simulated: true },
        ],
      },
      storage: {
        label: 'Storage',
        icon: 'hard-drive',
        estimatedCost: storageCost.toFixed(3),
        items: [
          { label: 'S3 Buckets', value: s3Count, simulated: true },
          { label: 'S3 Monthly Cost', value: `$${storageCost.toFixed(3)}`, simulated: true },
        ],
      },
      database: {
        label: 'Database',
        icon: 'database',
        estimatedCost: databaseCost.toFixed(2),
        items: [
          { label: 'RDS Instances', value: rdsCount, realCost: `$${databaseCost.toFixed(2)}`, simulated: false },
          { label: 'RDS Monthly Cost', value: `$${databaseCost.toFixed(2)}`, realCost: `$${databaseCost.toFixed(2)}`, simulated: false },
        ],
      },
      api: {
        label: 'IAM / API',
        icon: 'key',
        estimatedCost: apiCost.toFixed(2),
        items: [
          { label: 'API Gateways', value: apiCount, realCost: `$${apiCost.toFixed(2)}`, simulated: false },
          { label: 'API Monthly Cost', value: `$${apiCost.toFixed(2)}`, simulated: false },
        ],
      },
    },
    totalRealCost,
    totalSimulatedCost,
    savings,
    savingsPercent,
    lastUpdated: new Date().toISOString(),
  };
};

export const CostEstimationPanel: React.FC<CostEstimationPanelProps> = ({
  metrics,
  resources,
  currency = 'USD',
  compact = false,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(!compact);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [pulseBadge, setPulseBadge] = useState(false);
  
  // Use heuristic costs if resources are provided, otherwise use provided metrics or generate empty heuristics
  const initialCostData = metrics || generateHeuristicCosts(resources);
  const [costData, setCostData] = useState<CostEstimationData>(initialCostData);

  // Re-calculate if resources prop changes
  useEffect(() => {
    if (resources && !metrics) {
      setCostData(generateHeuristicCosts(resources));
    }
  }, [resources, metrics]);

  // Currency Formatter
  const formatCost = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
    }).format(value);
  };

  // Simulating live refresh with pulse badges and micro updates based on current resources
  const handleRefresh = async () => {
    if (isRefreshing) return;
    
    setIsRefreshing(true);
    // Simulate API network latency of 600ms
    await new Promise((resolve) => setTimeout(resolve, 600));

    // Refresh using the heuristic model
    const newData = generateHeuristicCosts(resources);
    setCostData({
      ...newData,
      lastUpdated: new Date().toISOString(),
    });

    setIsRefreshing(false);
    
    // Trigger design-token `cost-pulse` on badge
    setPulseBadge(true);
    setTimeout(() => setPulseBadge(false), 1500); // matches --duration-cost-pulse (1.5s)
  };

  // Map icon name to Lucide components
  const renderIcon = (iconName: string, activeColorClass: string) => {
    const classStyle = `w-4 h-4 ${activeColorClass}`;
    switch (iconName) {
      case 'cpu':
        return <Cpu className={classStyle} />;
      case 'hard-drive':
        return <HardDrive className={classStyle} />;
      case 'database':
        return <Database className={classStyle} />;
      case 'key':
        return <Key className={classStyle} />;
      default:
        return <Cpu className={classStyle} />;
    }
  };

  // Pulse badge once on mount
  useEffect(() => {
    setPulseBadge(true);
    const timer = setTimeout(() => setPulseBadge(false), 1500);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div
      role="region"
      aria-label="Cost estimation for current pipeline run"
      className={`border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-2xl shadow-md overflow-hidden ${className}`}
    >
      {/* Header Bar */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 dark:border-slate-700 select-none bg-slate-50/50 dark:bg-slate-900/20">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 bg-emerald-500 rounded-full animate-pulse-subtle" />
          <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wider font-sans">
            LocalStack Cost Estimate
          </h3>
        </div>

        <div className="flex items-center gap-2">
          {/* Refresh Action */}
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            aria-label="Refresh cost estimation"
            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-750 text-slate-400 hover:text-slate-650 dark:hover:text-slate-200 bg-white dark:bg-slate-800 transition flex items-center justify-center cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-brand-primary' : ''}`} />
          </button>

          {/* Toggle Expand Action (hidden in compact mode) */}
          {!compact && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              aria-label={isExpanded ? 'Collapse section' : 'Expand section'}
              className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-750 text-slate-400 hover:text-slate-650 dark:hover:text-slate-200 bg-white dark:bg-slate-800 transition flex items-center justify-center cursor-pointer"
            >
              {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          )}
        </div>
      </div>

      {/* Summary / Collapsed row */}
      <div className="px-5 py-3.5 border-b border-slate-100 dark:border-slate-700/50 bg-slate-50/20 dark:bg-slate-900/10 flex flex-wrap items-center justify-between gap-3 text-xs select-none">
        <div className="flex items-center gap-4 text-slate-500 dark:text-slate-400 font-semibold font-sans">
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-500" />
            Mode: <strong className="text-slate-750 dark:text-slate-200">LocalStack Simulation</strong>
          </span>
          <span className="hidden sm:inline border-l border-slate-200 dark:border-slate-700 h-3" />
          <span className="hidden sm:inline">
            Total Real AWS Est: <strong className="text-slate-750 dark:text-slate-200">{formatCost(costData.totalRealCost)}</strong>
          </span>
        </div>

        {/* Savings Badge */}
        <span
          style={{
            backgroundColor: 'var(--color-cost-savings-bg)',
            color: 'var(--color-cost-savings)',
          }}
          className={`px-3 py-1 rounded-full font-bold inline-flex items-center gap-1.5 text-xs transition-transform duration-300 ${
            pulseBadge ? 'animate-[cost-pulse_1.5s_var(--ease-smooth)_infinite]' : ''
          }`}
          aria-label={`Savings of ${formatCost(costData.savings)} (${costData.savingsPercent}%)`}
        >
          <Tag className="w-3 h-3" />
          Estimated Savings: {formatCost(costData.savings)} ({costData.savingsPercent}%)
        </span>
      </div>

      {/* Expanded Breakdown area */}
      {isExpanded && !compact && (
        <div className="p-5 space-y-5 animate-[console-log-enter_300ms_var(--ease-default)_forwards]">
          {/* 2x2 responsive Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(Object.keys(costData.metrics) as CostMetric[]).map((key) => {
              const metric = costData.metrics[key];
              
              return (
                <div
                  key={key}
                  className="p-4 border border-slate-200/60 dark:border-slate-700/60 bg-slate-50/30 dark:bg-slate-900/30 rounded-xl flex flex-col justify-between"
                  role="group"
                  aria-label={`${metric.label} metrics`}
                >
                  <div>
                    {/* Category Title */}
                    <div className="flex items-center justify-between mb-3.5 pb-2 border-b border-slate-100 dark:border-slate-800/80">
                      <span className="flex items-center gap-2 text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wide">
                        {renderIcon(metric.icon, 'text-slate-500 dark:text-slate-400')}
                        {metric.label}
                      </span>
                      <span className="text-xs font-mono font-bold text-slate-400 dark:text-slate-500">
                        {metric.estimatedCost === '0.00' ? (
                          <span className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 text-[9px] text-slate-500 rounded font-sans uppercase">
                            Simulated
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.5 bg-emerald-50 dark:bg-emerald-950/40 text-[9px] text-emerald-600 rounded font-sans uppercase">
                            Real AWS
                          </span>
                        )}
                      </span>
                    </div>

                    {/* Category Items */}
                    <div className="space-y-2 select-text">
                      {metric.items.map((item, idx) => (
                        <div key={idx} className="flex justify-between items-center text-xs font-sans leading-relaxed">
                          <span className="text-slate-500 dark:text-slate-400 font-semibold">
                            {item.label}
                          </span>
                          <span className="text-slate-850 dark:text-slate-200 font-bold font-mono">
                            {item.value}
                            {item.simulated && (
                              <span className="ml-1 text-[9px] text-slate-400 font-normal uppercase select-none">
                                (simulated)
                              </span>
                            )}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Estimated cost box */}
                  <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/50 flex justify-between items-center text-xs font-sans font-bold">
                    <span className="text-slate-400">Category Total:</span>
                    <span
                      style={{
                        color: metric.estimatedCost === '0.00' ? 'var(--color-cost-label)' : 'var(--color-cost-total)',
                      }}
                      className="font-mono text-sm"
                    >
                      {formatCost(parseFloat(metric.estimatedCost))}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Expanded Bottom Row: Total Estimation Row */}
          <div
            style={{
              backgroundColor: 'var(--color-cost-total-bg)',
              borderColor: 'var(--color-cost-total)30',
            }}
            className="border p-4.5 rounded-xl flex flex-col sm:flex-row justify-between items-center gap-3 select-none"
          >
            <div className="text-center sm:text-left">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-0.5">
                Total Real AWS Estimate
              </h4>
              <p className="text-[10px] font-semibold text-slate-400">
                Accrued monthly equivalent based on calculated plan resources.
              </p>
            </div>

            <div className="flex items-center gap-5">
              <div className="text-center sm:text-right border-r border-slate-200/50 pr-5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide block mb-0.5">
                  AWS Equivalent
                </span>
                <span className="text-xl font-mono font-black text-slate-800 dark:text-slate-200">
                  {formatCost(costData.totalRealCost)}
                </span>
              </div>
              <div className="text-center sm:text-right">
                <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wide block mb-0.5">
                  Saved via Simulation
                </span>
                <span
                  style={{ color: 'var(--color-cost-total)' }}
                  className="text-xl font-mono font-black"
                >
                  {formatCost(costData.savings)}
                </span>
              </div>
            </div>
          </div>

          {/* Last updated summary info */}
          <div className="text-right text-[9px] font-mono font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide select-none">
            LAST SIMULATED UPDATED: {new Date(costData.lastUpdated).toLocaleTimeString()} • REFRESH IS AVAILABLE
          </div>
        </div>
      )}
    </div>
  );
};

export default CostEstimationPanel;
