import React, { useRef, useEffect } from 'react';
import ContextPill from '../ui/ContextPill';
import { Cloud, Cpu, ArrowRight } from 'lucide-react';

interface PromptCanvasProps {
  prompt: string;
  setPrompt: (prompt: string) => void;
  model: string;
  setModel: (model: string) => void;
  provider: string;
  setProvider: (provider: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
  modelOptions: { value: string; label: string }[];
  providerOptions: { value: string; label: string }[];
  isCompact?: boolean;
}

const PromptCanvas: React.FC<PromptCanvasProps> = ({
  prompt,
  setPrompt,
  model,
  setModel,
  provider,
  setProvider,
  onSubmit,
  isLoading,
  modelOptions,
  providerOptions,
  isCompact = false,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(Math.max(textareaRef.current.scrollHeight, 60), 200)}px`;
    }
  }, [prompt]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (prompt.trim() && !isLoading) {
        onSubmit();
      }
    }
  };

  if (isCompact) {
    return (
      <div className="w-full max-w-6xl mx-auto bg-slate-50 dark:bg-slate-900/50 rounded-full px-6 py-3 border border-slate-200 dark:border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-4 flex-1 truncate">
          <span className="w-2 h-2 rounded-full bg-brand-primary"></span>
          <span className="text-slate-600 dark:text-slate-400 truncate">{prompt}</span>
        </div>
        <div className="flex gap-2 shrink-0">
          <div className="px-3 py-1 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-500">
            {provider}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full max-w-6xl mx-auto bg-white dark:bg-slate-900 rounded-2xl shadow-xl shadow-slate-200/50 dark:shadow-none border border-slate-200 dark:border-slate-800 transition-all duration-200 focus-within:ring-2 ring-brand-primary ring-offset-2 dark:ring-offset-slate-950">
      <textarea
        ref={textareaRef}
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Describe the infrastructure you want to generate..."
        className="w-full bg-transparent resize-none outline-none p-6 text-lg text-slate-900 dark:text-slate-100 placeholder:text-slate-400 min-h-[120px]"
        disabled={isLoading}
      />
      
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center px-4 py-3 border-t border-slate-100 dark:border-slate-800/60 bg-slate-50/50 dark:bg-slate-900/50 rounded-b-2xl gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <ContextPill
            label="Provider"
            icon={Cloud}
            options={providerOptions}
            value={provider}
            onChange={setProvider}
            disabled={isLoading}
          />
          <ContextPill
            label="Model"
            icon={Cpu}
            options={modelOptions}
            value={model}
            onChange={setModel}
            disabled={isLoading}
          />
        </div>
        
        <button
          onClick={onSubmit}
          disabled={isLoading || !prompt.trim()}
          className={`flex items-center justify-center w-10 h-10 rounded-full transition-all duration-300
            ${isLoading || !prompt.trim() 
              ? 'bg-slate-200 dark:bg-slate-800 text-slate-400 cursor-not-allowed' 
              : 'bg-gradient-to-br from-orange-500 to-red-500 text-white shadow-lg shadow-orange-500/30 hover:scale-105 active:scale-95'
            }`}
        >
          {isLoading ? (
            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <ArrowRight className="w-5 h-5" />
          )}
        </button>
      </div>
    </div>
  );
};

export default PromptCanvas;
