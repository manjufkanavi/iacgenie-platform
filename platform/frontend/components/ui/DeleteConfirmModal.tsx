import React, { useState, useEffect, useRef } from 'react';
import Modal from './Modal';

interface DeleteConfirmModalProps {
  open: boolean;
  onClose: () => void;
  /** Main title of the modal. Default: "Delete Item" */
  title?: string;
  /** Description body — can include JSX for rich formatting. */
  description?: React.ReactNode;
  /** The word the user must type to confirm. Default: "DELETE" */
  confirmWord?: string;
  /** Label for the confirm button. Default: "Delete" */
  confirmLabel?: string;
  /** Callback when confirm is clicked. */
  onConfirm: () => void;
  /** Show an "invalidate sessions" checkbox. Default: false */
  showInvalidateSessions?: boolean;
  /** Loading/disabled state. Default: false */
  loading?: boolean;

  // ─── Legacy props for backward compat with CloudCredentialsSettings ───
  provider?: string;
  keyName?: string;
}

const DeleteConfirmModal: React.FC<DeleteConfirmModalProps> = ({
  open,
  onClose,
  onConfirm,
  showInvalidateSessions = false,
  loading = false,

  // Explicit new API props
  title,
  description,
  confirmWord: confirmWordProp,
  confirmLabel: confirmLabelProp,

  // Legacy props (backward compat)
  provider,
  keyName,
}) => {
  const [confirmText, setConfirmText] = useState('');
  const [invalidateSessions, setInvalidateSessions] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  // Resolve confirm word: explicit prop → legacy mode fallback
  const confirmWord = confirmWordProp ?? 'DELETE';

  // Resolve title: explicit prop → legacy fallback
  const resolvedTitle = title ?? (provider !== undefined ? 'Delete Credential' : 'Delete Item');

  // Resolve description: explicit prop → legacy fallback
  const resolvedDescription = description !== undefined
    ? description
    : provider !== undefined
      ? (
        <p className="text-sm text-slate-600 dark:text-slate-400">
          This action cannot be undone. The credentials for <strong>{provider}</strong>
          {keyName ? ` (key: <strong>{keyName}</strong>)` : ''} will be permanently removed from OpenBao.
        </p>
      )
      : null;

  // Resolve confirm button label: explicit prop → default
  const confirmLabel = confirmLabelProp ?? 'Delete';

  const isConfirmed = confirmText.trim().toUpperCase() === confirmWord.toUpperCase();
  const isPartialMatch = confirmText.trim().length > 0 && !isConfirmed;

  useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus();
    }
    if (!open) {
      setConfirmText('');
      setInvalidateSessions(false);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const modal = modalRef.current;
    if (!modal) return;
    const focusableElements = modal.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];
    firstFocusable?.focus();
    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;
      if (e.shiftKey) {
        if (document.activeElement === firstFocusable) { e.preventDefault(); lastFocusable?.focus(); }
      } else {
        if (document.activeElement === lastFocusable) { e.preventDefault(); firstFocusable?.focus(); }
      }
    };
    document.addEventListener('keydown', handleTab);
    return () => document.removeEventListener('keydown', handleTab);
  }, [open]);

  const handleEsc = (e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
  };

  useEffect(() => {
    if (open) document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, [open]);

  const handleConfirm = () => {
    if (isConfirmed && !loading) {
      onConfirm();
    }
  };

  return (
    <Modal
      isOpen={open}
      onClose={onClose}
      title={resolvedTitle}
      icon={
        <div className="flex items-center justify-center h-10 w-10 rounded-full bg-red-100 dark:bg-red-950">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-red-500 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
      }
      size="sm"
      showCloseButton={!loading}
    >
      <div className="text-center mb-4">
        {resolvedDescription || (
          <p className="text-sm text-slate-600 dark:text-slate-400">
            This action cannot be undone.
          </p>
        )}
      </div>

      {showInvalidateSessions && (
        <div className="mb-4">
          <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={invalidateSessions}
              onChange={(e) => setInvalidateSessions(e.target.checked)}
              className="rounded border-slate-300 text-brand-primary focus:ring-brand-primary"
            />
            Also invalidate active sessions
          </label>
          <p className="text-xs text-slate-500 dark:text-slate-500 mt-1 ml-6">Optional</p>
        </div>
      )}

      <div className="mb-4">
        <label htmlFor="delete-confirm-input" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
          Type <span className="font-bold">{confirmWord}</span> to confirm:
        </label>
        <input
          ref={inputRef}
          id="delete-confirm-input"
          type="text"
          value={confirmText}
          onChange={(e) => setConfirmText(e.target.value)}
          className={`w-full bg-white border rounded-lg py-2 px-3 text-slate-900 placeholder-slate-400 dark:placeholder-slate-500 dark:bg-slate-700 dark:text-slate-50 focus:outline-none focus:ring-2 sm:text-sm transition ${
            isPartialMatch
              ? 'border-red-300 focus:border-red-500 focus:ring-red-500 dark:border-red-700 dark:focus:border-red-400 dark:focus:ring-red-400'
              : isConfirmed
              ? 'border-green-300 focus:border-green-500 focus:ring-green-500 dark:border-green-700 dark:focus:border-green-400 dark:focus:ring-green-400'
              : 'border-slate-300 dark:border-slate-600'
          }`}
          placeholder={confirmWord}
          aria-invalid={isPartialMatch}
        />
      </div>

      <div className="flex items-center justify-end gap-3">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 text-sm font-semibold text-slate-700 bg-slate-100 border border-slate-200 rounded-lg hover:bg-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-primary dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600 dark:border-slate-600 transition-colors"
        >
          Cancel
        </button>
        <button
          type="button"
          data-testid="confirm-dialog-btn"
          onClick={handleConfirm}
          disabled={!isConfirmed || loading}
          className="px-4 py-2 text-sm font-semibold text-white bg-[#ef4444] rounded-lg hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Deleting...
            </span>
          ) : (
            confirmLabel
          )}
        </button>
      </div>
    </Modal>
  );
};

export default DeleteConfirmModal;
