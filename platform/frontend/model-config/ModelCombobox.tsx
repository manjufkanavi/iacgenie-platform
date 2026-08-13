import React, { useState, useRef, useEffect } from 'react';
import { ModelDefinition } from '../../constants/models';
import Badge from '../ui/Badge';

interface ModelComboboxProps {
  providerId: string;
  value: string;
  onChange: (modelId: string) => void;
  models: ModelDefinition[];
  placeholder?: string;
  disabled?: boolean;
}

export const ModelCombobox: React.FC<ModelComboboxProps> = ({
  value,
  onChange,
  models,
  placeholder = 'Search models...',
  disabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const wrapperRef = useRef<HTMLDivElement>(null);

  const selectedModel = models.find((m) => m.id === value);
  const displayValue = isOpen ? searchTerm : (selectedModel?.id || searchTerm);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setSearchTerm('');
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredModels = models.filter((m) =>
    m.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.displayName.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSelect = (modelId: string) => {
    onChange(modelId);
    setIsOpen(false);
    setSearchTerm('');
  };

  const formatContext = (tokens: number) => {
    if (tokens >= 1000000) return `${Math.round(tokens / 1000000)}M`;
    if (tokens >= 1000) return `${Math.round(tokens / 1000)}K`;
    return tokens.toString();
  };

  return (
    <div className="relative w-full" ref={wrapperRef}>
      <div
        className={`relative flex items-center w-full px-3 py-2 bg-white dark:bg-slate-800 border rounded-md shadow-sm 
          ${disabled ? 'bg-slate-50 border-slate-200 text-slate-400 cursor-not-allowed' : 'border-slate-300 dark:border-slate-600 focus-within:ring-1 focus-within:ring-brand-primary focus-within:border-brand-primary cursor-text'}
        `}
        onClick={() => !disabled && setIsOpen(true)}
      >
        <div className="flex-1 overflow-hidden">
          {(!isOpen && selectedModel) ? (
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm text-slate-900 dark:text-slate-100">{selectedModel.id}</span>
              {selectedModel.tier === 'recommended' && <Badge variant="warning">★ Rec.</Badge>}
            </div>
          ) : (
            <input
              type="text"
              value={displayValue}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setIsOpen(true);
              }}
              onFocus={() => setIsOpen(true)}
              placeholder={placeholder}
              disabled={disabled}
              className="w-full bg-transparent border-none p-0 text-sm focus:ring-0 text-slate-900 dark:text-slate-100"
              role="combobox"
              aria-expanded={isOpen}
              aria-autocomplete="list"
              aria-controls="model-listbox"
            />
          )}
        </div>
        <div className="flex-shrink-0 ml-2 text-slate-400">
          <svg className={`w-5 h-5 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md shadow-lg max-h-64 overflow-y-auto" role="listbox" id="model-listbox">
          {/* Categorize models if needed, for now just list them */}
          {filteredModels.length > 0 ? (
            <ul className="py-1">
              {filteredModels.map((model) => (
                <li
                  key={model.id}
                  role="option"
                  aria-selected={model.id === value}
                  onClick={() => handleSelect(model.id)}
                  className={`
                    px-4 py-3 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700
                    ${model.id === value ? 'bg-brand-primary/5 dark:bg-brand-primary/10' : ''}
                  `}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full border flex items-center justify-center ${model.id === value ? 'border-brand-primary' : 'border-slate-300'}`}>
                        {model.id === value && <div className="w-1.5 h-1.5 rounded-full bg-brand-primary"></div>}
                      </div>
                      <span className="font-semibold text-sm text-slate-900 dark:text-slate-100">{model.id}</span>
                      <span className="text-xs text-slate-500">{formatContext(model.contextWindow)} ctx</span>
                    </div>
                    {model.tier === 'recommended' && <Badge variant="warning">★ Recommended</Badge>}
                  </div>
                  <div className="pl-5 flex flex-wrap items-center gap-2 mt-1">
                    <span className="text-xs text-slate-500">{model.displayName}</span>
                    {model.capabilities.includes('vision') && <Badge variant="info">Vision</Badge>}
                    {model.capabilities.includes('code') && <Badge variant="success">Code</Badge>}
                    {model.capabilities.includes('reasoning') && <Badge variant="info">Reasoning</Badge>}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="px-4 py-3 text-sm text-slate-500">
              No models found for "{searchTerm}"
            </div>
          )}
          {/* Allow custom entry if no exact match or if custom provider */}
          {searchTerm && !models.some(m => m.id === searchTerm) && (
            <div 
              className="px-4 py-3 border-t border-slate-100 dark:border-slate-700 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700 text-sm text-brand-primary"
              onClick={() => handleSelect(searchTerm)}
            >
              Use custom model: <span className="font-semibold">{searchTerm}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
