import React from 'react';

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  id: string;
  error?: string;
  helperText?: string;
}

const Textarea: React.FC<TextareaProps> = ({ label, id, className, error, helperText, ...props }) => {
  return (
    <div className={className}>
      <label htmlFor={id} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
        {label}
      </label>
      <textarea
        id={id}
        {...props}
        className={`w-full bg-white border rounded-lg py-2 px-3 text-slate-900 placeholder-slate-400 dark:placeholder-slate-500 dark:bg-slate-800 dark:text-slate-50 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary sm:text-sm transition ${
          error ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : 'border-slate-300 dark:border-slate-600'
        }`}
      />
      {error && (
        <p className="text-red-500 text-sm mt-1">{error}</p>
      )}
      {helperText && !error && (
        <p className="text-slate-500 text-sm mt-1">{helperText}</p>
      )}
    </div>
  );
};

export default Textarea;