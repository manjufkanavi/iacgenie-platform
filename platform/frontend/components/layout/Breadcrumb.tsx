import React from 'react';
import { useAppStore } from '../../store/useAppStore';
import { View } from '../../types';
import { ChevronRight, Home } from 'lucide-react';

const Breadcrumb: React.FC = () => {
  const { currentView, navigate } = useAppStore();

  const getBreadcrumbs = (view: View): { label: string; view?: View }[] => {
    const base = [{ label: 'Home', view: 'dashboard' as View }];

    switch (view) {
      case 'dashboard':
        return [{ label: 'Dashboard' }];
      case 'generator':
        return [...base, { label: 'Generator' }];
      case 'deployments':
        return [...base, { label: 'Deployments' }];
      case 'usage-analytics':
        return [...base, { label: 'Usage Analytics' }];
      case 'pipeline-dashboard':
        return [...base, { label: 'Pipelines' }];
      case 'clarify-agent':
        return [...base, { label: 'Pipelines', view: 'pipeline-dashboard' as View }, { label: 'Clarify' }];
      case 'generator-agent':
        return [...base, { label: 'Pipelines', view: 'pipeline-dashboard' as View }, { label: 'Generator Agent' }];
      case 'settings':
        return [...base, { label: 'Settings' }];
      case 'team-members':
        return [...base, { label: 'Settings', view: 'settings' as View }, { label: 'Team Members' }];
      case 'billing':
        return [...base, { label: 'Settings', view: 'settings' as View }, { label: 'Billing' }];
      case 'developer':
        return [...base, { label: 'Settings', view: 'settings' as View }, { label: 'Developer API' }];
      case 'audit-log':
        return [...base, { label: 'Settings', view: 'settings' as View }, { label: 'Audit Log' }];
      case 'human-review':
        return [...base, { label: 'Human Review Queue' }];
      case 'docs':
        return [...base, { label: 'Documentation' }];
      case 'api-docs':
        return [...base, { label: 'API reference' }];
      default:
        return [...base, { label: 'Overview' }];
    }
  };

  const crumbs = getBreadcrumbs(currentView);

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-bold text-slate-500 dark:text-slate-400 py-1 mb-2 select-none">
      {crumbs.map((crumb, index) => {
        const isLast = index === crumbs.length - 1;

        return (
          <React.Fragment key={index}>
            {index > 0 && <ChevronRight className="h-3.5 w-3.5 text-gray-350 flex-shrink-0" />}
            {isLast ? (
              <span className="text-brand-primary font-bold max-w-[120px] truncate" aria-current="page">
                {crumb.label}
              </span>
            ) : (
              <button
                onClick={() => crumb.view && navigate(crumb.view)}
                className="hover:text-gray-900 transition flex items-center gap-1 focus:outline-none"
              >
                {index === 0 && <Home className="h-3.5 w-3.5" />}
                <span>{crumb.label}</span>
              </button>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
};

export default Breadcrumb;
