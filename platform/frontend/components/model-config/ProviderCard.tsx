import React from 'react';
import { ProviderConfig } from '../.../constants/providers';
import Badge from '../ui/Badge';

interface ProviderCardProps {
  provider: ProviderConfig;
  isSelected: boolean;
  onClick: () => void;
}

export const ProviderCard: React.FC<ProviderCardProps> = ({ provider, isSelected, onClick }) => {
  return (
    <div
      role="radio"
      aria-checked={isSelected}
      aria-label={`Select ${provider.name} as your AI provider`}
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      className={`
        relative flex flex-col p-4 rounded-xl cursor-pointer min-h-[120px] transition-all duration-200
        border flex-grow
        ${isSelected 
          ? 'border-brand-primary border-2 bg-brand-primary/5 shadow-md ring-1 ring-brand-primary/20' 
          : 'border-slate-200 bg-white hover:border-brand-primary/50 hover:shadow-md dark:border-slate-700 dark:bg-slate-800 dark:hover:border-brand-primary/50'}
      `}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center space-x-3">
          {provider.logoUrl ? (
            <img src={provider.logoUrl} alt={`${provider.name} logo`} className="w-8 h-8 rounded-md" />
          ) : (
            <div className="w-8 h-8 rounded-md bg-slate-100 dark:bg-slate-700 flex items-center justify-center text-slate-500 font-bold">
              {provider.name.charAt(0)}
            </div>
          )}
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-50">{provider.name}</h3>
        </div>
      </div>
      
      <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 mt-1 mb-3 flex-grow">
        {provider.description}
      </p>

      {provider.badge && (
        <div className="mt-auto">
          <Badge variant={provider.badge.color === 'orange' ? 'warning' : provider.badge.color === 'blue' ? 'info' : provider.badge.color === 'green' ? 'success' : provider.badge.color === 'purple' ? 'info' : 'neutral'}>
            {provider.badge.label}
          </Badge>
        </div>
      )}

      {/* Focus ring indicator */}
      <div className="absolute inset-0 rounded-xl pointer-events-none group-focus-visible:ring-2 group-focus-visible:ring-brand-primary group-focus-visible:ring-offset-2"></div>
    </div>
  );
};
