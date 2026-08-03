import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, AlertTriangle, Sparkles, Play, X } from 'lucide-react';

export interface TofuStage {
  id: string;
  label: string;
  status: 'idle' | 'running' | 'success' | 'failed';
  errorLog?: string;
}

interface TofuWorkflowStatusBarProps {
  workspaceId?: string;
  stages: TofuStage[];
  currentStageId?: string | null;
  onRunWorkflow: () => void;
  onFixWithAi: (stageId: string, errorLog: string) => void;
  isExecuting: boolean;
  onCancel?: () => void;
}

const TofuWorkflowStatusBar: React.FC<TofuWorkflowStatusBarProps> = ({
  stages,
  onRunWorkflow,
  onFixWithAi,
  isExecuting,
  onCancel,
}) => {
  const [expandedErrorStageId, setExpandedErrorStageId] = useState<string | null>(null);

  const failedStage = stages.find((s) => s.status === 'failed');

  const handleStageClick = (stage: TofuStage) => {
    if (stage.status === 'failed' && stage.errorLog) {
      setExpandedErrorStageId(expandedErrorStageId === stage.id ? null : stage.id);
    }
  };

  return (
    <div className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 backdrop-blur-md select-none shrink-0 flex flex-col">
      {/* Track Stepper Area */}
      <div className="flex items-center justify-between px-6 py-3 min-h-[56px] gap-4">
        {/* Stepper Nodes */}
        <div className="flex-1 flex items-center max-w-4xl">
          {stages.map((stage, index) => {
            const isFirst = index === 0;

            // Determine connector color
            let connectorBg = 'bg-slate-200 dark:bg-slate-800';
            if (!isFirst) {
              const prevStage = stages[index - 1];
              if (prevStage.status === 'success') {
                if (stage.status === 'failed') {
                  connectorBg = 'bg-red-500';
                } else if (stage.status === 'success' || stage.status === 'running') {
                  connectorBg = 'bg-emerald-500';
                } else {
                  connectorBg = 'bg-emerald-500/50';
                }
              } else if (prevStage.status === 'failed') {
                connectorBg = 'bg-red-500/30';
              }
            }

            return (
              <React.Fragment key={stage.id}>
                {/* Connector Line */}
                {!isFirst && (
                  <div className="flex-1 h-[2px] mx-2 relative min-w-[20px]">
                    <div className={`absolute inset-0 ${connectorBg} rounded transition-all duration-300`} />
                  </div>
                )}

                {/* Node */}
                <div
                  onClick={() => handleStageClick(stage)}
                  className={`flex items-center gap-2 cursor-pointer ${
                    stage.status === 'failed' ? 'hover:opacity-90' : ''
                  }`}
                >
                  {/* Status Indicator Bubble */}
                  <div className="relative flex items-center justify-center shrink-0">
                    {stage.status === 'idle' && (
                      <div className="w-3.5 h-3.5 rounded-full bg-slate-300 dark:bg-slate-700 transition-colors" />
                    )}

                    {stage.status === 'running' && (
                      <div className="relative flex items-center justify-center">
                        <div className="absolute w-5 h-5 rounded-full bg-blue-500/30 animate-ping" />
                        <div className="w-3.5 h-3.5 rounded-full bg-blue-500 animate-pulse" />
                      </div>
                    )}

                    {stage.status === 'success' && (
                      <div className="w-5 h-5 rounded-full bg-emerald-500/10 text-emerald-500 flex items-center justify-center border border-emerald-500/20">
                        <Check size={12} className="stroke-[3]" />
                      </div>
                    )}

                    {stage.status === 'failed' && (
                      <div className="w-5 h-5 rounded-full bg-red-500 text-white flex items-center justify-center shadow-md shadow-red-500/20">
                        <AlertTriangle size={11} className="stroke-[2.5]" />
                      </div>
                    )}
                  </div>

                  {/* Stage Label */}
                  <span
                    className={`text-xs font-mono transition-colors ${
                      stage.status === 'running'
                        ? 'text-blue-500 font-semibold'
                        : stage.status === 'success'
                        ? 'text-slate-700 dark:text-slate-300 font-medium'
                        : stage.status === 'failed'
                        ? 'text-red-500 font-bold'
                        : 'text-slate-500 dark:text-slate-500'
                    }`}
                  >
                    {stage.label}
                  </span>
                </div>
              </React.Fragment>
            );
          })}
        </div>

        {/* Action Button */}
        <div className="shrink-0 flex items-center gap-2">
          {isExecuting ? (
            <button
              onClick={onCancel}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-850 hover:text-red-500 transition-colors"
            >
              <X size={13} />
              Cancel Run
            </button>
          ) : (
            <button
              onClick={onRunWorkflow}
              className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-md bg-orange-500 text-white hover:bg-orange-600 active:scale-95 transition-all shadow-sm"
            >
              <Play size={12} fill="currentColor" />
              {failedStage ? 'Re-run Checks' : 'Run Pipeline'}
            </button>
          )}
        </div>
      </div>

      {/* Expandable Failure Info Panel */}
      <AnimatePresence>
        {failedStage && failedStage.errorLog && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="border-t border-red-200 dark:border-red-950/40 bg-red-50/20 dark:bg-red-950/10 overflow-hidden"
          >
            <div className="px-6 py-4 flex flex-col md:flex-row justify-between items-start gap-4">
              <div className="flex-1 min-w-0">
                <h4 className="text-xs font-bold text-red-600 dark:text-red-400 mb-1.5 flex items-center gap-1.5">
                  <AlertTriangle size={14} />
                  Validate Failed: OpenTofu checking error
                </h4>
                <pre className="font-mono text-xs text-red-500/90 whitespace-pre-wrap break-words max-h-32 overflow-y-auto leading-relaxed">
                  {failedStage.errorLog}
                </pre>
              </div>

              <button
                onClick={() => onFixWithAi(failedStage.id, failedStage.errorLog || '')}
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-650 active:scale-95 transition-all rounded-lg shadow-md shadow-orange-500/20 md:self-center shrink-0"
              >
                <Sparkles size={13} className="animate-pulse" />
                Fix with AI
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default TofuWorkflowStatusBar;
