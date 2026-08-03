import React, { useState } from 'react';
import Card from './Card';
import Button from './Button';

interface SSOModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (domain: string) => Promise<void> | void;
}

const SSOModal: React.FC<SSOModalProps> = ({ isOpen, onClose, onSubmit }) => {
  const [domain, setDomain] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedDomain = domain.trim();
    if (!trimmedDomain) {
      setError('Please enter your organization domain or email');
      return;
    }

    setIsLoading(true);
    try {
      await onSubmit(trimmedDomain);
    } catch (err: any) {
      setError(err.message || 'SSO authentication failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-sm"
      data-testid="sso-modal-backdrop"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white shadow-2xl transition-all"
        onClick={(e) => e.stopPropagation()}
        data-testid="sso-modal"
      >
        <Card className="border-0 bg-white">
          <div className="p-6 sm:p-8">
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
              <div>
                <h3 className="text-xl font-bold text-gray-900">Enterprise Single Sign-On</h3>
                <p className="text-sm text-gray-500 mt-1">Sign in using your corporate credentials</p>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="p-1 rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-all duration-200"
                aria-label="Close"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="sso-domain" className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                  Organization Domain or Email
                </label>
                <input
                  id="sso-domain"
                  type="text"
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  placeholder="e.g. acme.com or user@acme.com"
                  disabled={isLoading}
                  className="block w-full px-4 py-3 border border-gray-200 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-4 focus:ring-brand-primary/10 focus:border-brand-primary transition-all duration-200"
                  data-testid="sso-domain-input"
                  required
                />
              </div>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-center">
                  <p className="text-xs font-semibold text-red-600">{error}</p>
                </div>
              )}

              <div className="flex space-x-3 pt-2">
                <Button
                  variant="secondary"
                  size="md"
                  onClick={onClose}
                  className="flex-1"
                  disabled={isLoading}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="md"
                  type="submit"
                  className="flex-1"
                  disabled={isLoading || !domain.trim()}
                  data-testid="sso-submit-button"
                >
                  {isLoading ? (
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mx-auto" />
                  ) : (
                    'Proceed to SSO'
                  )}
                </Button>
              </div>
            </form>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default SSOModal;
