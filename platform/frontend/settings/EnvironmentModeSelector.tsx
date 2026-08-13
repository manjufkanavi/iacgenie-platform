import React, { useState } from 'react';
import { Cloud, Server, MonitorOff, Loader2 } from 'lucide-react';
import { DeploymentMode } from '../types';

interface EnvironmentModeSelectorProps {
  mode: DeploymentMode;
  onModeChange: (mode: DeploymentMode) => void;
  disabled?: boolean;
  className?: string;
}

export const EnvironmentModeSelector: React.FC<EnvironmentModeSelectorProps> = ({
  mode,
  onModeChange,
  disabled = false,
  className = '',
}) => {
  const [transitioningMode, setTransitioningMode] = useState<DeploymentMode | null>(null);

  const handleSelect = async (cardMode: DeploymentMode) => {
    if (disabled || cardMode === mode || transitioningMode) return;

    setTransitioningMode(cardMode);
    // Simulate brief loading state (<1s) as requested in the interaction specs
    await new Promise((resolve) => setTimeout(resolve, 800));
    onModeChange(cardMode);
    setTransitioningMode(null);
  };

  const cards = [
    {
      id: 'aws' as DeploymentMode,
      name: 'AWS (Production)',
      icon: Cloud,
      description: 'Deploy to real AWS accounts. Run actual infrastructure provisioning. Charges apply.',
      endpoint: 'aws.amazon.com',
      activeColor: 'var(--color-env-aws)',
      activeBg: 'var(--color-env-aws-bg)',
    },
    {
      id: 'localstack' as DeploymentMode,
      name: 'LocalStack (Simulation)',
      icon: Server,
      description: 'Emulate AWS services locally. No real AWS charges. Safe for experimentation.',
      endpoint: 'localhost:4566',
      activeColor: 'var(--color-env-localstack)',
      activeBg: 'var(--color-env-localstack-bg)',
    },
    {
      id: 'offline' as DeploymentMode,
      name: 'Offline (Manual Review)',
      icon: MonitorOff,
      description: 'Generate IaC configuration without auto-applying. Review and deploy manually.',
      endpoint: 'No automated deployment',
      activeColor: 'var(--color-env-offline)',
      activeBg: 'var(--color-env-offline-bg)',
    },
  ];

  return (
    <div className={`space-y-4 ${className}`} role="radiogroup" aria-label="Deployment target selection">
      {/* Warning message if disabled (e.g., active pipeline running) */}
      {disabled && (
        <div className="p-3.5 bg-amber-50 dark:bg-amber-950/30 border border-amber-200/50 dark:border-amber-900/50 rounded-xl text-amber-800 dark:text-amber-300 text-xs font-semibold leading-relaxed animate-in fade-in duration-200">
          <span className="flex items-center gap-2">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            Switching deployment mode while a pipeline is running is disabled.
          </span>
        </div>
      )}

      {/* Main card list */}
      <div className="flex flex-col md:flex-row gap-4 w-full">
        {cards.map((card) => {
          const Icon = card.icon;
          const isActive = mode === card.id;
          const isTransitioning = transitioningMode === card.id;
          
          return (
            <div
              key={card.id}
              role="radio"
              aria-checked={isActive}
              aria-label={card.name}
              tabIndex={disabled ? -1 : 0}
              onClick={() => handleSelect(card.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleSelect(card.id);
                }
              }}
              style={{
                borderColor: isActive ? card.activeColor : 'var(--color-border-default)',
                borderLeftColor: isActive ? card.activeColor : 'var(--color-border-default)',
                borderLeftWidth: isActive ? '4px' : '1px',
              }}
              className={`flex-1 relative border rounded-2xl bg-white dark:bg-slate-800 p-5 cursor-pointer select-none transition-all duration-300 flex flex-col justify-between min-h-[190px] ${
                disabled
                  ? 'opacity-50 cursor-not-allowed pointer-events-none'
                  : isActive
                  ? 'shadow-md scale-[1.01] dark:shadow-slate-900/50'
                  : 'hover:shadow-lg hover:-translate-y-0.5 hover:border-slate-300 dark:hover:border-slate-600'
              }`}
            >
              {/* Spinner Overlay on selection change */}
              {isTransitioning && (
                <div className="absolute inset-0 bg-white/70 dark:bg-slate-800/70 backdrop-blur-[1px] flex flex-col items-center justify-center rounded-2xl z-10 animate-in fade-in duration-150">
                  <Loader2 className="w-8 h-8 text-brand-primary animate-spin" />
                  <span className="text-xs font-bold text-brand-primary mt-2 uppercase tracking-wide">
                    Switching...
                  </span>
                </div>
              )}

              {/* Top part: Icon + Title + Selected indicator */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div
                    className="p-2.5 rounded-xl flex items-center justify-center"
                    style={{
                      backgroundColor: isActive ? card.activeBg : 'var(--color-bg-muted)',
                      color: isActive ? card.activeColor : 'var(--color-text-muted)',
                    }}
                  >
                    <Icon className="w-5 h-5 transition-transform duration-300" />
                  </div>

                  {/* Radio Indicator */}
                  <div
                    style={{
                      borderColor: isActive ? card.activeColor : 'var(--color-border-strong)',
                      backgroundColor: isActive ? card.activeColor : 'transparent',
                    }}
                    className="w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all duration-300"
                  >
                    {isActive && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                  </div>
                </div>

                <h4 className="text-sm font-bold text-slate-900 dark:text-slate-50 font-sans tracking-wide">
                  {card.name}
                </h4>

                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 font-sans leading-relaxed font-semibold">
                  {card.description}
                </p>
              </div>

              {/* Bottom part: Endpoint Info */}
              <div className="mt-4 border-t border-slate-100 dark:border-slate-700/50 pt-3 flex justify-between items-center text-[10px] font-mono font-bold tracking-wide text-slate-400 dark:text-slate-500 select-all">
                <span>ENDPOINT:</span>
                <span className="text-slate-600 dark:text-slate-300 truncate max-w-[160px]">
                  {card.endpoint}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default EnvironmentModeSelector;
