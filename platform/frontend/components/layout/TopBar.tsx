import React, { useState, useRef, useEffect } from 'react';
import { useAppStore } from '../store/useAppStore';
import ProjectDropdown from './ProjectDropdown';
import NotificationBell from './NotificationBell';
import SearchModal from './SearchModal';
import { Search, Sun, Moon, LogOut, User, Menu } from 'lucide-react';

interface TopBarProps {
  onToggleMobileSidebar: () => void;
}

const TopBar: React.FC<TopBarProps> = ({ onToggleMobileSidebar }) => {
  const { user, signOut, navigate, currentView } = useAppStore();
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);
  
  const [isDark, setIsDark] = useState(() => {
    const stored = localStorage.getItem('darkMode');
    if (stored !== null) return stored === 'true';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
    localStorage.setItem('darkMode', String(isDark));
  }, [isDark]);

  const toggleDark = () => setIsDark((prev) => !prev);

  // Handle Cmd+K global key binding for search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Handle profile dropdown click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setIsProfileOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <>
      <header className="h-16 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-4 md:px-6 flex items-center justify-between sticky top-0 z-40 select-none shadow-sm">
        
        {/* Left Side: Mobile Menu Button + Project Switcher */}
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleMobileSidebar}
            className="p-2 -ml-2 rounded-lg text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 md:hidden hover:bg-slate-50 dark:hover:bg-slate-700 border border-transparent hover:border-slate-200 dark:hover:border-slate-600"
            aria-label="Toggle mobile menu"
          >
            <Menu className="h-5 w-5" />
          </button>
          
          <ProjectDropdown />
        </div>

        {/* Right Side: Search, Theme, Notifications, User Menu */}
        <div className="flex items-center gap-2">
          {currentView !== 'generator' && (
            <>
              {/* Spotlight Search Activator */}
              <button
                onClick={() => setIsSearchOpen(true)}
                data-testid="top-bar-search-trigger"
                className="hidden sm:flex items-center gap-2.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600 hover:border-slate-300 dark:hover:border-slate-500 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition text-xs font-semibold w-48 text-left mr-2 bg-white dark:bg-slate-900"
              >
                <Search className="h-4 w-4 text-slate-400 dark:text-slate-500" />
                <span className="flex-1">Search settings...</span>
                <kbd className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded font-sans text-[10px] text-slate-400 dark:text-slate-500 uppercase tracking-widest font-bold">
                  ⌘K
                </kbd>
              </button>
              
              {/* Mobile search icon */}
              <button
                onClick={() => setIsSearchOpen(true)}
                className="sm:hidden p-2 rounded-lg text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 border border-transparent hover:border-slate-200 dark:hover:border-slate-600 transition"
                aria-label="Open search menu"
              >
                <Search className="h-5 w-5" />
              </button>
            </>
          )}

          {/* Theme toggler */}
          <button
            onClick={toggleDark}
            className="p-2 rounded-lg text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 border border-transparent hover:border-slate-200 dark:hover:border-slate-600 transition"
            aria-label="Toggle theme mode"
          >
            {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>

          {/* Alert Notification System */}
          <NotificationBell />

          <div className="h-6 w-px bg-slate-200 dark:bg-slate-700 mx-1 hidden sm:block" />

          {/* User profile option */}
          <div className="relative" ref={profileRef}>
            <button
              onClick={() => setIsProfileOpen(!isProfileOpen)}
              data-testid="top-bar-user-menu"
              className="flex items-center gap-2 p-1 rounded-lg border border-transparent hover:border-slate-200 dark:hover:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700 transition"
              aria-label="User avatar profile menu"
            >
              <img
                src={user?.avatarUrl || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=256&auto=format&fit=crop'}
                alt={user?.name || 'User profile'}
                className="h-8 w-8 rounded-full object-cover ring-1 ring-brand-primary/25"
              />
            </button>

            {isProfileOpen && (
              <div
                className="absolute right-0 mt-2 w-56 rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 shadow-xl z-55 overflow-hidden py-1 animate-in fade-in slide-in-from-top-2 duration-200"
                role="menu"
              >
                <div className="px-4 py-2.5 border-b border-slate-100 dark:border-slate-600">
                  <div className="text-xs font-bold text-slate-800 dark:text-slate-100 truncate">{user?.name || 'Iacgenie User'}</div>
                  <div className="text-[10px] text-slate-400 dark:text-slate-500 truncate mt-0.5">{user?.email || 'user@iacgenie.ai'}</div>
                </div>

                <div className="py-1">
                  <button
                    onClick={() => {
                      setIsProfileOpen(false);
                      navigate('settings');
                    }}
                    role="menuitem"
                    className="w-full flex items-center gap-2 px-4 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition"
                  >
                    <User className="h-4 w-4 text-slate-400 dark:text-slate-500" />
                    <span>Project Settings</span>
                  </button>
                </div>

                <div className="border-t border-slate-100 dark:border-slate-600 mt-1 pt-1 bg-slate-50/50 dark:bg-slate-700/30">
                  <button
                    onClick={() => {
                      setIsProfileOpen(false);
                      signOut();
                    }}
                    role="menuitem"
                    className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 hover:text-red-700 dark:hover:text-red-300 transition font-semibold"
                  >
                    <LogOut className="h-4 w-4 text-red-400 dark:text-red-500" />
                    <span>Sign Out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Cmd+K modal launcher portal */}
      <SearchModal isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} />
    </>
  );
};

export default TopBar;
