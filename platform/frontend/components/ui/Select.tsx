
import React from 'react';
import { ChevronDown } from 'lucide-react';

interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'onChange'> {
  label: string;
  children: React.ReactNode;
  onChange?: (e: React.ChangeEvent<HTMLSelectElement>) => void;
}

const Select: React.FC<SelectProps> = ({ label, children, onChange, ...props }) => {
  return (
    <div>
      {label && (
        <label htmlFor={props.id || props.name} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
          {label}
        </label>
      )}
      <div className="relative">
        <select
          onChange={onChange}
          {...props}
          className="w-full appearance-none bg-white border border-slate-300 rounded-lg py-2 pl-3 pr-10 text-slate-900 dark:text-slate-50 dark:bg-slate-800 dark:border-slate-600 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary sm:text-sm transition-colors duration-200 hover:border-slate-400 dark:hover:border-slate-500 disabled:bg-slate-100 dark:disabled:bg-slate-700 disabled:cursor-not-allowed"
        >
          {children}
        </select>
        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-slate-400 dark:text-slate-500">
          <ChevronDown className="w-4 h-4" />
        </div>
      </div>
    </div>
  );
};

export default Select;
