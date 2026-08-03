import React, { KeyboardEvent } from 'react';

export interface TabDefinition {
  key: string;
  label: string;
  icon?: React.ReactNode;
  count?: number;
  disabled?: boolean;
}

interface OpenTofuTabPanelProps {
  tabs: TabDefinition[];
  activeTab: string;
  onTabChange: (key: string) => void;
  className?: string;
}

export const OpenTofuTabPanel: React.FC<OpenTofuTabPanelProps> = ({
  tabs,
  activeTab,
  onTabChange,
  className = '',
}) => {
  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>, index: number) => {
    let targetIndex = -1;
    if (e.key === 'ArrowRight') {
      targetIndex = (index + 1) % tabs.length;
    } else if (e.key === 'ArrowLeft') {
      targetIndex = (index - 1 + tabs.length) % tabs.length;
    }

    if (targetIndex !== -1) {
      const targetTab = tabs[targetIndex];
      if (!targetTab.disabled) {
        onTabChange(targetTab.key);
        // Find and focus the next active button
        const buttons = document.querySelectorAll<HTMLButtonElement>('[role="tab"]');
        buttons[targetIndex]?.focus();
      }
    }
  };

  return (
    <div className={`flex flex-col border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-white dark:bg-slate-900 ${className}`}>
      
      {/* Tabs Header */}
      <div 
        className="flex border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 overflow-x-auto select-none"
        role="tablist"
        aria-label="OpenTofu outputs tabs"
      >
        {tabs.map((tab, idx) => {
          const isActive = tab.key === activeTab;
          return (
            <button
              key={tab.key}
              role="tab"
              id={`tab-${tab.key}`}
              aria-selected={isActive}
              aria-controls={`panel-${tab.key}`}
              disabled={tab.disabled}
              onClick={() => onTabChange(tab.key)}
              onKeyDown={(e) => handleKeyDown(e, idx)}
              className={`flex items-center gap-2 px-5 py-3.5 text-xs font-bold transition-all relative border-b-2 outline-none cursor-pointer ${
                isActive
                  ? 'border-[var(--color-brand-primary)] text-[var(--color-text-primary)] dark:text-white'
                  : tab.disabled
                  ? 'border-transparent text-[var(--color-text-muted)] cursor-not-allowed'
                  : 'border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-slate-300 dark:hover:border-slate-700'
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
              
              {/* Count / Status indicator badge */}
              {tab.count !== undefined && tab.count > 0 && (
                <span className="flex items-center justify-center min-w-4 h-4 rounded-full bg-[var(--color-brand-primary)] text-white text-[9px] px-1 select-none font-bold">
                  {tab.count > 9 ? '9+' : tab.count}
                </span>
              )}

              {/* Success/Pending green dot dot */}
              {tab.count === 0 && (
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-status-success)] shrink-0 select-none animate-[indicator-pulse_1.5s_infinite]"></span>
              )}
            </button>
          );
        })}
      </div>

    </div>
  );
};

export default OpenTofuTabPanel;
