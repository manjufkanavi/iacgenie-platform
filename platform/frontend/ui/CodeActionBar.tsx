import React, { useState, useCallback } from 'react';
import { Loader2, FileCheck, Copy, Check } from 'lucide-react';
import { CodeActionState, ValidationIssue } from '../types';
import { Wifi, WifiOff, FileDiff } from 'lucide-react';

interface CodeActionBarProps {
  onFormat: () => void;
  onValidate: () => void;
  onCopy: () => void;
  formatState: CodeActionState;
  validationIssues: ValidationIssue[];
  isValidationRunning: boolean;
  isReadOnly?: boolean;
  isDiffMode?: boolean;
  onToggleDiff?: () => void;
  isOffline?: boolean;
}

const CodeActionBar: React.FC<CodeActionBarProps> = ({
  onFormat,
  onValidate,
  onCopy,
  formatState,
  validationIssues,
  isValidationRunning,
  isReadOnly = false,
  isDiffMode = false,
  onToggleDiff,
  isOffline = false,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    onCopy();
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [onCopy]);

  return (
    <div
      className="flex items-center gap-2 px-3 h-[36px] min-h-[36px] border-b"
      style={{
        background: 'var(--color-m7-actionbar-bg)',
        borderColor: 'var(--color-m7-actionbar-border)',
      }}
    >
      {/* Format button */}
      <button
        onClick={onFormat}
        disabled={isReadOnly || formatState.formatStatus === 'formatting'}
        className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium
                   transition-colors duration-100 disabled:opacity-40 disabled:cursor-not-allowed"
        style={{
          color: 'var(--color-m7-tab-text)',
          background: 'transparent',
        }}
        onMouseEnter={(e) => {
          if (!isReadOnly && formatState.formatStatus !== 'formatting') {
            (e.currentTarget as HTMLButtonElement).style.background =
              'var(--color-m7-tab-hover-bg)';
          }
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
        }}
        aria-label="Format document"
      >
        {formatState.formatStatus === 'formatting' ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <span style={{ fontSize: '14px' }}>&#x21bb;</span>
        )}
        <span>Format</span>
      </button>

      {/* Validate button */}
      <button
        onClick={onValidate}
        disabled={isValidationRunning}
        className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium
                   transition-colors duration-100 disabled:opacity-40 disabled:cursor-not-allowed"
        style={{
          color: 'var(--color-m7-tab-text)',
          background: 'transparent',
        }}
        onMouseEnter={(e) => {
          if (!isValidationRunning) {
            (e.currentTarget as HTMLButtonElement).style.background =
              'var(--color-m7-tab-hover-bg)';
          }
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
        }}
        aria-label="Validate code"
      >
        <FileCheck size={14} />
        <span>Validate</span>
        {validationIssues.length > 0 && (
          <span
            className="flex items-center justify-center min-w-[16px] h-[16px] px-1 rounded-full text-[11px] font-bold"
            style={{
              background:
                validationIssues.some((i) => i.severity === 'error')
                  ? 'var(--color-m7-error-squiggle)'
                  : 'var(--color-m7-warning-squiggle)',
              color: '#ffffff',
            }}
          >
            {validationIssues.length}
          </span>
        )}
      </button>

      {/* Copy button */}
      <button
        onClick={handleCopy}
        className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium
                   transition-colors duration-100"
        style={{
          color: 'var(--color-m7-tab-text)',
          background: 'transparent',
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background =
            'var(--color-m7-tab-hover-bg)';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
        }}
        aria-label="Copy to clipboard"
      >
        {copied ? (
          <>
            <Check size={14} />
            <span>Copied!</span>
          </>
        ) : (
          <>
            <Copy size={14} />
            <span>Copy</span>
          </>
        )}
      </button>

      {/* Diff Mode Toggle button */}
      {onToggleDiff && (
        <button
          onClick={onToggleDiff}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium
                     transition-colors duration-100"
          style={{
            color: isDiffMode ? 'var(--color-m7-tab-active-text)' : 'var(--color-m7-tab-text)',
            background: isDiffMode ? 'var(--color-m7-tab-active-bg)' : 'transparent',
            border: isDiffMode ? '1px solid var(--color-m7-tab-active-border)' : '1px solid transparent',
          }}
          onMouseEnter={(e) => {
            if (!isDiffMode) {
              (e.currentTarget as HTMLButtonElement).style.background =
                'var(--color-m7-tab-hover-bg)';
            }
          }}
          onMouseLeave={(e) => {
            if (!isDiffMode) {
              (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
            }
          }}
          aria-label="Toggle diff mode"
        >
          <FileDiff size={14} />
          <span>Diff View</span>
        </button>
      )}

      {/* Network Status indicator */}
      <div
        className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium ml-2"
        style={{
          color: isOffline ? '#ef4444' : '#10b981',
        }}
        title={isOffline ? "Disconnected - Changes saved locally" : "Connected to Language Server"}
      >
        {isOffline ? <WifiOff size={14} /> : <Wifi size={14} />}
        <span>{isOffline ? "Offline (Saved locally)" : "Connected"}</span>
      </div>

      {/* Status bar text (right side) */}
      <div
        className="flex items-center ml-auto text-[11px] font-mono"
        style={{
          color: 'var(--color-m7-statusbar-text)',
        }}
        aria-live="polite"
      >
        {validationIssues.length > 0 && (
          <span className="mr-2">
            {validationIssues.filter((i) => i.severity === 'error').length} errors,{' '}
            {validationIssues.filter((i) => i.severity === 'warning').length} warnings
          </span>
        )}
        {formatState.formatStatus === 'formatted' && (
          <span className="text-emerald-500">Formatted</span>
        )}
        {formatState.formatStatus === 'error' && (
          <span className="text-red-500">Format failed</span>
        )}
      </div>
    </div>
  );
};

export default CodeActionBar;
