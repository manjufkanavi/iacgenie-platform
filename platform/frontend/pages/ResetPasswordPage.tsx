import React, { useState, useEffect } from 'react';
import { View } from '../types';
import Card from '../ui/Card';
import FormGroup from '../ui/FormGroup';
import { localAuthService } from '../services/localAuthService';

interface ResetPasswordPageProps {
    onNavigate: (view: View) => void;
}

const ResetPasswordPage: React.FC<ResetPasswordPageProps> = ({ onNavigate }) => {
    // Extract token and email from URL query string (not React Router)
    const [token, setToken] = useState<string>('');
    const [resetEmail, setResetEmail] = useState<string>('');

    // Password state
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [status, setStatus] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);

    // Extract token from URL on mount
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const urlToken = params.get('token') || '';
        const urlEmail = params.get('email') || '';

        // Also check sessionStorage as fallback (from forgot-password flow)
        const sessionToken = sessionStorage.getItem('password_reset_token');
        const sessionEmail = sessionStorage.getItem('reset_password_email');

        setToken(urlToken || (sessionToken ? decodeURIComponent(sessionToken) : ''));
        setResetEmail(urlEmail || sessionEmail || '');
    }, []);

    // Password requirements synced with backend validation rules:
    // min 8 chars, uppercase, lowercase, number, special char
    const getPasswordRequirements = (password: string) => ({
        minLength: password.length >= 8,
        hasUppercase: /[A-Z]/.test(password),
        hasLowercase: /[a-z]/.test(password),
        hasNumber: /[0-9]/.test(password),
        hasSpecialChar: /[!@#$%^&*(),.?":{}|<>]/.test(password),
    });

    const requirements = getPasswordRequirements(newPassword);
    const allRequirementsMet = Object.values(requirements).every(Boolean);

    // Check if password is strong
    const isPasswordStrong = (_password: string): { valid: boolean; message?: string } => {
        if (!requirements.minLength) {
            return { valid: false, message: 'Password must be at least 8 characters long' };
        }
        if (!requirements.hasUppercase) {
            return { valid: false, message: 'Password must contain at least one uppercase letter' };
        }
        if (!requirements.hasLowercase) {
            return { valid: false, message: 'Password must contain at least one lowercase letter' };
        }
        if (!requirements.hasNumber) {
            return { valid: false, message: 'Password must contain at least one number' };
        }
        if (!requirements.hasSpecialChar) {
            return { valid: false, message: 'Password must contain at least one special character' };
        }
        return { valid: true };
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setStatus(null);
        setError(null);

        // Validate form
        if (!newPassword) {
            setError('New password is required');
            return;
        }

        if (newPassword !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        const passwordCheck = isPasswordStrong(newPassword);
        if (!passwordCheck.valid) {
            setError(passwordCheck.message || 'Password does not meet requirements');
            return;
        }

        if (!token) {
            setError('Invalid or missing token. Please request a new password reset.');
            return;
        }

        setIsLoading(true);

        try {
            const user = await localAuthService.verifyOtpAndResetPassword(token, newPassword);

            if (user && user.email) {
                setIsSuccess(true);
                setStatus('Password reset successfully. You can now sign in with your new password.');

                // Clear session storage tokens after successful reset
                sessionStorage.removeItem('password_reset_token');
                sessionStorage.removeItem('reset_password_email');
            }
        } catch (err: any) {
            setError(err.message || 'Failed to reset password.');
        } finally {
            setIsLoading(false);
        }
    };

    // Success page
    if (isSuccess) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 py-8 px-4 sm:px-6 lg:px-8">
                <div className="max-w-md w-full">
                    <Card className="shadow-xl border-0 bg-white/80 backdrop-blur-sm">
                        <div className="p-8 text-center">
                            <div className="mx-auto h-16 w-16 bg-green-100 rounded-full flex items-center justify-center mb-6">
                                <svg className="h-8 w-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                            </div>
                            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 mb-4">Password Reset Successful!</h1>
                            <p className="text-slate-600 dark:text-slate-300 mb-6">{status}</p>
                            <div className="bg-blue-50 p-4 rounded-lg mb-6">
                                <p className="text-sm text-blue-800">
                                    Your password has been updated. Please sign in with your new password.
                                </p>
                            </div>
                            <button
                                onClick={() => {
                                    // Store email for auto-fill on signin page
                                    if (resetEmail) {
                                        sessionStorage.setItem('signin_email', resetEmail);
                                    }
                                    window.history.pushState({ fromResetPassword: true }, '', '/signin');
                                }}
                                className="w-full py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-medium text-white bg-gradient-to-r from-brand-primary to-red-500 hover:from-brand-primary/90 hover:to-red-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-primary transition-all duration-200"
                            >
                                Sign In with New Password
                            </button>
                        </div>
                    </Card>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 py-8 px-4 sm:px-6 lg:px-8">
            <div className="max-w-md w-full">
                {/* Header */}
                <div className="text-center mb-8">
                    <button
                        type="button"
                        onClick={() => onNavigate('landing')}
                        title="Go to home"
                        aria-label="Go to home"
                        className="mx-auto h-16 w-16 bg-gradient-to-r from-brand-primary to-red-500 rounded-2xl flex items-center justify-center mb-6 shadow-lg transform hover:scale-105 transition-transform duration-300 focus:outline-none focus:ring-4 focus:ring-brand-primary/20"
                    >
                        <svg className="h-8 w-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                        </svg>
                    </button>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50 mb-2">Reset your password</h1>
                    <p className="text-slate-600 dark:text-slate-300">Enter a new password for your account</p>
                </div>

                {/* Auth Card */}
                <Card className="shadow-xl border-0 bg-white/80 backdrop-blur-sm">
                    <div className="p-8">
                        {/* Token Status */}
                        {!token && (
                            <div className="mb-6 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                                <p className="text-yellow-700 text-sm">
                                    No valid token found. Please request a new password reset.
                                </p>
                            </div>
                        )}

                        {token && (
                            <div className="mb-6 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                                <p className="text-blue-700 text-sm font-medium">
                                    Valid token found. Please create a new password.
                                </p>
                            </div>
                        )}

                        <FormGroup onSubmit={handleSubmit} isSubmitting={isLoading}>
                            {/* New Password Field */}
                            <div className="mb-4">
                                <label htmlFor="newPassword" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                                    New Password
                                </label>
                                <div className="relative">
                                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                        <svg className="h-5 w-5 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                        </svg>
                                    </div>
                                    <input
                                        id="newPassword"
                                        name="newPassword"
                                        type="password"
                                        autoComplete="new-password"
                                        required
                                        value={newPassword}
                                        onChange={(e) => setNewPassword(e.target.value)}
                                        className={`block w-full pl-10 pr-3 py-3 border rounded-xl shadow-sm placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition-all duration-200 ${
                                            newPassword && !allRequirementsMet ? 'border-red-300' : 'border-slate-300 dark:border-slate-500'
                                        }`}
                                        placeholder="Enter new password"
                                        disabled={isLoading}
                                    />
                                </div>

                                {/* Password Requirements Checklist */}
                                {newPassword && (
                                    <div className="mt-3 space-y-2">
                                        <p className="text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Password must contain:</p>
                                        <div className="grid grid-cols-1 gap-1.5">
                                            {[
                                                { label: 'At least 8 characters', met: requirements.minLength },
                                                { label: 'One uppercase letter', met: requirements.hasUppercase },
                                                { label: 'One lowercase letter', met: requirements.hasLowercase },
                                                { label: 'One number', met: requirements.hasNumber },
                                                { label: 'One special character (!@#$%^&*...)', met: requirements.hasSpecialChar },
                                            ].map((req) => (
                                                <div key={req.label} className="flex items-center text-xs">
                                                    <span className={`mr-2 h-4 w-4 flex items-center justify-center rounded-full border ${
                                                        req.met
                                                            ? 'bg-green-500 border-green-500 text-white'
                                                            : 'border-slate-300 dark:border-slate-500 bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500'
                                                    }`}>
                                                        {req.met ? (
                                                            <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                                            </svg>
                                                        ) : (
                                                            <span className="text-[10px]">○</span>
                                                        )}
                                                    </span>
                                                    <span className={req.met ? 'text-green-700 font-medium' : 'text-slate-500 dark:text-slate-400'}>
                                                        {req.label}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Confirm Password Field */}
                            <div className="mb-6">
                                <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                                    Confirm Password
                                </label>
                                <div className="relative">
                                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                        <svg className="h-5 w-5 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                                        </svg>
                                    </div>
                                    <input
                                        id="confirmPassword"
                                        name="confirmPassword"
                                        type="password"
                                        autoComplete="new-password"
                                        required
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        className={`block w-full pl-10 pr-3 py-3 border rounded-xl shadow-sm placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition-all duration-200 ${
                                            confirmPassword && newPassword !== confirmPassword ? 'border-red-300' : 'border-slate-300 dark:border-slate-500'
                                        }`}
                                        placeholder="Confirm new password"
                                        disabled={isLoading}
                                    />
                                </div>
                                {confirmPassword && newPassword !== confirmPassword && (
                                    <p className="mt-1 text-sm text-red-600">Passwords do not match</p>
                                )}
                                {confirmPassword && newPassword === confirmPassword && (
                                    <p className="mt-1 text-sm text-green-600">Passwords match</p>
                                )}
                            </div>

                            {/* Error Messages */}
                            {error && (
                                <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg">
                                    <p className="text-red-600 text-sm text-center">{error}</p>
                                </div>
                            )}

                            {/* Reset Password Button */}
                            <button
                                type="submit"
                                disabled={isLoading || !newPassword || newPassword !== confirmPassword || !allRequirementsMet}
                                className="w-full flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-medium text-white bg-gradient-to-r from-brand-primary to-red-500 hover:from-brand-primary/90 hover:to-red-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-primary transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {isLoading ? (
                                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                ) : (
                                    <>
                                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                        </svg>
                                        Reset Password
                                    </>
                                )}
                            </button>
                        </FormGroup>

                        {/* Back to Sign In Link */}
                        <div className="mt-8 text-center">
                            <p className="text-sm text-slate-600 dark:text-slate-300">
                                Remember your password?{' '}
                                <button
                                    type="button"
                                    onClick={() => onNavigate('signin')}
                                    className="font-medium text-brand-primary hover:text-brand-primary/80 transition-colors duration-200"
                                    disabled={isLoading}
                                >
                                    Sign in
                                </button>
                            </p>
                        </div>
                    </div>
                </Card>
            </div>
        </div>
    );
};

export default ResetPasswordPage;
