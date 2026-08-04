import React, { useState } from 'react';
import { View } from './types';
import Card from '../ui/Card';
import FormGroup from '../ui/FormGroup';
import SecurePasswordInput from '../ui/SecurePasswordInput';
import SocialLogin from '../ui/SocialLogin';
import SSOModal from '../ui/SSOModal';
import Button from '../ui/Button';
import { useAuthStore } from '../../store/useAuthStore';
import { handleKeycloakCallback } from '../../services/keycloakAuthService';

interface SignInPageProps {
    onSignIn: (user: any) => void;
    onNavigate: (view: View) => void;
}

const SignInPage: React.FC<SignInPageProps> = ({ onSignIn, onNavigate }) => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [rememberMe, setRememberMe] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isSSOOpen, setIsSSOOpen] = useState(false);
    const { login, isLoading } = useAuthStore();

    React.useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const errorParam = params.get('error');

        if (errorParam) {
            setError(decodeURIComponent(errorParam));
            window.history.replaceState(null, '', window.location.pathname);
            return;
        }

        // Handle Keycloak OAuth callback
        const token = params.get('token');
        const provider = params.get('provider');
        if (token && provider === 'keycloak') {
            setError(null);
            handleKeycloakCallback()
                .then((success) => {
                    if (success) {
                        onSignIn(useAuthStore.getState().user);
                    }
                })
                .catch((err) => {
                    setError(err.message || 'Token verification failed.');
                });
        }
    }, [onSignIn]);

    // Email/password login
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        try {
            const user = await login(email, password);
            onSignIn(user);
        } catch (err: any) {
            setError(err.message || 'Authentication failed. Please check your credentials.');
        }
    };

    // SSO Submit Action
    const handleSSOSubmit = async (domain: string) => {
        // Construct enterprise SSO redirect url
        window.location.href = `/api/auth/sso?domain=${encodeURIComponent(domain)}`;
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 py-8 px-4 sm:px-6 lg:px-8" data-testid="signin-page">
            <div className="max-w-md w-full">
                {/* Header */}
                <div className="text-center mb-8">
                    <button
                        type="button"
                        onClick={() => onNavigate('landing')}
                        title="Go to home"
                        aria-label="Go to home"
                        className="mx-auto h-16 w-16 bg-brand-primary rounded-xl flex items-center justify-center mb-6 shadow-sm transform hover:scale-105 transition-transform duration-300 focus:outline-none focus:ring-4 focus:ring-brand-primary/20"
                    >
                        <svg className="h-8 w-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                        </svg>
                    </button>
                    <h1 className="text-3xl font-extrabold text-slate-900 dark:text-slate-50 tracking-tight mb-2">Welcome back</h1>
                    <p className="text-slate-600 dark:text-slate-400 font-medium">Sign in to your account to continue</p>
                </div>

                {/* Auth Card */}
                <Card className="shadow-xl">
                    <div className="p-6 sm:p-8">
                        <FormGroup onSubmit={handleSubmit} isSubmitting={isLoading}>
                            {/* Email Field */}
                            <div>
                                <label htmlFor="email" className="block text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">
                                    Email address
                                </label>
                                <div className="relative">
                                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                        <svg className="h-5 w-5 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                                        </svg>
                                    </div>
                                    <input
                                        id="email"
                                        name="email"
                                        type="email"
                                        autoComplete="email"
                                        required
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="block w-full pl-10 pr-3 py-3 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-xl shadow-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition-all duration-200 hover:border-slate-450 dark:hover:border-slate-500 text-slate-900 dark:text-slate-50"
                                        placeholder="Enter your email"
                                        disabled={isLoading}
                                        data-testid="signin-email-input"
                                    />
                                </div>
                            </div>

                            {/* Password Field */}
                            <SecurePasswordInput
                                label="Password"
                                id="password"
                                name="password"
                                autoComplete="current-password"
                                required
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Enter your password"
                                disabled={isLoading}
                                data-testid="signin-password-input"
                            />

                            {/* Error Messages */}
                            {error && (
                                <div className="p-3 bg-red-50 border border-red-200 rounded-xl">
                                    <p className="text-red-600 text-xs font-semibold text-center">{error}</p>
                                </div>
                            )}

                            {/* Remember Me & Forgot Password */}
                            <div className="flex items-center justify-between">
                                <div className="flex items-center">
                                    <input
                                        id="remember-me"
                                        name="remember-me"
                                        type="checkbox"
                                        checked={rememberMe}
                                        onChange={(e) => setRememberMe(e.target.checked)}
                                        className="h-4 w-4 text-brand-primary focus:ring-brand-primary border-slate-300 dark:border-slate-600 rounded transition duration-150 cursor-pointer"
                                        disabled={isLoading}
                                        data-testid="signin-remember-me"
                                    />
                                    <label htmlFor="remember-me" className="ml-2 block text-sm font-semibold text-slate-700 dark:text-slate-200 cursor-pointer">
                                        Remember me
                                    </label>
                                </div>
                                <div className="text-sm font-bold">
                                    <button
                                        type="button"
                                        onClick={() => onNavigate('forgot-password')}
                                        className="text-brand-primary hover:text-brand-primary/80 hover:underline transition-colors duration-200"
                                        disabled={isLoading}
                                        data-testid="signin-forgot-password-link"
                                    >
                                        Forgot password?
                                    </button>
                                </div>
                            </div>

                            {/* Sign In Button */}
                            <Button
                                type="submit"
                                isLoading={isLoading}
                                size="lg"
                                className="w-full"
                                data-testid="signin-submit-button"
                            >
                                Sign in
                            </Button>
                        </FormGroup>

                        {/* Social Login Rows */}
                        <div className="mt-6">
                            <SocialLogin
                                onSSOClick={() => setIsSSOOpen(true)}
                                disabled={isLoading}
                            />
                        </div>

                        {/* Sign Up Link */}
                        <div className="mt-8 text-center border-t border-slate-100 dark:border-slate-600 pt-6">
                            <p className="text-sm font-semibold text-slate-500 dark:text-slate-400">
                                Don't have an account?{' '}
                                <button
                                    type="button"
                                    onClick={() => onNavigate('signup')}
                                    className="font-bold text-brand-primary hover:text-orange-600 hover:underline transition-colors duration-200"
                                    disabled={isLoading}
                                    data-testid="signin-signup-link"
                                >
                                    Sign up
                                </button>
                            </p>
                        </div>
                    </div>
                </Card>
            </div>

            {/* SSO Modal Dialog */}
            <SSOModal
                isOpen={isSSOOpen}
                onClose={() => setIsSSOOpen(false)}
                onSubmit={handleSSOSubmit}
            />
        </div>
    );
};

export default SignInPage;