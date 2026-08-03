import React from 'react';

type CardPadding = 'sm' | 'md' | 'lg' | 'none';
type CardVariant = 'default' | 'metric' | 'empty-state' | 'elevated' | 'interactive';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: CardPadding;
  variant?: CardVariant;
  accentColor?: string;
  header?: React.ReactNode;
  footer?: React.ReactNode;
  hoverable?: boolean;
  onClick?: () => void;
}

const paddingStyles: Record<CardPadding, string> = {
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
  none: 'p-0',
};

const variantStyles: Record<CardVariant, string> = {
  default: 'bg-white border border-slate-200 dark:bg-slate-800 dark:border-slate-700 shadow-sm',
  metric: 'bg-slate-50 border border-slate-200 dark:bg-slate-800 dark:border-slate-700 text-center',
  'empty-state': 'bg-slate-50 border border-slate-200 border-dashed dark:bg-slate-800 dark:border-slate-700',
  elevated: 'bg-white border border-slate-200 shadow-md dark:bg-slate-800 dark:border-slate-700',
  interactive: 'bg-white border border-slate-200 shadow-sm hover:shadow-md hover:border-brand-primary/30 hover:-translate-y-0.5 cursor-pointer transition-all duration-200 dark:bg-slate-800 dark:border-slate-700',
};

const Card: React.FC<CardProps> = ({
  children,
  className = '',
  padding = 'md',
  variant = 'default',
  accentColor,
  header,
  footer,
  hoverable = false,
  onClick,
}) => {
  const baseStyles = `rounded-xl overflow-hidden ${variantStyles[variant]} ${paddingStyles[padding]}`;

  const hoverClass = hoverable ? 'transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md' : '';
  const accentStyle = accentColor ? { '--card-accent': accentColor } as React.CSSProperties : {};

  return (
    <div
      className={`${baseStyles} ${hoverClass} ${className}`}
      style={accentStyle}
      onClick={onClick}
    >
      {header && <div className="mb-4">{header}</div>}
      <div>{children}</div>
      {footer && <div className="mt-4">{footer}</div>}
    </div>
  );
};

export default Card;
