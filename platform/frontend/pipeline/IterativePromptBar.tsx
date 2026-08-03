import React, { useState } from 'react';
import { ArrowRight, MessageSquarePlus } from 'lucide-react';

interface IterativePromptBarProps {
  onIterate: (prompt: string) => void;
  isLoading: boolean;
}

const IterativePromptBar: React.FC<IterativePromptBarProps> = ({ onIterate, isLoading }) => {
  const [prompt, setPrompt] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim() && !isLoading) {
      onIterate(prompt);
      setPrompt('');
    }
  };

  return (
    <div className="fixed bottom-8 left-1/2 -translate-x-1/2 w-full max-w-3xl z-40 px-4 animate-fadeIn">
      <form 
        onSubmit={handleSubmit}
        className="bg-white/90 dark:bg-slate-900/90 backdrop-blur-md shadow-2xl rounded-full p-2 border border-slate-200/80 dark:border-slate-700/80 flex items-center transition-all duration-300 focus-within:ring-2 ring-brand-primary ring-offset-2 dark:ring-offset-slate-950"
      >
        <div className="pl-4 pr-2 text-brand-primary">
          <MessageSquarePlus className="w-5 h-5" />
        </div>
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Refine this generation (e.g. 'Add a load balancer', 'Make it highly available')..."
          className="flex-1 bg-transparent border-none outline-none text-slate-800 dark:text-slate-200 placeholder:text-slate-400 text-base py-3"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !prompt.trim()}
          className={`flex items-center justify-center w-12 h-12 rounded-full ml-2 shrink-0 transition-all duration-300
            ${isLoading || !prompt.trim()
              ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-not-allowed'
              : 'bg-gradient-to-br from-brand-primary to-red-500 text-white shadow-lg shadow-orange-500/20 hover:scale-105 active:scale-95'
            }`}
        >
          {isLoading ? (
            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <ArrowRight className="w-5 h-5" />
          )}
        </button>
      </form>
    </div>
  );
};

export default IterativePromptBar;
