
import React from 'react';

interface TabsProps {
  tabs: string[];
  activeTab: string;
  onTabClick: (tab: string) => void;
}

const Tabs: React.FC<TabsProps> = ({ tabs, activeTab, onTabClick }) => {
  return (
    <div>
      <div className="border-b border-slate-200 dark:border-slate-700">
        <nav className="-mb-px flex space-x-2 px-4" aria-label="Tabs">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => onTabClick(tab)}
              className={`${
                activeTab === tab
                  ? 'bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-slate-50 border-b-2 border-brand-primary'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-700'
              } rounded-t-lg whitespace-nowrap py-2 px-3 font-medium text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-brand-primary focus:ring-offset-2`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>
    </div>
  );
};

export default Tabs;
