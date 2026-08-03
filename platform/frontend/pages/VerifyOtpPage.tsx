import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import Card from '../ui/Card';

interface VerifyOtpPageProps {
  onNavigate?: (path: string) => void;
}

const VerifyOtpPage: React.FC<VerifyOtpPageProps> = ({ onNavigate }) => {
  const { token } = useParams<{ token: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const action = searchParams.get('action') || 'email_verification';
  const emailParam = searchParams.get('email');
  
  // For password reset flow, navigate to reset password page after OTP verification
  const _onNavigateForReset = onNavigate || ((path: string) => navigate(path));
  void _onNavigateForReset;

  const [status, setStatus] = useState<'enter-otp' | 'verifying' | 'success' | 'error'>('enter-otp');
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // OTP digits state - one for each digit
  const [otpDigits, setOtpDigits] = useState(['', '', '', '', '', '']);
  
  // Refs for each digit input
  const digitRefs = useRef<(HTMLInputElement | null)[]>([]);
  
  // Resend timer
  const [resendTimer, setResendTimer] = useState(60);
  const [email, _setEmail] = useState(emailParam || '');
  
  // Handle resend timer
  useEffect(() => {
    if (resendTimer > 0) {
      const timer = setTimeout(() => setResendTimer(resendTimer - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendTimer]);

  // Focus first input on mount
  useEffect(() => {
    if (digitRefs.current[0]) {
      digitRefs.current[0].focus();
    }
  }, []);

  // Handle OTP submit for password reset (uses /api/auth/verify-otp-for-password-reset)
  const handlePasswordResetOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const otp = otpDigits.join('');
    
    if (!otp || otp.length !== 6) {
      setError('Please enter the complete 6-digit OTP code');
      return;
    }
    
    if (!token) {
      setError('No verification token found');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/auth/verify-otp-for-password-reset`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json' 
        },
        body: JSON.stringify({ 
          token: token,
          otp: otp
        })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setStatus('success');
        setMessage(data.message || 'OTP verified successfully! Redirecting to reset password page...');
        
        // Store reset token from backend response, or fallback to the current token
        const resetToken = data.data?.reset_token || data.reset_token || token;
        sessionStorage.setItem('password_reset_token', resetToken);
        
        // Wait a moment then redirect to reset password page
        setTimeout(() => {
          navigate('/reset-password');
        }, 1500);
      } else {
        setStatus('error');
        setMessage(data.message || 'Verification failed');
        // Extract error message for wrong OTP
        const errorMessage = data.error?.message || data.message || 'Wrong OTP code';
        setError(errorMessage);
      }
    } catch (err: any) {
      setStatus('error');
      setMessage('Network error. Please try again.');
      setError(err.message || 'Failed to verify OTP');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle input change for digit
  const handleDigitChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return; // Only allow digits
    
    const newOtpDigits = [...otpDigits];
    
    if (value.length > 1) {
      // Handle paste - take first digit
      newOtpDigits[index] = value[0];
      // Fill remaining digits if available
      for (let i = 1; i < value.length && index + i < 6; i++) {
        newOtpDigits[index + i] = value[i];
      }
      // Focus the next input if available
      const nextIndex = Math.min(index + value.length, 5);
      digitRefs.current[nextIndex]?.focus();
    } else {
      newOtpDigits[index] = value;
    }
    
    setOtpDigits(newOtpDigits);
    setError(null); // Clear error on input
    
    // Auto-focus next input
    if (value && index < 5) {
      digitRefs.current[index + 1]?.focus();
    }
  };

  // Handle backspace
  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace') {
      if (!otpDigits[index] && index > 0) {
        // Move to previous input if current is empty
        const newOtpDigits = [...otpDigits];
        newOtpDigits[index - 1] = '';
        setOtpDigits(newOtpDigits);
        digitRefs.current[index - 1]?.focus();
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      digitRefs.current[index - 1]?.focus();
    } else if (e.key === 'ArrowRight' && index < 5) {
      digitRefs.current[index + 1]?.focus();
    }
  };

  // Handle paste
  const handlePaste = (e: React.ClipboardEvent, startIndex: number) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text');
    if (!/^\d+$/.test(pastedData)) return; // Only allow numeric paste
    
    const newOtpDigits = [...otpDigits];
    let pastedIndex = 0;
    
    for (let i = startIndex; i < 6 && pastedIndex < pastedData.length; i++) {
      newOtpDigits[i] = pastedData[pastedIndex];
      pastedIndex++;
    }
    
    setOtpDigits(newOtpDigits);
    setError(null);
    
    // Focus the next empty input or last filled
    const nextIndex = Math.min(startIndex + pastedData.length, 5);
    digitRefs.current[nextIndex]?.focus();
  };

  const handleResendOtp = async () => {
    if (!token || !email) return;
    
    // Call the backend to resend OTP
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/auth/resend-otp`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json' 
        },
        body: JSON.stringify({
          token: token,
          email: email
        })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setMessage(data.message || 'OTP resent successfully. Please check your email.');
        
        // Reset OTP digits
        setOtpDigits(['', '', '', '', '', '']);
        
        // Show success for a moment then redirect to verification page
        setTimeout(() => {
          navigate(`/verify-otp/${token}?email=${encodeURIComponent(email)}&action=${action}`);
        }, 2000);
      } else {
        setError(data.message || 'Failed to resend OTP');
        setMessage('');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to resend OTP');
      setMessage('');
    }
  };

  // OTP Entry Form
  if (status === 'enter-otp') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 py-8 px-4 sm:px-6 lg:px-8">
        <Card className="shadow-xl border-0 bg-white/80 backdrop-blur-sm max-w-md w-full">
          <div className="p-8 text-center">
            {/* Header */}
            <div className="text-center mb-6">
              <div className="mx-auto h-16 w-16 bg-gradient-to-r from-brand-primary to-red-500 rounded-2xl flex items-center justify-center mb-4 shadow-lg">
                <svg className="h-8 w-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50 mb-2">Enter Verification Code</h1>
              <p className="text-slate-600 dark:text-slate-300">We've sent a 6-digit code to your email</p>
              {email && (
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{email}</p>
              )}
            </div>

            <form onSubmit={handlePasswordResetOtpSubmit} className="space-y-6">
              {/* OTP Input - 6 separate digit fields */}
              <div className="flex justify-center gap-2 sm:gap-3 mb-6">
                {otpDigits.map((digit, index) => (
                  <input
                    key={index}
                    ref={(el) => { digitRefs.current[index] = el; }}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleDigitChange(index, e.target.value)}
                    onKeyDown={(e) => handleKeyDown(index, e)}
                    onPaste={(e) => handlePaste(e, index)}
                    className="w-12 h-14 sm:w-14 sm:h-16 border-2 rounded-xl shadow-sm text-center text-lg font-semibold text-slate-900 dark:text-slate-50 focus:outline-none focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/10 transition-all duration-200 bg-white"
                    placeholder="-"
                  />
                ))}
              </div>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-red-600 text-sm">{error}</p>
                </div>
              )}

              {/* Error Messages */}
              {((status as 'enter-otp' | 'verifying' | 'success' | 'error') === 'success' || (status as 'enter-otp' | 'verifying' | 'success' | 'error') === 'error') && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-red-600 text-sm">{message}</p>
                </div>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading || otpDigits.some(d => d === '')}
                className="w-full flex justify-center py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-medium text-white bg-gradient-to-r from-brand-primary to-red-500 hover:from-brand-primary/90 hover:to-red-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-primary/10 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  'Verify Code'
                )}
              </button>

              {/* Resend Link */}
              {token && (
                <div className="text-center">
                  <p className="text-sm text-slate-600 dark:text-slate-300">
                    Didn't receive the code?{' '}
                    <button
                      type="button"
                      onClick={handleResendOtp}
                      disabled={resendTimer > 0}
                      className="font-medium text-brand-primary hover:text-brand-primary/80 transition-colors disabled:opacity-50"
                    >
                      {resendTimer > 0 ? `Resend in ${resendTimer}s` : 'Resend code'}
                    </button>
                  </p>
                </div>
              )}
              
              {/* Timer Reset Effect */}
              {status === 'enter-otp' && resendTimer > 0 && (
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">
                  New OTP sent. You can request another in {resendTimer} seconds.
                </p>
              )}
            </form>

            {/* Back to Sign In Link */}
            <div className="mt-6 text-center">
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => navigate('/signin')}
                  className="font-medium text-brand-primary hover:text-brand-primary/80 transition-colors"
                >
                  Sign in
                </button>
              </p>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-green-50">
        <Card className="text-center p-8 max-w-md">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center text-green-500 mx-auto mb-4">
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-50">Success!</h2>
          <p className="text-green-600 mt-2">{message}</p>
        </Card>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-red-50">
        <Card className="text-center p-8 max-w-md">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center text-red-500 mx-auto mb-4">
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-50">Verification Failed</h2>
          <p className="text-red-600 mt-2">{message}</p>
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
          <button
            onClick={() => navigate('/signin')}
            className="mt-4 bg-brand-primary text-white px-6 py-2 rounded-lg hover:bg-brand-primary/90 transition"
          >
            Try Again
          </button>
        </Card>
      </div>
    );
  }

  // Fallback for any unexpected state
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-700/50">
      <Card className="text-center p-8 max-w-md">
        <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Error</h2>
        <p className="text-slate-600 dark:text-slate-300 mt-2">An unexpected error occurred.</p>
        <button
          onClick={() => navigate('/signin')}
          className="mt-4 bg-brand-primary text-white px-6 py-2 rounded-lg hover:bg-brand-primary/90 transition"
        >
          Back to Sign In
        </button>
      </Card>
    </div>
  );
};

export default VerifyOtpPage;