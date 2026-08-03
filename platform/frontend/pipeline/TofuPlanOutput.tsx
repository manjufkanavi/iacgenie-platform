import React, { useState, useEffect, useRef, useMemo } from 'react';
import Card from '../ui/Card';
import { Search, Download, Copy, Check, ChevronDown, ChevronUp } from 'lucide-react';
import toast from 'react-hot-toast';

interface TofuPlanOutputProps {
  output: string;
  mode?: 'plan' | 'apply' | 'output';
  isLive?: boolean;
  maxLines?: number;
  searchQuery?: string;
  onResourceClick?: (address: string) => void;
  className?: string;
}

const RESOURCE_REGEX = /\b((?:aws|google|azurerm|kubernetes|docker|null|random)_[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)\b/g;

export const TofuPlanOutput: React.FC<TofuPlanOutputProps> = ({
  output,
  mode = 'plan',
  isLive = false,
  maxLines = 200,
  searchQuery: propSearchQuery = '',
  onResourceClick,
  className = '',
}) => {
  const [searchQuery, setSearchQuery] = useState(propSearchQuery);
  const [showAll, setShowAll] = useState(false);
  const [copied, setCopied] = useState(false);
  
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSearchQuery(propSearchQuery);
  }, [propSearchQuery]);

  // Split into lines
  const allLines = useMemo(() => {
    if (!output) return [];
    return output.split('\n');
  }, [output]);

  // Filter lines by search query if present
  const filteredLines = useMemo(() => {
    if (!searchQuery) return allLines.map((line, idx) => ({ line, originalIndex: idx }));
    
    const query = searchQuery.toLowerCase();
    return allLines
      .map((line, idx) => ({ line, originalIndex: idx }))
      .filter(({ line }) => line.toLowerCase().includes(query));
  }, [allLines, searchQuery]);

  // Slice lines based on maxLines and collapse state
  const visibleLines = useMemo(() => {
    if (showAll || searchQuery) return filteredLines;
    return filteredLines.slice(0, maxLines);
  }, [filteredLines, showAll, maxLines, searchQuery]);

  // Auto-scroll when live content changes
  useEffect(() => {
    if (isLive && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [allLines.length, isLive]);

  const handleCopy = () => {
    navigator.clipboard.writeText(output);
    setCopied(true);
    toast.success('Plan output copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExport = () => {
    const blob = new Blob([output], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `tofu-${mode}-output-${new Date().toISOString().slice(0, 10)}.log`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success('Logs exported successfully');
  };

  // Helper to parse line highlighting styles
  const getLineStyle = (line: string): { className: string; style?: React.CSSProperties } => {
    if (mode === 'plan') {
      if (/^\s*\+/.test(line)) return { className: 'text-[var(--color-plan-create)]' };
      if (/^\s*~/.test(line)) return { className: 'text-[var(--color-plan-update)]' };
      if (/^\s*-/.test(line)) return { className: 'text-[var(--color-plan-destroy)]' };
      if (/^\s*#/.test(line)) return { className: 'text-[var(--color-tofu-comment)]' };
      if (/Warning:/.test(line)) return { className: 'text-[var(--color-severity-warning)]' };
      if (/Error:/.test(line)) return { className: 'text-[var(--color-severity-error)] font-bold' };
      if (/#\s+\w+/.test(line)) return { className: 'text-[var(--color-plan-resource)]' };
    }

    if (mode === 'apply') {
      if (/#.*will be created/.test(line)) return { className: 'text-[var(--color-plan-create)]' };
      if (/#.*will be updated/.test(line)) return { className: 'text-[var(--color-plan-update)]' };
      if (/#.*will be destroyed/.test(line)) return { className: 'text-[var(--color-plan-destroy)]' };
      if (/Error:/.test(line)) return { className: 'text-[var(--color-severity-error)] font-bold' };
      if (/Warning:/.test(line)) return { className: 'text-[var(--color-severity-warning)]' };
      if (/^\*/.test(line)) return { className: 'text-[var(--color-text-secondary)]' };
      if (/Apply complete!/.test(line)) return { className: 'text-[var(--color-plan-create)] font-bold' };
    }

    return { className: 'text-[var(--color-tofu-text)]' };
  };

  // Render text segment, highlighting search query and making resources clickable
  const renderLineContent = (lineText: string) => {
    // If output mode and matches key = value pattern
    if (mode === 'output') {
      const match = lineText.match(/^(\s*[\w.-]+)\s*=\s*(.*)$/);
      if (match) {
        const [, key, val] = match;
        return (
          <>
            <span className="text-[var(--color-tofu-key)] font-semibold">{key}</span>
            <span className="text-[var(--color-tofu-text)]"> = </span>
            <span className="text-[var(--color-tofu-value)]">{val}</span>
          </>
        );
      }
    }

    // Identify and split by resource addresses to make them clickable
    let parts: { text: string; isResource: boolean }[] = [];
    let lastIndex = 0;
    let match;

    RESOURCE_REGEX.lastIndex = 0;
    while ((match = RESOURCE_REGEX.exec(lineText)) !== null) {
      const matchStr = match[0];
      const matchIndex = match.index;

      if (matchIndex > lastIndex) {
        parts.push({ text: lineText.substring(lastIndex, matchIndex), isResource: false });
      }
      parts.push({ text: matchStr, isResource: true });
      lastIndex = RESOURCE_REGEX.lastIndex;
    }

    if (lastIndex < lineText.length) {
      parts.push({ text: lineText.substring(lastIndex), isResource: false });
    }

    if (parts.length === 0) {
      parts.push({ text: lineText, isResource: false });
    }

    // Apply search query highlighting on top of segments
    return parts.map((part, pIdx) => {
      if (part.isResource) {
        return (
          <button
            key={pIdx}
            onClick={() => onResourceClick?.(part.text)}
            className="text-[var(--color-plan-resource)] underline font-semibold hover:text-[var(--color-brand-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--color-brand-primary)] px-0.5 rounded cursor-pointer text-left inline-block"
            aria-label={`View details for ${part.text}`}
          >
            {part.text}
          </button>
        );
      }

      if (!searchQuery) return <span key={pIdx}>{part.text}</span>;

      // Highlight search match
      const escapedQuery = searchQuery.replace(/[/\-\\^$*+?.()|[\]{}]/g, '\\$&');
      const subParts = part.text.split(new RegExp(`(${escapedQuery})`, 'gi')); // nosemgrep
      return (
        <span key={pIdx}>
          {subParts.map((subPart, sIdx) => 
            subPart.toLowerCase() === searchQuery.toLowerCase() ? (
              <mark key={sIdx} className="bg-slate-700 text-amber-300 font-bold px-0.5 rounded">
                {subPart}
              </mark>
            ) : (
              subPart
            )
          )}
        </span>
      );
    });
  };

  return (
    <Card padding="none" className={`overflow-hidden border border-slate-800 bg-[var(--color-tofu-bg)] rounded-xl ${className}`}>
      {/* Header toolbar */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-800 bg-slate-950/60 select-none">
        <span className="text-xs font-black uppercase tracking-widest text-slate-400">
          {mode.toUpperCase()} OUTPUT
        </span>

        {/* Search */}
        <div className="relative flex-1 max-w-xs ml-auto">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter lines..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 bg-slate-900/60 border border-slate-800 text-xs text-slate-300 rounded-lg outline-none focus:border-[var(--color-brand-primary)] focus:ring-1 focus:ring-[var(--color-brand-primary)] transition"
            aria-label="Filter plan output"
          />
        </div>

        {/* Copy & Export */}
        <button
          onClick={handleCopy}
          className="p-1.5 hover:bg-slate-900/80 text-slate-400 hover:text-slate-200 rounded-lg transition"
          title="Copy raw output"
        >
          {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
        </button>
        <button
          onClick={handleExport}
          className="p-1.5 hover:bg-slate-900/80 text-slate-400 hover:text-slate-200 rounded-lg transition"
          title="Export output"
        >
          <Download className="w-4 h-4" />
        </button>
      </div>

      {/* Main output console */}
      <div
        ref={containerRef}
        className="overflow-y-auto p-4 font-mono leading-relaxed min-h-[150px] max-h-[500px]"
        style={{
          fontFamily: 'var(--size-tofu-font)',
          fontSize: 'var(--size-tofu-font-size)',
          lineHeight: 'var(--size-tofu-line-height)',
        }}
        role="log"
        aria-live={isLive ? 'polite' : 'off'}
        aria-label="OpenTofu Console Logs"
      >
        {visibleLines.length === 0 ? (
          <div className="flex items-center justify-center h-48 text-[var(--color-text-muted)] italic text-sm">
            {searchQuery ? 'No matching plan lines found' : 'No plan output available'}
          </div>
        ) : (
          <div className="space-y-0.5">
            {visibleLines.map(({ line, originalIndex }) => {
              const lineStyle = getLineStyle(line);
              return (
                <div
                  key={originalIndex}
                  className={`flex items-start gap-4 px-2 py-0.5 rounded transition hover:bg-[var(--color-console-line-highlight)] ${
                    lineStyle.className
                  } ${isLive ? 'animate-[console-log-enter_150ms_ease-out]' : ''}`}
                >
                  <span className="text-slate-700 dark:text-slate-600 select-none font-bold tabular-nums w-8 text-right shrink-0">
                    {originalIndex + 1}
                  </span>
                  <pre className="flex-1 whitespace-pre-wrap break-all pr-4">
                    <code>{renderLineContent(line)}</code>
                  </pre>
                </div>
              );
            })}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Collapsible "Show More" banner */}
      {filteredLines.length > maxLines && !searchQuery && (
        <div className="border-t border-slate-800 bg-slate-950/40 p-2 text-center">
          <button
            onClick={() => setShowAll(!showAll)}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-bold text-[var(--color-brand-primary)] hover:text-[var(--color-brand-primary-hover)] transition"
          >
            {showAll ? (
              <>
                Show Less <ChevronUp className="w-3.5 h-3.5" />
              </>
            ) : (
              <>
                Show All ({filteredLines.length} lines) <ChevronDown className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </div>
      )}
    </Card>
  );
};

export default TofuPlanOutput;
