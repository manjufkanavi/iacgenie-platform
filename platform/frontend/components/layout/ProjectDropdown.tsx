import React, { useState, useRef, useEffect } from 'react';
import { useAppStore } from '.././store/useAppStore';
import { ChevronDown, Folder, Plus } from 'lucide-react';

const ProjectDropdown: React.FC = () => {
  const { projects, currentProject, setCurrentProjectId, listProjects, navigate } = useAppStore();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listProjects();
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = async (projectId: string) => {
    try {
      await setCurrentProjectId(projectId);
      setIsOpen(false);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        data-testid="top-bar-project-dropdown"
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all text-sm font-medium text-gray-700 bg-white"
      >
        <Folder className="h-4 w-4 text-brand-primary" />
        <span className="max-w-[150px] truncate">
          {currentProject?.name || 'Select Project'}
        </span>
        <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div 
          className="absolute left-0 mt-2 w-64 rounded-xl border border-gray-150 bg-white shadow-xl z-55 overflow-hidden py-1 animate-in fade-in slide-in-from-top-2 duration-200"
          role="menu"
        >
          <div className="px-3 py-2 text-xs font-semibold text-gray-400 border-b border-gray-100">
            Workspaces
          </div>
          <div className="max-h-60 overflow-y-auto">
            {projects.map((project) => (
              <button
                key={project.id}
                onClick={() => handleSelect(project.id)}
                role="menuitem"
                className={`w-full flex items-center justify-between px-4 py-2.5 text-sm text-left transition-colors ${
                  project.id === currentProject?.id
                    ? 'bg-brand-primary/10 text-brand-primary font-semibold'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <span className="truncate">{project.name}</span>
                {project.id === currentProject?.id && (
                  <span className="h-1.5 w-1.5 rounded-full bg-brand-primary" />
                )}
              </button>
            ))}
            {projects.length === 0 && (
              <div className="px-4 py-3 text-xs text-gray-400 italic text-center">
                No workspaces available
              </div>
            )}
          </div>
          <div className="border-t border-gray-100 mt-1 pt-1 bg-gray-50">
            <button
              onClick={() => {
                setIsOpen(false);
                navigate('settings'); // Settings has project creation
              }}
              className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-gray-600 hover:text-gray-900 transition-colors"
            >
              <Plus className="h-4 w-4 text-gray-400" />
              <span>Create New Workspace</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectDropdown;
