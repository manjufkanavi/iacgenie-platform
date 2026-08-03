import React, { useState, useCallback, useRef, useEffect } from 'react';

interface SecureInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'value'> {
  label: string;
  id: string;
  showPassword?: boolean;
  onShowPasswordToggle?: (show: boolean) => void;
  /** Character to use for masking (e.g., '•' for bullet). Shows hidden text when mask is set. */
  maskChar?: string;
  strengthPercent?: number;
  strengthLabel?: string;
  strengthBar?: boolean;
  /** Debounce delay for strength calculation in ms. Defaults to 150. */
  strengthDebounceMs?: number;
  charCount?: number;
  maxLength?: number;
  error?: string;
  helperText?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  /** Called with the raw value when debounced strength updates fire. */
  onDebouncedChange?: (value: string) => void;
}

const SecureInput: React.FC<SecureInputProps> = ({
  label,
  id,
  className,
  showPassword = false,
  onShowPasswordToggle,
  maskChar,
  strengthPercent,
  strengthLabel,
  strengthBar = true,
  strengthDebounceMs = 150,
  charCount,
  maxLength,
  error,
  helperText,
  value: controlledValue,
  type = 'password',
  onChange,
  autoComplete,
  onDebouncedChange,
  ...props
}) => {
  const [localShowPassword, setLocalShowPassword] = useState(showPassword);
  const hasToggle = !props.disabled && type === 'password';
  const effectiveShow = hasToggle ? localShowPassword : showPassword;
  const inputType = hasToggle ? (effectiveShow ? 'text' : 'password') : type;

  // Debounced timer for strength calculation callbacks
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      onDebouncedChange?.(controlledValue ?? '');
    }, strengthDebounceMs);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [controlledValue, strengthDebounceMs, onDebouncedChange]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    onChange?.(e);
  }, [onChange]);

  // Mask the value for display
  const displayValue = maskChar && !effectiveShow ? (controlledValue ?? '')
    .split('').map(c => c === '\n' ? '\n' : maskChar).join('') : (controlledValue ?? '');

  const handleToggle = useCallback(() => {
    setLocalShowPassword(prev => {
      const next = !prev;
      onShowPasswordToggle?.(next);
      return next;
    });
  }, [onShowPasswordToggle]);

  const getAutoComplete = () => {
    if (autoComplete) return autoComplete;
    if (type === 'email') return 'email';
    if (type === 'password') return 'new-password';
    return 'off';
  };

  const inputClasses = `w-full bg-white border rounded-lg py-2 px-3 text-slate-900 placeholder-slate-400 dark:placeholder-slate-500 dark:bg-slate-800 dark:text-slate-50 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary sm:text-sm transition disabled:bg-slate-100 dark:disabled:bg-slate-700 ${
    hasToggle ? 'pr-10' : ''
  } ${
    error ? 'border-red-300 focus:border-red-500 focus:ring-red-500 dark:border-red-700 dark:focus:border-red-400 dark:focus:ring-red-400' : 'border-slate-300 dark:border-slate-600'
  } ${className || ''}`.trim();

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
          onChange={handleChange}
          value={displayValue}
          {...props}
          className={inputClasses}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-error` : helperText ? `${id}-helper` : undefined}
        />
        {hasToggle && (
          <button
            type="button"
            onClick={handleToggle}
            className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 focus:outline-none focus:text-slate-600"
            aria-label={effectiveShow ? "Hide password" : "Show password"}
          >
            {effectiveShow ? (
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
        <p className="text-red-500 text-sm mt-1" id={`${id}-error`}>{error}</p>
      )}
      {!error && helperText && (
        <p className="text-slate-600 dark:text-slate-400 text-sm mt-1" id={`${id}-helper`}>{helperText}</p>
      )}
      {!error && strengthBar && (strengthPercent !== undefined || charCount !== undefined) && (
        <div className="mt-2 space-y-1">
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-150 ${
                  strengthPercent === undefined
                    ? 'bg-transparent w-0'
                    : `${
                        strengthPercent <= 30
                          ? 'bg-[var(--color-strength-weak)] dark:bg-[var(--color-strength-weak)]'
                          : strengthPercent <= 60
                          ? 'bg-[var(--color-strength-fair)] dark:bg-[var(--color-strength-fair)]'
                          : strengthPercent <= 85
                          ? 'bg-[var(--color-strength-strong)] dark:bg-[var(--color-strength-strong)]'
                          : 'bg-[var(--color-strength-excellent)] dark:bg-[var(--color-strength-excellent)]'
                      }`
                }`}
                style={{ width: `${strengthPercent ?? 0}%` }}
              />
            </div>
            {charCount !== undefined && maxLength && (
              <span className="text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                {charCount} / {maxLength}
              </span>
            )}
          </div>
          {strengthLabel && (
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Strength: {strengthLabel}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default SecureInput;
