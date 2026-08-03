import React from 'react';
import Breadcrumb from './Breadcrumb';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

const PageHeader: React.FC<PageHeaderProps> = ({ title, subtitle, actions }) => {
  return (
    <div className="mb-6 flex flex-col md:flex-row md:items-start md:justify-between gap-4 animate-in fade-in slide-in-from-top-2 duration-300">
      <div className="flex-1 min-w-0">
        <Breadcrumb />
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50 md:text-3xl">
          {title}
        </h1>
        {subtitle && (
          <p className="mt-1.5 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
            {subtitle}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex flex-shrink-0 flex-wrap items-center gap-3 md:mt-6">
          {actions}
        </div>
      )}
    </div>
  );
};

export default PageHeader;
