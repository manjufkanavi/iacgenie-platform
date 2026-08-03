import React from 'react';

type ChatRole = 'agent' | 'user';

interface SuggestionChip {
  label: string;
  onClick: () => void;
}

interface ChatBubbleProps {
  role: ChatRole;
  content: string;
  streaming?: boolean;
  suggestions?: SuggestionChip[];
  confidence?: number; // 0-100
  timestamp?: string;
}

const ChatBubble: React.FC<ChatBubbleProps> = ({
  role,
  content,
  streaming = false,
  suggestions = [],
  confidence,
  timestamp,
}) => {
  const isAgent = role === 'agent';

  return (
    <div className={`flex items-start gap-3 ${isAgent ? '' : 'flex-row-reverse'}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold ${
        isAgent ? 'bg-purple-500' : 'bg-brand-primary'
      }`}>
        {isAgent ? 'AI' : 'U'}
      </div>

      {/* Bubble */}
      <div className={`max-w-[75%] ${isAgent ? '' : 'flex flex-col items-end'}`}>
        <div className={`rounded-2xl px-4 py-3 ${
          isAgent
            ? 'bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 text-gray-900 dark:text-gray-100 rounded-tl-sm'
            : 'bg-brand-primary text-white rounded-tr-sm'
        }`}>
          <p className="text-sm whitespace-pre-wrap">{content}</p>

          {/* Streaming typing dots */}
          {streaming && (
            <div className="flex items-center gap-1 mt-2">
              <span className="w-1.5 h-1.5 bg-gray-400 dark:bg-gray-500 rounded-full animate-typing-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 bg-gray-400 dark:bg-gray-500 rounded-full animate-typing-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 bg-gray-400 dark:bg-gray-500 rounded-full animate-typing-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          )}

          {/* Confidence badge */}
          {confidence !== undefined && !streaming && (
            <div className="flex items-center gap-1 mt-2">
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                confidence >= 80 ? 'bg-status-success-bg text-status-success-text' :
                confidence >= 50 ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400' :
                'bg-status-failed-bg text-status-failed-text'
              }`}>
                {confidence}% confident
              </span>
            </div>
          )}
        </div>

        {/* Suggestions (agent only) */}
        {isAgent && suggestions.length > 0 && !streaming && (
          <div className="flex flex-wrap gap-2 mt-2">
            {suggestions.map((chip, idx) => (
              <button
                key={idx}
                onClick={chip.onClick}
                className="px-3 py-1 text-xs font-medium rounded-full border border-gray-200 dark:border-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
              >
                {chip.label}
              </button>
            ))}
          </div>
        )}

        {/* Timestamp */}
        {timestamp && (
          <span className={`text-xs text-gray-400 dark:text-gray-500 mt-1 ${isAgent ? '' : 'text-right'}`}>
            {timestamp}
          </span>
        )}
      </div>
    </div>
  );
};

export default ChatBubble;
