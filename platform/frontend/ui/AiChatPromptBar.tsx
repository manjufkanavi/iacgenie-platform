import React, { useRef, useEffect } from 'react';
import { Sparkles, ArrowRight, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';

interface AiChatPromptBarProps {
  value: string;
  onChange: (val: string) => void;
  onSubmit: (prompt: string) => void;
  placeholder?: string;
  isDisabled?: boolean;
  isLoading?: boolean;
}

const AiChatPromptBar: React.FC<AiChatPromptBarProps> = ({
  value,
  onChange,
  onSubmit,
  placeholder = 'Ask AI to modify code... (e.g. "Add security group rule for port 443")',
  isDisabled = false,
  isLoading = false,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim() && !isDisabled && !isLoading) {
      onSubmit(value);
    }
  };

  // Focus recovery when "Fix with AI" or similar is clicked (represented by value changes)
  useEffect(() => {
    if (value && inputRef.current) {
      inputRef.current.focus();
    }
  }, [value]);

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-2 select-none relative">
      <form onSubmit={handleSubmit} className="relative group">
        {/* Animated gradient top border on loading */}
        {isLoading && (
          <div className="absolute top-0 left-6 right-6 h-[2px] bg-gradient-to-r from-orange-500 via-red-500 to-orange-500 bg-[length:200%_auto] animate-bgPan rounded-full z-15" />
        )}

        <div
          className={`flex items-center w-full bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-xl px-4 py-2.5 transition-all duration-200 relative z-10 ${
            isDisabled ? 'opacity-60 cursor-not-allowed' : 'hover:border-slate-350 dark:hover:border-slate-700'
          } focus-within:border-orange-500 focus-within:ring-2 focus-within:ring-orange-500/20`}
        >
          {/* Sparkles Icon / Loader */}
          <div className="shrink-0 mr-3 text-orange-500">
            {isLoading ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
              >
                <Loader2 size={18} />
              </motion.div>
            ) : (
              <motion.div
                animate={{
                  scale: [1, 1.15, 1],
                  filter: [
                    'drop-shadow(0 0 0px rgba(249, 115, 22, 0.2))',
                    'drop-shadow(0 0 4px rgba(249, 115, 22, 0.6))',
                    'drop-shadow(0 0 0px rgba(249, 115, 22, 0.2))',
                  ],
                }}
                transition={{
                  repeat: Infinity,
                  duration: 1.8,
                  ease: 'easeInOut',
                }}
              >
                <Sparkles size={18} fill="currentColor" />
              </motion.div>
            )}
          </div>

          {/* Text Input */}
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={isDisabled || isLoading}
            placeholder={placeholder}
            className="flex-1 bg-transparent border-none outline-none font-sans text-sm text-slate-800 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-500 py-1.5 focus:ring-0 focus:outline-none"
          />

          {/* Submit Action */}
          <button
            type="submit"
            disabled={isDisabled || isLoading || !value.trim()}
            className={`shrink-0 flex items-center justify-center w-8 h-8 rounded-lg transition-all ${
              !value.trim() || isDisabled || isLoading
                ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-650 cursor-not-allowed'
                : 'bg-orange-500 hover:bg-orange-600 text-white active:scale-95 shadow-sm shadow-orange-500/10'
            }`}
          >
            <ArrowRight size={16} />
          </button>
        </div>
      </form>

      {/* Inject custom bgPan styles inline for ease of distribution */}
      <style>{`
        @keyframes bg-pan {
          0% { background-position: 0% 50%; }
          100% { background-position: 200% 50%; }
        }
        .animate-bgPan {
          animation: bg-pan 3s linear infinite;
        }
      `}</style>
    </div>
  );
};

export default AiChatPromptBar;
