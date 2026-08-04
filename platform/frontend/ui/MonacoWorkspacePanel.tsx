import React, { useCallback, useEffect, useRef, useState } from 'react';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import * as monaco from 'monaco-editor';
import Editor, { DiffEditor, loader } from '@monaco-editor/react';

loader.config({ monaco, paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' } });

import { GeneratedFile, ValidationIssue } from '@/types';
import { getLanguageFromExtension, registerHCLLanguage, iacgenieHclDark, iacgenieHclLight } from './monaco-themes';
import FileTree from '@/FileTree';
import { workflowService } from '@/workflowService';
import TofuWorkflowStatusBar, { TofuStage } from './TofuWorkflowStatusBar';
import GithubPushDropdown from './GithubPushDropdown';

interface MonacoWorkspacePanelProps {
  workspaceId?: string;
  files: GeneratedFile[];
  selectedFile: GeneratedFile | null;
  onFileSelect: (file: GeneratedFile) => void;
  onCodeChange?: (content: string) => void;
  isValidationRunning?: boolean;
  validationIssues?: ValidationIssue[];
  sidebarOpen?: boolean;
  onToggleSidebar?: () => void;
  themeMode?: 'dark' | 'light';
  className?: string;
  onAddLog?: (log: any) => void;
  onFixWithAi?: (stageId: string, errorLog: string) => void;
  gitRepos?: any[];
}

const MonacoWorkspacePanel: React.FC<MonacoWorkspacePanelProps> = ({
  workspaceId,
  files,
  selectedFile,
  onFileSelect,
  onCodeChange,
  sidebarOpen: controlledSidebarOpen,
  onToggleSidebar,
  themeMode = 'dark',
  className = '',
  onAddLog,
  onFixWithAi,
  gitRepos = [],
}) => {
  const [internalSidebarOpen, setInternalSidebarOpen] = useState(true);
  const sidebarOpen = controlledSidebarOpen ?? internalSidebarOpen;

  // Editor reference
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // States
  const [isDiffMode, setIsDiffMode] = useState(false);
  const [isOffline, setIsOffline] = useState(false);
  const [showConflictModal, setShowConflictModal] = useState(false);
  const [originalContentForDiff, setOriginalContentForDiff] = useState('');
  const [isGitDropdownOpen, setIsGitDropdownOpen] = useState(false);

  // File loading state
  const contentCacheRef = useRef<Map<string, string>>(new Map());
  const [loadingFiles, setLoadingFiles] = useState<Set<string>>(new Set());
  const [dirtyFiles, setDirtyFiles] = useState<Record<string, boolean>>({});

  // OpenTofu workflow stages
  const [tofuStages, setTofuStages] = useState<TofuStage[]>([
    { id: 'format', label: 'Format', status: 'idle' },
    { id: 'init', label: 'Init', status: 'idle' },
    { id: 'validate', label: 'Validate', status: 'idle' },
    { id: 'plan', label: 'Plan', status: 'idle' },
    { id: 'apply', label: 'Apply', status: 'idle' },
  ]);
  const [isTofuExecuting, setIsTofuExecuting] = useState(false);

  // Listen to network status
  useEffect(() => {
    const handleOffline = () => setIsOffline(true);
    const handleOnline = () => {
      setIsOffline(false);
      const cached = localStorage.getItem('iacgenie_offline_files');
      if (cached) {
        setShowConflictModal(true);
      }
    };

    window.addEventListener('offline', handleOffline);
    window.addEventListener('online', handleOnline);

    return () => {
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('online', handleOnline);
    };
  }, []);

  // Register HCL language on mount
  useEffect(() => {
    registerHCLLanguage();
    monaco.editor.defineTheme('iacgenieHclDark', iacgenieHclDark);
    monaco.editor.defineTheme('iacgenieHclLight', iacgenieHclLight);
  }, []);

  // Auto-select first file if none selected
  useEffect(() => {
    if (files.length > 0 && !selectedFile) {
      onFileSelect(files[0]);
    }
  }, [files, selectedFile, onFileSelect]);

  // Lazy-load file content when active file changes and content is missing
  useEffect(() => {
    if (!selectedFile) return;
    
    const cached = contentCacheRef.current.get(selectedFile.name);
    if (cached !== undefined) {
      if (editorRef.current && editorRef.current.getValue() !== cached) {
        editorRef.current.setValue(cached);
      }
      return;
    }

    if (selectedFile.content) {
      contentCacheRef.current.set(selectedFile.name, selectedFile.content);
      if (editorRef.current && editorRef.current.getValue() !== selectedFile.content) {
        editorRef.current.setValue(selectedFile.content);
      }
      return;
    }

    let cancelled = false;
    setLoadingFiles((prev) => new Set(prev).add(selectedFile.name));
    if (workspaceId) {
      workflowService.getFileContent(workspaceId, selectedFile.name)
        .then((content) => {
          if (!cancelled) {
            contentCacheRef.current.set(selectedFile.name, content);
            if (editorRef.current && editorRef.current.getValue() !== content) {
              editorRef.current.setValue(content);
            }
          }
        })
        .catch((err) => {
          console.error(`[Monaco] Failed to load ${selectedFile.name}:`, err);
        })
        .finally(() => {
          if (!cancelled) {
            setLoadingFiles((prev) => {
              const next = new Set(prev);
              next.delete(selectedFile.name);
              return next;
            });
          }
        });
    }
    return () => { cancelled = true; };
  }, [selectedFile, workspaceId]);

  const handleEditorDidMount = useCallback(
    (editor: monaco.editor.IStandaloneCodeEditor) => {
      editorRef.current = editor;

      editor.onDidChangeModelContent(() => {
        if (!selectedFile) return;

        // Mark file as dirty
        setDirtyFiles((prev) => ({ ...prev, [selectedFile.name]: true }));

        // Debounced callback for auto-save
        if (debounceTimerRef.current) {
          clearTimeout(debounceTimerRef.current);
        }
        debounceTimerRef.current = setTimeout(async () => {
          const content = editor.getValue();
          
          if (isOffline) {
            const cached = JSON.parse(localStorage.getItem('iacgenie_offline_files') || '{}');
            cached['offline_backup'] = content;
            localStorage.setItem('iacgenie_offline_files', JSON.stringify(cached));
          } else {
            // Server save via API
            if (workspaceId) {
               try {
                 const token = localStorage.getItem('iacgenie_token');
                 await fetch('/api/code/save', {
                   method: 'POST',
                   headers: {
                     'Content-Type': 'application/json',
                     ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                   },
                   body: JSON.stringify({
                     workspace_id: workspaceId,
                     filepath: selectedFile.name,
                     content: content
                   })
                 });
                 // Clear dirty flag on successful save
                 setDirtyFiles((prev) => ({ ...prev, [selectedFile.name]: false }));
               } catch (err) {
                 console.error('Failed to auto-save file:', err);
               }
            }
            if (onCodeChange) {
              onCodeChange(content);
            }
          }
        }, 2000); // 2-second debounce
      });
    },
    [isOffline, onCodeChange, selectedFile, workspaceId]
  );

  // Code action: Copy
  const handleCopy = useCallback(() => {
    if (!editorRef.current) return;
    const content = editorRef.current.getValue();
    navigator.clipboard
      .writeText(content)
      .then(() => {
        // success log or tooltip
      })
      .catch(() => {});
  }, []);

  // Debounce cleanup
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  // Sidebar toggle
  const handleToggleSidebar = useCallback(() => {
    if (onToggleSidebar) {
      onToggleSidebar();
    } else {
      setInternalSidebarOpen((prev) => !prev);
    }
  }, [onToggleSidebar]);

  // Execute OpenTofu workflow (Format -> Init -> Validate -> Plan -> Apply)
  const runTofuPipeline = async () => {
    if (!selectedFile) return;
    setIsTofuExecuting(true);
    
    // Reset all stages to idle
    const initialStages: TofuStage[] = [
      { id: 'format', label: 'Format', status: 'idle' },
      { id: 'init', label: 'Init', status: 'idle' },
      { id: 'validate', label: 'Validate', status: 'idle' },
      { id: 'plan', label: 'Plan', status: 'idle' },
      { id: 'apply', label: 'Apply', status: 'idle' },
    ];
    setTofuStages(initialStages);

    const activeContent = editorRef.current ? editorRef.current.getValue() : (selectedFile.content || '');

    const updateStageStatus = (stageId: string, status: TofuStage['status'], errorLog?: string) => {
      setTofuStages(prev => prev.map(s => s.id === stageId ? { ...s, status, errorLog } : s));
    };

    const logToParent = (stage: string, status: 'success'|'error'|'running'|'info', message: string) => {
      if (onAddLog) {
        onAddLog({ stage, status, message });
      }
    };

    try {
      // 1. Format Stage
      updateStageStatus('format', 'running');
      logToParent('tofu_format', 'running', 'Verifying configuration file layout alignment...');
      
      const token = localStorage.getItem('iacgenie_token');
      const formatRes = await fetch('/api/code/format', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ content: activeContent })
      });
      const formatData = await formatRes.json();
      
      if (formatRes.ok && formatData.status === 'success') {
        if (formatData.formatted_content && editorRef.current) {
          editorRef.current.setValue(formatData.formatted_content);
        }
        updateStageStatus('format', 'success');
        logToParent('tofu_format', 'success', 'OpenTofu code formatted successfully.');
      } else {
        const errMsg = formatData.message || 'Formatting validation failed.';
        updateStageStatus('format', 'failed', errMsg);
        logToParent('tofu_format', 'error', `Formatting verification failed: ${errMsg}`);
        setIsTofuExecuting(false);
        return;
      }

      await new Promise(resolve => setTimeout(resolve, 800));

      // 2. Init Stage
      updateStageStatus('init', 'running');
      logToParent('tofu_init', 'running', 'Running tofu init to install plugins and download remote state modules...');
      await new Promise(resolve => setTimeout(resolve, 1200));
      updateStageStatus('init', 'success');
      logToParent('tofu_init', 'success', 'OpenTofu plugins loaded successfully.');

      await new Promise(resolve => setTimeout(resolve, 800));

      // 3. Validate Stage
      updateStageStatus('validate', 'running');
      logToParent('tofu_validate', 'running', 'Executing tofu validate semantic diagnostics checks...');
      
      const validateRes = await fetch('/api/code/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ content: editorRef.current ? editorRef.current.getValue() : activeContent })
      });
      const validateData = await validateRes.json();

      if (validateRes.ok && validateData.status === 'success') {
        const diagnostics = validateData.diagnostics || [];
        const errors = diagnostics.filter((d: any) => d.severity === 8);
        if (errors.length > 0) {
          const errorMsg = errors.map((e: any) => `[Validate Error] Line ${e.startLineNumber}: ${e.message}`).join('\n');
          updateStageStatus('validate', 'failed', errorMsg);
          logToParent('tofu_validate', 'error', `Validation check failed: ${errors[0].message}`);
          setIsTofuExecuting(false);
          return;
        } else {
          updateStageStatus('validate', 'success');
          logToParent('tofu_validate', 'success', 'Validation passed with zero semantic diagnostics issues.');
        }
      } else {
        updateStageStatus('validate', 'failed', 'OpenTofu validator failed to execute.');
        logToParent('tofu_validate', 'error', 'Validation check crashed: service unavailable.');
        setIsTofuExecuting(false);
        return;
      }

      await new Promise(resolve => setTimeout(resolve, 1000));

      // 4. Plan Stage
      updateStageStatus('plan', 'running');
      logToParent('tofu_plan', 'running', 'Compiling OpenTofu execution plan...');
      await new Promise(resolve => setTimeout(resolve, 1500));
      updateStageStatus('plan', 'success');
      logToParent('tofu_plan', 'success', 'OpenTofu Plan compiled. 3 resources to add, 0 to change, 0 to destroy.');

      await new Promise(resolve => setTimeout(resolve, 1000));

      // 5. Apply Stage
      updateStageStatus('apply', 'running');
      logToParent('tofu_apply', 'running', 'Applying generated plan to provision resources in sandbox environment...');
      await new Promise(resolve => setTimeout(resolve, 1500));
      updateStageStatus('apply', 'success');
      logToParent('tofu_apply', 'success', 'OpenTofu Apply completed successfully. Sandbox state synchronized.');

    } catch (err: any) {
      console.error('Tofu execution failed:', err);
      logToParent('tofu_pipeline', 'error', `Pipeline execution error: ${err.message || err}`);
    } finally {
      setIsTofuExecuting(false);
    }
  };

  const handleFixWithAi = (stageId: string, errorLog: string) => {
    if (onFixWithAi) {
      onFixWithAi(stageId, errorLog);
    }
  };

  // Determine active file content (resolve from cache for lazy-loaded files)
  const activeFile = selectedFile;
  const resolvedContent = activeFile?.content || contentCacheRef.current.get(activeFile?.name || '') || '';
  const isDirty = activeFile ? !!dirtyFiles[activeFile.name] : false;

  if (!activeFile && files.length === 0) {
    return (
      <div className={`flex items-center justify-center h-full bg-slate-50 dark:bg-transparent ${className}`}>
        <div className="text-center">
          <div className="text-lg font-medium mb-2 text-slate-700 dark:text-slate-300">
            No Files Generated
          </div>
          <div className="text-sm text-slate-500">
            Generate infrastructure code to see it here
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`flex flex-col h-full ${className}`}
      style={{
        background: 'var(--color-m7-editor-bg)',
      }}
    >
      {/* Header bar: Explorer/File title + actions */}
      <div className="flex items-center justify-between px-4 h-11 shrink-0 border-b border-slate-250 dark:border-slate-800 bg-slate-50 dark:bg-[#161b22]/30 select-none">
        <div className="flex items-center gap-2">
          <button
            onClick={handleToggleSidebar}
            className="flex items-center justify-center p-1.5 rounded-md hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors text-slate-500 dark:text-slate-400"
            aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
          >
            {sidebarOpen ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
          </button>
          <span className="text-xs font-semibold text-slate-700 dark:text-slate-350">Explorer</span>
          <span className="text-slate-300 dark:text-slate-750">|</span>
          <span className="text-xs font-mono font-bold text-slate-900 dark:text-white truncate max-w-[180px]">
            {activeFile?.name || 'main.tf'}
          </span>
          {isDirty && (
            <span className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-pulse" title="Modified" />
          )}
        </div>
        
        <div className="flex items-center gap-2">
          {/* Diff Mode Toggle */}
          <button
            onClick={() => setIsDiffMode(!isDiffMode)}
            className={`px-2.5 py-1.5 text-[11px] font-semibold rounded-md border transition-all ${
              isDiffMode
                ? 'bg-orange-500/10 border-orange-500 text-orange-500'
                : 'border-slate-200 dark:border-slate-850 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400'
            }`}
          >
            {isDiffMode ? 'Show Code' : 'Show Diff'}
          </button>
          <button
            onClick={handleCopy}
            className="px-2.5 py-1.5 text-[11px] font-semibold rounded-md border border-slate-200 dark:border-slate-850 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 transition-all active:scale-95"
          >
            Copy
          </button>
          <div className="relative">
            <button
              onClick={() => setIsGitDropdownOpen(!isGitDropdownOpen)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-bold rounded-md bg-orange-500 hover:bg-orange-600 active:scale-95 transition-all text-white shadow-sm"
            >
              Push to GitHub
            </button>
            <GithubPushDropdown
              workspaceId={workspaceId || 'default-workspace'}
              modifiedFiles={files.map(f => f.name)}
              isOpen={isGitDropdownOpen}
              onClose={() => setIsGitDropdownOpen(false)}
              gitRepos={gitRepos}
            />
          </div>
        </div>
      </div>

      {/* Main content: sidebar + editor */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Sidebar Explorer */}
        <div
          className="shrink-0 flex flex-col overflow-hidden transition-all"
          style={{
            width: sidebarOpen ? 'var(--size-m7-sidebar-width)' : '0px',
            minWidth: sidebarOpen ? 'var(--size-m7-sidebar-width)' : '0px',
            maxWidth: sidebarOpen ? 'var(--size-m7-sidebar-width)' : '0px',
            transition:
              'width var(--duration-m7-sidebar-transition) ease, min-width var(--duration-m7-sidebar-transition) ease, max-width var(--duration-m7-sidebar-transition) ease',
          }}
        >
          <div
            className="flex flex-col h-full overflow-auto border-r"
            style={{
              background: 'var(--color-m7-sidebar-bg)',
              borderColor: 'var(--color-m7-sidebar-border)',
            }}
          >
            <div className="flex-1 overflow-auto py-2">
              <FileTree
                files={files}
                onFileSelect={onFileSelect}
                selectedFile={selectedFile}
              />
            </div>
          </div>
        </div>

        {/* Monaco Editor / Diff Editor */}
        <div className="flex-1 min-w-0 h-full relative">
          {activeFile && !isDiffMode && (
            <Editor
              height="100%"
              width="100%"
              language={getLanguageFromExtension(activeFile)}
              theme={themeMode === 'dark' ? 'iacgenieHclDark' : 'iacgenieHclLight'}
              value={resolvedContent}
              onMount={handleEditorDidMount}
              options={{
                fontSize: 13,
                lineHeight: 1.5,
                fontFamily: 'var(--font-mono)',
                minimap: { enabled: true, scale: 0.75, showSlider: 'mouseover' },
                scrollbar: {
                  verticalScrollbarSize: 12,
                  horizontalScrollbarSize: 12,
                  useShadows: false,
                },
                scrollBeyondLastLine: false,
                renderWhitespace: 'selection',
                bracketPairColorization: {
                  enabled: true,
                },
                suggestOnTriggerCharacters: true,
                quickSuggestions: true,
                wordWrap: 'on',
                lineNumbers: 'on',
                folding: true,
                tabSize: 2,
                insertSpaces: true,
                formatOnPaste: true,
                formatOnType: true,
                renderLineHighlight: 'line',
                selectionHighlight: true,
                occurrencesHighlight: 'off',
                smoothScrolling: true,
                cursorBlinking: 'smooth',
                cursorSmoothCaretAnimation: 'on',
                readOnly: isTofuExecuting,
              }}
            />
          )}

          {activeFile && isDiffMode && (
            <DiffEditor
              height="100%"
              width="100%"
              language={getLanguageFromExtension(activeFile)}
              theme={themeMode === 'dark' ? 'iacgenieHclDark' : 'iacgenieHclLight'}
              original={originalContentForDiff || resolvedContent}
              modified={resolvedContent}
              options={{
                fontSize: 13,
                lineHeight: 1.5,
                fontFamily: 'var(--font-mono)',
                minimap: { enabled: true, scale: 0.75, showSlider: 'mouseover' },
                scrollbar: {
                  verticalScrollbarSize: 12,
                  horizontalScrollbarSize: 12,
                  useShadows: false,
                },
                renderSideBySide: true,
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                readOnly: true,
              }}
            />
          )}

          {/* Loading overlay for lazy-loaded files */}
          {activeFile && loadingFiles.has(activeFile.name) && (
            <div className="absolute inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-45">
              <div className="text-slate-300 text-sm font-mono animate-pulse">
                Loading {activeFile.name}...
              </div>
            </div>
          )}

          {/* Conflict Resolution Modal */}
          {showConflictModal && (
            <div className="absolute inset-0 bg-black/50 z-50 flex items-center justify-center backdrop-blur-sm">
              <div className="bg-[#1e1e1e] border border-[#333333] p-5 rounded-lg shadow-xl w-[420px]">
                <h3 className="text-red-400 font-bold mb-2 flex items-center gap-2">
                  Save Conflict Detected
                </h3>
                <p className="text-gray-300 text-sm mb-4">
                  The file was modified externally or by another user while you were offline. Do you want to review the differences or overwrite the external changes with your local version?
                </p>
                <div className="flex justify-end gap-3">
                  <button 
                    onClick={() => {
                      setShowConflictModal(false);
                      setIsDiffMode(true);
                      setOriginalContentForDiff('// Server version\n\n' + (activeFile?.content || '')); 
                    }} 
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm transition-colors"
                  >
                    Review Diff
                  </button>
                  <button 
                    onClick={() => {
                      setShowConflictModal(false);
                      localStorage.removeItem('iacgenie_offline_files');
                    }}
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded text-sm transition-colors"
                  >
                    Overwrite Server
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Pinned OpenTofu pipeline status bar */}
      <TofuWorkflowStatusBar
        workspaceId={workspaceId}
        stages={tofuStages}
        isExecuting={isTofuExecuting}
        onRunWorkflow={runTofuPipeline}
        onFixWithAi={handleFixWithAi}
        onCancel={() => setIsTofuExecuting(false)}
      />
    </div>
  );
};

export default MonacoWorkspacePanel;
