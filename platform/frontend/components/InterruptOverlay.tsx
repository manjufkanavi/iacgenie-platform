'use client';

import React, { useState } from 'react';

interface InterruptOverlayProps {
  visible: boolean;
  reason: string | null;
  sessionId: string;
  onAction: (action: 'approve' | 'clarify' | 'escalate', comment: string) => Promise<void>;
  onClose: () => void;
}

export function InterruptOverlay({ visible, reason, sessionId, onAction, onClose }: InterruptOverlayProps) {
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(false);
  const [action, setAction] = useState<'approve' | 'clarify' | 'escalate' | null>(null);

  if (!visible) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!action || !sessionId) return;
    setLoading(true);
    try {
      await onAction(action, comment);
      setAction(null);
      setComment('');
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-lg border border-gray-700 bg-gray-900 p-6 shadow-2xl">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-yellow-500/20">
            <svg className="h-6 w-6 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Human Review Required</h3>
            {reason && <p className="text-sm text-gray-400">{reason}</p>}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <textarea
            className="w-full rounded-md border border-gray-700 bg-gray-800 p-3 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
            rows={3}
            placeholder="Add a comment (optional)..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />

          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => { setAction('approve'); }}
              className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                action === 'approve'
                  ? 'bg-green-600 text-white'
                  : 'border border-green-600 text-green-400 hover:bg-green-600/10'
              }`}
            >
              Approve
            </button>
            <button
              type="button"
              onClick={() => { setAction('clarify'); }}
              className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                action === 'clarify'
                  ? 'bg-blue-600 text-white'
                  : 'border border-blue-600 text-blue-400 hover:bg-blue-600/10'
              }`}
            >
              Request Clarification
            </button>
            <button
              type="button"
              onClick={() => { setAction('escalate'); }}
              className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                action === 'escalate'
                  ? 'bg-red-600 text-white'
                  : 'border border-red-600 text-red-400 hover:bg-red-600/10'
              }`}
            >
              Escalate
            </button>
          </div>

          {action && (
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Submitting...' : `Confirm ${action}`}
              </button>
              <button
                type="button"
                onClick={() => setAction(null)}
                className="flex-1 rounded-md border border-gray-600 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-800"
              >
                Cancel
              </button>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
