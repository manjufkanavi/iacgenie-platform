import React, { useState } from 'react';
import { useAppStore } from '.././store/useAppStore';
import { ChevronDown, ChevronRight, ChevronLeft, LayoutDashboard, Wrench, Rocket, BarChart3, Workflow, Settings, CreditCard, Code2, FileText, CheckCircle2, Book, FileCode, LogOut } from 'lucide-react';

interface NavItemProps {
  icon: React.ReactNode;
  label: string;
  isActive?: boolean;
  isCollapsed?: boolean;
  onClick: () => void;
  className?: string;
  viewName?: string;
}

const NavItem: React.FC<NavItemProps> = ({
  icon,
  label,
  isActive = false,
  isCollapsed = false,
  onClick,
  className = '',
  viewName = ''
}) => {
  const baseClasses = 'w-full flex items-center py-2.5 text-sm font-medium rounded-lg transition-colors text-left group relative focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-2';

  const stateClasses = isActive
    ? 'text-slate-900 dark:text-slate-50 bg-brand-primary-subtle font-semibold'
    : 'text-slate-600 dark:text-slate-400 hover:text-slate-950 dark:hover:text-slate-50 hover:bg-slate-50 dark:hover:bg-slate-700/50';

  return (
    <div className="relative">
      {isActive && (
        <div className="absolute left-0 top-1/2 -translate-y-1/2 h-6 w-[3px] bg-brand-primary rounded-r-[2px]" />
      )}
      <button
        onClick={onClick}
        data-testid={`sidebar-item-${viewName || 'btn'}`}
        className={`${baseClasses} ${stateClasses} ${isCollapsed ? 'justify-center px-0' : 'px-4'} ${className}`}
        title={isCollapsed ? label : undefined}
      >
        <span className={`w-6 h-6 flex-shrink-0 flex items-center justify-center ${isActive ? 'text-brand-primary' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'}`}>
          {icon}
        </span>
        {!isCollapsed && <span className="ml-3 truncate">{label}</span>}
      </button>
    </div>
  );
};

interface SidebarProps {
  isSidebarCollapsed?: boolean;
  onToggleSidebar?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ 
  isSidebarCollapsed = false, 
  onToggleSidebar 
}) => {
  const { currentView, navigate, signOut } = useAppStore();

  // Subsection expansion states
  const [sections, setSections] = useState({
    workspace: true,
    pipelines: true,
    manage: true,
    resources: false,
  });

  const toggleSection = (section: keyof typeof sections) => {
    if (isSidebarCollapsed) return; // Disallow collapsing sub-sections if sidebar is already mini
    setSections(prev => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const renderSectionHeader = (name: keyof typeof sections, label: string) => {
    if (isSidebarCollapsed) {
      return <div className="h-px bg-slate-200 dark:bg-slate-700 my-4" />;
    }

    const isOpen = sections[name];
    return (
      <button
        onClick={() => toggleSection(name)}
        data-testid={`sidebar-section-toggle-${name}`}
        className="w-full flex items-center justify-between px-4 mt-6 mb-2 text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider hover:text-slate-600 dark:hover:text-slate-300 transition focus:outline-none"
      >
        <span>{label}</span>
        {isOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
      </button>
    );
  };

  return (
    <aside 
      data-testid="sidebar"
      aria-label="Workspace navigation"
      className={`hidden md:flex flex-col bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-700 transition-all duration-300 relative select-none h-screen ${
        isSidebarCollapsed ? 'w-20' : 'w-64'
      }`}
    >
      {/* Brand Header Logo */}
      <div className="flex items-center h-16 flex-shrink-0 px-4 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 justify-between">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div className="h-8 w-8 rounded-lg bg-brand-primary flex items-center justify-center text-white font-bold flex-shrink-0">
            T
          </div>
          {!isSidebarCollapsed && (
            <span className="text-slate-900 dark:text-slate-50 text-lg font-black tracking-tight animate-in fade-in duration-200">
              Iacgenie
            </span>
          )}
        </div>

        {/* Sidebar Collapse Toggle Button */}
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="p-1 rounded bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-600 text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 transition"
            aria-label={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isSidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        )}
      </div>

      {/* Main Nav Items Viewport */}
      <div className="flex-1 flex flex-col justify-between overflow-y-auto p-3">
        <div>
          {/* Workspace Group */}
          {renderSectionHeader('workspace', 'Workspace')}
          {(isSidebarCollapsed || sections.workspace) && (
            <nav className="space-y-1" data-testid="sidebar-section-workspace">
              <NavItem viewName="dashboard" icon={<LayoutDashboard className="h-4 w-4" />} label="Dashboard" isCollapsed={isSidebarCollapsed} isActive={currentView === 'dashboard'} onClick={() => navigate('dashboard')} />
              <NavItem viewName="generator" icon={<Wrench className="h-4 w-4" />} label="Generator" isCollapsed={isSidebarCollapsed} isActive={currentView === 'generator'} onClick={() => navigate('generator')} />
              <NavItem viewName="deployments" icon={<Rocket className="h-4 w-4" />} label="Deployments" isCollapsed={isSidebarCollapsed} isActive={currentView === 'deployments'} onClick={() => navigate('deployments')} />
              <NavItem viewName="usage-analytics" icon={<BarChart3 className="h-4 w-4" />} label="Usage Analytics" isCollapsed={isSidebarCollapsed} isActive={currentView === 'usage-analytics'} onClick={() => navigate('usage-analytics')} />
            </nav>
          )}

          {/* Workflows Group */}
          {renderSectionHeader('pipelines', 'Workflows')}
          {(isSidebarCollapsed || sections.pipelines) && (
            <nav className="space-y-1" data-testid="sidebar-section-pipelines">
              <NavItem viewName="pipeline-dashboard" icon={<Workflow className="h-4 w-4" />} label="Runs" isCollapsed={isSidebarCollapsed} isActive={currentView === 'pipeline-dashboard'} onClick={() => navigate('pipeline-dashboard')} />
              <NavItem viewName="session-manager" icon={<Workflow className="h-4 w-4" />} label="Session Manager" isCollapsed={isSidebarCollapsed} isActive={currentView === 'session-manager'} onClick={() => navigate('session-manager')} />
            </nav>
          )}

          {/* Manage Group */}
          {renderSectionHeader('manage', 'Manage')}
          {(isSidebarCollapsed || sections.manage) && (
            <nav className="space-y-1" data-testid="sidebar-section-manage">
              <NavItem viewName="settings" icon={<Settings className="h-4 w-4" />} label="Project Settings" isCollapsed={isSidebarCollapsed} isActive={currentView === 'settings'} onClick={() => navigate('settings')} />
              <NavItem viewName="billing" icon={<CreditCard className="h-4 w-4" />} label="Billing" isCollapsed={isSidebarCollapsed} isActive={currentView === 'billing'} onClick={() => navigate('billing')} />
              <NavItem viewName="developer" icon={<Code2 className="h-4 w-4" />} label="Developer" isCollapsed={isSidebarCollapsed} isActive={currentView === 'developer'} onClick={() => navigate('developer')} />
              <NavItem viewName="audit-log" icon={<FileText className="h-4 w-4" />} label="Audit Log" isCollapsed={isSidebarCollapsed} isActive={currentView === 'audit-log'} onClick={() => navigate('audit-log')} />
              <NavItem viewName="human-review" icon={<CheckCircle2 className="h-4 w-4" />} label="Human Review" isCollapsed={isSidebarCollapsed} isActive={currentView === 'human-review'} onClick={() => navigate('human-review')} />
            </nav>
          )}

          {/* Resources Group */}
          {renderSectionHeader('resources', 'Resources')}
          {(isSidebarCollapsed || sections.resources) && (
            <nav className="space-y-1" data-testid="sidebar-section-resources">
              <NavItem viewName="docs" icon={<Book className="h-4 w-4" />} label="Documentation" isCollapsed={isSidebarCollapsed} isActive={currentView === 'docs'} onClick={() => navigate('docs')} />
              <NavItem viewName="api-docs" icon={<FileCode className="h-4 w-4" />} label="API Reference" isCollapsed={isSidebarCollapsed} isActive={currentView === 'api-docs'} onClick={() => navigate('api-docs')} />
            </nav>
          )}
        </div>

        {/* Footer Actions */}
        <div className="mt-6 pt-4 border-t border-slate-200 dark:border-slate-700">
          <nav className="space-y-1">
            <NavItem
              viewName="signout"
              icon={<LogOut className="h-4 w-4" />}
              label="Sign Out"
              isCollapsed={isSidebarCollapsed}
              onClick={signOut}
              className="text-red-500 hover:text-red-600 dark:hover:bg-red-950/30 hover:bg-red-50"
            />
          </nav>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;