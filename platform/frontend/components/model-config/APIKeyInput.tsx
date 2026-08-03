import React, { useState } from 'react';

interface APIKeyInputProps {
  value: string;
  onChange: (v: string) => void;
  provider: string;
  error?: string | null;
  hint?: string;
  onCopy?: () => void;
}

export const APIKeyInput: React.FC<APIKeyInputProps> = ({
  value,
  onChange,
  provider,
  error,
  hint,
  onCopy,
}) => {
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (value) {
      navigator.clipboard.writeText(value);
      setCopied(true);
      if (onCopy) onCopy();
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="w-full">
      <div className="relative flex items-center">
        <input
          type={showKey ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={`Enter API key for ${provider}`}
          className={`w-full px-3 py-2 pr-20 bg-white dark:bg-slate-800 border rounded-md shadow-sm focus:outline-none focus:ring-1 text-sm text-slate-900 dark:text-slate-100 ${
            error
              ? 'border-red-500 focus:ring-red-500 focus:border-red-500'
              : 'border-slate-300 dark:border-slate-600 focus:ring-brand-primary focus:border-brand-primary'
          }`}
          aria-label={`API Key for ${provider}`}
          autoComplete="current-password"
        />
        <div className="absolute right-0 flex items-center pr-2">
          <button
            type="button"
            onClick={() => setShowKey(!showKey)}
            className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 focus:outline-none focus:text-brand-primary"
            aria-label={showKey ? "Hide API key" : "Show API key"}
          >
            {showKey ? (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            )}
          </button>
          <button
            type="button"
            onClick={handleCopy}
            className="p-1.5 ml-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 focus:outline-none focus:text-brand-primary"
            aria-label="Copy API key"
            title="Copy API key"
          >
            {copied ? (
              <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
              </svg>
            )}
          </button>
        </div>
      </div>
      {(error || hint) && (
        <p className={`mt-1 text-xs ${error ? 'text-red-500' : 'text-slate-500'}`}>
          {error || hint}
        </p>
      )}
    </div>
  );
};
