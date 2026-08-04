import React, { useState } from 'react';
import { DeploymentMode } from './types';

interface EnvironmentStatusBadgeProps {
  mode: DeploymentMode;
  size?: 'sm' | 'md';
  showLabel?: boolean;
  className?: string;
}

export const EnvironmentStatusBadge: React.FC<EnvironmentStatusBadgeProps> = ({
  mode,
  size = 'sm',
  showLabel = true,
  className = '',
}) => {
  const [showTooltip, setShowTooltip] = useState(false);

  // Config mapping for each mode
  const config = {
    aws: {
      label: 'AWS',
      dotColor: 'var(--color-env-aws)',
      bgColor: 'var(--color-env-aws-bg)',
      textColor: 'var(--color-env-aws)',
      tooltip: 'AWS — Deploy to real AWS accounts. Charges apply.',
      details: {
        provider: 'AWS (Production)',
        endpoint: 'aws.amazon.com',
        services: 'All Cloud Resources',
        mode: 'Real Cloud (Charges apply)',
      },
    },
    localstack: {
      label: 'LocalStack',
      dotColor: 'var(--color-env-localstack)',
      bgColor: 'var(--color-env-localstack-bg)',
      textColor: 'var(--color-env-localstack)',
      tooltip: 'LocalStack Community v3.4.0 — localhost:4566. No real charges.',
      details: {
        provider: 'LocalStack Community v3.4.0',
        endpoint: 'localhost:4566',
        services: 'S3, EC2, RDS, Lambda, IAM',
        mode: 'Simulation (Zero cost)',
      },
    },
    offline: {
      label: 'Offline',
      dotColor: 'var(--color-env-offline)',
      bgColor: 'var(--color-env-offline-bg)',
      textColor: 'var(--color-env-offline)',
      tooltip: 'Offline — Manual review mode. No automated deployment.',
      details: {
        provider: 'Offline Review Mode',
        endpoint: 'None (Local execution)',
        services: 'Advisor / Configs only',
        mode: 'Manual Review & Tofu apply',
      },
    },
  }[mode];

  const dotSize = size === 'sm' ? 'w-2 h-2' : 'w-2.5 h-2.5';
  const textSize = size === 'sm' ? 'text-xs' : 'text-sm font-semibold';
  const padding = size === 'sm' ? 'px-2 py-0.5' : 'px-3 py-1';
  const gap = size === 'sm' ? 'gap-1' : 'gap-1.5';

  return (
    <div
      className="relative inline-block select-none"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      onFocus={() => setShowTooltip(true)}
      onBlur={() => setShowTooltip(false)}
      tabIndex={0}
      aria-label={`Deployment environment: ${config.label}`}
    >
      {/* Badge Pill */}
      <span
        className={`inline-flex items-center rounded-full border transition-all duration-300 ${padding} ${gap} ${className}`}
        style={{
          backgroundColor: config.bgColor,
          borderColor: config.dotColor + '20', // subtle opacity for border
        }}
      >
        <span
          className={`rounded-full inline-block animate-pulse-subtle ${dotSize}`}
          style={{ backgroundColor: config.dotColor }}
        />
        {showLabel && (
          <span style={{ color: config.textColor }} className={`font-sans tracking-wide leading-none ${textSize}`}>
            {config.label}
          </span>
        )}
      </span>

      {/* Glassmorphic Premium Tooltip */}
      {showTooltip && (
        <div
          role="tooltip"
          className="absolute z-50 bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 bg-slate-900/95 dark:bg-slate-950/95 backdrop-blur-md border border-slate-700/50 rounded-xl p-3.5 shadow-xl text-left animate-in fade-in slide-in-from-bottom-2 duration-150 text-white"
        >
          <div className="flex items-center gap-2 mb-2">
            <span
              className="w-2.5 h-2.5 rounded-full inline-block"
              style={{ backgroundColor: config.dotColor }}
            />
            <h4 className="text-xs font-bold font-sans uppercase tracking-wider text-slate-300">
              Environment Details
            </h4>
          </div>
          <div className="space-y-1.5 text-[11px] font-sans text-slate-400">
            <div className="flex justify-between border-b border-slate-800 pb-1">
              <span className="font-semibold text-slate-500">Provider:</span>
              <span className="text-slate-200 font-bold text-right">{config.details.provider}</span>
            </div>
            <div className="flex justify-between border-b border-slate-800 pb-1">
              <span className="font-semibold text-slate-500">Endpoint:</span>
              <span className="text-slate-200 font-mono text-right">{config.details.endpoint}</span>
            </div>
            <div className="flex justify-between border-b border-slate-800 pb-1">
              <span className="font-semibold text-slate-500">Services:</span>
              <span className="text-slate-200 text-right">{config.details.services}</span>
            </div>
            <div className="flex justify-between pt-0.5">
              <span className="font-semibold text-slate-500">Mode:</span>
              <span className="text-slate-200 text-right font-medium">{config.details.mode}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EnvironmentStatusBadge;
