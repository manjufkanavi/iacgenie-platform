import React, { useState, useEffect } from 'react';
import { TriangleAlert, MonitorOff, X } from 'lucide-react';
import { DeploymentMode } from './types';

interface SandboxWarningBannerProps {
  mode: DeploymentMode;
  compact?: boolean;
  learnMoreUrl?: string | null;
}

export const SandboxWarningBanner: React.FC<SandboxWarningBannerProps> = ({
  mode,
  compact = true,
  learnMoreUrl = '/docs',
}) => {
  const [isDismissed, setIsDismissed] = useState(true); // default true until check passes
  const [isAnimatingOut, setIsAnimatingOut] = useState(false);

  // If environment target is 'aws', do not render banner at all
  const isSandbox = mode === 'localstack' || mode === 'offline';

  // Check localStorage dismiss expiration
  useEffect(() => {
    if (!isSandbox) {
      setIsDismissed(true);
      return;
    }

    const dismissedTimestamp = localStorage.getItem(`sandbox_banner_dismissed_${mode}`);
    if (dismissedTimestamp) {
      const dismissTime = new Date(dismissedTimestamp).getTime();
      const now = new Date().getTime();
      const twentyFourHours = 24 * 60 * 60 * 1000;

      if (now - dismissTime < twentyFourHours) {
        setIsDismissed(true);
        return;
      }
    }
    
    // Not dismissed or expired
    setIsDismissed(false);
  }, [mode, isSandbox]);

  const handleDismiss = () => {
    setIsAnimatingOut(true);
    // Wait for the exit animation to complete (200ms as per design token `--duration-banner-exit`)
    setTimeout(() => {
      localStorage.setItem(`sandbox_banner_dismissed_${mode}`, new Date().toISOString());
      setIsDismissed(true);
      setIsAnimatingOut(false);
    }, 200);
  };

  if (!isSandbox || isDismissed) return null;

  const isLocalStack = mode === 'localstack';
  const Icon = isLocalStack ? TriangleAlert : MonitorOff;

  // Variables mapping based on mode
  const styles = isLocalStack
    ? {
        bg: 'var(--color-banner-localstack-bg)',
        border: 'var(--color-banner-localstack-border)',
        text: 'var(--color-banner-localstack-text)',
        title: 'Simulation Mode Active: LocalStack',
        desc: 'Deploying to local emulated services at localhost:4566. No AWS charges will be incurred.',
        expandedDesc: 'Your pipeline is currently targeting LocalStack Community v3.4.0 running at localhost:4566. This environment emulates core AWS services (S3, EC2, RDS, Lambda, IAM) locally inside isolated Docker containers. Cost estimation is available under the pipeline cost analysis panel.',
      }
    : {
        bg: 'var(--color-banner-offline-bg)',
        border: 'var(--color-banner-offline-border)',
        text: 'var(--color-banner-offline-text)',
        title: 'Manual Mode Active: Offline',
        desc: 'IaC is generated for manual review only. Automated deployments are disabled.',
        expandedDesc: 'Your pipeline will generate Terraform/OpenTofu configurations for manual review and CLI provisioning only. No automated infrastructure changes will be deployed to any real cloud environment. You can download or review generated code packages in the Pipeline detail panel.',
      };

  if (compact) {
    return (
      <div
        role="alert"
        aria-live="polite"
        style={{
          backgroundColor: styles.bg,
          borderColor: styles.border,
          height: 'var(--size-banner-height-compact)',
        }}
        className={`w-full border-b px-4 flex items-center justify-between select-none overflow-hidden transition-all duration-300 z-30 ${
          isAnimatingOut
            ? 'animate-[banner-exit_200ms_var(--ease-default)_forwards]'
            : 'animate-[banner-enter_250ms_var(--ease-default)_forwards]'
        }`}
      >
        <div className="flex items-center gap-2 max-w-[90%] truncate">
          <Icon className="w-4.5 h-4.5 flex-shrink-0 animate-pulse-subtle" style={{ color: styles.text }} />
          <span
            style={{ color: styles.text }}
            className="text-xs font-sans font-bold tracking-wide truncate"
          >
            <span className="font-extrabold mr-1 border-r border-current pr-2">{styles.title}</span>
            <span className="hidden md:inline font-semibold">{styles.desc}</span>
          </span>
        </div>

        {/* Dismiss trigger */}
        <button
          onClick={handleDismiss}
          aria-label={`Dismiss ${mode} warning banner`}
          style={{ color: styles.text }}
          className="p-1 rounded-lg hover:bg-black/5 dark:hover:bg-white/5 transition flex items-center justify-center"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  // Expanded variant (settings page context)
  return (
    <div
      role="region"
      aria-label={`${mode} environment configuration warning`}
      style={{
        backgroundColor: styles.bg,
        borderColor: styles.border,
      }}
      className={`w-full border-l-4 rounded-xl p-5 shadow-sm overflow-hidden border transition-all duration-300 ${
        isAnimatingOut
          ? 'animate-[banner-exit_200ms_var(--ease-default)_forwards]'
          : 'animate-[banner-enter_250ms_var(--ease-default)_forwards]'
      }`}
    >
      <div className="flex gap-4 items-start">
        <div
          className="p-2 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5"
          style={{ backgroundColor: styles.border + '20', color: styles.text }}
        >
          <Icon className="w-5 h-5 animate-pulse-subtle" />
        </div>

        <div className="flex-1">
          <div className="flex justify-between items-center mb-1">
            <h4 style={{ color: styles.text }} className="text-sm font-extrabold uppercase tracking-wider font-sans">
              {styles.title}
            </h4>
            <button
              onClick={handleDismiss}
              aria-label="Dismiss banner"
              style={{ color: styles.text }}
              className="p-1 rounded-lg hover:bg-black/5 dark:hover:bg-white/5 transition"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <p style={{ color: styles.text }} className="text-xs font-medium font-sans leading-relaxed text-opacity-90">
            {styles.expandedDesc}
          </p>

          <div className="mt-4 flex gap-3.5 items-center">
            {learnMoreUrl && (
              <a
                href={learnMoreUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: styles.text,
                  borderColor: styles.text + '30',
                }}
                className="px-3 py-1.5 border rounded-lg text-[10px] font-sans font-extrabold uppercase tracking-wider hover:bg-black/5 dark:hover:bg-white/5 transition"
              >
                Learn More
              </a>
            )}
            <button
              onClick={handleDismiss}
              style={{ color: styles.text }}
              className="text-[10px] font-sans font-extrabold uppercase tracking-wider hover:underline"
            >
              Dismiss warning
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SandboxWarningBanner;
