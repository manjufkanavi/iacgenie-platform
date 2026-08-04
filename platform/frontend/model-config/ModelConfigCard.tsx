import React, { useState, useRef, useEffect } from 'react';
import { ModelConfig } from '../store/useAppStore';
import { TestResult } from './ConnectionTestButton';
import Badge from '../ui/Badge';
import { PROVIDERS, ProviderConfig } from '../constants/providers';
import { MODELS } from '../constants/models';

interface ModelConfigCardProps {
  config: ModelConfig;
  testResult: TestResult | null;
  onTest: () => void;
  onEdit: () => void;
  /** Requests deletion — parent opens a confirmation modal instead of deleting immediately. */
  onDeleteRequest: () => void;
  isTesting?: boolean;
}

export const ModelConfigCard: React.FC<ModelConfigCardProps> = ({
  config,
  testResult,
  onTest,
  onEdit,
  onDeleteRequest,
  isTesting = false,
}) => {
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu on outside click
  useEffect(() => {
    if (!showMenu) return;
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showMenu]);

  const providerDef = PROVIDERS.find(p => p.id === config.provider) ||
    { name: config.provider, id: config.provider } as ProviderConfig;

  const modelDefs = MODELS[config.provider] || [];
  const modelDef = modelDefs.find(m => m.id === config.model_name);

  return (
    <div className="relative p-6 border rounded-xl shadow-sm bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:border-brand-primary/50 transition-colors">
      <div className="flex justify-between items-start">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 flex-shrink-0 bg-slate-100 dark:bg-slate-700 rounded-lg flex items-center justify-center text-xl font-bold text-slate-500">
            {providerDef.logoUrl ? (
              <img src={providerDef.logoUrl} alt={providerDef.name} className="w-8 h-8" />
            ) : (
              providerDef.name.charAt(0).toUpperCase()
            )}
          </div>

          <div>
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">{config.model_name}</h3>
              <Badge variant={testResult?.success ? 'success' : 'neutral'}>
                {testResult?.success ? 'Connected' : 'Configured'}
              </Badge>
              {config.secure && <Badge variant="info">Secure</Badge>}
            </div>

            <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">
              {providerDef.name} {modelDef?.displayName ? `· ${modelDef.displayName}` : ''}
            </p>

            <div className="flex items-center gap-2 flex-wrap mb-4">
              {modelDef?.capabilities.includes('vision') && <Badge variant="info">👁 Vision</Badge>}
              {modelDef?.capabilities.includes('code') && <Badge variant="success">💻 Code</Badge>}
              {modelDef?.contextWindow && <Badge variant="neutral">{Math.round(modelDef.contextWindow/1000)}K ctx</Badge>}
            </div>

            <div className="text-xs text-slate-500 dark:text-slate-400 grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-1">
              <p><span className="font-medium text-slate-700 dark:text-slate-300">Base URL:</span> <span className="truncate block max-w-xs sm:inline">{config.base_url}</span></p>
              <p><span className="font-medium text-slate-700 dark:text-slate-300">Project ID:</span> {config.projectId}</p>
              {testResult?.response_time_ms && (
                <p><span className="font-medium text-slate-700 dark:text-slate-300">Last test:</span> {testResult.response_time_ms}ms response time</p>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onTest}
            disabled={isTesting}
            className="hidden sm:flex items-center justify-center px-3 py-1.5 text-sm font-medium text-brand-primary bg-brand-primary/10 hover:bg-brand-primary/20 rounded-md transition-colors disabled:opacity-50"
          >
            {isTesting ? (
              <svg className="w-4 h-4 animate-spin mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <circle cx="12" cy="12" r="10" strokeWidth="4" strokeOpacity="0.25" />
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            ) : 'Test'}
          </button>

          <button
            onClick={onEdit}
            className="hidden sm:block px-3 py-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 transition-colors"
          >
            Edit
          </button>

          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-1.5 text-slate-400 hover:text-slate-600 bg-white border border-transparent rounded-md hover:border-slate-300 hover:bg-slate-50 transition-colors"
              aria-label="More options"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
              </svg>
            </button>

            {showMenu && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)}></div>
                <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-slate-800 rounded-md shadow-lg border border-slate-200 dark:border-slate-700 z-20">
                  <div className="py-1">
                    <button onClick={() => { setShowMenu(false); onTest(); }} className="sm:hidden w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-100">Test Connection</button>
                    <button onClick={() => { setShowMenu(false); onEdit(); }} className="sm:hidden w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-100">Edit Configuration</button>
                    <button onClick={() => { setShowMenu(false); }} className="w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-100">Duplicate</button>
                    <div className="h-px bg-slate-200 dark:bg-slate-700 my-1"></div>
                    <button
                      data-testid="model-delete-btn"
                      onClick={() => { setShowMenu(false); onDeleteRequest(); }}
                      className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {testResult && (
        <div className={`mt-4 p-3 rounded-lg border flex items-center justify-between
          ${testResult.success
            ? 'bg-green-50/50 border-green-200 dark:bg-green-900/10 dark:border-green-800 text-green-800 dark:text-green-400'
            : 'bg-red-50/50 border-red-200 dark:bg-red-900/10 dark:border-red-800 text-red-800 dark:text-red-400'
          }
        `}>
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {testResult.success ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              )}
            </svg>
            <span className="text-sm font-medium">
              {testResult.success
                ? `Connected · ${config.model_name} responded in ${testResult.response_time_ms || 0}ms · HTTP ${testResult.status_code || 200}`
                : `Test failed · ${testResult.message}`
              }
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
