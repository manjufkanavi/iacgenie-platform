import React from 'react';
import { X, Filter } from 'lucide-react';

interface FilterBarProps {
  children: React.ReactNode;
  title?: string;
  onClear?: () => void;
  hasActiveFilters?: boolean;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  children,
  title = 'Filters',
  onClear,
  hasActiveFilters = false
}) => {
  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-500" />
          <h2 className="text-sm font-semibold text-gray-700">{title}</h2>
          {hasActiveFilters && (
            <span className="px-2 py-0.5 bg-brand-primary/10 text-brand-primary rounded-full text-xs font-medium">
              Active
            </span>
          )}
        </div>
        {onClear && hasActiveFilters && (
          <button
            onClick={onClear}
            className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            <X className="w-4 h-4" />
            Clear all
          </button>
        )}
      </div>
      <div className="p-4">
        {children}
      </div>
    </div>
  );
};

export default FilterBar;