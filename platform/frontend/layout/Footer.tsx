import React from 'react';
import { View } from '../types';

interface FooterLink {
  label: string;
  view?: View;
  href?: string;
  toast?: string;
}

interface FooterColumn {
  title: string;
  links: FooterLink[];
}

interface FooterProps {
  onNavigate: (view: View) => void;
  showToast?: (message: string, type?: 'success' | 'info' | 'warning') => void;
}

const Footer: React.FC<FooterProps> = ({ onNavigate, showToast }) => {
  const footerColumns: FooterColumn[] = [
    {
      title: 'Product',
      links: [
        { label: 'Features', href: '#features' },
        { label: 'Pricing', href: '#pricing' },
        { label: 'Changelog', toast: 'Changelog coming soon' },
      ],
    },
    {
      title: 'Resources',
      links: [
        { label: 'Documentation', view: 'docs' },
        { label: 'API Reference', view: 'api-docs' },
        { label: 'Status Page', toast: 'Status Page coming soon' },
      ],
    },
    {
      title: 'Company',
      links: [
        { label: 'Blog', toast: 'Blog coming soon' },
        { label: 'Careers', toast: 'Careers coming soon' },
        { label: 'Contact Us', view: 'contact' },
      ],
    },
    {
      title: 'Legal',
      links: [
        { label: 'Terms of Service', view: 'terms' },
        { label: 'Privacy Policy', view: 'privacy' },
        { label: 'Cookie Policy', toast: 'Cookie Policy coming soon' },
      ],
    },
  ];

  const handleLinkClick = (link: FooterLink) => {
    if (link.toast) {
      if (showToast) {
        showToast(link.toast, 'info');
      } else {
        alert(link.toast);
      }
    } else if (link.href) {
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
    <footer className="bg-white dark:bg-slate-950 border-t border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 transition-colors duration-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Logo Section */}
        <div className="flex flex-col md:flex-row justify-between items-start gap-8 pb-8 border-b border-slate-200 dark:border-slate-700">
          <div className="flex-1">
            <h3 className="text-xl font-bold text-slate-900 dark:text-slate-50 mb-2">Iacgenie</h3>
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">Build cloud infrastructure at the speed of thought.</p>
          </div>

          {/* Columns Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 pt-4 md:pt-0 flex-1">
            {footerColumns.map((column, index) => (
              <div key={index} className="flex flex-col gap-3">
                <h4 className="text-slate-900 dark:text-slate-50 font-semibold">{column.title}</h4>
                <ul className="space-y-2">
                  {column.links.map((link, i) => (
                    <li key={i}>
                      <button onClick={() => handleLinkClick(link)} className="text-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-50 transition-colors">
                        {link.label}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom Section */}
        <div className="pt-8 border-t border-slate-200 dark:border-slate-700 mt-8 text-center text-sm">
          <p className="text-slate-400 dark:text-slate-500">&copy; {new Date().getFullYear()} Iacgenie. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
