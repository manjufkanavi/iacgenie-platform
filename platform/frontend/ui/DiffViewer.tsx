import React, { useState } from 'react';
import { Copy, Check, ArrowRight } from 'lucide-react';

interface DiffLine {
  lineNumber: number;
  type: 'unchanged' | 'added' | 'removed';
  content: string;
}

interface DiffViewerProps {
  leftFile?: { name: string; content: string };
  rightFile: { name: string; content: string; language?: string };
  viewMode?: 'side-by-side' | 'inline';
  showLineNumbers?: boolean;
}

const computeDiff = (leftContent: string, rightContent: string): DiffLine[] => {
  const leftLines = leftContent?.split('\n') || [];
  const rightLines = rightContent.split('\n');
  
  const diff: DiffLine[] = [];
  let leftIndex = 0;
  let rightIndex = 0;

  // Simple line-by-line diff algorithm
  while (leftIndex < leftLines.length || rightIndex < rightLines.length) {
    if (rightIndex >= rightLines.length) {
      // Remaining lines are removed
      while (leftIndex < leftLines.length) {
        diff.push({
          lineNumber: leftIndex + 1,
          type: 'removed',
          content: leftLines[leftIndex]
        });
        leftIndex++;
      }
    } else if (leftIndex >= leftLines.length) {
      // Remaining lines are added
      while (rightIndex < rightLines.length) {
        diff.push({
          lineNumber: rightIndex + 1,
          type: 'added',
          content: rightLines[rightIndex]
        });
        rightIndex++;
      }
    } else if (leftLines[leftIndex] === rightLines[rightIndex]) {
      // Unchanged line
      diff.push({
        lineNumber: leftIndex + 1,
        type: 'unchanged',
        content: leftLines[leftIndex]
      });
      leftIndex++;
      rightIndex++;
    } else {
      // Simplified diff - mark as removed and added
      diff.push({
        lineNumber: leftIndex + 1,
        type: 'removed',
        content: leftLines[leftIndex]
      });
      diff.push({
        lineNumber: rightIndex + 1,
        type: 'added',
        content: rightLines[rightIndex]
      });
      leftIndex++;
      rightIndex++;
    }
  }

  return diff;
};

export const DiffViewer: React.FC<DiffViewerProps> = ({
  leftFile,
  rightFile,
  viewMode = 'inline',
  showLineNumbers = true
}) => {
  const [copied, setCopied] = useState(false);
  const diffLines = leftFile 
    ? computeDiff(leftFile.content, rightFile.content)
    : rightFile.content.split('\n').map((line, index) => ({
      lineNumber: index + 1,
      type: 'added' as const,
      content: line
    }));

  const copyToClipboard = () => {
    navigator.clipboard.writeText(rightFile.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getLineClass = (type: string) => {
    switch (type) {
      case 'added':
        return 'bg-green-100 text-green-800';
      case 'removed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-50 text-gray-800';
    }
  };

  const getLinePrefix = (type: string) => {
    switch (type) {
      case 'added':
        return '+';
      case 'removed':
        return '-';
      default:
        return ' ';
    }
  };

  if (viewMode === 'side-by-side' && leftFile) {
    return (
      <div className="flex gap-4">
        {/* Left panel - original */}
        <div className="flex-1 bg-gray-800 rounded-lg overflow-hidden">
          <div className="flex justify-between items-center px-4 py-2 bg-gray-700">
            <span className="text-xs font-semibold text-gray-400 uppercase">{leftFile.name}</span>
            <span className="text-xs text-gray-500">Original</span>
          </div>
          <pre className="p-4 text-sm overflow-auto max-h-[450px] text-gray-300 font-mono">
            {leftFile.content}
          </pre>
        </div>

        {/* Arrow */}
        <div className="flex items-center justify-center pt-12">
          <ArrowRight className="w-6 h-6 text-gray-400" />
        </div>

        {/* Right panel - new */}
        <div className="flex-1 bg-gray-800 rounded-lg overflow-hidden">
          <div className="flex justify-between items-center px-4 py-2 bg-gray-700">
            <span className="text-xs font-semibold text-gray-400 uppercase">{rightFile.name}</span>
            <button
              onClick={copyToClipboard}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
            >
              {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
          <pre className="p-4 text-sm overflow-auto max-h-[450px] text-gray-300 font-mono">
            {rightFile.content}
          </pre>
        </div>
      </div>
    );
  }

  // Inline view mode
  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden">
      <div className="flex justify-between items-center px-4 py-2 bg-gray-700">
        <span className="text-xs font-semibold text-gray-400 uppercase">{rightFile.name}</span>
        <div className="flex items-center gap-3">
          {showLineNumbers && (
            <label className="flex items-center gap-2 text-xs text-gray-400">
              <input
                type="checkbox"
                checked={showLineNumbers}
                readOnly
              />
              Line numbers
            </label>
          )}
          <button
            onClick={copyToClipboard}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
          >
            {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      </div>

      <div className="p-4 overflow-auto max-h-[450px] font-mono text-sm">
        {diffLines.map((line, index) => (
          <div
            key={index}
            className={`flex ${getLineClass(line.type)}`}
          >
            {showLineNumbers && (
              <span className="w-12 flex-shrink-0 text-right pr-3 select-none opacity-50">
                {line.lineNumber}
              </span>
            )}
            <span className="flex-1 whitespace-pre">
              <span className="inline-block w-6 text-gray-500">
                {getLinePrefix(line.type)}
              </span>
              {line.content}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DiffViewer;