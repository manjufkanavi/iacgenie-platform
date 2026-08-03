import React, { useState, useRef, useEffect } from 'react';
import { LucideIcon, ChevronDown } from 'lucide-react';

interface Option {
  value: string;
  label: string;
  icon?: React.ReactNode;
}

interface ContextPillProps {
  label: string;
  icon?: LucideIcon;
  options: Option[];
  value: string;
  onChange: (val: string) => void;
  disabled?: boolean;
}

const ContextPill: React.FC<ContextPillProps> = ({ label, icon: Icon, options, value, onChange, disabled }) => {
  const [isOpen, setIsOpen] = useState(false);
  const pillRef = useRef<HTMLDivElement>(null);

  const selectedOption = options.find(o => o.value === value) || options[0];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (pillRef.current && !pillRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative inline-block text-left" ref={pillRef}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors
          ${disabled ? 'opacity-50 cursor-not-allowed bg-slate-100 dark:bg-slate-800 text-slate-500' : 
            isOpen ? 'bg-orange-50 text-orange-600 dark:bg-orange-500/10 dark:text-orange-400' : 
            'bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300'}
        `}
      >
        {Icon && <Icon className="w-4 h-4" />}
        <span className="text-xs text-slate-500 dark:text-slate-400 mr-1">{label}:</span>
        <span>{selectedOption?.label || value}</span>
        <ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-2 w-56 rounded-xl bg-white dark:bg-slate-900 shadow-lg border border-slate-200 dark:border-slate-800 py-1 origin-top-left">
          <div className="max-h-60 overflow-y-auto">
            {options.map((option) => (
              <button
                key={option.value}
                onClick={() => {
                  onChange(option.value);
                  setIsOpen(false);
                }}
                className={`w-full text-left px-4 py-2.5 text-sm flex items-center gap-2 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors
                  ${value === option.value ? 'bg-slate-50 dark:bg-slate-800/50 font-medium text-brand-primary' : 'text-slate-700 dark:text-slate-300'}
                `}
              >
                {option.icon && <span className="w-4 h-4 shrink-0">{option.icon}</span>}
                <span className="truncate">{option.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ContextPill;
