import React, { useState, useEffect } from 'react';
import { GeneratedFile } from '../types';
import { FileCode2, Terminal, Code2 } from 'lucide-react';
import { Editor } from '@monaco-editor/react';

interface GenerativePreviewPaneProps {
  files: GeneratedFile[];
  isGenerating: boolean;
}

const GenerativePreviewPane: React.FC<GenerativePreviewPaneProps> = ({ files, isGenerating }) => {
  const [selectedFileIndex, setSelectedFileIndex] = useState(0);

  // If new files arrive and current index is out of bounds, reset it
  useEffect(() => {
    if (files.length > 0 && selectedFileIndex >= files.length) {
      setSelectedFileIndex(0);
    }
  }, [files, selectedFileIndex]);

  const selectedFile = files[selectedFileIndex] || null;

  // Simple language mapping for Monaco
  const getMonacoLanguage = (lang: string) => {
    const l = lang.toLowerCase();
    if (l.includes('tf') || l.includes('terraform')) return 'hcl';
    if (l.includes('yml') || l.includes('yaml')) return 'yaml';
    if (l.includes('json')) return 'json';
    if (l.includes('docker')) return 'dockerfile';
    if (l.includes('sh') || l.includes('bash')) return 'shell';
    if (l.includes('py')) return 'python';
    if (l.includes('js') || l.includes('ts')) return 'typescript';
    return 'plaintext';
  };

  return (
    <div className="flex flex-col h-full bg-[#0d1117] rounded-2xl border border-slate-800 shadow-xl overflow-hidden font-mono">
      <div className="flex items-center gap-2 px-4 py-3 bg-[#161b22] border-b border-slate-800 shrink-0">
        <Terminal className="w-4 h-4 text-slate-400" />
        <span className="text-xs font-medium text-slate-400">Workspace Preview</span>
      </div>
      
      <div className="flex flex-1 overflow-hidden">
        {files.length > 0 ? (
          <>
            {/* Sidebar File List */}
            <div className="w-64 shrink-0 bg-[#0d1117] border-r border-slate-800 overflow-y-auto">
              <div className="p-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Files
              </div>
              <div className="px-2 pb-4 space-y-1">
                {files.map((file, idx) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedFileIndex(idx)}
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors text-left truncate ${
                      selectedFileIndex === idx 
                        ? 'bg-brand-primary/10 text-brand-primary' 
                        : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-300'
                    }`}
                  >
                    <FileCode2 className={`w-4 h-4 shrink-0 ${selectedFileIndex === idx ? 'text-brand-primary' : 'text-slate-500'}`} />
                    <span className="truncate">{file.name}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Monaco Editor Pane */}
            <div className="flex-1 flex flex-col min-w-0 bg-[#0d1117]">
              {/* File Header Tab */}
              <div className="flex items-center gap-2 px-4 py-2 bg-[#0d1117] border-b border-slate-800/50 shrink-0">
                <Code2 className="w-4 h-4 text-slate-500" />
                <span className="text-sm font-medium text-slate-300">{selectedFile?.name}</span>
                {isGenerating && <span className="ml-2 text-xs text-brand-primary animate-pulse">(Generating...)</span>}
              </div>
              
              <div className="flex-1 w-full h-full relative">
                {selectedFile && (
                  <Editor
                    height="100%"
                    width="100%"
                    theme="vs-dark"
                    language={getMonacoLanguage(selectedFile.language || selectedFile.name.split('.').pop() || '')}
                    value={selectedFile.content}
                    options={{
                      readOnly: isGenerating,
                      minimap: { enabled: false },
                      wordWrap: 'on',
                      lineNumbers: 'on',
                      scrollBeyondLastLine: false,
                      fontSize: 13,
                      fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, monospace",
                      padding: { top: 16 },
                      renderLineHighlight: 'all',
                    }}
                    loading={
                      <div className="h-full w-full flex items-center justify-center text-slate-500 animate-pulse text-sm">
                        Loading editor...
                      </div>
                    }
                  />
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center space-y-6 p-6">
            <div className="w-full max-w-sm space-y-4">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded bg-slate-800 animate-shimmer" />
                <div className="w-24 h-4 rounded bg-slate-800 animate-shimmer" />
              </div>
              <div className="space-y-2">
                <div className="w-full h-4 bg-slate-800/50 rounded animate-shimmer" />
                <div className="w-5/6 h-4 bg-slate-800/50 rounded animate-shimmer" style={{ animationDelay: '100ms' }} />
                <div className="w-4/6 h-4 bg-slate-800/50 rounded animate-shimmer" style={{ animationDelay: '200ms' }} />
              </div>
              
              <div className="flex items-center gap-2 pt-6">
                <div className="w-4 h-4 rounded bg-slate-800 animate-shimmer" style={{ animationDelay: '300ms' }} />
                <div className="w-32 h-4 rounded bg-slate-800 animate-shimmer" style={{ animationDelay: '300ms' }} />
              </div>
              <div className="space-y-2">
                <div className="w-full h-4 bg-slate-800/50 rounded animate-shimmer" style={{ animationDelay: '400ms' }} />
                <div className="w-3/4 h-4 bg-slate-800/50 rounded animate-shimmer" style={{ animationDelay: '500ms' }} />
              </div>
            </div>
            <p className="text-slate-500 text-sm mt-8 animate-pulse">Scaffolding infrastructure...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default GenerativePreviewPane;
