import React, { useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import MobileNav from './MobileNav';
import { X } from 'lucide-react';
import { useAppStore } from '.././store/useAppStore';
import SandboxWarningBanner from '../common/SandboxWarningBanner';

interface LayoutShellProps {
  children: React.ReactNode;
}

const LayoutShell: React.FC<LayoutShellProps> = ({ children }) => {
  const { currentView, deploymentMode } = useAppStore();
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    const cached = localStorage.getItem('sidebarCollapsed');
    return cached === 'true';
  });
  
  // Mobile drawers status
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  const toggleSidebar = () => {
    setIsSidebarCollapsed(prev => {
      const next = !prev;
      localStorage.setItem('sidebarCollapsed', String(next));
      return next;
    });
  };

  // Close mobile sidebar on route change
  useEffect(() => {
    setIsMobileSidebarOpen(false);
  }, [currentView]);

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-slate-900 overflow-hidden font-sans text-gray-800 antialiased">
      
      {/* Desktop Sidebar: stays inline */}
      <Sidebar 
        isSidebarCollapsed={isSidebarCollapsed} 
        onToggleSidebar={toggleSidebar} 
      />

      {/* Mobile Drawer Sidebar Backing Overlay */}
      {isMobileSidebarOpen && (
        <div 
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 md:hidden animate-in fade-in duration-200"
          onClick={() => setIsMobileSidebarOpen(false)}
        />
      )}

      {/* Mobile Slide-out Drawer Sidebar Container */}
      <div 
        className={`fixed top-0 bottom-0 left-0 w-64 bg-white z-50 md:hidden flex flex-col shadow-2xl transition-transform duration-300 transform ${
          isMobileSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between h-16 px-4 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-brand-primary flex items-center justify-center text-white font-bold">
              T
            </div>
            <span className="text-slate-900 dark:text-slate-50 text-lg font-black tracking-tight">
              Iacgenie
            </span>
          </div>
          <button
            onClick={() => setIsMobileSidebarOpen(false)}
            className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 transition"
            aria-label="Close drawer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        
        {/* Render standard expanded sidebar inside mobile drawer */}
        <div className="flex-1 overflow-y-auto">
          <Sidebar isSidebarCollapsed={false} />
        </div>
      </div>

      {/* Right Side Content Viewport Frame */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar controls */}
        <TopBar onToggleMobileSidebar={() => setIsMobileSidebarOpen(true)} />

        {/* Global Sandbox Warning Banner */}
        <SandboxWarningBanner mode={deploymentMode} compact={true} />

        {/* Scrollable Main Area Viewport */}
        <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-8 pb-24 md:pb-8" role="main">
          <div className="max-w-7xl mx-auto h-full">
            {children}
          </div>
        </main>
      </div>

      {/* Mobile bottom quick nav menu */}
      <MobileNav />
    </div>
  );
};

export default LayoutShell;
