import React, { useState } from 'react';

interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  label: string;
  id: string;
  showPasswordToggle?: boolean;
  error?: string;
  helperText?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

const Input: React.FC<InputProps> = ({ 
  label, 
  id, 
  className, 
  showPasswordToggle = false, 
  type, 
  error,
  helperText,
  autoComplete,
  onChange,
  ...props 
}) => {
  const [showPassword, setShowPassword] = useState(false);
  const inputType = showPasswordToggle && type === 'password' ? (showPassword ? 'text' : 'password') : type;

  // Determine autocomplete value if not provided
  const getAutoComplete = () => {
    if (autoComplete) return autoComplete;
    if (type === 'email') return 'email';
    if (type === 'password') return 'new-password';
    if (id.includes('name')) return 'name';
    if (id.includes('username')) return 'username';
    if (id.includes('phone')) return 'tel';
    if (id.includes('url')) return 'url';
    return 'off';
  };

  return (
    <div className={className}>
      <label htmlFor={id} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type={inputType}
          autoComplete={getAutoComplete()}
          onChange={onChange}
          {...props}
          className={`w-full bg-white border rounded-lg py-2 px-3 text-slate-900 placeholder-slate-400 dark:placeholder-slate-500 dark:bg-slate-800 dark:text-slate-50 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary sm:text-sm transition disabled:bg-slate-100 dark:disabled:bg-slate-700 ${
            showPasswordToggle && type === 'password' ? 'pr-10' : ''
          } ${
            error ? 'border-red-300 focus:border-red-500 focus:ring-red-500 dark:border-red-700 dark:focus:border-red-400 dark:focus:ring-red-400' : 'border-slate-300 dark:border-slate-600'
          }`}
        />
        {showPasswordToggle && type === 'password' && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 focus:outline-none focus:text-slate-600"
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            )}
          </button>
        )}
      </div>
      {error && (
        <p className="text-red-500 text-sm mt-1">{error}</p>
      )}
      {helperText && !error && (
        <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">{helperText}</p>
      )}
    </div>
  );
};

export default Input;