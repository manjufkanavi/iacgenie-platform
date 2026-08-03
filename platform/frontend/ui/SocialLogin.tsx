import React, { useState } from 'react';

interface SocialLoginProps {
  onSSOClick?: () => void;
  disabled?: boolean;
}

const SocialLogin: React.FC<SocialLoginProps> = ({ onSSOClick, disabled = false }) => {
  const [loadingProvider, setLoadingProvider] = useState<string | null>(null);

  const handleProviderLogin = (provider: string, endpoint: string) => {
    if (disabled || loadingProvider) return;
    setLoadingProvider(provider);
    
    // Redirecting to OAuth server endpoints
    window.location.href = endpoint;
  };

  return (
    <div className="space-y-4" data-testid="social-login-container">
      {/* Divider */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-150" />
        </div>
        <div className="relative flex justify-center text-xs font-bold uppercase tracking-wider">
          <span className="px-3 bg-white text-gray-400">Or continue with</span>
        </div>
      </div>

      {/* Social Button Grid */}
      <div className="grid grid-cols-3 gap-3">
        {/* Google Login */}
        <button
          type="button"
          disabled={disabled || !!loadingProvider}
          onClick={() => handleProviderLogin('google', '/api/auth/google')}
          className="flex justify-center items-center py-2.5 px-4 border border-gray-200 rounded-xl shadow-sm text-sm font-semibold text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-4 focus:ring-brand-primary/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="social-login-google"
        >
          {loadingProvider === 'google' ? (
            <div className="w-5 h-5 border-2 border-gray-600 border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Google
            </>
          )}
        </button>

        {/* GitHub Login */}
        <button
          type="button"
          disabled={disabled || !!loadingProvider}
          onClick={() => handleProviderLogin('github', '/api/auth/github')}
          className="flex justify-center items-center py-2.5 px-4 border border-gray-200 rounded-xl shadow-sm text-sm font-semibold text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-4 focus:ring-brand-primary/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="social-login-github"
        >
          {loadingProvider === 'github' ? (
            <div className="w-5 h-5 border-2 border-gray-600 border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <svg className="w-5 h-5 mr-2 text-gray-900 fill-current" viewBox="0 0 24 24">
                <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
              </svg>
              GitHub
            </>
          )}
        </button>

        {/* Keycloak SSO Login */}
        <button
          type="button"
          disabled={disabled || !!loadingProvider}
          onClick={() => handleProviderLogin('keycloak', '/api/auth/keycloak/login')}
          className="flex justify-center items-center py-2.5 px-4 border border-gray-200 rounded-xl shadow-sm text-sm font-semibold text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-4 focus:ring-brand-primary/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="social-login-keycloak"
        >
          {loadingProvider === 'keycloak' ? (
            <div className="w-5 h-5 border-2 border-gray-600 border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <svg className="w-5 h-5 mr-2 text-blue-600 fill-current" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
              </svg>
              SSO
            </>
          )}
        </button>
      </div>

      {/* Enterprise SSO Toggle Link */}
      {onSSOClick && (
        <div className="text-center pt-2">
          <button
            type="button"
            disabled={disabled}
            onClick={onSSOClick}
            className="text-xs font-semibold text-gray-500 hover:text-brand-primary transition-colors uppercase tracking-wider"
            data-testid="sso-login-link"
          >
            Sign in with Enterprise SSO
          </button>
        </div>
      )}
    </div>
  );
};

export default SocialLogin;
