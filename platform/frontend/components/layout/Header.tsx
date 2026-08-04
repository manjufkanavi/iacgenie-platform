import React, { useState, useEffect } from 'react';
import { View } from './types';
import Button from '../ui/Button';
import { Sun, Moon } from 'lucide-react';

interface HeaderProps {
  onNavigate: (view: View) => void;
  isAuthenticated?: boolean;
}

const Header: React.FC<HeaderProps> = ({ onNavigate, isAuthenticated = false }) => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isDark, setIsDark] = useState(() => {
    const stored = localStorage.getItem('darkMode');
    if (stored !== null) return stored === 'true';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
    localStorage.setItem('darkMode', String(isDark));
  }, [isDark]);

  const toggleDark = () => setIsDark((prev) => !prev);

  const navLinks = [
    { label: 'Features', href: '#features' },
    { label: 'Pricing', href: '#pricing' },
    { label: 'Documentation', view: 'docs' as View },
    { label: 'API Reference', view: 'api-docs' as View },
  ];

  const handleNavLinkClick = (link: typeof navLinks[number]) => {
    if (link.href) {
      if (window.location.pathname === '/') {
        const element = document.querySelector(link.href);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth' });
        }
      } else {
        window.location.href = `/${link.href}`;
      }
    } else if (link.view) {
      onNavigate(link.view);
    }
  };

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled
          ? 'bg-white/95 dark:bg-slate-950/95 backdrop-blur-md border-b border-slate-200 dark:border-slate-700 shadow-lg'
          : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 md:h-20">
          {/* Logo */}
          <button
            onClick={() => onNavigate('landing')}
            className="flex items-center gap-2 group"
          >
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-brand-primary to-red-500 flex items-center justify-center text-white font-bold group-hover:scale-105 transition-transform duration-200">
              T
            </div>
            <span className="text-xl font-bold text-slate-900 dark:text-slate-50">Iacgenie</span>
          </button>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <button
                key={link.label}
                onClick={() => handleNavLinkClick(link)}
                className="text-slate-600 dark:text-slate-300 hover:text-brand-primary dark:hover:text-brand-primary transition-colors duration-200 font-medium text-sm"
              >
                {link.label}
              </button>
            ))}
          </nav>

          {/* Desktop Auth Buttons */}
          <div className="hidden md:flex items-center gap-4">
            {isAuthenticated ? (
              <Button size="md" onClick={() => onNavigate('dashboard')}>
                Go to Dashboard
              </Button>
            ) : (
              <Button size="md" onClick={() => onNavigate('signin')}>
                Get Started Free
              </Button>
            )}
          </div>

          {/* Dark Mode Toggle */}
          <button
            onClick={toggleDark}
            className="text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-50 p-2 rounded-lg transition-colors"
            aria-label="Toggle dark mode"
          >
            {isDark ? (
              <Sun className="h-5 w-5" />
            ) : (
              <Moon className="h-5 w-5" />
            )}
          </button>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-50 p-2"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {isMobileMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-slate-200 dark:border-slate-700">
            <nav className="flex flex-col gap-4">
              {navLinks.map((link) => (
                <button
                  key={link.label}
                  onClick={() => {
                    handleNavLinkClick(link);
                    setIsMobileMenuOpen(false);
                  }}
                  className="text-slate-600 dark:text-slate-300 hover:text-brand-primary dark:hover:text-brand-primary transition-colors duration-200 font-medium text-left py-2"
                >
                  {link.label}
                </button>
              ))}
              <div className="flex flex-col gap-3 pt-4 border-t border-slate-200 dark:border-slate-700">
                {isAuthenticated ? (
                   <Button size="md" onClick={() => { onNavigate('dashboard'); setIsMobileMenuOpen(false); }}>
                    Go to Dashboard
                  </Button>
                ) : (
                  <Button size="md" onClick={() => { onNavigate('signin'); setIsMobileMenuOpen(false); }}>
                    Get Started Free
                  </Button>
                )}
              </div>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;