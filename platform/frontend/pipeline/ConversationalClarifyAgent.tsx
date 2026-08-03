import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Card from '../ui/Card';
import Button from '../ui/Button';
import Textarea from '../ui/Textarea';
import { Bot, User, Send, X, CheckCircle2 } from 'lucide-react';

export interface ClarifyOption {
  label: string;
  value: string;
  description?: string;
  [key: string]: any;
}

export interface ConversationalClarifyAgentProps {
  questions: string[];
  options?: ClarifyOption[];
  onSubmit: (message: string, selectedOptionValue?: string) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

type Message = {
  id: string;
  role: 'agent' | 'user';
  content: string;
  options?: ClarifyOption[];
};

// Custom hook for typewriter effect
const useTypewriter = (text: string, speed: number = 30) => {
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(true);

  useEffect(() => {
    let index = 0;
    setDisplayedText('');
    setIsTyping(true);

    const timer = setInterval(() => {
      setDisplayedText((prev) => prev + text.charAt(index));
      index++;
      if (index >= text.length) {
        clearInterval(timer);
        setIsTyping(false);
      }
    }, speed);

    return () => clearInterval(timer);
  }, [text, speed]);

  return { displayedText, isTyping };
};

const TypewriterMessage: React.FC<{ content: string; onComplete?: () => void }> = ({ content, onComplete }) => {
  const { displayedText, isTyping } = useTypewriter(content, 20);

  useEffect(() => {
    if (!isTyping && onComplete) {
      onComplete();
    }
  }, [isTyping, onComplete]);

  return (
    <span>
      {displayedText}
      {isTyping && <span className="inline-block w-1 h-4 ml-1 bg-amber-600 animate-pulse" />}
    </span>
  );
};

const ConversationalClarifyAgent: React.FC<ConversationalClarifyAgentProps> = ({
  questions,
  options = [],
  onSubmit,
  onCancel,
  isLoading = false,
}) => {
  const [chatHistory, setChatHistory] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isAgentTyping, setIsAgentTyping] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [chatHistory, isAgentTyping, inputValue]);

  // Initial load: Add first question
  useEffect(() => {
    if (questions.length > 0) {
      // If questions prop changes (new question from backend)
      let latestQuestion = questions[questions.length - 1];
      
      // Strip out <think> blocks if any made it through to the frontend
      latestQuestion = latestQuestion.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
      
      setChatHistory(prev => {
        // Only add if it's not already the last message
        const isDuplicate = prev.length > 0 && prev[prev.length - 1].content === latestQuestion;
        if (!isDuplicate) {
          return [...prev, { id: `q-${Date.now()}`, role: 'agent', content: latestQuestion, options }];
        }
        return prev;
      });
      // Allow user to answer
      setIsAgentTyping(true); // Will turn off when typewriter finishes
    }
  }, [questions, options]);

  const handleSend = (text: string, optionValue?: string) => {
    if ((!text.trim() && !optionValue) || isAgentTyping) return;

    setInputValue('');

    const displayContent = optionValue ? `Selected option: ${optionValue}` : text.trim();

    setChatHistory(prev => [
      ...prev,
      { id: `a-${Date.now()}`, role: 'user', content: displayContent }
    ]);

    // Submit single message to backend for conversational AI
    onSubmit(text, optionValue);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(inputValue);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="w-full overflow-hidden"
    >
      <Card className="w-full border-amber-200 dark:border-amber-900/50 bg-white dark:bg-slate-900 mb-6 rounded-[var(--radius-xl)] shadow-lg flex flex-col">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-amber-100 dark:border-amber-900/30 bg-amber-50/50 dark:bg-amber-950/20">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-full bg-amber-100 dark:bg-amber-900/50 flex items-center justify-center text-amber-600 dark:text-amber-400">
              <Bot size={18} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100">Clarify Agent</h3>
              <p className="text-xs text-amber-600 dark:text-amber-500 font-medium">
                Refining specifications...
              </p>
            </div>
          </div>
          <button 
            onClick={onCancel}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
            title="Cancel Generation"
          >
            <X size={18} />
          </button>
        </div>

        {/* Chat Area */}
        <div 
          ref={scrollRef}
          className="flex-1 p-6 space-y-6"
        >
          <AnimatePresence initial={false}>
            {chatHistory.map((msg, idx) => {
              const isLastAgentMsg = msg.role === 'agent' && idx === chatHistory.length - 1;
              return (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  className={`flex items-start space-x-3 ${msg.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}
                >
                  <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center mt-1 ${
                    msg.role === 'agent' 
                      ? 'bg-slate-100 dark:bg-slate-800 text-slate-500' 
                      : 'bg-brand-primary text-white'
                  }`}>
                    {msg.role === 'agent' ? <Bot size={16} /> : <User size={16} />}
                  </div>
                  <div className={`max-w-[80%] flex flex-col gap-3`}>
                    <div className={`rounded-2xl px-4 py-3 text-sm ${
                      msg.role === 'agent'
                        ? 'bg-slate-50 dark:bg-slate-800/50 text-slate-800 dark:text-slate-200 rounded-tl-sm'
                        : 'bg-brand-primary text-white rounded-tr-sm shadow-md self-end'
                    }`}>
                      {isLastAgentMsg ? (
                        <TypewriterMessage 
                          content={msg.content} 
                          onComplete={() => setIsAgentTyping(false)} 
                        />
                      ) : (
                        <span className="whitespace-pre-wrap">{msg.content}</span>
                      )}
                    </div>
                    {/* Render Options for Last Agent Message */}
                    {isLastAgentMsg && !isAgentTyping && msg.options && msg.options.length > 0 && (
                      <motion.div 
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ staggerChildren: 0.1 }}
                        className="flex flex-col gap-2 mt-1"
                      >
                        {msg.options.map((opt, optIdx) => {
                          const value = typeof opt === 'string' ? opt : (opt.value || opt.id || opt.name || opt.label || opt.option || String(optIdx));
                          let label = typeof opt === 'string' ? opt : (opt.label || opt.name || opt.title || opt.option || opt.value);
                          const description = typeof opt === 'string' ? undefined : opt.description;
                          
                          // Avoid rendering completely empty boxes or invalid objects
                          if (!label || (typeof label === 'string' && label.trim() === '')) {
                            return null;
                          }
                          
                          return (
                            <motion.button
                              key={`opt-${value || optIdx}`}
                              whileHover={{ scale: 1.02 }}
                              whileTap={{ scale: 0.98 }}
                              onClick={() => handleSend('', value)}
                              disabled={isLoading}
                              className="flex flex-col text-left border border-amber-200 dark:border-amber-800/50 bg-white dark:bg-slate-900 rounded-xl p-3 hover:border-amber-400 dark:hover:border-amber-600 hover:shadow-md transition-all group disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              <div className="flex items-center gap-2">
                                <CheckCircle2 size={16} className="text-amber-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                                <span className="font-semibold text-slate-800 dark:text-slate-200">{label}</span>
                              </div>
                              {description && (
                                <span className="text-xs text-slate-500 dark:text-slate-400 mt-1 pl-6">
                                  {description}
                                </span>
                              )}
                            </motion.button>
                          );
                        })}
                      </motion.div>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center space-x-2 text-slate-400 text-sm italic ml-11"
            >
              <LoaderDots /> Submitting...
            </motion.div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
          <div className="relative flex items-end gap-2 max-w-4xl mx-auto">
            <div className="flex-1 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 focus-within:border-brand-primary focus-within:ring-1 focus-within:ring-brand-primary shadow-sm overflow-hidden transition-all">
              <Textarea
                id="clarify-input"
                label=""
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={isAgentTyping ? "Agent is typing..." : "Type your answer..."}
                disabled={isAgentTyping || isLoading}
                className="w-full max-h-32 bg-transparent border-0 focus:ring-0 resize-none py-3 px-4 text-sm"
              />
            </div>
            <Button
              variant="primary"
              onClick={() => handleSend(inputValue)}
              disabled={!inputValue.trim() || isAgentTyping || isLoading}
              className="h-[46px] w-[46px] rounded-xl flex items-center justify-center p-0 flex-shrink-0"
              aria-label="Send Answer"
            >
              <Send size={18} className={inputValue.trim() && !isAgentTyping ? "text-white" : "text-white/50"} />
            </Button>
          </div>
          <div className="text-center mt-2">
            <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">
              Press <kbd className="font-mono bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded text-slate-500">Enter</kbd> to send
            </span>
          </div>
        </div>
      </Card>
    </motion.div>
  );
};

const LoaderDots = () => (
  <span className="inline-flex items-center space-x-1">
    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"></span>
  </span>
);

export default ConversationalClarifyAgent;
