import React, { useState } from 'react';
import { AdvancedConfig } from '.../constants/models';

interface AdvancedConfigAccordionProps {
  values: AdvancedConfig;
  defaults: Partial<AdvancedConfig>;
  onChange: (v: AdvancedConfig) => void;
}

export const AdvancedConfigAccordion: React.FC<AdvancedConfigAccordionProps> = ({
  values,
  defaults,
  onChange,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [headersStr, setHeadersStr] = useState(JSON.stringify(values.headers, null, 2));
  const [metadataStr, setMetadataStr] = useState(JSON.stringify(values.metadata, null, 2));

  const updateValue = <K extends keyof AdvancedConfig>(key: K, value: AdvancedConfig[K]) => {
    onChange({ ...values, [key]: value });
  };

  const handleHeadersChange = (str: string) => {
    setHeadersStr(str);
    try {
      const parsed = JSON.parse(str);
      updateValue('headers', parsed);
    } catch (e) {
      // Don't update state if invalid JSON, wait until valid
    }
  };

  const handleMetadataChange = (str: string) => {
    setMetadataStr(str);
    try {
      const parsed = JSON.parse(str);
      updateValue('metadata', parsed);
    } catch (e) {
      // Don't update state if invalid JSON, wait until valid
    }
  };

  const resetToDefaults = () => {
    const newValues = { ...values, ...defaults };
    onChange(newValues);
    if (defaults.headers) setHeadersStr(JSON.stringify(defaults.headers, null, 2));
    if (defaults.metadata) setMetadataStr(JSON.stringify(defaults.metadata, null, 2));
  };

  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden bg-slate-50/50 dark:bg-slate-800/50">
      <button
        type="button"
        className="w-full px-4 py-3 flex items-center justify-between bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700/80 transition-colors focus:outline-none"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-controls="advanced-config-panel"
      >
        <div className="flex items-center gap-2">
          <svg className={`w-4 h-4 text-slate-500 transition-transform ${isOpen ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          <span className="font-medium text-sm text-slate-700 dark:text-slate-200">Advanced Settings</span>
        </div>
        {!isOpen && (
          <span className="text-xs text-slate-500">
            {values.max_tokens.toLocaleString()} tokens · {values.temperature} temp
          </span>
        )}
      </button>

      {isOpen && (
        <div id="advanced-config-panel" className="p-4 bg-white dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700">
          <div className="flex justify-end mb-4">
            <button
              type="button"
              onClick={resetToDefaults}
              className="text-xs text-brand-primary hover:underline"
            >
              Reset to provider defaults
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Max Tokens</label>
              <input
                type="number"
                value={values.max_tokens}
                onChange={(e) => updateValue('max_tokens', parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-md text-sm focus:ring-1 focus:ring-brand-primary focus:border-brand-primary"
                min="1"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Temperature</label>
              <input
                type="number"
                value={values.temperature}
                onChange={(e) => updateValue('temperature', parseFloat(e.target.value) || 0)}
                className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-md text-sm focus:ring-1 focus:ring-brand-primary focus:border-brand-primary"
                min="0"
                max="2"
                step="0.1"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Timeout (sec)</label>
              <input
                type="number"
                value={values.timeout}
                onChange={(e) => updateValue('timeout', parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-md text-sm focus:ring-1 focus:ring-brand-primary focus:border-brand-primary"
                min="1"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Retry Attempts</label>
              <input
                type="number"
                value={values.retry_attempts}
                onChange={(e) => updateValue('retry_attempts', parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-md text-sm focus:ring-1 focus:ring-brand-primary focus:border-brand-primary"
                min="0"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Retry Delay (sec)</label>
              <input
                type="number"
                value={values.retry_delay}
                onChange={(e) => updateValue('retry_delay', parseFloat(e.target.value) || 0)}
                className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-md text-sm focus:ring-1 focus:ring-brand-primary focus:border-brand-primary"
                min="0"
                step="0.1"
              />
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Custom Headers (JSON)</label>
              <textarea
                value={headersStr}
                onChange={(e) => handleHeadersChange(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-md text-sm font-mono focus:ring-1 focus:ring-brand-primary focus:border-brand-primary"
                placeholder="{}"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Metadata (JSON)</label>
              <textarea
                value={metadataStr}
                onChange={(e) => handleMetadataChange(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-md text-sm font-mono focus:ring-1 focus:ring-brand-primary focus:border-brand-primary"
                placeholder="{}"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
