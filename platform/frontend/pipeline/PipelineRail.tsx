import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Check, X, HelpCircle, Circle, Loader2 } from 'lucide-react';
import { PipelinePhase } from '../types';

export type RailPhaseState = 'pending' | 'active' | 'completed' | 'failed' | 'needs_input';

export interface PipelineRailProps {
  phases: PipelinePhase[];
  currentPhase: PipelinePhase | null;
  phaseStates: Record<string, RailPhaseState>;
}

interface GroupedStage {
  id: string;
  label: string;
  phases: PipelinePhase[];
}

const STAGES: GroupedStage[] = [
  { id: 'prep', label: 'Preparation', phases: ['clarify', 'init'] },
  { id: 'gen', label: 'Generation', phases: ['generate', 'format'] },
  { id: 'val', label: 'Validation', phases: ['static_analysis', 'validate'] },
  { id: 'rev', label: 'Review', phases: ['plan_review', 'plan', 'apply_review'] },
  { id: 'dep', label: 'Deployment', phases: ['apply', 'complete', 'escalate'] },
];

const PipelineRail: React.FC<PipelineRailProps> = ({
  phases,
  currentPhase,
  phaseStates,
}) => {
  // Determine the state of each grouped stage based on its constituent phases
  const stageStates = useMemo(() => {
    return STAGES.map((stage) => {
      let state: RailPhaseState = 'pending';
      let hasFailed = false;
      let hasNeedsInput = false;
      let isActive = false;
      let allCompleted = true;
      let anyStarted = false;

      for (const phase of stage.phases) {
        // If the phase is not even in the pipeline, we skip it
        if (!phases.includes(phase)) continue;

        const pState = phaseStates[phase] || 'pending';
        if (pState === 'failed') hasFailed = true;
        if (pState === 'needs_input') hasNeedsInput = true;
        if (pState === 'active' || phase === currentPhase) isActive = true;
        if (pState !== 'completed') allCompleted = false;
        if (pState !== 'pending') anyStarted = true;
      }

      if (hasFailed) state = 'failed';
      else if (hasNeedsInput) state = 'needs_input';
      else if (isActive) state = 'active';
      else if (allCompleted && anyStarted) state = 'completed';
      else if (anyStarted) state = 'active'; // Partway through

      return { ...stage, state };
    });
  }, [phases, currentPhase, phaseStates]);

  // Find index of the highest active or completed stage to fill the progress bar
  const activeIndex = stageStates.reduce((acc, stage, idx) => {
    if (stage.state !== 'pending') return idx;
    return acc;
  }, -1);

  const progressPercentage = activeIndex >= 0 ? (activeIndex / (STAGES.length - 1)) * 100 : 0;

  return (
    <div className="w-full max-w-4xl mx-auto py-8 relative">
      {/* Background Track */}
      <div className="absolute top-1/2 left-0 w-full h-1 bg-slate-200 dark:bg-slate-800 -translate-y-1/2 rounded-full overflow-hidden" />
      
      {/* Active Progress Track */}
      <motion.div 
        className="absolute top-1/2 left-0 h-1 bg-blue-500 -translate-y-1/2 rounded-full"
        initial={{ width: 0 }}
        animate={{ width: `${progressPercentage}%` }}
        transition={{ duration: 0.5, ease: "easeInOut" }}
      />

      <div className="relative flex justify-between items-center w-full">
        {stageStates.map((stage, idx) => {
          const isPast = idx < activeIndex;
          const isCurrent = idx === activeIndex;
          
          let Icon = Circle;
          let iconClass = 'text-slate-300 dark:text-slate-600';
          let bgClass = 'bg-white dark:bg-[#0d1117] border-2 border-slate-200 dark:border-slate-800';
          let ringClass = '';

          if (stage.state === 'completed' || isPast) {
            Icon = Check;
            iconClass = 'text-white';
            bgClass = 'bg-emerald-500 border-2 border-emerald-500';
          } else if (stage.state === 'active') {
            Icon = Loader2;
            iconClass = 'text-blue-500 animate-spin';
            bgClass = 'bg-white dark:bg-[#0d1117] border-2 border-blue-500';
            ringClass = 'ring-4 ring-blue-500/20';
          } else if (stage.state === 'needs_input') {
            Icon = HelpCircle;
            iconClass = 'text-amber-500';
            bgClass = 'bg-white dark:bg-[#0d1117] border-2 border-amber-500';
            ringClass = 'ring-4 ring-amber-500/20 animate-pulse';
          } else if (stage.state === 'failed') {
            Icon = X;
            iconClass = 'text-white';
            bgClass = 'bg-red-500 border-2 border-red-500';
            ringClass = 'ring-4 ring-red-500/20';
          }

          return (
            <div key={stage.id} className="flex flex-col items-center relative group">
              <motion.div
                layout
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: idx * 0.1 }}
                className={`w-8 h-8 rounded-full flex items-center justify-center z-10 transition-all duration-300 ${bgClass} ${ringClass}`}
              >
                <Icon size={14} className={iconClass} strokeWidth={3} />
              </motion.div>
              
              <div className="absolute top-10 flex flex-col items-center">
                <span className={`text-xs font-semibold whitespace-nowrap transition-colors duration-300 ${
                  isCurrent ? 'text-blue-600 dark:text-blue-400' : 
                  (isPast || stage.state === 'completed') ? 'text-slate-700 dark:text-slate-300' : 
                  'text-slate-400 dark:text-slate-600'
                }`}>
                  {stage.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default PipelineRail;
