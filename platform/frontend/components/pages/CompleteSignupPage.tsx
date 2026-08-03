// Ensure you have: npm install react-router-dom
import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiClient } from '../../services/apiClient';
import Button from '../ui/Button';
import Input from '../ui/Input';

const CompleteSignupPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [mode, setMode] = useState<string | null>(null);
  const [oobCode, setOobCode] = useState<string | null>(null);
  const [email, setEmail] = useState<string>('');
  const [token, setToken] = useState<string>('');
  const [status, setStatus] = useState<'verifying' | 'verified' | 'error' | 'setPassword' | 'passwordSet' | 'validating' | 'tokenValid'>('verifying');
  const [error, setError] = useState<string | null>(null);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [userInfo, setUserInfo] = useState<any>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const modeParam = searchParams.get('mode');
    const oobCodeParam = searchParams.get('oobCode');
    const emailParam = searchParams.get('email');
    const tokenParam = searchParams.get('token');

    setMode(modeParam);
    setOobCode(oobCodeParam);
    setEmail(emailParam || '');
    setToken(tokenParam || '');
  }, [searchParams]);

  useEffect(() => {
    if (mode === 'invite' && email && token) {
      // Handle invitation flow
      validateInvitationToken();
    } else if (oobCode) {
      // Handle existing email verification flow
      handleEmailVerification();
    }
  }, [mode, oobCode, email, token]);

  const validateInvitationToken = async () => {
    setStatus('validating');
    setError(null);

    try {
      const response = await apiClient.post('/api/auth/validate-invitation', {
        email,
        token
      });

      if ((response.data as any).valid) {
        setUserInfo((response.data as any).user);
        setStatus('tokenValid');
        setTimeout(() => setStatus('setPassword'), 1000);
      } else {
        setError('Invalid invitation token');
        setStatus('error');
      }
    } catch (err: any) {
      console.error('Token validation error:', err);
      setError(err.response?.data?.detail || 'Failed to validate invitation token');
      setStatus('error');
    }
  };

  const handleEmailVerification = () => {
    // Email verification and password reset are now handled by the backend
    if (mode === 'verifyEmail') {
      // For email verification, the backend should handle this via email links
      setStatus('verified');
      setTimeout(() => setStatus('setPassword'), 1000);
    } else if (mode === 'resetPassword') {
      // For password reset, the backend should validate the token
      setStatus('setPassword');
    }
  };

  const handleSetPassword = async (e: React.FormEvent) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    setError(null);
    setStatus('verifying');

    try {
      if (mode === 'invite') {
        // Handle invitation password setup
        const response = await apiClient.post('/api/auth/complete-signup', {
          email,
          token,
          password
        });

        if ((response.data as any).success) {
          setStatus('passwordSet');
          toast.success('Password set successfully! You can now sign in.');
          setTimeout(() => navigate('/signin'), 2000);
        } else {
          setError('Failed to set password. Please try again.');
          setStatus('setPassword');
        }
      } else {
        // Handle existing password reset flow via backend
        const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        fetch(`${baseUrl}/api/auth/reset-password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: oobCode, password })
        })
          .then(response => response.json())
          .then(data => {
            if (data.success) {
              setStatus('passwordSet');
              setTimeout(() => navigate('/signin'), 2000);
            } else {
              setError(data.message || 'Failed to reset password');
              setStatus('setPassword');
            }
          })
          .catch(err => {
            console.error('Password reset error:', err);
            setError('Failed to reset password. Please try again.');
            setStatus('setPassword');
          });
      }
    } catch (err: any) {
      console.error('Password setup error:', err);
      setError(err.response?.data?.detail || 'Failed to set password. Try again.');
      setStatus('setPassword');
    }
  };

  const renderInvitationHeader = () => (
    <div className="text-center mb-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Welcome to Iacgenie!</h1>
      <p className="text-gray-600">Complete your registration to get started</p>
      {userInfo && (
        <div className="mt-4 p-4 bg-blue-50 rounded-lg">
          <p className="text-sm text-blue-800">
            <strong>Email:</strong> {userInfo.email}<br />
            <strong>Role:</strong> {userInfo.role}<br />
            <strong>Status:</strong> {userInfo.status}
          </p>
        </div>
      )}
    </div>
  );

  const renderPasswordForm = () => (
    <form onSubmit={handleSetPassword} className="space-y-6">
      <div>
        <Input
          id="password"
          label="Set Password"
          type="password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          placeholder="Enter your password"
          required
          minLength={8}
        />
        <p className="text-xs text-gray-500 mt-1">Password must be at least 8 characters long</p>
      </div>

      <div>
        <Input
          id="confirmPassword"
          label="Confirm Password"
          type="password"
          value={confirmPassword}
          onChange={e => setConfirmPassword(e.target.value)}
          placeholder="Confirm your password"
          required
        />
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      <Button
        type="submit"
        variant="primary"
        className="w-full"
        disabled={status === 'verifying'}
      >
        {status === 'verifying' ? 'Setting Password...' : 'Set Password & Complete Registration'}
      </Button>
    </form>
  );

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          {mode === 'invite' && renderInvitationHeader()}

          {status === 'verifying' && (
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Verifying your email...</p>
            </div>
          )}

          {status === 'validating' && (
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Validating invitation token...</p>
            </div>
          )}

          {status === 'verified' && (
            <div className="text-center">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-green-600 font-medium">Email verified! Redirecting...</p>
            </div>
          )}

          {status === 'tokenValid' && (
            <div className="text-center">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-green-600 font-medium">Invitation validated! Setting up your account...</p>
            </div>
          )}

          {status === 'error' && (
            <div className="text-center">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <p className="text-red-600 font-medium">{error}</p>
              <Button
                variant="secondary"
                className="mt-4"
                onClick={() => navigate('/signin')}
              >
                Go to Sign In
              </Button>
            </div>
          )}

          {status === 'setPassword' && renderPasswordForm()}

          {status === 'passwordSet' && (
            <div className="text-center">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-green-600 font-medium">Password set successfully!</p>
              <p className="text-gray-600 mt-2">Redirecting to sign in...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CompleteSignupPage; 