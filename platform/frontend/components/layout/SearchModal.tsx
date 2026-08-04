import React, { useState, useEffect, useRef } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { Search, Folder, FileText, Settings, ArrowRight } from 'lucide-react';
import { View } from '../types';

interface SearchItem {
  id: string;
  title: string;
  description: string;
  category: 'page' | 'project' | 'settings';
  view?: View;
  action?: () => void;
}

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SearchModal: React.FC<SearchModalProps> = ({ isOpen, onClose }) => {
  const { projects, setCurrentProjectId, navigate } = useAppStore();
  const [query, setQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<'all' | 'page' | 'project' | 'settings'>('all');
  const [selectedIndex, setSelectedIndex] = useState(0);
  
  const modalRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Search items list
  const getSearchItems = (): SearchItem[] => {
    const pages: SearchItem[] = [
      { id: 'dash', title: 'Dashboard', description: 'Overview of infrastructure and deployment metrics', category: 'page', view: 'dashboard' },
      { id: 'gen', title: 'Generator', description: 'Standalone infrastructure code generator tool', category: 'page', view: 'generator' },
      { id: 'pipes', title: 'Pipeline Dashboard', description: 'Agentic CI/CD deployment pipelines', category: 'page', view: 'pipeline-dashboard' },
      { id: 'analytics', title: 'Usage Analytics', description: 'Detailed model performance, cost, and usage graphs', category: 'page', view: 'usage-analytics' },
      { id: 'docs', title: 'Documentation', description: 'Learn how to utilize Iacgenie AI guides', category: 'page', view: 'docs' },
      { id: 'api', title: 'API Swagger Reference', description: 'Developer interactive API testing platform', category: 'page', view: 'api-docs' },
    ];

    const settings: SearchItem[] = [
      { id: 'set-proj', title: 'Project Settings', description: 'Modify project name, description, or delete workspace', category: 'settings', view: 'settings' },
      { id: 'set-team', title: 'Team Management', description: 'Invite coworkers and assign project role access', category: 'settings', view: 'team-members' },
      { id: 'set-bill', title: 'Billing & Plan', description: 'Upgrade to pro plan or download monthly invoices', category: 'settings', view: 'billing' },
      { id: 'set-dev', title: 'Developer Configs', description: 'Generate API tokens and endpoint tokens', category: 'settings', view: 'developer' },
    ];

    const projectItems: SearchItem[] = projects.map(p => ({
      id: `proj-${p.id}`,
      title: `Switch Workspace: ${p.name}`,
      description: p.description || 'Access infrastructure for this workspace',
      category: 'project',
      action: async () => {
        await setCurrentProjectId(p.id);
        navigate('dashboard');
      }
    }));

    return [...pages, ...settings, ...projectItems];
  };

  const filteredItems = getSearchItems().filter(item => {
    const matchesQuery = item.title.toLowerCase().includes(query.toLowerCase()) || 
                         item.description.toLowerCase().includes(query.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || item.category === categoryFilter;
    return matchesQuery && matchesCategory;
  });

  // Handle focus trapping
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      setTimeout(() => inputRef.current?.focus(), 50);
      setSelectedIndex(0);
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // Keyboard navigation inside search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => (prev + 1) % Math.max(1, filteredItems.length));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => (prev - 1 + filteredItems.length) % Math.max(1, filteredItems.length));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filteredItems[selectedIndex]) {
          handleItemClick(filteredItems[selectedIndex]);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, selectedIndex, filteredItems]);

  const handleItemClick = (item: SearchItem) => {
    if (item.view) {
      navigate(item.view);
    } else if (item.action) {
      item.action();
    }
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-100 flex items-start justify-center p-4 pt-[15vh] animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div 
        ref={modalRef}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-2xl bg-white border border-gray-150 rounded-2xl shadow-2xl flex flex-col overflow-hidden max-h-[60vh] animate-in zoom-in-95 duration-200"
        role="dialog"
        aria-modal="true"
      >
        <div className="relative border-b border-gray-100 p-4 flex items-center gap-3">
          <Search className="h-5 w-5 text-gray-400" />
          <input
            ref={inputRef}
            type="text"
            data-testid="top-bar-search-input"
            aria-label="Search pages, projects, and settings"
            placeholder="Search pages, workspaces, cloud settings... (arrow keys)"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            className="w-full text-base text-gray-800 placeholder-gray-400 outline-none border-none ring-none"
          />
          <button 
            onClick={onClose}
            className="text-xs px-2 py-1 bg-gray-100 text-gray-500 rounded-md font-medium border border-gray-200 hover:bg-gray-150 transition"
          >
            ESC
          </button>
        </div>

        {/* Category Filters */}
        <div className="flex gap-2 px-4 py-2 border-b border-gray-50 bg-gray-50/50">
          {(['all', 'page', 'project', 'settings'] as const).map((cat) => (
            <button
              key={cat}
              onClick={() => {
                setCategoryFilter(cat);
                setSelectedIndex(0);
              }}
              className={`text-xs px-3 py-1 rounded-full font-medium capitalize transition-colors ${
                categoryFilter === cat
                  ? 'bg-brand-primary text-white shadow-sm'
                  : 'bg-white border border-gray-200 text-gray-500 hover:bg-gray-50'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Search Results */}
        <div className="flex-1 overflow-y-auto p-2">
          {filteredItems.map((item, index) => {
            const isSelected = index === selectedIndex;
            const CategoryIcon = item.category === 'page' 
              ? FileText 
              : item.category === 'project'
                ? Folder 
                : Settings;

            return (
              <button
                key={item.id}
                onClick={() => handleItemClick(item)}
                className={`w-full flex items-center justify-between p-3 rounded-xl transition-all text-left ${
                  isSelected 
                    ? 'bg-brand-primary/10 border-l-4 border-l-brand-primary pl-2'
                    : 'hover:bg-gray-50 pl-3'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`h-8 w-8 rounded-lg flex items-center justify-center ${
                    isSelected ? 'bg-brand-primary/10 text-brand-primary' : 'bg-gray-100 text-gray-500'
                  }`}>
                    <CategoryIcon className="h-4.5 w-4.5" />
                  </div>
                  <div>
                    <div className={`text-sm font-semibold ${isSelected ? 'text-brand-primary dark:text-brand-primary' : 'text-gray-800 dark:text-gray-200'}`}>
                      {item.title}
                    </div>
                    <div className="text-xs text-gray-400 mt-0.5 line-clamp-1">
                      {item.description}
                    </div>
                  </div>
                </div>
                {isSelected && (
                  <ArrowRight className="h-4 w-4 text-brand-primary animate-in slide-in-from-left-2 duration-200" />
                )}
              </button>
            );
          })}

          {filteredItems.length === 0 && (
            <div className="py-12 text-center">
              <Search className="h-8 w-8 text-gray-300 mx-auto mb-3" />
              <div className="text-sm font-medium text-gray-500">No results found for "{query}"</div>
              <div className="text-xs text-gray-400 mt-1">Try expanding filters or search different keyword</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SearchModal;
