import React from 'react';
import Spinner from './Spinner';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  className = '',
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-semibold focus:outline-none focus:ring-2 focus:ring-offset-2 transition-all duration-200 disabled:opacity-disabled disabled:cursor-not-allowed hover:-translate-y-0.5';

  const radiusBySize = { sm: 'rounded-md', md: 'rounded-lg', lg: 'rounded-xl' };

  const variantStyles = {
    primary: 'bg-brand-primary text-white border-brand-primary hover:bg-brand-primary-hover active:bg-brand-primary-active focus:ring-brand-primary shadow-sm hover:shadow-md border',
    secondary: 'bg-slate-50 text-slate-700 hover:bg-slate-100 active:bg-slate-200 focus:ring-brand-primary border border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 dark:active:bg-slate-600 dark:border-slate-700',
    outline: 'bg-transparent text-brand-primary hover:bg-brand-primary-subtle active:bg-brand-primary-subtle/50 focus:ring-brand-primary border border-brand-primary dark:text-brand-primary dark:border-brand-primary',
    danger: 'bg-status-failed text-white hover:bg-red-600 active:bg-red-700 focus:ring-status-failed border border-status-failed dark:bg-red-500 dark:hover:bg-red-400 dark:border-red-500',
    ghost: 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 active:bg-slate-200 focus:ring-slate-300 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-800 dark:active:bg-slate-700',
  };

  const sizeStyles = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
  };

  const combinedClassName = `${baseStyles} ${radiusBySize[size]} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`;

  return (
    <button className={combinedClassName} disabled={isLoading || props.disabled} {...props}>
      {isLoading && (
        <Spinner size={size === 'lg' ? 'md' : 'sm'} className="-ml-1 mr-2" />
      )}
      {children}
    </button>
  );
};

export default Button;
