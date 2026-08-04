import React, { useState, useEffect } from 'react';
import { View } from '../types';
import Card from '../ui/Card';
import OTPInput from '../ui/OTPInput';
import ResendTimer from '../ui/ResendTimer';
import { localAuthService } from '../../services/localAuthService';

interface ForgotPasswordPageProps {
    onNavigate: (view: View) => void;
}

const ForgotPasswordPage: React.FC<ForgotPasswordPageProps> = ({ onNavigate }) => {
    const [email, setEmail] = useState('');
    const [step, setStep] = useState<'email' | 'otp'>('email');
    const [error, setError] = useState<string | null>(null);
    const [message, setMessage] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [otpToken, setOtpToken] = useState<string | null>(null);

    // OTP state
    const [otpDigits, setOtpDigits] = useState<string[]>(['', '', '', '', '', '']);

    // Build the full OTP code from digits
    const otpCode = otpDigits.join('');

    // Email validation
    const isValidEmail = (val: string) => {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
    };

    // Reset OTP digits when switching to OTP screen
    useEffect(() => {
        if (step === 'otp') {
            setOtpDigits(['', '', '', '', '', '']);
        }
    }, [step]);

    // Step 1: Send OTP to email
    const handleSendOtp = async (e: React.FormEvent) => {
        e.preventDefault();
        setMessage(null);
        setError(null);
        setIsLoading(true);

        if (!isValidEmail(email)) {
            setError('Please enter a valid email address');
            setIsLoading(false);
            return;
        }

        try {
            const result = await localAuthService.requestPasswordResetOTP(email);

            if (result.token) {
                setOtpToken(result.token);
                setStep('otp');
                setMessage('OTP verification code sent successfully. Please check your email inbox.');
            } else if (result.message) {
                setStep('otp');
                setMessage(result.message);
            }
        } catch (err: any) {
            setError(err.message || 'Failed to send OTP email.');
        } finally {
            setIsLoading(false);
        }
    };

    // Step 2: Verify OTP and navigate to reset password
    const handleVerifyOtp = async () => {
        if (otpCode.length !== 6) {
            setError('Please enter the complete 6-digit OTP code');
            return;
        }

        if (!otpToken) {
            setError('Verification session token is not available. Please request a new password reset.');
            return;
        }

        setError(null);
        setIsLoading(true);

        try {
            const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

            const response = await fetch(`${baseUrl}/api/auth/verify-otp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: otpToken }),
            });

            const result = await response.json();

            if (response.ok && result.success) {
                // Store token and email for the reset password page
                const fullToken = result.data?.otp_token || otpToken;
                sessionStorage.setItem('password_reset_token', encodeURIComponent(fullToken));
                sessionStorage.setItem('reset_password_email', email);

                // Navigate to reset password page with token in URL
                window.history.pushState(
                    { fromForgotPassword: true },
                    '',
                    `/reset-password?token=${encodeURIComponent(fullToken)}&email=${encodeURIComponent(email)}`
                );
                
                // Triggers App's routing system to move to reset-password
                onNavigate('reset-password');
            } else {
                setError(result.error?.message || result.message || 'OTP verification failed.');
            }
        } catch (err: any) {
            setError(err.message || 'OTP verification failed.');
        } finally {
            setIsLoading(false);
        }
    };

    // Resend OTP
    const handleResendOtp = async () => {
        if (!email) return;

        setError(null);
        try {
            const result = await localAuthService.requestPasswordResetOTP(email);

            if (result.token) {
                setOtpToken(result.token);
                setMessage('A new verification code has been sent to your email.');
            } else if (result.message) {
                setMessage(result.message);
            }
        } catch (err: any) {
            setError(err.message || 'Failed to resend verification code.');
        }
    };

    // Back to email step
    const handleBackToEmail = () => {
        setStep('email');
        setError(null);
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 py-8 px-4 sm:px-6 lg:px-8" data-testid="forgot-password-page">
            <div className="max-w-md w-full">
                {/* Header */}
                <div className="text-center mb-8">
                    <button
                        type="button"
                        onClick={() => onNavigate('landing')}
                        title="Go to home"
                        aria-label="Go to home"
                        className="mx-auto h-16 w-16 bg-brand-primary rounded-2xl flex items-center justify-center mb-6 shadow-lg hover:bg-brand-primary/90 transition-colors duration-200 focus:outline-none focus:ring-4 focus:ring-brand-primary/20"
                    >
                        <svg className="h-8 w-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                        </svg>
                    </button>
                    <h1 className="text-3xl font-extrabold text-slate-900 dark:text-slate-50 tracking-tight mb-2">
                        {step === 'email' ? 'Reset your password' : 'Enter verification code'}
                    </h1>
                    <p className="text-slate-600 dark:text-slate-300 font-medium">
                        {step === 'email'
                            ? 'Enter your email and we\'ll send you a code to reset your password'
                            : `We've sent a 6-digit verification code to your email inbox`}
                    </p>
                </div>

                {/* Auth Card */}
                <Card className="shadow-2xl border-0 bg-white dark:bg-slate-800">
                    <div className="p-6 sm:p-8">
                        {step === 'email' ? (
                            /* Email form step */
                            <form onSubmit={handleSendOtp} className="space-y-6">
                                {/* Email Field */}
                                <div>
                                    <label htmlFor="email" className="block text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">
                                        Email address
                                    </label>
                                    <div className="relative">
                                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                            <svg className="h-5 w-5 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
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
                                            className={`block w-full pl-10 pr-3 py-3 border rounded-xl shadow-sm placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-4 focus:ring-brand-primary/20 focus:border-brand-primary transition-all duration-200 text-slate-900 dark:text-slate-50 ${
                                                email && !isValidEmail(email) ? 'border-red-300' : 'border-slate-200 dark:border-slate-600'
                                            }`}
                                            placeholder="Enter your email address"
                                            disabled={isLoading}
                                            data-testid="forgot-password-email-input"
                                        />
                                    </div>
                                    {email && !isValidEmail(email) && (
                                        <p className="mt-1.5 text-xs font-semibold text-red-500">Please enter a valid email address</p>
                                    )}
                                </div>

                                {/* Messages & Errors */}
                                {error && (
                                    <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-center">
                                        <p className="text-red-600 text-xs font-semibold">{error}</p>
                                    </div>
                                )}

                                {message && (
                                    <div className="p-3 bg-green-50 border border-green-200 rounded-xl text-center">
                                        <p className="text-green-700 text-xs font-semibold">{message}</p>
                                    </div>
                                )}

                                {/* Send OTP Button */}
                                <button
                                    type="submit"
                                    disabled={isLoading || !isValidEmail(email)}
                                    className="w-full flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-xl shadow-lg text-sm font-bold text-white bg-brand-primary hover:bg-brand-primary/90 focus:outline-none focus:ring-4 focus:ring-brand-primary/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed transform hover:-translate-y-0.5 active:translate-y-0"
                                    data-testid="forgot-password-submit-button"
                                >
                                    {isLoading ? (
                                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                    ) : (
                                        <>
                                            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                                            </svg>
                                            Send Verification Code
                                        </>
                                    )}
                                </button>

                                {/* Back to Login Link */}
                                <div className="mt-8 text-center border-t border-slate-100 dark:border-slate-600 pt-6">
                                    <p className="text-sm font-semibold text-slate-500 dark:text-slate-400">
                                        Remember your password?{' '}
                                        <button
                                            type="button"
                                            onClick={() => onNavigate('signin')}
                                            className="font-bold text-brand-primary hover:text-brand-primary/80 hover:underline transition-colors duration-200"
                                            disabled={isLoading}
                                            data-testid="forgot-password-signin-link"
                                        >
                                            Sign in
                                        </button>
                                    </p>
                                </div>
                            </form>
                        ) : (
                            /* OTP verification step */
                            <div className="space-y-6">
                                {/* Back to email link */}
                                <button
                                    type="button"
                                    onClick={handleBackToEmail}
                                    className="flex items-center gap-1.5 text-sm font-semibold text-slate-500 dark:text-slate-400 hover:text-brand-primary transition-colors"
                                >
                                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                                    </svg>
                                    Not <span className="text-slate-700 dark:text-slate-200 font-bold">{email}</span>? Change email
                                </button>

                                {/* Reusable OTPInput component */}
                                <div>
                                    <label htmlFor="otp" className="block text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-3 text-center">
                                        6-digit Verification Code
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
                                <button
                                    type="button"
                                    onClick={handleVerifyOtp}
                                    disabled={isLoading || otpCode.length !== 6}
                                    className="w-full flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-xl shadow-lg text-sm font-bold text-white bg-brand-primary hover:bg-brand-primary/90 focus:outline-none focus:ring-4 focus:ring-brand-primary/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed transform hover:-translate-y-0.5 active:translate-y-0"
                                    data-testid="forgot-password-verify-button"
                                >
                                    {isLoading ? (
                                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                    ) : (
                                        'Verify Code & Continue'
                                    )}
                                </button>

                                {/* Reusable ResendTimer */}
                                <ResendTimer
                                    initialSeconds={60}
                                    onResend={handleResendOtp}
                                    disabled={isLoading}
                                />

                                {/* Back to Login Link */}
                                <div className="mt-6 text-center border-t border-slate-100 dark:border-slate-600 pt-6">
                                    <p className="text-sm font-semibold text-slate-500 dark:text-slate-400">
                                        Remember your password?{' '}
                                        <button
                                            type="button"
                                            onClick={() => onNavigate('signin')}
                                            className="font-bold text-brand-primary hover:text-brand-primary/80 hover:underline transition-colors duration-200"
                                            disabled={isLoading}
                                        >
                                            Sign in
                                        </button>
                                    </p>
                                </div>
                            </div>
                        )}
                    </div>
                </Card>
            </div>
        </div>
    );
};

export default ForgotPasswordPage;
