import React, { useState } from 'react';
import Card from '../ui/Card';

interface CodeFile {
  name: string;
  language: string;
  content: string;
  status: 'generated' | 'generating' | 'locked' | 'error';
}

interface CodePreviewPanelProps {
  files: CodeFile[];
  selectedFileIndex?: number;
  onSelectFile?: (index: number) => void;
}

const statusIndicator: Record<CodeFile['status'], { color: string; label: string }> = {
  generated: { color: 'text-status-success', label: 'Generated' },
  generating: { color: 'text-agent-thinking', label: 'Generating' },
  locked: { color: 'text-gray-400 dark:text-gray-500', label: 'Locked' },
  error: { color: 'text-status-failed', label: 'Error' },
};

const CodePreviewPanel: React.FC<CodePreviewPanelProps> = ({
  files,
  selectedFileIndex = 0,
  onSelectFile,
}) => {
  const [selected, setSelected] = useState(selectedFileIndex);

  const handleSelect = (idx: number) => {
    setSelected(idx);
    onSelectFile?.(idx);
  };

  if (files.length === 0) {
    return (
      <Card variant="empty-state" padding="lg" className="text-center">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="mx-auto text-gray-300 dark:text-slate-600 mb-3"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
        <p className="text-sm text-gray-400 dark:text-gray-500">No files generated yet</p>
      </Card>
    );
  }

  const selectedFile = files[selected] || files[0];
  const statusInfo = statusIndicator[selectedFile.status];

  return (
    <Card padding="none" className="overflow-hidden">
      <div className="flex h-[400px]">
        {/* File tree (left) */}
        <div className="w-[280px] border-r border-gray-700 dark:border-slate-700 overflow-y-auto">
          <div className="px-4 py-2 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider border-b border-gray-700 dark:border-slate-700">
            Files ({files.length})
          </div>
          {files.map((file, idx) => {
            const info = statusIndicator[file.status];
            return (
              <button
                key={idx}
                onClick={() => handleSelect(idx)}
                className={`w-full flex items-center gap-2 px-4 py-2 text-sm text-left transition-colors border-b border-gray-800 dark:border-slate-800 ${
                  idx === selected
                    ? 'bg-gray-700/50 text-white'
                    : 'text-gray-300 dark:text-gray-400 hover:bg-gray-800/50'
                }`}
              >
                <span className={`flex-shrink-0 ${info.color}`}>
                  {file.status === 'generating' ? (
                    <svg className="w-4 h-4 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                  ) : file.status === 'error' ? (
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" x2="9" y1="9" y2="15"/><line x1="9" x2="15" y1="9" y2="15"/></svg>
                  ) : file.status === 'locked' ? (
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                  ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
                  )}
                </span>
                <span className="truncate flex-1">{file.name}</span>
                <span className={`text-xs ${info.color}`} title={info.label}>
                  {file.status === 'generating' ? '' : info.label.charAt(0)}
                </span>
              </button>
            );
          })}
        </div>

        {/* Code preview (right) */}
        <div className="flex-1 overflow-auto bg-gray-950 dark:bg-slate-950">
          <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-300 dark:text-gray-400 font-mono">{selectedFile.name}</span>
              <span className={`text-xs px-1.5 py-0.5 rounded ${
                selectedFile.status === 'generated' ? 'bg-status-success/20 text-status-success' :
                selectedFile.status === 'generating' ? 'bg-agent-thinking/20 text-agent-thinking animate-pulse-agent' :
                selectedFile.status === 'error' ? 'bg-status-failed/20 text-status-failed' :
                'bg-gray-700 text-gray-400'
              }`}>
                {statusInfo.label}
              </span>
            </div>
          </div>
          <pre className="p-4 text-sm font-mono text-gray-300 dark:text-gray-400 leading-relaxed overflow-x-auto">
            <code>{selectedFile.content || '// No content yet'}</code>
          </pre>
        </div>
      </div>
    </Card>
  );
};

export default CodePreviewPanel;
