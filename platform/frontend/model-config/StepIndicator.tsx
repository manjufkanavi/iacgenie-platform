import React from 'react';

export interface Step {
  id: number;
  label: string;
  status: 'complete' | 'current' | 'upcoming' | 'error';
}

interface StepIndicatorProps {
  steps: Step[];
  currentStep: number; // 0-indexed
}

export const StepIndicator: React.FC<StepIndicatorProps> = ({ steps, currentStep }) => {
  return (
    <div className="w-full">
      {/* Mobile view (< sm) */}
      <div className="sm:hidden flex items-center justify-between mb-6 px-1">
        <div className="flex items-center gap-2">
          <div className="bg-brand-primary text-white text-xs font-bold px-2 py-1 rounded-full">
            {currentStep + 1} / {steps.length}
          </div>
          <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            {steps[currentStep].label}
          </span>
        </div>
      </div>

      {/* Desktop view (>= sm) */}
      <nav aria-label="Progress" className="hidden sm:block mb-8">
        <ol role="list" className="flex items-center">
          {steps.map((step, stepIdx) => (
            <li key={step.id} className={`relative ${stepIdx !== steps.length - 1 ? 'pr-8 sm:pr-20' : ''}`}>
              {step.status === 'complete' ? (
                <>
                  <div className="absolute inset-0 flex items-center" aria-hidden="true">
                    <div className="h-0.5 w-full bg-brand-primary" />
                  </div>
                  <div className="relative flex h-8 w-8 items-center justify-center rounded-full bg-brand-primary hover:bg-brand-primary/90">
                    <svg className="h-5 w-5 text-white" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                      <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                    </svg>
                  </div>
                </>
              ) : step.status === 'current' ? (
                <>
                  <div className="absolute inset-0 flex items-center" aria-hidden="true">
                    <div className="h-0.5 w-full bg-slate-200 dark:bg-slate-700" />
                  </div>
                  <div className="relative flex h-8 w-8 items-center justify-center rounded-full border-2 border-brand-primary bg-white dark:bg-slate-900" aria-current="step">
                    <span className="h-2.5 w-2.5 rounded-full bg-brand-primary" aria-hidden="true" />
                  </div>
                </>
              ) : step.status === 'error' ? (
                <>
                  <div className="absolute inset-0 flex items-center" aria-hidden="true">
                    <div className="h-0.5 w-full bg-red-200 dark:bg-red-900/50" />
                  </div>
                  <div className="relative flex h-8 w-8 items-center justify-center rounded-full bg-red-600 hover:bg-red-700">
                    <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </div>
                </>
              ) : (
                <>
                  <div className="absolute inset-0 flex items-center" aria-hidden="true">
                    <div className="h-0.5 w-full bg-slate-200 dark:bg-slate-700" />
                  </div>
                  <div className="relative flex h-8 w-8 items-center justify-center rounded-full border-2 border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 hover:border-slate-400">
                    <span className="text-sm font-medium text-slate-500 dark:text-slate-400">{step.id}</span>
                  </div>
                </>
              )}
              
              {/* Label */}
              <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 w-max text-center">
                <span className={`text-xs font-medium ${
                  step.status === 'complete' ? 'text-brand-primary' :
                  step.status === 'current' ? 'text-slate-900 dark:text-white font-semibold' :
                  step.status === 'error' ? 'text-red-600 dark:text-red-400' :
                  'text-slate-500 dark:text-slate-400'
                }`}>
                  {step.label}
                </span>
              </div>
            </li>
          ))}
        </ol>
      </nav>
    </div>
  );
};
