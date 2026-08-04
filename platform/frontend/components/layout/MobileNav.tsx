import React from 'react';
import { useAppStore } from '../../store/useAppStore';
import { View } from '../types';
import { LayoutDashboard, Terminal, RefreshCw, BarChart2, Settings } from 'lucide-react';

const MobileNav: React.FC = () => {
  const { currentView, navigate } = useAppStore();

  const navItems: { label: string; view: View; icon: React.ComponentType<any> }[] = [
    { label: 'Dashboard', view: 'dashboard', icon: LayoutDashboard },
    { label: 'Generator', view: 'generator', icon: Terminal },
    { label: 'Pipelines', view: 'pipeline-dashboard', icon: RefreshCw },
    { label: 'Analytics', view: 'usage-analytics', icon: BarChart2 },
    { label: 'Settings', view: 'settings', icon: Settings },
  ];

  return (
    <nav 
      className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-t border-slate-200 dark:border-slate-700 z-40 flex items-center justify-around px-2 shadow-lg"
      aria-label="Mobile Navigation"
    >
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = currentView === item.view || 
                         (item.view === 'pipeline-dashboard' && currentView.startsWith('pipeline')) ||
                         (item.view === 'settings' && ['settings', 'team-members', 'integration-hub', 'cloud-credentials', 'billing', 'developer', 'audit-log'].includes(currentView));

        return (
          <button
            key={item.view}
            onClick={() => navigate(item.view)}
            className={`flex flex-col items-center justify-center flex-1 h-full py-1.5 transition-colors relative ${
              isActive ? 'text-brand-primary dark:text-brand-primary font-bold' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
            }`}
          >
            {isActive && (
              <span className="absolute top-0 h-0.5 w-8 bg-brand-primary rounded-full" />
            )}
            <Icon className="h-5.5 w-5.5" />
            <span className="text-[10px] mt-1 tracking-tight truncate max-w-[64px]">
              {item.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
};

export default MobileNav;
