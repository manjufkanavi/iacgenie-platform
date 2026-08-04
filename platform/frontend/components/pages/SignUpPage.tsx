import React, { useState, useEffect } from 'react';
import { View } from './types';
import Card from '../ui/Card';
import FormGroup from '../ui/FormGroup';
import SecurePasswordInput from '../ui/SecurePasswordInput';
import PasswordStrengthMeter from '../ui/PasswordStrengthMeter';
import SocialLogin from '../ui/SocialLogin';
import SSOModal from '../ui/SSOModal';
import Button from '../ui/Button';
import OTPInput from '../ui/OTPInput';
import ResendTimer from '../ui/ResendTimer';
import { useAuthStore } from '../../store/useAuthStore';
import type { SignupCredentials, SignupResult } from '../../services/localAuthService';

interface SignUpPageProps {
    onNavigate: (view: View) => void;
}

const SignUpPage: React.FC<SignUpPageProps> = ({ onNavigate }) => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [firstName, setFirstName] = useState('');
    const [lastName, setLastName] = useState('');
    const [status, setStatus] = useState<'form' | 'otp_required' | 'verify_email_sent' | 'success'>('form');
    const [error, setError] = useState<string | null>(null);
    const [otpDigits, setOtpDigits] = useState<string[]>(['', '', '', '', '', '']);
    const [message, setMessage] = useState('');
    const [otpToken, setOtpToken] = useState<string | null>(null);
    const [isSSOOpen, setIsSSOOpen] = useState(false);

    const { signup, isLoading } = useAuthStore();

    // Reset OTP digits when switching to OTP screen
    useEffect(() => {
        if (status === 'otp_required') {
            setOtpDigits(['', '', '', '', '', '']);
        }
    }, [status]);

    const isValidEmail = (val: string) => {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
    };

    const passwordsMatch = password === confirmPassword && password.length > 0;

    // Handle OTP verification
    const handleVerifyOtp = async () => {
        const otpCode = otpDigits.join('');
        if (otpCode.length !== 6) {
            setError('Please enter the complete 6-digit OTP code');
            return;
        }

        setError(null);

        try {
            const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

            if (!otpToken) {
                setError('OTP token not available. Please sign up again.');
                return;
            }

            const response = await fetch(`${baseUrl}/api/auth/verify-otp`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    token: otpToken,
                    otp: otpCode
                }),
            });

            const result = await response.json();

            if (response.ok && result.success) {
                setStatus('success');
                setMessage(result.message || 'OTP verified successfully! Please sign in to continue.');
            } else {
                setError(result.error?.message || result.message || 'OTP verification failed.');
            }
        } catch (err: any) {
            setError(err.message || 'OTP verification failed.');
        }
    };

    // Resend OTP Code
    const handleResendOtp = async () => {
        if (!email || !otpToken) {
            setError('Email or session token is not available');
            return;
        }

        setError(null);

        try {
            const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
            const response = await fetch(`${baseUrl}/api/auth/resend-otp`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    token: otpToken,
                    email: email
                }),
            });

            const result = await response.json();

            if (response.ok) {
                setMessage(result.message || 'Verification code resent successfully. Please check your email inbox.');
                if (result.data?.otp_token) {
                    setOtpToken(result.data.otp_token);
                }
            } else {
                setError(result.message || result.error?.message || 'Failed to resend verification code');
            }
        } catch (err: any) {
            setError(err.message || 'Failed to resend verification code');
        }
    };

    // Submit Registration Details
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!firstName.trim()) {
            setError('Please enter your first name');
            return;
        }
        if (!lastName.trim()) {
            setError('Please enter your last name');
            return;
        }
        if (!isValidEmail(email)) {
            setError('Please enter a valid email address');
            return;
        }
        if (password.length < 8) {
            setError('Password must be at least 8 characters long');
            return;
        }
        if (!passwordsMatch) {
            setError('Passwords do not match');
            return;
        }

        try {
            const displayName = [firstName, lastName].filter(Boolean).join(' ');
            const creds: SignupCredentials = { email, password, firstName, lastName, displayName };
            const result: SignupResult = await signup(creds);

            if (result.success) {
                const storedOtpToken = result.otpToken;

                if (storedOtpToken) {
                    setOtpToken(storedOtpToken);
                    setStatus('otp_required');
                } else {
                    // Link-based verification (Keycloak flow): email with link was sent
                    setMessage(result.message || 'A verification link has been sent to your email. Please check your inbox and click the link to verify your account.');
                    setStatus('verify_email_sent');
                }
            } else {
                setError(result.message || 'Signup failed.');
            }
        } catch (err: any) {
            setError(err.message || 'Signup failed.');
        }
    };

    // SSO Redirection
    const handleSSOSubmit = async (domain: string) => {
        window.location.href = `/api/auth/sso?domain=${encodeURIComponent(domain)}`;
    };

    // 1. Success View
    if (status === 'success') {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 py-8 px-4 sm:px-6 lg:px-8" data-testid="signup-success-page">
                <div className="max-w-md w-full">
                    <Card className="shadow-xl">
                        <div className="p-8 text-center animate-fade-in">
                            <div className="mx-auto h-16 w-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mb-6">
                                <svg className="h-8 w-8 text-green-600 dark:text-green-400 animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 13l4 4L19 7" />
                                </svg>
                            </div>
                            <h1 className="text-2xl font-extrabold text-slate-900 dark:text-slate-50 mb-4">Email Verified!</h1>
                            <p className="text-slate-600 dark:text-slate-400 mb-6 font-medium">{message}</p>
                            <Button
                                onClick={() => onNavigate('signin')}
                                size="lg"
                                className="w-full"
                                data-testid="signup-success-signin-button"
                            >
                                Sign In
                            </Button>
                        </div>
                    </Card>
                </div>
            </div>
        );
    }
    // 2. Verification Link Sent View (Keycloak link-based flow)
    if (status === 'verify_email_sent') {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 py-8 px-4 sm:px-6 lg:px-8" data-testid="signup-verify-email-sent-page">
                <div className="max-w-md w-full">
                    <Card className="shadow-xl">
                        <div className="p-8 text-center animate-fade-in">
                            <div className="mx-auto h-16 w-16 bg-brand-primary/10 rounded-full flex items-center justify-center mb-6">
                                <svg className="h-8 w-8 text-brand-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                                </svg>
                            </div>
                            <h1 className="text-2xl font-extrabold text-slate-900 dark:text-slate-50 mb-4">Check Your Email</h1>
                            <p className="text-slate-600 dark:text-slate-400 mb-2 font-medium">
                                We sent a verification link to
                            </p>
                            <p className="text-brand-primary font-bold mb-6">{email}</p>
                            <p className="text-slate-500 dark:text-slate-400 text-sm mb-8">
                                {message || 'Click the link in the email to verify your account. The link expires in 24 hours.'}
                            </p>
                            <Button
                                onClick={() => onNavigate('signin')}
                                size="lg"
                                className="w-full"
                                data-testid="verify-email-sent-signin-button"
                            >
                                Go to Sign In
                            </Button>
                        </div>
                    </Card>
                </div>
            </div>
        );
    }

    // 3. OTP Code Verification Step
    if (status === 'otp_required') {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 py-8 px-4 sm:px-6 lg:px-8" data-testid="signup-otp-page">
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
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                            </svg>
                        </button>
                        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-slate-50 mb-2">Enter Verification Code</h1>
                        <p className="text-slate-600 dark:text-slate-400 font-medium">
                            We've sent a 6-digit code to<br/>
                            <span className="text-brand-primary font-bold">{email}</span>
                        </p>
                    </div>

                    {/* Auth Card */}
                    <Card className="shadow-xl">
                        <div className="p-6 sm:p-8 space-y-6">
                            <div>
                                <label htmlFor="otp" className="block text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-3 text-center">
                                    6-digit OTP Code
                                </label>
                                <OTPInput
                                    value={otpDigits}
                                    onChange={setOtpDigits}
                                    length={6}
                                    disabled={isLoading}
                                    error={!!error}
                                />
                            </div>

                            {/* Messages & Errors */}
                            {error && (
                                <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-center">
                                    <p className="text-red-600 text-xs font-semibold">{error}</p>
                                </div>
                            )}

                            {message && (
                                <div className="p-3 bg-green-50 border border-green-200 rounded-xl text-center animate-fade-in">
                                    <p className="text-green-700 text-xs font-semibold">{message}</p>
                                </div>
                            )}

                            {/* Verify Button */}
                            <Button
                                type="button"
                                onClick={handleVerifyOtp}
                                disabled={otpDigits.some(d => d === '')}
                                isLoading={isLoading}
                                size="lg"
                                className="w-full"
                                data-testid="otp-verify-button"
                            >
                                Verify Code
                            </Button>

                            {/* Reusable Resend Timer */}
                            <ResendTimer
                                initialSeconds={60}
                                onResend={handleResendOtp}
                                disabled={isLoading}
                            />

                            {/* Back to Sign In Link */}
                            <div className="mt-6 text-center border-t border-slate-100 dark:border-slate-600 pt-6">
                                <p className="text-sm font-semibold text-slate-500 dark:text-slate-400">
                                    Already have an account?{' '}
                                    <button
                                        type="button"
                                        onClick={() => onNavigate('signin')}
                                        className="font-bold text-brand-primary hover:text-brand-primary/80 hover:underline transition-colors duration-200"
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
    }

    // 3. Main Sign Up Form
    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 py-8 px-4 sm:px-6 lg:px-8" data-testid="signup-page">
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
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                        </svg>
                    </button>
                    <h1 className="text-3xl font-extrabold text-slate-900 dark:text-slate-50 tracking-tight mb-2">Create your account</h1>
                    <p className="text-slate-600 dark:text-slate-400 font-medium">Join Iacgenie to start building infrastructure</p>
                </div>

                {/* Auth Card */}
                <Card className="shadow-xl">
                    <div className="p-6 sm:p-8">
                        <FormGroup onSubmit={handleSubmit} isSubmitting={isLoading}>
                            {/* First Name Field */}
                            <div>
                                <label htmlFor="firstName" className="block text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">
                                    First name
                                </label>
                                <div className="relative">
                                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                        <svg className="h-5 w-5 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                        </svg>
                                    </div>
                                    <input
                                        id="firstName"
                                        name="firstName"
                                        type="text"
                                        autoComplete="given-name"
                                        required
                                        value={firstName}
                                        onChange={(e) => setFirstName(e.target.value)}
                                        className="block w-full pl-10 pr-3 py-3 border bg-white dark:bg-slate-800 rounded-xl shadow-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition-all duration-200 hover:border-slate-450 dark:hover:border-slate-500 text-slate-900 dark:text-slate-50 border-slate-200 dark:border-slate-700"
                                        placeholder="Enter your first name"
                                        disabled={isLoading}
                                        data-testid="signup-first-name-input"
                                    />
                                </div>
                            </div>

                            {/* Last Name Field */}
                            <div>
                                <label htmlFor="lastName" className="block text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">
                                    Last name
                                </label>
                                <div className="relative">
                                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                        <svg className="h-5 w-5 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                        </svg>
                                    </div>
                                    <input
                                        id="lastName"
                                        name="lastName"
                                        type="text"
                                        autoComplete="family-name"
                                        required
                                        value={lastName}
                                        onChange={(e) => setLastName(e.target.value)}
                                        className="block w-full pl-10 pr-3 py-3 border bg-white dark:bg-slate-800 rounded-xl shadow-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition-all duration-200 hover:border-slate-450 dark:hover:border-slate-500 text-slate-900 dark:text-slate-50 border-slate-200 dark:border-slate-700"
                                        placeholder="Enter your last name"
                                        disabled={isLoading}
                                        data-testid="signup-last-name-input"
                                    />
                                </div>
                            </div>

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
                                        className={`block w-full pl-10 pr-3 py-3 border bg-white dark:bg-slate-800 rounded-xl shadow-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition-all duration-200 hover:border-slate-450 dark:hover:border-slate-500 text-slate-900 dark:text-slate-50 ${
                                            email && !isValidEmail(email) ? 'border-red-300' : 'border-slate-200 dark:border-slate-700'
                                        }`}
                                        placeholder="Enter your email"
                                        disabled={isLoading}
                                        data-testid="signup-email-input"
                                    />
                                </div>
                                {email && !isValidEmail(email) && (
                                    <p className="mt-1.5 text-xs font-semibold text-red-500">Please enter a valid email address</p>
                                )}
                            </div>

                            {/* Password Field */}
                            <div>
                                <SecurePasswordInput
                                    label="Password"
                                    id="password"
                                    name="password"
                                    autoComplete="new-password"
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="Create a password"
                                    disabled={isLoading}
                                    data-testid="signup-password-input"
                                />
                                
                                {/* Reusable Password Strength Indicator */}
                                <PasswordStrengthMeter password={password} />
                            </div>

                            {/* Confirm Password Field */}
                            <SecurePasswordInput
                                label="Confirm Password"
                                id="confirmPassword"
                                name="confirmPassword"
                                autoComplete="new-password"
                                required
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder="Confirm your password"
                                disabled={isLoading}
                                error={confirmPassword && !passwordsMatch ? "Passwords do not match" : undefined}
                                helperText={confirmPassword && passwordsMatch ? "Passwords match" : undefined}
                                data-testid="signup-confirm-password-input"
                            />

                            {/* Error Messages */}
                            {error && (
                                <div className="p-3 bg-red-50 border border-red-200 rounded-xl">
                                    <p className="text-red-600 text-xs font-semibold text-center">{error}</p>
                                </div>
                            )}

                            {/* Sign Up Button */}
                            <Button
                                type="submit"
                                disabled={!isValidEmail(email) || password.length < 8 || !passwordsMatch}
                                isLoading={isLoading}
                                size="lg"
                                className="w-full"
                                data-testid="signup-submit-button"
                            >
                                Create account
                            </Button>
                        </FormGroup>

                        {/* Social Registration Options */}
                        <div className="mt-6">
                            <SocialLogin
                                onSSOClick={() => setIsSSOOpen(true)}
                                disabled={isLoading}
                            />
                        </div>

                        {/* Sign In Link */}
                        <div className="mt-8 text-center border-t border-slate-100 dark:border-slate-600 pt-6">
                            <p className="text-sm font-semibold text-slate-500 dark:text-slate-400">
                                Already have an account?{' '}
                                <button
                                    type="button"
                                    onClick={() => onNavigate('signin')}
                                    className="font-bold text-brand-primary hover:text-brand-primary/80 hover:underline transition-colors"
                                    disabled={isLoading}
                                    data-testid="signup-signin-link"
                                >
                                    Sign in
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

export default SignUpPage;