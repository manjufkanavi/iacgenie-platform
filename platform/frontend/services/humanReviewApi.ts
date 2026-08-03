/**
 * Human review API utilities for pipeline workflow.
 */

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

export async function approveReview(sessionId: string, comment?: string): Promise<void> {
  const token = localStorage.getItem('iacgenie_token');
  const res = await fetch(`${API_BASE}/api/workflow/${sessionId}/human-review/approve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ action: 'approve', comment }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail?.message || 'Failed to approve review');
  }
}

export async function clarifyReview(sessionId: string, comment?: string): Promise<void> {
  const token = localStorage.getItem('iacgenie_token');
  const res = await fetch(`${API_BASE}/api/workflow/${sessionId}/human-review/clarify`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ action: 'clarify', comment }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail?.message || 'Failed to request clarification');
  }
}

export async function escalateReview(sessionId: string, comment?: string): Promise<void> {
  const token = localStorage.getItem('iacgenie_token');
  const res = await fetch(`${API_BASE}/api/workflow/${sessionId}/human-review/escalate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ action: 'escalate', comment }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail?.message || 'Failed to escalate review');
  }
}

export type ReviewAction = 'approve' | 'clarify' | 'escalate';

export async function submitReviewAction(
  sessionId: string,
  action: ReviewAction,
  comment?: string,
): Promise<void> {
  switch (action) {
    case 'approve':
      return approveReview(sessionId, comment);
    case 'clarify':
      return clarifyReview(sessionId, comment);
    case 'escalate':
      return escalateReview(sessionId, comment);
  }
}
