import React from 'react';
import Button from '../ui/Button';

export interface TestResult {
  success: boolean;
  message: string;
  status_code?: number | null;
  response_time_ms?: number;
  model_id?: string;
  request?: unknown;
  response?: unknown;
  error_code?: string;
  suggestions?: string[];
}

export type TestStatus = 'idle' | 'testing' | 'success' | 'failure' | 'network-error';

interface ConnectionTestButtonProps {
  onTest: () => void;
  status: TestStatus;
  result: TestResult | null;
}

export const ConnectionTestButton: React.FC<ConnectionTestButtonProps> = ({
  onTest,
  status,
  result,
}) => {
  return (
    <div className="w-full">
      {status === 'idle' && (
        <div className="flex justify-center p-6 border border-dashed border-slate-300 dark:border-slate-700 rounded-lg bg-slate-50 dark:bg-slate-800/50">
          <Button onClick={onTest} variant="primary" className="w-48">
            Test Connection
          </Button>
        </div>
      )}

      {status === 'testing' && (
        <div className="p-4 border rounded-lg bg-blue-50/50 border-blue-200 dark:bg-blue-900/10 dark:border-blue-800 flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <div>
            <p className="text-sm font-medium text-slate-900 dark:text-slate-100">Testing connection...</p>
            <p className="text-xs text-slate-500">Sending test request to provider</p>
          </div>
        </div>
      )}

      {status === 'success' && result && (
        <div className="p-4 border rounded-lg bg-green-50/50 border-green-200 dark:bg-green-900/10 dark:border-green-800">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-green-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <p className="text-sm font-medium text-green-800 dark:text-green-400">Connection successful</p>
              <p className="text-xs text-green-700 dark:text-green-500 mt-1">
                {result.message} {result.response_time_ms && `(${result.response_time_ms}ms)`}
              </p>
              {result.status_code && (
                <p className="text-xs text-green-600 dark:text-green-500/80 mt-1">HTTP {result.status_code}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {(status === 'failure' || status === 'network-error') && result && (
        <div className="p-4 border rounded-lg bg-red-50/50 border-red-200 dark:bg-red-900/10 dark:border-red-800">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-red-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <p className="text-sm font-medium text-red-800 dark:text-red-400">
                {status === 'network-error' ? 'Network error' : 'Authentication failed'} {result.status_code && `(HTTP ${result.status_code})`}
              </p>
              <p className="text-sm text-red-700 dark:text-red-300 mt-2">{result.message}</p>
              
              {result.suggestions && result.suggestions.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs font-semibold text-red-800 dark:text-red-400 mb-1">Suggestions:</p>
                  <ul className="list-disc pl-4 text-xs text-red-700 dark:text-red-300 space-y-1">
                    {result.suggestions.map((suggestion, i) => (
                      <li key={i}>{suggestion}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
